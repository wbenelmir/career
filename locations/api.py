from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from locations.models import Commune


@login_required
def communes_by_wilaya(request):
    wilaya_id = request.GET.get("wilaya_id")
    term = (request.GET.get("term") or "").strip()

    if not wilaya_id:
        return JsonResponse({"results": []})

    qs = Commune.objects.filter(wilaya_id=wilaya_id)

    if term:
        qs = qs.filter(name_fr__icontains=term)

    results = [{"id": c.id, "text": c.name_fr} for c in qs.order_by("name_fr")[:50]]
    return JsonResponse({"results": results})