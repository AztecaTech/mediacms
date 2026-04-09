from rest_framework import serializers

from learning.models import LetterGradeScheme


class LetterGradeSchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LetterGradeScheme
        fields = ("id", "name", "bands")
        read_only_fields = ("id",)
