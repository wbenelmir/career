# dashboard/views.py
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from root.models import Poste

from applications.models import Application
from documents.models import ApplicationDocument
from tracking.models import ApplicationTracking
from notifications.services import NotificationService
from .forms import (
    ApplicationStatusUpdateForm,
    TrackingEntryForm,
    InterviewScheduleForm,
)


def is_admin_user(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_admin_user)
def dashboard_home(request):
    context = {
        'total_applications': Application.objects.count(),
        'submitted_applications': Application.objects.filter(
            status=Application.Status.SUBMITTED
        ).count(),
        'under_review_applications': Application.objects.filter(
            status=Application.Status.UNDER_REVIEW
        ).count(),
        'incomplete_applications': Application.objects.filter(
            status=Application.Status.INCOMPLETE
        ).count(),
        'preselected_applications': Application.objects.filter(
            status=Application.Status.PRESELECTED
        ).count(),
        'preliminary_rejected_applications': Application.objects.filter(
            status=Application.Status.PRELIMINARY_REJECTED
        ).count(),
        'interview_scheduled_applications': Application.objects.filter(
            status=Application.Status.INTERVIEW_SCHEDULED
        ).count(),
        'interview_completed_applications': Application.objects.filter(
            status=Application.Status.INTERVIEW_COMPLETED
        ).count(),
        'no_show_applications': Application.objects.filter(
            status=Application.Status.NO_SHOW
        ).count(),
        'final_accepted_applications': Application.objects.filter(
            status=Application.Status.FINAL_ACCEPTED
        ).count(),
        'final_rejected_applications': Application.objects.filter(
            status=Application.Status.FINAL_REJECTED
        ).count(),
        'waiting_list_applications': Application.objects.filter(
            status=Application.Status.WAITING_LIST
        ).count(),
    }
    return render(request, 'adminpanel/dashboard.html', context)


@user_passes_test(is_admin_user)
def applications_list(request):
    applications_qs = Application.objects.select_related(
        'candidate',
        'poste',
    ).order_by('-created_at')

    search_query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    poste_filter = request.GET.get('poste', '').strip()
    eligibility_filter = request.GET.get('eligible', '').strip()

    if search_query:
        applications_qs = applications_qs.filter(
            Q(application_number__icontains=search_query) |
            Q(tracking_code__icontains=search_query) |
            Q(candidate__first_name__icontains=search_query) |
            Q(candidate__last_name__icontains=search_query) |
            Q(candidate__national_id_number__icontains=search_query)
        )

    if status_filter:
        applications_qs = applications_qs.filter(status=status_filter)

    if poste_filter:
        applications_qs = applications_qs.filter(poste_id=poste_filter)

    if eligibility_filter == 'true':
        applications_qs = applications_qs.filter(is_eligible=True)
    elif eligibility_filter == 'false':
        applications_qs = applications_qs.filter(is_eligible=False)

    postes = Poste.objects.filter(is_open=True).order_by('title')

    paginator = Paginator(applications_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'applications': page_obj.object_list,
        'page_obj': page_obj,
        'postes': postes,
        'search_query': search_query,
        'status_filter': status_filter,
        'poste_filter': poste_filter,
        'eligibility_filter': eligibility_filter,
        'status_choices': Application.Status.choices,
    }
    return render(request, 'adminpanel/applications/applications_list.html', context)

