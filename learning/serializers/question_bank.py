from rest_framework import serializers

from learning.models import Choice, Question, QuestionBank


class QuestionBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionBank
        fields = ("id", "title", "description", "created_at")
        read_only_fields = ("id", "created_at")


class BankChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "text", "is_correct", "order")
        read_only_fields = ("id",)


class BankQuestionSerializer(serializers.ModelSerializer):
    choices = BankChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ("id", "bank", "order", "prompt", "type", "points", "explanation", "metadata", "choices")
        read_only_fields = ("id", "bank")
