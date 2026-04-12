"""main URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

admin.site.site_header = "Career MKESM - Admin"

urlpatterns = [
    path('career-khfJF89dfsf', admin.site.urls),
    path('', include('root.urls')),
    path('applications/', include('applications.urls')),
    path('tracking/', include('tracking.urls')),
    path('dashboard/', include('dashboard.urls')),
    path("auth/", include(("authentification.urls", "authentification"), namespace="auth")), 

    path("api/locations/", include("locations.urls", namespace="locations_api")),

    path("captcha/", include("captcha.urls")),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

