# tracking/views.py
from django.shortcuts import get_object_or_404, redirect, render

from applications.models import Application
from .forms import TrackingForm


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
        Application.objects.select_related('candidate', 'poste').prefetch_related('tracking_entries'),
        tracking_code=tracking_code
    )

    timeline = application.tracking_entries.filter(
        is_visible_to_candidate=True
    ).order_by('created_at')

    context = {
        'application': application,
        'timeline': timeline,
        'page_title': 'نتيجة التتبع',
        'page_subtitle': 'الحالة الحالية والتسلسل الزمني للطلب.',
    }
    return render(request, 'public/tracking/tracking_result.html', context)

def tracking_result_direct(request, tracking_code):
    application = get_object_or_404(Application, tracking_code=tracking_code)

    timeline = application.tracking_entries.filter(
        is_visible_to_candidate=True
    ).order_by("created_at")

    context = {
        "application": application,
        "timeline": timeline,
        "page_title": "نتيجة التتبع",
        "page_subtitle": "الحالة الحالية والتسلسل الزمني لمعالجة الطلب",
    }
    return render(request, "public/tracking/tracking_result.html", context)