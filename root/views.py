# root/views.py
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from .models import LegalReferenceType, Poste, LegalReference


def home(request):
    selected_type = request.GET.get("type")

    postes = Poste.objects.filter(is_open=True)

    if selected_type:
        postes = postes.filter(poste_type=selected_type)

    today = timezone.localdate()
    postes = postes.filter(deadline__gte=today).order_by("deadline", "-publish_date")

    context = {
        "postes": postes[:6],
    }
    return render(request, "public/home.html", context)


def poste_list(request):
    selected_type = request.GET.get("type")

    postes = Poste.objects.all()

    if selected_type:
        postes = postes.filter(poste_type=selected_type)

    postes = postes.order_by("-is_open", "deadline", "-publish_date", "title")

    context = {
        "postes": postes,
    }
    return render(request, "public/poste_list.html", context)


def poste_detail(request, slug):
    poste = get_object_or_404(Poste, slug=slug)

    context = {
        "poste": poste,
    }
    return render(request, "public/poste_detail.html", context)


def about_ministry(request):
    return render(request, "public/about_ministry.html")


def legal_text(request):
    selected_type = request.GET.get("type")

    legal_references = LegalReference.objects.filter(is_active=True)

    if selected_type:
        legal_references = legal_references.filter(reference_type=selected_type)

    legal_references = legal_references.order_by("display_order", "-published_date", "title")

    used_types = (
        LegalReference.objects.filter(is_active=True)
        .exclude(reference_type__isnull=True)
        .exclude(reference_type__exact="")
        .values_list("reference_type", flat=True)
        .distinct()
    )
    used_types = list(dict.fromkeys(used_types))
    type_labels = dict(LegalReference._meta.get_field("reference_type").choices)

    reference_types = [
        (value, type_labels.get(value, value))
        for value in used_types
        if value in type_labels
    ]

    context = {
        "legal_references": legal_references,
        "selected_type": selected_type,
        "reference_types": reference_types,
        "page_title": "النصوص القانونية والتنظيمية",
        "page_subtitle": "الإطار المرجعي المؤطر لعملية الترشح ودراسة الملفات عبر المنصة.",
    }
    return render(request, "public/legal_text.html", context)