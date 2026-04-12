from django.urls import path
from .api import communes_by_wilaya

app_name = "locations_api"

urlpatterns = [
    path("communes/", communes_by_wilaya, name="communes_by_wilaya"),
]