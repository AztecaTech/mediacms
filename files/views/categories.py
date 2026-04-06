from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from ..methods import is_mediacms_editor
from ..models import Category, Tag
from ..serializers import CategorySerializer, TagSerializer


class CategoryList(APIView):
    """List categories"""

    @swagger_auto_schema(
        manual_parameters=[],
        tags=['Categories'],
        operation_summary='Lists Categories',
        operation_description='Lists all categories',
        responses={
            200: openapi.Response('response description', CategorySerializer),
        },
    )
    def get(self, request, format=None):
        base_queryset = Category.objects.prefetch_related("user")

        if is_mediacms_editor(request.user):
            categories = base_queryset.all()
        elif request.user.is_authenticated:
            # Signed-in users see: non-RBAC public + requires_login + their RBAC categories
            from django.db.models import Q
            conditions = Q(is_rbac_category=False)
            if getattr(settings, 'USE_RBAC', False):
                rbac_categories = request.user.get_rbac_categories_as_member()
                conditions |= Q(pk__in=rbac_categories)
            categories = base_queryset.filter(conditions).distinct()
        else:
            # Anonymous users: only non-RBAC categories that don't require login
            categories = base_queryset.filter(is_rbac_category=False, requires_login=False)

        categories = categories.order_by("title")

        serializer = CategorySerializer(categories, many=True, context={"request": request})
        ret = serializer.data
        return Response(ret)


class TagList(APIView):
    """List tags"""

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(name='page', type=openapi.TYPE_INTEGER, in_=openapi.IN_QUERY, description='Page number'),
        ],
        tags=['Tags'],
        operation_summary='Lists Tags',
        operation_description='Paginated listing of all tags',
        responses={
            200: openapi.Response('response description', TagSerializer),
        },
    )
    def get(self, request, format=None):
        tags = Tag.objects.filter().order_by("-media_count")
        pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
        paginator = pagination_class()
        page = paginator.paginate_queryset(tags, request)
        serializer = TagSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)
