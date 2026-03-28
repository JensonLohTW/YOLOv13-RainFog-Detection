from django.urls import path

from .views import CurrentUserView, LoginView

urlpatterns = [
    path("login", LoginView.as_view(), name="login"),
    path("me", CurrentUserView.as_view(), name="current-user"),
]
