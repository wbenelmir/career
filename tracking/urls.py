from django.urls import path
from . import views

app_name = 'tracking'

urlpatterns = [
    path('', views.track_application, name='track_application'),
    path('<str:tracking_code>/', views.tracking_result, name='tracking_result'),
    path("result/<str:tracking_code>/", views.tracking_result_direct, name="tracking_result_direct"),
]