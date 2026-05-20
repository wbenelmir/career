# tracking/views.py
from django.shortcuts import get_object_or_404, redirect, render
import io
import os

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from applications.pdf_utils import (
    register_arabic_font,
    rtl_text,
    ARABIC_FONT_NAME,
)

from applications.utils import (
    build_tracking_url,
    generate_qr_png_bytes,
)
from .pdf_utils import (
    build_interview_summons_pdf,
)
from applications.models import Application
from .forms import TrackingForm
from .models import InterviewSchedule

def track_application(request):
    if request.method == 'POST':
        form = TrackingForm(request.POST)
        if form.is_valid():
            tracking_code = form.cleaned_data['tracking_code'].strip()
            return redirect('tracking:tracking_result', tracking_code=tracking_code)
    else:
        form = TrackingForm()

    context = {
        'form': form,
        'page_title': 'تتبع الطلب',
        'page_subtitle': 'أدخل رمز التتبع للاطلاع على حالة الملف.',
    }
    return render(request, 'public/tracking/track_application.html', context)


def tracking_result(request, tracking_code):

    application = get_object_or_404(
        Application.objects.select_related(
            'candidate',
            'poste',
        ).prefetch_related(
            'tracking_entries',
            'completion_requests',
        ),
        tracking_code=tracking_code
    )

    timeline = application.tracking_entries.filter(
        is_visible_to_candidate=True
    ).order_by('created_at')

    active_completion_requests = (
        application.completion_requests.filter(
            is_resolved=False
        )
    )

    context = {
        'application': application,
        'timeline': timeline,
        'active_completion_requests':
            active_completion_requests,
        'page_title': 'نتيجة التتبع',
        'page_subtitle':
            'الحالة الحالية والتسلسل الزمني للطلب.',
        "interview_schedule":
            getattr(
                application,
                "interview_schedule",
                None
            ),
    }

    return render(
        request,
        'public/tracking/tracking_result.html',
        context
    )

def tracking_result_direct(
    request,
    tracking_code
):

    application = get_object_or_404(
        Application.objects.prefetch_related(
            'tracking_entries',
            'completion_requests',
        ),
        tracking_code=tracking_code
    )

    timeline = application.tracking_entries.filter(
        is_visible_to_candidate=True
    ).order_by("created_at")

    active_completion_requests = (
        application.completion_requests.filter(
            is_resolved=False
        )
    )

    context = {
        "application": application,
        "timeline": timeline,
        "active_completion_requests":
            active_completion_requests,
        "page_title": "نتيجة التتبع",
        "page_subtitle":
            "الحالة الحالية والتسلسل الزمني لمعالجة الطلب",
        "interview_schedule":
            getattr(
                application,
                "interview_schedule",
                None
            ),
    }

    return render(
        request,
        "public/tracking/tracking_result.html",
        context
    )

def download_interview_summons_pdf(
    request,
    tracking_code
):

    application = get_object_or_404(
        Application.objects.select_related(
            "candidate",
            "poste",
        ),
        tracking_code=tracking_code,
    )

    interview_schedule = getattr(
        application,
        "interview_schedule",
        None,
    )

    if not interview_schedule:

        return HttpResponse(
            "لا توجد مقابلة مبرمجة لهذا الطلب.",
            status=404,
        )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; '
        f'filename="interview_summons_'
        f'{application.application_number}.pdf"'
    )

    tracking_url = build_tracking_url(
        request,
        application.tracking_code,
    )

    pdf = build_interview_summons_pdf(
        application=application,
        interview_schedule=interview_schedule,
        tracking_url=tracking_url,
    )

    response.write(pdf)

    return response

def resume_completion_workflow(
    request,
    tracking_code
):

    application = get_object_or_404(
        Application.objects.select_related(
            "candidate",
            "poste",
        ),
        tracking_code=tracking_code,
    )

    if application.status != Application.Status.INCOMPLETE:

        messages.warning(
            request,
            "لا يوجد طلب استكمال نشط لهذا الملف."
        )

        return redirect(
            "tracking:tracking_result",
            tracking_code=tracking_code,
        )

    request.session["candidate_id"] = (
        application.candidate_id
    )

    request.session["draft_application_id"] = (
        application.id
    )

    ordered_choices = (
        application.get_ordered_choices()
    )

    selected_poste_ids = [
        choice.poste_id
        for choice in ordered_choices
    ]

    if selected_poste_ids:

        request.session["selected_poste_ids"] = (
            selected_poste_ids
        )

        request.session["selected_poste_id"] = (
            selected_poste_ids[0]
        )

    messages.info(
        request,
        "يمكنكم الآن استكمال الوثائق أو المعلومات المطلوبة."
    )

    return redirect(
        "applications:upload_documents"
    )