@user_passes_test(is_admin_user)
def application_detail(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('candidate', 'poste'),
        pk=pk
    )

    documents = ApplicationDocument.objects.select_related(
        'document_type'
    ).filter(application=application)

    tracking_entries = ApplicationTracking.objects.filter(
        application=application
    ).order_by('created_at')

    interview_schedule = getattr(application, 'interview_schedule', None)

    status_form = ApplicationStatusUpdateForm(instance=application)
    tracking_form = TrackingEntryForm(application=application)
    interview_form = InterviewScheduleForm(instance=interview_schedule)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_status':
            status_form = ApplicationStatusUpdateForm(request.POST, instance=application)

            if status_form.is_valid():
                new_status = status_form.cleaned_data['status']
                rejection_reason = status_form.cleaned_data.get('rejection_reason')
                admin_notes = status_form.cleaned_data.get('admin_notes')

                try:
                    application.rejection_reason = rejection_reason
                    application.admin_notes = admin_notes

                    if new_status == application.status:
                        application.save(update_fields=['rejection_reason', 'admin_notes', 'updated_at'])
                        messages.success(request, "تم تحديث الملاحظات الإدارية بنجاح.")
                    else:
                        note_parts = []
                        if rejection_reason:
                            note_parts.append(f"سبب الرفض: {rejection_reason}")
                        if admin_notes:
                            note_parts.append(f"ملاحظات الإدارة: {admin_notes}")

                        note = " | ".join(note_parts) if note_parts else "تم تحديث حالة الطلب."

                        application.save(update_fields=['rejection_reason', 'admin_notes', 'updated_at'])
                        application.set_status(
                            new_status,
                            changed_by=request.user,
                            note=note,
                            visible_to_candidate=True
                        )

                        NotificationService.send_application_status_update(application)

                        messages.success(request, "تم تحديث حالة الطلب بنجاح.")

                    return redirect('dashboard:application_detail', pk=application.pk)

                except ValidationError as e:
                    status_form.add_error(None, e)

        elif action == 'add_tracking':
            tracking_form = TrackingEntryForm(request.POST, application=application)

            if tracking_form.is_valid():
                selected_status = tracking_form.cleaned_data['status']
                note = tracking_form.cleaned_data.get('note')
                is_visible = tracking_form.cleaned_data.get('is_visible_to_candidate', True)

                try:
                    if selected_status == application.status:
                        ApplicationTracking.objects.create(
                            application=application,
                            status=selected_status,
                            note=note,
                            is_visible_to_candidate=is_visible,
                            changed_by=request.user,
                        )
                        messages.success(request, "تمت إضافة ملاحظة التتبع بنجاح.")
                    else:
                        application.set_status(
                            selected_status,
                            changed_by=request.user,
                            note=note,
                            visible_to_candidate=is_visible
                        )

                        if is_visible:
                            NotificationService.send_application_status_update(application)

                        messages.success(request, "تمت إضافة سجل التتبع وتحديث الحالة بنجاح.")

                    return redirect('dashboard:application_detail', pk=application.pk)

                except ValidationError as e:
                    tracking_form.add_error(None, e)

        elif action == 'schedule_interview':
            if interview_schedule:
                interview_form = InterviewScheduleForm(request.POST, instance=interview_schedule)
            else:
                interview_form = InterviewScheduleForm(request.POST)

            if interview_form.is_valid():
                try:
                    interview = interview_form.save(commit=False)
                    interview.application = application

                    if not interview.pk:
                        interview.created_by = request.user

                    interview.full_clean()
                    interview.save()

                    if application.status != Application.Status.INTERVIEW_SCHEDULED:
                        application.set_status(
                            Application.Status.INTERVIEW_SCHEDULED,
                            changed_by=request.user,
                            note='تمت برمجة المقابلة.',
                            visible_to_candidate=True
                        )

                    NotificationService.send_interview_scheduled(application)

                    messages.success(request, "تم حفظ برمجة المقابلة بنجاح.")
                    return redirect('dashboard:application_detail', pk=application.pk)

                except ValidationError as e:
                    if hasattr(e, 'message_dict'):
                        for field, errors in e.message_dict.items():
                            for error in errors:
                                if field in interview_form.fields:
                                    interview_form.add_error(field, error)
                                else:
                                    interview_form.add_error(None, error)
                    else:
                        interview_form.add_error(None, e)

    context = {
        'application': application,
        'candidate': application.candidate,
        'poste': application.poste,
        'documents': documents,
        'tracking_entries': tracking_entries,
        'interview_schedule': interview_schedule,
        'status_form': status_form,
        'tracking_form': tracking_form,
        'interview_form': interview_form,
        'missing_documents': application.get_missing_required_documents(),
        'is_complete': application.has_all_required_documents(),
    }
    return render(request, 'adminpanel/applications/application_detail.html', context)