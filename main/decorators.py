from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def role_required(*allowed_roles):
    """
    allowed_roles examples:
    - "SUPER_ADMIN"
    - ....
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                return redirect("auth:login")

            if user.is_superuser and "SUPER_ADMIN" in allowed_roles:
                return view_func(request, *args, **kwargs)

            user_roles = set(user.groups.values_list("name", flat=True))

            if user_roles.intersection(set(allowed_roles)):
                return view_func(request, *args, **kwargs)

            messages.error(request, "Accès non autorisé.")
            return redirect("root:index")
        return _wrapped_view
    return decorator