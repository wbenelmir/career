# applications/views.py
import io
import os

from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST
from django.shortcuts import render, redirect, get_object_or_404

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from locations.models import Commune
from root.models import Poste
from documents.models import ApplicationDocument
from tracking.models import ApplicationTracking

from .models import ApplicationChoice
from .forms import ApplicationForm, CandidateProfileForm, MotivationForm
from .models import Application, ApplicationChoice, CandidateProfile
from .pdf_utils import register_arabic_font, rtl_text, ARABIC_FONT_NAME
from .utils import build_tracking_url, generate_qr_base64, generate_qr_png_bytes
from notifications.tasks import (
    send_application_submitted_email_task,
    send_admin_new_application_email_task,
)
from .services import ApplicationWorkflowService

def _get_selected_postes_from_session(request):
    ids = request.session.get("selected_poste_ids", [])
    if not ids:
        return []

    today = timezone.localdate()

    return list(
        Poste.objects.filter(
            id__in=[i for i in ids if i],
            is_open=True
        ).filter(
            Q(deadline__isnull=True) | Q(deadline__gte=today)
        )
    )

def _validate_uploaded_document(uploaded_file, requirement):
    extension = os.path.splitext(uploaded_file.name.lower())[1].lstrip('.')

    allowed_extensions = requirement.get_allowed_extensions_list()
    if allowed_extensions and extension not in allowed_extensions:
        allowed_display = ", ".join(ext.upper() for ext in allowed_extensions)
        raise ValidationError(
            f"صيغة الملف غير مدعومة. الصيغ المقبولة لهذه الوثيقة: {allowed_display}."
        )

    max_size_bytes = requirement.max_file_size_mb * 1024 * 1024
    if uploaded_file.size > max_size_bytes:
        raise ValidationError(
            f"حجم الملف يتجاوز الحد الأقصى المسموح به ({requirement.max_file_size_mb}MB)."
        )


def communes_by_wilaya(request):
    wilaya_id = request.GET.get("wilaya_id")
    communes = []

    if wilaya_id:
        communes = list(
            Commune.objects.filter(wilaya_id=wilaya_id)
            .order_by("name_ar")
            .values("id", "name_ar")
        )

    return JsonResponse({"communes": communes})


def _get_selected_poste_from_session(request):
    poste_id = request.session.get("selected_poste_id")
    if not poste_id:
        return None

    today = timezone.localdate()
    return Poste.objects.filter(
        id=poste_id,
        is_open=True
    ).filter(
        Q(deadline__isnull=True) | Q(deadline__gte=today)
    ).first()


def _get_candidate_from_session(request):
    candidate_id = request.session.get("candidate_id")
    if not candidate_id:
        return None
    return CandidateProfile.objects.filter(id=candidate_id).first()


def _get_draft_application_from_session(request):
    application_id = request.session.get("draft_application_id")
    if not application_id:
        return None

    return (
        Application.objects
        .select_related("candidate", "poste")
        .prefetch_related("documents__document_type")
        .filter(id=application_id)
        .first()
    )


def _get_or_create_draft_application(poste, candidate, request=None):
    try:
        application, created = Application.objects.get_or_create(
            poste=poste,
            candidate=candidate,
            defaults={"status": Application.Status.DRAFT}
        )
    except IntegrityError:
        application = Application.objects.get(poste=poste, candidate=candidate)
        created = False

    # If we just created the application and have a request context, we can initialize the application choices based on the selected postes in the session
    if created and request:
        selected_ids = request.session.get("selected_poste_ids", [])

        for index, poste_id in enumerate(selected_ids, start=1):
            if not poste_id:
                continue

            ApplicationChoice.objects.create(
                application=application,
                poste_id=poste_id,
                priority=index
            )

    return application

def _clear_application_session(request):
    request.session.pop("selected_poste_id", None)
    request.session.pop("selected_poste_ids", None)
    request.session.pop("candidate_id", None)
    request.session.pop("draft_application_id", None)


