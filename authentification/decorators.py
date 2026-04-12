from django.http import HttpResponse
from django.shortcuts import redirect
from root.models import SettingApp
from functools import wraps
from authentification.permissions import is_opgi, is_opgi_admin

def check_coming_soon(view_func):
    def wrapper_func(request, *args, **kwargs):
        try:
            # Assuming there's only one instance of SettingApp (singleton setting)
            setting = SettingApp.objects.first()
            if setting and setting.comming_soon:
                return redirect('coming-soon')  
        except SettingApp.DoesNotExist:
            pass
        
        return view_func(request, *args, **kwargs)
    
    return wrapper_func

def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('index')
        else:
            return view_func(request, *args, **kwargs)

    return wrapper_func

def allowed_users(allowed_roles=[]):
    def decorator(view_func):
        def wrapper_func(request, *args, **kwargs):

            # Allow superuser access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Get all the groups the user belongs to
            if request.user.groups.exists():
                user_groups = request.user.groups.values_list('name', flat=True)
                
                # Check if any of the user's groups are in the allowed roles
                if any(group in allowed_roles for group in user_groups):
                    return view_func(request, *args, **kwargs)
            
            return redirect('index')
        
        return wrapper_func
    return decorator
