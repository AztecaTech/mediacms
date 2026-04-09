"""Question bank authoring endpoints (Phase 3 polish)."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from learning.models import Choice, Question, QuestionBank
from learning.permissions import _is_global_instructor
from learning.serializers.question_bank import BankQuestionSerializer, QuestionBankSerializer


def _bank_owner_qs(user):
    if _is_global_instructor(user):
        return QuestionBank.objects.all()
    return QuestionBank.objects.filter(owner=user)


class QuestionBankListCreateView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        qs = _bank_owner_qs(request.user).order_by("title", "id")
        return Response({"question_banks": QuestionBankSerializer(qs, many=True).data})

    def post(self, request):
        if not request.user.is_authenticated or not _is_global_instructor(request.user):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = QuestionBankSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        bank = QuestionBank.objects.create(
            owner=request.user,
            title=ser.validated_data["title"],
            description=ser.validated_data.get("description", ""),
        )
        return Response(QuestionBankSerializer(bank).data, status=status.HTTP_201_CREATED)


class QuestionBankDetailView(APIView):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        bank = get_object_or_404(_bank_owner_qs(request.user), pk=pk)
        qs = bank.questions.all().order_by("order", "id").prefetch_related("choices")
        return Response(
            {
                "question_bank": QuestionBankSerializer(bank).data,
                "questions": BankQuestionSerializer(qs, many=True).data,
            }
        )

    def patch(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        bank = get_object_or_404(_bank_owner_qs(request.user), pk=pk)
        if not (_is_global_instructor(request.user) or bank.owner_id == request.user.id):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        title = request.data.get("title")
        description = request.data.get("description")
        fields = []
        if title is not None:
            bank.title = str(title)[:255]
            fields.append("title")
        if description is not None:
            bank.description = str(description)
            fields.append("description")
        if fields:
            bank.save(update_fields=fields)
        return Response(QuestionBankSerializer(bank).data)


class QuestionBankQuestionCreateView(APIView):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        bank = get_object_or_404(_bank_owner_qs(request.user), pk=pk)
        if not (_is_global_instructor(request.user) or bank.owner_id == request.user.id):
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        ser = BankQuestionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        q = Question.objects.create(
            bank=bank,
            order=ser.validated_data.get("order", 0),
            prompt=ser.validated_data["prompt"],
            type=ser.validated_data["type"],
            points=ser.validated_data.get("points", 1),
            explanation=ser.validated_data.get("explanation", ""),
            metadata=ser.validated_data.get("metadata", {}),
        )
        choices = request.data.get("choices") or []
        if isinstance(choices, list):
            for i, row in enumerate(choices):
                text = (row.get("text") or "").strip()
                if not text:
                    continue
                Choice.objects.create(
                    question=q,
                    text=text[:2000],
                    is_correct=bool(row.get("is_correct", False)),
                    order=int(row.get("order", i)),
                )
        q.refresh_from_db()
        return Response(BankQuestionSerializer(q).data, status=status.HTTP_201_CREATED)