def _build_uploaded_documents(application):
    requirements = application.poste.document_requirements.filter(
        is_active=True
    ).select_related("document_type").order_by("display_order", "id")

    uploaded_map = {
        doc.document_type_id: doc
        for doc in application.documents.select_related("document_type")
    }

    rows = []
    for requirement in requirements:
        uploaded = uploaded_map.get(requirement.document_type_id)

        rows.append({
            "id": requirement.document_type_id,
            "requirement_id": requirement.id,
            "label": requirement.document_type.name,
            "description": requirement.help_text or requirement.document_type.description or "",
            "is_required": requirement.is_required,
            "is_uploaded": uploaded is not None,
            "file_name": (
                uploaded.original_filename
                if uploaded and uploaded.original_filename
                else (os.path.basename(uploaded.file.name) if uploaded and uploaded.file else "")
            ),
            "file_url": uploaded.file.url if uploaded and uploaded.file else "",
            "allowed_extensions": requirement.get_allowed_extensions_list(),
            "allowed_extensions_display": ", ".join(
                ext.upper() for ext in requirement.get_allowed_extensions_list()
            ),
            "max_file_size_mb": requirement.max_file_size_mb,
        })

    return rows


def _get_missing_required_document_labels(application):
    uploaded_documents = _build_uploaded_documents(application)
    missing_documents = [
        doc["label"]
        for doc in uploaded_documents
        if doc["is_required"] and not doc["is_uploaded"]
    ]
    return uploaded_documents, missing_documents


def _attach_current_documents_to_requirements(requirements, uploaded_documents):
    uploaded_map = {doc["id"]: doc for doc in uploaded_documents}

    for requirement in requirements:
        requirement.current_doc = uploaded_map.get(requirement.document_type_id)

    return requirements


def _build_candidate_summary(candidate):
    return [
        {"label": "الاسم", "value": getattr(candidate, "first_name", "") or "—"},
        {"label": "اللقب", "value": getattr(candidate, "last_name", "") or "—"},
        {
            "label": "الجنس",
            "value": candidate.get_gender_display() if getattr(candidate, "gender", None) else "—"
        },
        {
            "label": "تاريخ الميلاد",
            "value": candidate.date_of_birth.strftime("%d / %m / %Y")
            if getattr(candidate, "date_of_birth", None) else "—"
        },
        {"label": "مكان الميلاد", "value": getattr(candidate, "place_of_birth", "") or "—"},
        {"label": "رقم التعريف الوطني", "value": getattr(candidate, "national_id_number", "") or "—"},
        {"label": "البريد الإلكتروني", "value": getattr(candidate, "email", "") or "—"},
        {"label": "رقم الهاتف", "value": getattr(candidate, "phone_number", "") or "—"},
        {
            "label": "ولاية الإقامة",
            "value": getattr(candidate.wilaya, "name_ar", "—") if getattr(candidate, "wilaya", None) else "—"
        },
        {
            "label": "البلدية",
            "value": getattr(candidate.commune, "name_ar", "—") if getattr(candidate, "commune", None) else "—"
        },
        {"label": "العنوان", "value": getattr(candidate, "address", "") or "—"},
        {"label": "الإدارة الحالية", "value": getattr(candidate, "current_administration", "") or "—"},
        {"label": "الرتبة الحالية", "value": getattr(candidate, "current_position_grade", "") or "—"},
        {"label": "الوظيفة الحالية", "value": getattr(candidate, "current_function", "") or "—"},
        {
            "label": "تاريخ قرار الترسيم",
            "value": candidate.tenure_decision_date.strftime("%d / %m / %Y")
            if getattr(candidate, "tenure_decision_date", None) else "—"
        },
        {"label": "سنوات الأقدمية", "value": getattr(candidate, "years_of_seniority", "—")},
        {"label": "سنوات الخدمة الفعلية", "value": getattr(candidate, "years_of_effective_service", "—")},
    ]


