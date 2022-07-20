from django.http import JsonResponse

from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.parsers import FormParser, MultiPartParser

import fruitdb.serializer as sz

from drf_yasg.utils import swagger_auto_schema


class VersionAPIView(GenericAPIView):
    permission_classes = (HasAPIKey, )
    parser_classes = (FormParser, MultiPartParser, )
    serializer_class = sz.GetVersionInputSerializer

    @swagger_auto_schema(
        query_serializer=serializer_class,
    )
    def get(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.GET).get_data_or_response()
        target = "IOS" if data['target'] == "ios" else "ANDROID"
        return JsonResponse(sz.VersionListSerializer(data={}, context={"target": target}).create())
