from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.parsers import FormParser, MultiPartParser

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
from django.http import Http404

from drf_yasg.utils import swagger_auto_schema

from .auth import get_username_from_uat
import fruitdb.serializer as sz
from fruitdb.models import *


class FruitDetailAPIView(GenericAPIView):  # 설문조사 및 식품추천 API
    permission_classes = (HasAPIKey, )
    parser_classes = (FormParser, MultiPartParser, )
    serializer_class = sz.SurveyInputSerializer

    def get_object(self, if_id):
        try:
            return Fruit.objects.get(if_id=if_id)
        except Fruit.DoesNotExist:
            raise Http404

    @swagger_auto_schema(
        query_serializer=serializer_class,
    )
    def get(self, request, if_id, format=None):
        data = self.get_serializer(data=request.GET).get_data_or_response()
        context = get_username_from_uat(request)
        fruit = self.get_object(if_id)
        survey = Survey.objects.get(id=data['survey_id'])
        return JsonResponse(
            {
                "token": context['token'],
                "data": sz.FruitDetailSerializer(fruit, context={"survey": survey, "request": request}).create(),
            },
            status=200
        )


class ProductBannerAPIView(APIView):
    permission_classes = (HasAPIKey,)
    def get(self, request, *args, **kwargs):
        banners = ProductBanner.objects.filter(is_active=True)
        banner_data = sz.ProductBannerSerializers(banners, many=True).data
        return JsonResponse({"data":banner_data, "msg":"success"}, status=200)