def start_application(request, slug=None):
    selected_poste = None
    is_slug_locked = False
    today = timezone.localdate()

    open_postes_qs = Poste.objects.filter(
        is_open=True
    ).filter(
        Q(deadline__isnull=True) | Q(deadline__gte=today)
    )

    # =========================
    # SLUG MODE
    # =========================
    if slug:
        selected_poste = get_object_or_404(open_postes_qs, slug=slug)
        is_slug_locked = True

    has_open_postes = open_postes_qs.exists()

    # =========================
    # POST
    # =========================
    if request.method == "POST":
        form = ApplicationForm(request.POST)

        if form.is_valid():

            # FIX: slug mode handling
            if is_slug_locked and selected_poste:
                poste_1 = selected_poste
                poste_2 = form.cleaned_data.get("poste_2")
                poste_3 = form.cleaned_data.get("poste_3")
            else:
                poste_1 = form.cleaned_data.get("poste_1")
                poste_2 = form.cleaned_data.get("poste_2")
                poste_3 = form.cleaned_data.get("poste_3")

            selected_postes = [
                poste_1.id if poste_1 else None,
                poste_2.id if poste_2 else None,
                poste_3.id if poste_3 else None,
            ]

            # save in session
            request.session["selected_poste_ids"] = selected_postes
            request.session["selected_poste_id"] = poste_1.id

            # reset flow
            request.session.pop("candidate_id", None)
            request.session.pop("draft_application_id", None)

            return redirect("applications:candidate_information")

    # =========================
    # GET
    # =========================
    else:
        initial = {}

        # 🔥 FIX: pre-fill poste_1 instead of poste
        if selected_poste:
            initial["poste_1"] = selected_poste

        form = ApplicationForm(initial=initial)

    # =========================
    # SUBTITLE
    # =========================
    if not has_open_postes and not selected_poste:
        page_subtitle = "لا توجد وظائف أو مناصب مفتوحة حاليًا للتقديم."
    elif selected_poste:
        page_subtitle = "تم تحديد المنصب مسبقًا. راجع المعلومات ثم واصل إلى المرحلة التالية."
    else:
        page_subtitle = "اختر الوظيفة أو المنصب الذي تريد الترشح له ثم اضغط على متابعة الترشح."

    context = {
        "form": form,
        "selected_poste": selected_poste,
        "has_open_postes": has_open_postes,
        "is_slug_locked": is_slug_locked,
        "page_title": "بدء الترشح",
        "page_subtitle": page_subtitle,
    }

    return render(request, "public/applications/start_application.html", context)


def candidate_information(request):

    # =========================
    # GET SELECTED POSTE
    # =========================
    selected_poste = _get_selected_poste_from_session(request)

    if not selected_poste:
        messages.warning(request, "يرجى اختيار الوظيفة أو المنصب أولًا.")
        return redirect("applications:start_application")

    # =========================
    # POST
    # =========================
    if request.method == "POST":
        form = CandidateProfileForm(request.POST)

        if form.is_valid():
            national_id_number = form.cleaned_data.get("national_id_number")

            # =========================
            # CHECK ACTIVE APPLICATION
            # =========================
            active_applications = Application.objects.select_related("candidate").filter(
                candidate__national_id_number=national_id_number,
                status__in=[
                    Application.Status.SUBMITTED,
                    Application.Status.UNDER_REVIEW,
                    Application.Status.PRESELECTED,
                    Application.Status.INTERVIEW_SCHEDULED,
                    Application.Status.INTERVIEW_COMPLETED,
                ]
            )

            if active_applications.exists():
                active_application = active_applications.first()

                messages.error(
                    request,
                    "لديك طلب ترشح نشط (قيد الدراسة أو المعالجة). "
                    "يرجى انتظار نتيجة الطلب الحالي قبل تقديم طلب جديد."
                )

                return redirect(
                    "tracking:tracking_result_direct",
                    tracking_code=active_application.tracking_code
                )

            # =========================
            # SAVE CANDIDATE (SAFE)
            # =========================
            with transaction.atomic():
                candidate = form.save()

            request.session["candidate_id"] = candidate.id
            request.session.pop("draft_application_id", None)

            return redirect("applications:motivation_step")

    # =========================
    # GET
    # =========================
    else:
        form = CandidateProfileForm()

    # =========================
    # COMMUNE LOGIC
    # =========================
    selected_commune_id = ""

    if request.method == "POST":
        selected_commune_id = request.POST.get("commune", "")
    elif getattr(form.instance, "commune_id", None):
        selected_commune_id = form.instance.commune_id

    # =========================
    # CONTEXT
    # =========================
    context = {
        "form": form,
        "selected_poste": selected_poste,
        "communes_api_url": reverse("applications:communes_by_wilaya"),
        "selected_commune_id": selected_commune_id,
        "page_title": "المعلومات الشخصية والمهنية",
        "page_subtitle": "يرجى تعبئة البيانات المطلوبة بدقة قبل متابعة الترشح.",
    }

    return render(request, "public/applications/candidate_information.html", context)

