from django.urls import path

from .views import ResetPasswordView, UserDetailView, UserListCreateView

urlpatterns = [
    path("", UserListCreateView.as_view(), name="user-list-create"),
    path("<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path(
        "<int:pk>/reset-password/",
        ResetPasswordView.as_view(),
        name="user-reset-password",
    ),
]
