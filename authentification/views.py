from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import AdminLoginForm


def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard:dashboard_home')

    form = AdminLoginForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()

            if user.is_staff:
                login(request, user)
                return redirect('dashboard:dashboard_home')

            form.add_error(None, 'You do not have permission to access the admin panel.')

    context = {
        'form': form,
    }
    return render(request, 'adminpanel/auth/login.html', context)


def admin_logout_view(request):
    logout(request)
    return redirect('authentification:admin_login')