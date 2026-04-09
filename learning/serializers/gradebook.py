from rest_framework import serializers

from learning.models import Rubric, RubricCriterion, RubricScore


class RubricCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RubricCriterion
        fields = ("id", "title", "description", "max_points", "order")


class RubricSerializer(serializers.ModelSerializer):
    criteria = RubricCriterionSerializer(many=True, required=False)

    class Meta:
        model = Rubric
        fields = ("id", "grade_item", "title", "description", "criteria")
        read_only_fields = ("id", "grade_item")


class RubricScoreSerializer(serializers.ModelSerializer):
    criterion_id = serializers.IntegerField(source="criterion.id", read_only=True)
    criterion_title = serializers.CharField(source="criterion.title", read_only=True)

    class Meta:
        model = RubricScore
        fields = ("id", "criterion_id", "criterion_title", "points_awarded", "feedback")
