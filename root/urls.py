from django.urls import path

from . import views

app_name = 'root'

urlpatterns = [
    path('', views.home, name='home'),
    path('postes/', views.poste_list, name='poste_list'),
    path('postes/<slug:slug>/', views.poste_detail, name='poste_detail'),
    path('legal-text/', views.legal_text, name='legal_text'),
    path('about-ministry/', views.about_ministry, name='about_ministry'),
]