from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.views import (
    TelegramConnectionCodeView,
    UserEmailVerificationView,
    UserRegistrationView,
)

app_name = "users"

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path(
        "verify-email/<str:uidb64>/<str:token>/",
        UserEmailVerificationView.as_view(),
        name="verify_email",
    ),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "telegram/connection-code/",
        TelegramConnectionCodeView.as_view(),
        name="telegram_connection_code",
    ),
]
