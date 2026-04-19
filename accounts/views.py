from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import EmailSignupForm, EmailLoginForm


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")
    if request.method == "POST":
        form = EmailSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Welcome to Tapstar. Let's set up your business.")
            return redirect("business_onboarding")
    else:
        form = EmailSignupForm()
    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")
    if request.method == "POST":
        form = EmailLoginForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                auth_login(request, user)
                return redirect("dashboard_home")
        messages.error(request, "Invalid email or password.")
    else:
        form = EmailLoginForm()
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    auth_logout(request)
    return redirect("landing")
