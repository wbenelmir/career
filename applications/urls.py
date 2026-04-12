from django.urls import path
from . import views

app_name = 'applications'

urlpatterns = [
    path("", views.start_application, name="start_application"),
    path("start/<slug:slug>/", views.start_application, name="start_application_with_slug"),

    path("candidate-information/", views.candidate_information, name="candidate_information"),

    path("upload-documents/", views.upload_documents, name="upload_documents"),
    path("upload-document-ajax/", views.upload_single_document, name="upload_single_document"),

    path("review/", views.review_application, name="review_application"),
    path("submit/", views.submit_application, name="submit_application"),

    path("success/<str:tracking_code>/", views.application_success, name="application_success"),
    path("receipt/<str:tracking_code>/pdf/", views.download_receipt_pdf, name="download_receipt_pdf"),

    path("ajax/communes-by-wilaya/", views.communes_by_wilaya, name="communes_by_wilaya"),
]