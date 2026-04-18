# root/views.py
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from .models import LegalReferenceType, Poste, LegalReference
import random

def home(request):
    selected_type = request.GET.get("type")

    today = timezone.localdate()

    postes_qs = Poste.objects.filter(
        is_open=True,
        deadline__gte=today
    )

    if selected_type:
        postes_qs = postes_qs.filter(poste_type=selected_type)

    postes_qs = postes_qs.order_by("deadline", "-publish_date")

    postes_list = list(postes_qs)

    # random sample (max 6)
    postes = random.sample(
        postes_list,
        k=min(len(postes_list), 6)
    )

    context = {
        "postes": postes,
        "selected_type": selected_type,
    }

    return render(request, "public/home.html", context)


def poste_list(request):
    selected_type = request.GET.get("type")
    selected_direction = request.GET.get("direction")

    today = timezone.localdate()

    postes_qs = Poste.objects.filter(
        is_open=True,
        deadline__gte=today
    )

    # filter by type
    if selected_type:
        postes_qs = postes_qs.filter(poste_type=selected_type)

    # filter by direction
    if selected_direction:
        postes_qs = postes_qs.filter(direction=selected_direction)

    postes_qs = postes_qs.order_by("deadline", "-publish_date")

    # extract available directions (only those with open postes)
    directions = (
        Poste.objects.filter(
            is_open=True,
            deadline__gte=today
        )
        .exclude(direction__isnull=True)
        .exclude(direction__exact="")
        .values_list("direction", flat=True)
        .distinct()
        .order_by("direction")
    )

    # pagination
    paginator = Paginator(postes_qs, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "postes": page_obj.object_list,
        "page_obj": page_obj,
        "directions": directions,
        "selected_type": selected_type,
        "selected_direction": selected_direction,
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