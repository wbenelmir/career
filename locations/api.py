from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from locations.models import Commune


@login_required
def communes_by_wilaya(request):
    wilaya_id = request.GET.get("wilaya_id")
    term = (request.GET.get("term") or "").strip()

    if not wilaya_id:
        return JsonResponse({"results": []})

    # Security scope
    # if not is_opgi_admin(request.user):
    #     if not is_opgi(request.user):
    #         return JsonResponse({"results": []})
    #     profile = getattr(request.user, "profile", None)
    #     if not profile or str(profile.wilaya_id) != str(wilaya_id):
    #         return JsonResponse({"results": []})

    qs = Commune.objects.filter(wilaya_id=wilaya_id)

    if term:
        qs = qs.filter(name_fr__icontains=term)

    results = [{"id": c.id, "text": c.name_fr} for c in qs.order_by("name_fr")[:50]]
    return JsonResponse({"results": results})