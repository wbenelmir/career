# tracking/views.py
from django.shortcuts import get_object_or_404, redirect, render

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