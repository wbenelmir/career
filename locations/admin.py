# locations/admin.py
from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Wilaya, Commune

class WilayaResource(resources.ModelResource):
    class Meta:
        model = Wilaya
        fields = ("id", "code", "name_fr", "name_ar")
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(Wilaya)
class WilayaAdmin(ImportExportModelAdmin):
    resource_class = WilayaResource

    list_display = ("code", "name_fr", "name_ar")
    search_fields = ("code", "name_fr", "name_ar")
    ordering = ("code",)


class CommuneResource(resources.ModelResource):
    class Meta:
        model = Commune
        fields = ("id", "wilaya", "name_fr", "name_ar", "code")
        export_order = fields
        skip_unchanged = True
        report_skipped = True

@admin.register(Commune)
class CommuneAdmin(ImportExportModelAdmin):
    resource_class = CommuneResource

    list_display = ("name_fr", "wilaya", "code")
    list_filter = (("wilaya", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("name_fr", "name_ar", "code", "wilaya__code", "wilaya__name_fr")
    ordering = ("wilaya__code", "name_fr")
    autocomplete_fields = ("wilaya",)