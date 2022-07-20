from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.generics import GenericAPIView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import fruitdb.serializer as sz
from fruitdb.models import *

from drf_yasg.utils import swagger_auto_schema


import jwt
import datetime
import json
import pandas as pd
import numpy as np
import requests
from django.http import JsonResponse

from .auth import (
    get_username_from_uat,
    get_sat, search_user,
    jmf_user_mileage_edit_with_etc
)


class EventAPIView(GenericAPIView):  # 이벤트 적용
    permission_classes = (HasAPIKey, )

    parser_classes = (FormParser, MultiPartParser, )
    serializer_class = sz.EventInputSerializer

    @swagger_auto_schema(
        # responses={200: sz.GetInitDataSerializer},
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        context = get_username_from_uat(request)
        customer = Customer.objects.get(username=context['username'])
        event_code = data["event_code"]
        url = f"https://fruits-cms.d-if.kr/api/post/event/check?event_code={event_code}"
        response = requests.request(
            "GET", url, headers={"Api-key": settings.CMS_API_KEY})
        print(response.status_code)
        if response.status_code == 400:
            return JsonResponse(
                {
                    "token": context['token'],
                    "data": {
                        "status": "fail",
                        "msg": "이벤트 코드가 입력되지 않았습니다."
                    },
                },
                status=400
            )
        elif response.status_code == 404:
            return JsonResponse(
                {
                    "token": context['token'],
                    "data": {
                        "status": "fail",
                        "msg": "진행중인 이벤트가 아닙니다."
                    },
                },
                status=404
            )

        if event_code == "00001":  # 첫 가입자 5000 지급
            phone = None
            SAT = get_sat()
            users, status = search_user(context['username'], SAT)
            # print(users)
            for item in users:
                if item['username'] == customer.username:
                    if 'attributes' in item:
                        if "phone" in item['attributes']:
                            phone = item['attributes']['phone'][0]
            if phone == None:
                EventAPILog.objects.create(
                    customer=customer,
                    event_code=event_code,
                    event_text="SSO에 등록된 핸드폰이 없습니다.",
                    phone="",
                    is_success=False
                )
                return JsonResponse(
                    {
                        "token": context['token'],
                        "data": {
                            "status": "fail",
                            "msg": "등록된 번호가 존재하지 않습니다."
                        },
                    },
                    status=400
                )
            else:
                if EventAPILog.objects.filter(phone=phone, event_code=event_code, is_success=True).exists():
                    EventAPILog.objects.create(
                        customer=customer,
                        event_code=event_code,
                        event_text="이미 지급된 마일리지입니다.",
                        phone=phone,
                        is_success=False
                    )
                    return JsonResponse(
                        {
                            "token": context['token'],
                            "data": {
                                "status": "success",
                                "msg": "마일리지 지급 실패 | 이미 지급된 마일리지입니다.",
                                "event_type": "mileage",
                                "event_success": False,
                            },
                        },
                        status=200
                    )
                res = jmf_user_mileage_edit_with_etc(
                    context['username'], -5000, "과일궁합 신규 가입자 5000 포인트 지급")
                if res['result'] == '200':
                    EventAPILog.objects.create(
                        customer=customer,
                        event_code=event_code,
                        event_text="과일궁합 신규 가입자 5000 포인트 지급",
                        phone=phone,
                        is_success=True
                    )
                    return JsonResponse(
                        {
                            "token": context['token'],
                            "data": {
                                "status": "success",
                                "msg": "마일리지 지급 성공 | 5000",
                                "event_type": "mileage",
                                "event_success": True,
                            },
                        },
                        status=200
                    )
                else:
                    EventAPILog.objects.create(
                        customer=customer,
                        event_code=event_code,
                        event_text="과일궁합 신규 가입자 5000 포인트 지급 | 진맛과 에러",
                        phone=phone,
                        is_success=False
                    )
                    return JsonResponse(
                        {
                            "token": context['token'],
                            "data": {
                                "status": "fail",
                                "msg": "쇼핑몰 에러"
                            },
                        },
                        status=400
                    )
        else:
            return JsonResponse(
                {
                    "token": context['token'],
                    "data": {
                        "status": "fail",
                        "msg": "존재하지 않는 이벤트입니다",
                    },
                },
                status=404
            )