def motivation_step(request):
    selected_poste = _get_selected_poste_from_session(request)
    candidate = _get_candidate_from_session(request)

    if not selected_poste or not candidate:
        messages.warning(request, "يرجى استكمال المراحل السابقة أولًا.")
        return redirect("applications:start_application")

    application = _get_or_create_draft_application(
        poste=selected_poste,
        candidate=candidate,
        request=request
    )

    if request.method == "POST":
        form = MotivationForm(request.POST)

        if form.is_valid():
            application.motivation_text = form.cleaned_data["motivation_text"]
            application.save()

            request.session["draft_application_id"] = application.id

            return redirect("applications:upload_documents")
    else:
        form = MotivationForm(initial={
            "motivation_text": application.motivation_text
        })

    context = {
        "form": form,
        "selected_poste": selected_poste,
        "page_title": "الرسالة التحفيزية",
        "page_subtitle": "اكتب رسالة تبرز دوافعك وأسباب ترشحك.",
    }

    return render(request, "public/applications/motivation.html", context)

@require_http_methods(["GET", "POST"])
def upload_documents(request):
    selected_poste = _get_selected_poste_from_session(request)
    candidate = _get_candidate_from_session(request)

    if not selected_poste or not candidate:
        messages.warning(request, "يرجى استكمال المراحل السابقة أولًا.")
        return redirect("applications:start_application")

    application = _get_or_create_draft_application(
        poste=selected_poste,
        candidate=candidate,
        request=request
    )

    allowed_statuses = [
        Application.Status.DRAFT,
        Application.Status.INCOMPLETE,
    ]

    if application.status not in allowed_statuses:

        messages.warning(
            request,
            "لا يمكن تعديل الوثائق في الحالة الحالية."
        )

        return redirect(
            "tracking:tracking_result",
            tracking_code=application.tracking_code,
        )

    request.session["draft_application_id"] = application.id

    requirements = list(
        selected_poste.document_requirements.filter(
            is_active=True
        ).select_related("document_type").order_by("display_order", "id")
    )

    if request.method == "POST":
        uploaded_any = False

        for requirement in requirements:
            file_key = f"document_{requirement.document_type.id}"
            uploaded_file = request.FILES.get(file_key)

            if not uploaded_file:
                continue

            _validate_uploaded_document(uploaded_file, requirement)

            ApplicationDocument.objects.update_or_create(
                application=application,
                document_type=requirement.document_type,
                defaults={
                    "file": uploaded_file,
                    "original_filename": uploaded_file.name,
                }
            )
            uploaded_any = True

        uploaded_documents, missing_documents = _get_missing_required_document_labels(application)
        requirements = _attach_current_documents_to_requirements(requirements, uploaded_documents)

        if uploaded_any:
            messages.success(request, "تم حفظ الملفات المختارة بنجاح.")
        else:
            messages.info(request, "لم يتم اختيار ملفات جديدة.")

        if missing_documents:
            messages.warning(
                request,
                "تم حفظ ما تم رفعه، لكن ما تزال هناك وثائق مطلوبة غير مكتملة."
            )
            context = {
                "application": application,
                "selected_poste": selected_poste,
                "requirements": requirements,
                "uploaded_documents": uploaded_documents,
                "missing_documents": missing_documents,
                "single_upload_url": reverse("applications:upload_single_document"),
                "page_title": "رفع الوثائق",
                "page_subtitle": "يمكنك اختيار كل ملف ثم رفعه مباشرة.",
            }
            return render(request, "public/applications/upload_documents.html", context)

        return redirect("applications:review_application")

    uploaded_documents, missing_documents = _get_missing_required_document_labels(application)
    requirements = _attach_current_documents_to_requirements(requirements, uploaded_documents)

    context = {
        "application": application,
        "selected_poste": selected_poste,
        "requirements": requirements,
        "uploaded_documents": uploaded_documents,
        "missing_documents": missing_documents,
        "single_upload_url": reverse("applications:upload_single_document"),
        "page_title": "رفع الوثائق",
        "page_subtitle": "يمكنك اختيار كل ملف ثم رفعه مباشرة.",
    }
    return render(request, "public/applications/upload_documents.html", context)


