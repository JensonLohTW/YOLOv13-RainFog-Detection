from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.api.response import error_response, success_response

from .contracts import AgentAskRequest
from .serializers import AgentAskSerializer
from .services import AgentOrchestratorService, AgentServiceError


class AgentAskView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):  # noqa: ANN001
        serializer = AgentAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            result = AgentOrchestratorService().ask(
                AgentAskRequest(
                    agent_type=payload["agent_type"],
                    question=payload["question"],
                    task_no=payload.get("task_no", ""),
                    image_id=payload.get("image_id"),
                )
            )
        except AgentServiceError as exc:
            return error_response(str(exc), code=exc.code, status=exc.status)

        return success_response(result.to_dict())
