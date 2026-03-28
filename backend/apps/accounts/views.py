from django.contrib.auth import authenticate
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.api.response import error_response, success_response


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):  # noqa: ANN001
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "").strip()
        if not username or not password:
            return error_response("帳號與密碼不得為空", code=400, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return error_response("帳號或密碼錯誤", code=401, status=401)

        token, _ = Token.objects.get_or_create(user=user)
        return success_response(
            {
                "token": token.key,
                "user": {
                    "id": user.pk,
                    "username": user.username,
                    "display_name": user.get_full_name() or user.username,
                    "is_staff": user.is_staff,
                    "roles": ["super_admin"] if user.is_superuser else (["staff"] if user.is_staff else []),
                },
            }
        )


class CurrentUserView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):  # noqa: ANN001
        user = request.user
        return success_response(
            {
                "id": user.pk,
                "username": user.username,
                "display_name": user.get_full_name() or user.username,
                "is_staff": user.is_staff,
                "roles": ["super_admin"] if user.is_superuser else (["staff"] if user.is_staff else []),
            }
        )