@require_POST
def upload_single_document(request):
    selected_poste = _get_selected_poste_from_session(request)
    candidate = _get_candidate_from_session(request)

    if not selected_poste or not candidate:
        return JsonResponse(
            {"success": False, "message": "يرجى استكمال المراحل السابقة أولًا."},
            status=400
        )

    application = _get_or_create_draft_application(
        poste=selected_poste,
        candidate=candidate,
        request=request
    )

    if application.status != Application.Status.DRAFT:
        return JsonResponse(
            {"success": False, "message": "لا يمكن تعديل الوثائق بعد إرسال الطلب."},
            status=400
        )

    request.session["draft_application_id"] = application.id

    document_type_id = request.POST.get("document_type_id")
    uploaded_file = request.FILES.get("file")

    if not document_type_id:
        return JsonResponse(
            {"success": False, "message": "نوع الوثيقة غير محدد."},
            status=400
        )

    if not uploaded_file:
        return JsonResponse(
            {"success": False, "message": "لم يتم إرسال أي ملف."},
            status=400
        )

    requirement = selected_poste.document_requirements.filter(
        is_active=True,
        document_type_id=document_type_id
    ).select_related("document_type").first()

    if not requirement:
        return JsonResponse(
            {"success": False, "message": "الوثيقة المطلوبة غير مرتبطة بهذا المنصب."},
            status=404
        )

    try:
        _validate_uploaded_document(uploaded_file, requirement)

        ApplicationDocument.objects.update_or_create(
            application=application,
            document_type=requirement.document_type,
            defaults={
                "file": uploaded_file,
                "original_filename": uploaded_file.name,
            }
        )

        uploaded_documents, missing_documents = _get_missing_required_document_labels(application)

        return JsonResponse({
            "success": True,
            "message": "تم رفع الملف بنجاح.",
            "document_type_id": int(document_type_id),
            "file_name": uploaded_file.name,
            "missing_documents": missing_documents,
            "missing_count": len(missing_documents),
            "is_complete": len(missing_documents) == 0,
        })

    except ValidationError as exc:
        message = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
        return JsonResponse(
            {"success": False, "message": message},
            status=400
        )

    except Exception:
        return JsonResponse(
            {"success": False, "message": "حدث خطأ أثناء رفع الملف."},
            status=500
        )


def review_application(request):
    application = _get_draft_application_from_session(request)

    if not application or application.status != Application.Status.DRAFT:
        messages.warning(request, "لا يوجد ملف جاهز للمراجعة.")
        return redirect("applications:start_application")

    uploaded_documents, missing_documents = _get_missing_required_document_labels(application)
    is_complete = len(missing_documents) == 0
    candidate_summary = _build_candidate_summary(application.candidate)

    choices = application.get_ordered_choices()

    context = {
        "application": application,
        "candidate_summary": candidate_summary,
        "uploaded_documents": uploaded_documents,
        "missing_documents": missing_documents,
        "is_complete": is_complete,
        "choices": choices,
        "primary_poste": application.get_primary_poste(),
        "page_title": "مراجعة الطلب",
        "page_subtitle": "راجع معلوماتك بعناية قبل الإرسال.",
    }

    return render(request, "public/applications/review_application.html", context)


