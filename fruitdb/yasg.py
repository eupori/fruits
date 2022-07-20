from django.conf.urls import url
from django.urls import path, include
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from drf_yasg import openapi

schema_url_patterns = [
    path('/', include('fruitdb.urls')),
]

schema_view = get_schema_view(
    openapi.Info(
        title='과일궁합 API',
        default_version='v1.0',
        description='''
        과일궁합 API 문서 페이지입니다.
        ''',
        terms_of_service="https://www.google.com/policies/terms/"
    ),
    validators=['flex'],
    public=True,
    #   url='추후 url'
    # permission_classes=(IsAuthenticated, ),
    permission_classes=(AllowAny, ),
    patterns=schema_url_patterns,
)
