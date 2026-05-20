from django.urls import path
from . import views

app_name = 'tracking'

urlpatterns = [
    path('', views.track_application, name='track_application'),
    path('<str:tracking_code>/', views.tracking_result, name='tracking_result'),
    path("result/<str:tracking_code>/", views.tracking_result_direct, name="tracking_result_direct"),
    path("summons/<str:tracking_code>/pdf/",views.download_interview_summons_pdf,name="download_interview_summons_pdf",),
    path("resume/<str:tracking_code>/",views.resume_completion_workflow,name="resume_completion_workflow",),
]