@require_POST
def submit_application(request):
    application = _get_draft_application_from_session(request)

    if not application:
        messages.warning(request, "لا يوجد طلب جاهز للإرسال.")
        return redirect("applications:start_application")

    if application.status != Application.Status.DRAFT:
        messages.warning(request, "تم إرسال هذا الطلب مسبقًا.")
        return redirect("applications:start_application")

    # NEW: enforce motivation
    if not application.motivation_text:
        messages.error(request, "يجب إدخال الرسالة التحفيزية قبل إرسال الطلب.")
        return redirect("applications:motivation_step")

    # existing validation
    if not application.has_all_required_documents():
        missing_required = application.get_missing_required_documents()

        if missing_required.exists():
            missing_names = ", ".join(missing_required.values_list("name", flat=True))
            messages.error(
                request,
                f"لا يمكن الإرسال حتى يتم رفع جميع الوثائق المطلوبة: {missing_names}"
            )
        else:
            messages.error(
                request,
                "لا يمكن الإرسال حتى يتم رفع جميع الوثائق المطلوبة."
            )

        return redirect("applications:review_application")

    if application.status == Application.Status.INCOMPLETE:

        unresolved_requests = (
            application.completion_requests.filter(
                is_resolved=False
            )
        )

        unresolved_requests.update(
            is_resolved=True,
            resolved_at=timezone.now(),
        )

        ApplicationTracking.objects.create(
            application=application,
            status=Application.Status.SUBMITTED,
            note=(
                "تمت إعادة إرسال الملف بعد استكمال "
                "الوثائق أو المعلومات المطلوبة."
            ),
            is_visible_to_candidate=True,
        )

    ApplicationWorkflowService.submit_application(
        application
    )

    base_url = request.build_absolute_uri("/").rstrip("/")
    send_application_submitted_email_task.delay(application.id, base_url)
    send_admin_new_application_email_task.delay(application.id)

    tracking_code = application.tracking_code
    _clear_application_session(request)

    return redirect("applications:application_success", tracking_code=tracking_code)

def application_success(request, tracking_code):
    application = get_object_or_404(Application, tracking_code=tracking_code)

    tracking_url = build_tracking_url(request, application.tracking_code)
    qr_code_base64 = generate_qr_base64(tracking_url)

    choices = application.get_ordered_choices()

    context = {
        "application": application,
        "application_number": application.application_number,
        "tracking_code": application.tracking_code,
        "primary_poste": application.get_primary_poste(),
        "choices": choices,
        "tracking_url": tracking_url,
        "qr_code_base64": qr_code_base64,
        "page_title": "تم إرسال الطلب بنجاح",
        "page_subtitle": "احتفظ برمز التتبع.",
    }

    return render(request, "public/applications/application_success.html", context)


