from django.urls import path

from .views import ChangePasswordView, CsrfView, LoginView, LogoutView, SessionView

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("session/", SessionView.as_view(), name="auth-session"),
    path("change-password/", ChangePasswordView.as_view(), name="auth-change-password"),
]