def download_receipt_pdf(request, tracking_code):
    application = get_object_or_404(Application, tracking_code=tracking_code)

    register_arabic_font()

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="receipt_{application.application_number}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    green = (0.11, 0.64, 0.51)
    light_green = (0.97, 0.99, 0.98)
    border = (0.84, 0.90, 0.87)
    text_gray = (0.35, 0.35, 0.35)

    def set_stroke_rgb(color_tuple):
        p.setStrokeColorRGB(*color_tuple)

    def set_fill_rgb(color_tuple):
        p.setFillColorRGB(*color_tuple)

    def draw_rtl_right(text, x, y, font_size=12, color=(0, 0, 0)):
        p.setFont(ARABIC_FONT_NAME, font_size)
        p.setFillColorRGB(*color)
        p.drawRightString(x, y, rtl_text(text))

    def draw_ltr_left(text, x, y, font_size=11, color=(0, 0, 0)):
        p.setFont("Helvetica", font_size)
        p.setFillColorRGB(*color)
        p.drawString(x, y, str(text or ""))

    def draw_field_box(y_top, label, value, box_height=52):
        p.setLineWidth(1)
        set_stroke_rgb(border)
        set_fill_rgb(light_green)
        p.roundRect(45, y_top - box_height, width - 90, box_height, 10, stroke=1, fill=1)

        draw_rtl_right(label, width - 60, y_top - 16, font_size=10, color=text_gray)

        value_str = str(value or "")
        is_ltr_like = any(ch.isascii() and (ch.isalpha() or ch.isdigit()) for ch in value_str)

        if is_ltr_like:
            draw_ltr_left(value_str, 65, y_top - 34, font_size=13, color=(0, 0, 0))
        else:
            draw_rtl_right(value_str, width - 60, y_top - 34, font_size=13, color=(0, 0, 0))

    set_stroke_rgb(border)
    p.setLineWidth(1)
    p.roundRect(30, 30, width - 60, height - 60, 18, stroke=1, fill=0)

    header_x = 30
    header_y = height - 95
    header_w = width - 60
    header_h = 65
    radius = 18

    header_green = (0.11, 0.64, 0.51)
    header_text_soft = (0.92, 0.98, 0.96)

    p.setFillColorRGB(*header_green)
    p.rect(header_x, header_y, header_w, header_h - radius, stroke=0, fill=1)
    p.rect(header_x + radius, header_y + header_h - radius, header_w - (2 * radius), radius, stroke=0, fill=1)
    p.circle(header_x + radius, header_y + header_h - radius, radius, stroke=0, fill=1)
    p.circle(header_x + header_w - radius, header_y + header_h - radius, radius, stroke=0, fill=1)

    p.setStrokeColorRGB(*border)
    p.setLineWidth(0.8)
    p.line(header_x + 8, header_y, header_x + header_w - 8, header_y)

    logo_path = os.path.join(settings.BASE_DIR, "static", "assets", "images", "favicon.png")
    if os.path.exists(logo_path):
        p.drawImage(
            logo_path,
            header_x + 18,
            header_y + 12,
            width=36,
            height=36,
            mask="auto"
        )

    draw_rtl_right(
        "وصل تسجيل طلب الترشح",
        header_x + header_w - 35,
        header_y + 40,
        font_size=20,
        color=(1, 1, 1)
    )

    draw_rtl_right(
        "تم استلام الطلب بنجاح داخل المنصة",
        header_x + header_w - 35,
        header_y + 18,
        font_size=10,
        color=header_text_soft
    )

    y = height - 125
    draw_rtl_right(
        "يرجى الاحتفاظ بهذا الوصل ورمز التتبع لاستعمالهما عند متابعة حالة الملف لاحقًا.",
        width - 55,
        y,
        font_size=10,
        color=text_gray
    )

    y -= 28
    fields = [
        ("رقم الطلب", application.application_number),
        ("رمز التتبع", application.tracking_code),
        ("المنصب", application.poste.title if application.poste else ""),
        (
            "المترشح",
            f"{application.candidate.first_name} {application.candidate.last_name}"
            if application.candidate else ""
        ),
        (
            "تاريخ الإرسال",
            application.submitted_at.strftime("%Y-%m-%d %H:%M")
            if application.submitted_at else ""
        ),
    ]

    for label, value in fields:
        draw_field_box(y, label, value)
        y -= 62

    tracking_url = build_tracking_url(request, application.tracking_code)
    qr_bytes = generate_qr_png_bytes(tracking_url)
    qr_image = ImageReader(io.BytesIO(qr_bytes))

    qr_box_y = y - 150

    p.setLineWidth(0.6)
    set_stroke_rgb(border)
    p.line(50, qr_box_y + 140, width - 50, qr_box_y + 140)

    set_stroke_rgb(border)
    p.setFillColorRGB(0.98, 0.99, 0.985)
    p.roundRect(45, qr_box_y, width - 90, 135, 12, stroke=1, fill=1)

    qr_size = 92
    qr_x = width - 155
    qr_y = qr_box_y + 22

    p.drawImage(
        qr_image,
        qr_x,
        qr_y,
        width=qr_size,
        height=qr_size,
        preserveAspectRatio=True,
        mask="auto"
    )

    draw_rtl_right("التتبع الإلكتروني", qr_x - 20, qr_box_y + 98, font_size=12, color=green)
    draw_rtl_right(
        "يمكنكم مسح رمز QR للانتقال مباشرة إلى صفحة تتبع الطلب.",
        qr_x - 20,
        qr_box_y + 74,
        font_size=10,
        color=text_gray
    )
    draw_rtl_right(
        "كما يمكن استعمال رمز التتبع يدويًا عبر منصة الترشح.",
        qr_x - 20,
        qr_box_y + 54,
        font_size=10,
        color=text_gray
    )

    p.setLineWidth(0.7)
    set_stroke_rgb(border)
    p.line(50, 65, width - 50, 65)

    p.setFont(ARABIC_FONT_NAME, 9)
    p.setFillColorRGB(*text_gray)
    p.drawCentredString(
        width / 2,
        48,
        rtl_text("منصة الترشح - وزارة اقتصاد المعرفة والمؤسسات الناشئة والمؤسسات المصغرة")
    )

    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.45, 0.45, 0.45)
    p.drawString(50, 70, f"Ref: {application.application_number}")

    p.showPage()
    p.save()

    return response