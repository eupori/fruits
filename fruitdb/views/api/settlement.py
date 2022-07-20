from rest_framework.views import APIView
from django.views.generic import TemplateView

from rest_framework.generics import GenericAPIView
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.permissions import AllowAny

from fruitsite.settings import (
    JMF_API_KEY,
    GENETIC_API_HOST,
    GENETIC_API_TOKEN,
    SHOPMAN_API_KEY,
)

JMF_API_URL = "https://bestf.co.kr/api/ig_member_info.php"
# JMF_API_URL = "http://bestfruit.godomall.com/api/ig_member_info.php"
from rest_framework.response import Response
from django.http import JsonResponse
from django.core.mail import send_mail
from django.http import Http404
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.staticfiles import finders
from django.views.generic import RedirectView
from django.db.models import Q

from drf_yasg.utils import swagger_auto_schema
from dateutil.relativedelta import relativedelta

import requests
import json
import jwt
import base64
import random
import datetime
import hashlib
import xmltodict
import time
import re
from email.mime.image import MIMEImage

from fruitdb.models import *
from fruitdb.views.api.auth import get_username_from_uat, get_sat, search_user
import fruitdb.serializer as sz

def jmf_order_check(from_date, to_date):
    url = JMF_API_URL
    params = f"start_date={from_date}&end_date={to_date}&ig_key={JMF_API_KEY}&ig_type=dnacode"
    response = requests.request("GET", f"{url}?{params}")

    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]

def jmf_coupon_check(coupon):
    url = JMF_API_URL
    params = f"use_code={coupon}&ig_key={JMF_API_KEY}&ig_type=dnacode"
    response = requests.request("GET", f"{url}?{params}")
    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]

def jmf_coupon_regist(user_id, coupon):
    url = JMF_API_URL
    params = f"ig_key={JMF_API_KEY}&ig_type=dnacode_reg&use_mem_no={user_id}&use_code={coupon}"
    response = requests.request("GET", f"{url}?{params}")
    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]

def jmf_coupon_cancel(user_id, coupon):
    url = JMF_API_URL
    params = f"ig_key={JMF_API_KEY}&ig_type=dnacode_cancel&use_mem_no={user_id}&use_code={coupon}"
    response = requests.request("GET", f"{url}?{params}")
    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]

def macrogen_kit_cancel(genetic_test, client_key):
    kit = genetic_test.genetictestkit_set.first()
    url = f"{GENETIC_API_HOST}/api_v8/cancel/jinmasgwa"
    headers={
        'Authorization': f'Bearer {GENETIC_API_TOKEN}',
        'Content-Type': 'application/json;charset=utf-8',
    }
    if kit:
        if kit.invoice_datetime + datetime.timedelta(days=180) > datetime.datetime.now():
            cancel_type = "auto_cancel"
        else:
            cancel_type = "req_cancel"
    else:
        cancel_type = "req_cancel"

    data = {
        "client_key" : client_key,
        "cancel_type": cancel_type,
        "cancel_date": datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%I:%S")
    }
    response = requests.request("PUT", url, headers=headers,data=json.dumps(data))
    if response.status_code == 200:
        return json.loads(response.text)


def shopman_order_cancel(username):
    url = f"https://shopman.d-if.kr/order/genetictest?username={username}"
    headers={
        'api-key': SHOPMAN_API_KEY,
    }
    response = requests.request("DELETE", url, headers=headers)
    if response.status_code == 200:
        return json.loads(response.text)


def shopman_order_update(username, status):
    url = f"https://shopman.d-if.kr/order/genetictest"
    headers={
        'api-key': SHOPMAN_API_KEY,
    }
    data={
        'username': username,
        'status': status,
    }
    response = requests.request("PUT", url, headers=headers, data=data)
    if response.status_code == 200:
        return json.loads(response.text)


class SubscriptionOnCouponInfoAPIView(APIView):
    # permission_classes = (HasAPIKey,)
    permission_classes = [permissions.AllowAny,]

    def get(self, request, *args, **kwargs):
        # data = self.get_serializer(data=request.data).get_data_or_response()
        data = request.GET.get("coupon")
        response = jmf_coupon_check(data)
        if response["result"] == "200":
            if "igDataVal" in response.keys():
                respnse_value = response["igDataVal"]
                is_used = False if respnse_value["use_yn"] == "1" else True
                return Response(is_used)
            else:
                return Response(False)
        else:
            return Response(False)

    def post(self, request, *args, **kwargs):
        # data = self.get_serializer(data=request.data).get_data_or_response()
        context = get_username_from_uat(request)
        username = context["username"]

        user_id = request.POST.get("user_id")
        coupon = request.POST.get("coupon")

        response = jmf_coupon_regist(user_id, coupon)

        if response["result"] == "C01":
            customers = Customer.objects.filter(username=user_id)
            if len(customers) > 0:
                customer = customers.first()
                customer.is_genetic = True
                customer.save()
                return JsonResponse({"result": response["result"], "resultComment": response["resultComment"]}, status=200)
            else:
                response = jmf_coupon_cancel(user_id, coupon)
                return JsonResponse({"result": response["result"], "resultComment": response["resultComment"], "message": "쿠폰 사용중 문제가 발생하였습니다."}, status=500)
        else:
            response = jmf_coupon_cancel(user_id, coupon)
            return JsonResponse({"result": response["result"], "resultComment": response["resultComment"], "message": "쿠폰 사용중 문제가 발생하였습니다."}, status=500)


class SubscriptionOnOrderInfoAPIView(APIView):
    permission_classes = (HasAPIKey,)
    # permission_classes = [permissions.AllowAny,]

    def get(self, request, *args, **kwargs):
        # data = self.get_serializer(data=request.data).get_data_or_response()
        from_date = request.GET.get("start_date")
        to_date = request.GET.get("end_date")
        response = jmf_order_check(from_date, to_date)
        if response["result"] == "200":
            return Response(response)
        else:
            return Response(response)


class SubscriptionOnUserInfoAPIView(APIView):
    permission_classes = (HasAPIKey,)
    # permission_classes = [permissions.AllowAny,]

    def get(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        username = context["username"]
        phone_number = request.GET.get("phone_number")
        customer = Customer.objects.filter(username=username)

        if len(customer) > 0:
            return JsonResponse({"is_genetic": customer.first().is_genetic}, status=200)
        else:
            return JsonResponse({"message": "처리중 오류가 발생했습니다."}, status=500)

        # if response["result"] == "200":
        #     return Response(True)
        # else:
        #     return Response(False)

"""
test data set
"user_id": "cmmmmmm",
"status": "test_request",
"datetime": "2022-04-04 11:52:11",


"""

"""
상황
1. 구독 온 주문 확정 이후 쿠폰번호를 이용하여 키트 신청: user_id, coupon이 있고 kit_id는 없는 상태
    * 고도몰에 쿠폰번호가 발급되었지만 과일궁합 내  GeneticPromotion에는 갱신이 안될 수 있는 상태일 경우는?
        * 해당 기능에서 추가를 하는 방법 확인 필요
2. 과일궁합 내 단품상품을 이용하여 키트 신청: user_id만 있는 상태
"""

class GeneticPromotionAPIView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        request_data = json.loads(request.data)
        user_id = request_data.get("user_id")
        request_datetime = request_data.get("datetime")
        order_id = request_data.get("order_id")
        request_status = request_data.get("action")
        coupon = request_data.get("coupon")
        action = request_data.get("action")
        kit_id = request_data.get("kit_id")
        invoice_date = request_data.get("invoice_date")


        genetic_test = None
        p = re.compile("[0-9]*O-[0-9]*")
        if order_id and p.fullmatch(order_id):
            category = "fruits"
            test_product = GeneticTestProduct.objects.get(product_code="P00000ZN")
        else:
            category = "godo"
            test_product = None

        if user_id:
            SAT = get_sat()
            users, status = search_user(user_id, SAT)
            user = next(
                (item for item in users if item["username"] == user_id), None
            )
            attr_dict = {"name": "", "phone": "", "fruit_match": True}
            if user:
                if "attributes" in user:
                    if "name" in user["attributes"]:
                        attr_dict["name"] = user["attributes"]["name"][0]
                    if "phone" in user["attributes"]:
                        attr_dict["phone"] = user["attributes"]["phone"][0]
            else:
                return JsonResponse({"msg": "user not found"}, status=404)
            # attr_dict = {"phone":"01022353287"}
            request.user = User.objects.first()
            # 쿠폰 번호가 같거나 주문번호가 같은 경우 같은 건으로 취급
            # 주문번호가 비어있는 경우는 제외
            # 단 쿠폰번호로 들어온 경우는 주문번호가 없음

            if order_id == "" or order_id == None or order_id == "1234":
                genetic_tests = GeneticTest.objects.filter(coupon=coupon)
            else:
                genetic_tests = GeneticTest.objects.filter(order_id=order_id)

            # genetic_tests = GeneticTest.objects.filter(Q(order_id=order_id)|Q(coupon=coupon)).exclude(order_id=None).exclude(order_id="").exclude(order_id="1234")
            customer = Customer.objects.get(username=user_id)

            #GeneticPromotionProduct 생성 코드 필요
            #s_product = GeneticPromotionProduct.objects.create()
            if len(genetic_tests) == 0:
                genetic_test = GeneticTest.objects.create(
                    customer=customer,
                    phone=attr_dict["phone"],
                    test_product=test_product,
                    coupon=coupon,
                    order_id=order_id,
                    start_datetime=datetime.datetime.now(),
                    end_datetime=datetime.datetime.now() + relativedelta(years=1),
                )
            elif len(genetic_tests) == 1:
                genetic_test = genetic_tests.first()

                if action == "kit_send":
                    genetic_test.is_active = True
                    genetic_test.current_times = 1
                    shopman_order_update(customer.username, "2")
                elif action == "kit_recept":
                    genetic_test.is_kit_recept = True

                genetic_test.save()

            if not genetic_test.coupon and coupon:
                genetic_test.coupon = coupon

                #구독온 결제 진행 후 과일궁합에서 갱신이 안된 경우.


            if kit_id: #kit_id가 있으면 무조건 이전에 키트 신청을 해야 함. 따라서 GenetieTest가 있어야 함
                genetic_test_kit = GeneticTestKit.objects.get_or_create(genetic_test=genetic_test, kit_code=kit_id, order_id=order_id, invoice_datetime=invoice_date)

            GeneticTestLog.objects.create(
                order_date=datetime.datetime.now(),
                genetic_test = genetic_test if genetic_test else None,
                action = request_status,
                billing_price = 0,
                registrant = request.user
            )

            macrogen_status_for_shopman = ["kit_send", "analized"]
            shopman_status = {
                "kit_send":"2",
                "analized":"3",
            }
            if request_status in macrogen_status_for_shopman:
                shopman_order_update(customer.username, shopman_status[request_status])

        return JsonResponse({"data": request.data, "result": "OK"}, status=200)

    def put(self, request, *args, **kwargs):
        client_key = request.POST.get("client_key")

        #  'end' : 서비스 종료, 'ing' : 서비스 진행중
        process = request.POST.get("process")
        # 0 : 미개봉, 1 : 키트개봉, 2 : 키트 미반송 또는 분실
        kit_status = request.POST.get("kit_status")
        # 취소 발생 전 상태코드
        prev_status = request.POST.get("prev_status")
        # 0 : 무과금, 1 : 배송비. 2 : 키트비 + 배송비, 3 : 분석비
        charge_type = request.POST.get("charge_type")

        customers = Customer.objects.filter(username=client_key)
        if len(customers) == 1:
            customer = customers.first()
        else:
            return JsonResponse({"msg":"customer does not exist."}, status=403)
        
        genetic_tests = GeneticTest.objects.filter(customer=customer)
        if len(genetic_tests) == 1:
            genetic_test = genetic_tests.first()

        subs = JMFSubscription.objects.filter(coupon=genetic_test.coupon)
        if len(subs) == 1:
            sub = subs.first()
        else:
            return JsonResponse({"msg":"jmf subscription does not exist."}, status=403)

        response_data = shopman_order_cancel(customer.username)
        if response_data == None:
            return JsonResponse({"msg":"shopman order not found"}, status=503)

        #1번 상황 - 키트 발송 전 : 무과금
        if charge_type == "0":
            genetic_test.kit_status = "cancel"
            genetic_test.status = "cancel"
            genetic_test.save()

            GeneticTestLog.objects.create(
                order_date=datetime.datetime.now(),
                genetic_test=genetic_test,
                action="normal_kit_cancel",
                billing_price=0,
                current_times=genetic_test.genetictestlog_set.last().current_times,
                registrant=User.objects.first(),
            )
            JMFSubscriptionPaymentLog.objects.create(
                order_date=datetime.datetime.now(),
                jmf_subscription=sub,
                action="normal_kit_cancel",
                billing_price=0,
                current_times=sub.jmfsubscriptionpaymentlog_set.last().current_times,
                registrant=User.objects.first(),
            )
        # 과금 - 키트 발송 후 정상 키트 반송 시 배송비만 청구
        elif charge_type == "1":
            genetic_test.kit_status = "normal_kit_return"
            genetic_test.status = "cancel"
            genetic_test.save()

            GeneticTestLog.objects.create(
                order_date=datetime.datetime.now(),
                genetic_test=genetic_test,
                action="normal_kit_return",
                billing_price=6000,
                current_times=genetic_test.genetictestlog_set.last().current_times,
                registrant=User.objects.first(),
            )
            JMFSubscriptionPaymentLog.objects.create(
                order_date=datetime.datetime.now(),
                jmf_subscription=sub,
                action="normal_kit_return",
                billing_price=0,
                current_times=sub.jmfsubscriptionpaymentlog_set.last().current_times,
                registrant=User.objects.first(),
            )
        # 과금 - 키트 발송 후 파손 키트 반송 시 배송비 + 키트비 청구
        elif charge_type == "2":
            genetic_test.kit_status = "damaged_kit_return"
            genetic_test.status = "cancel"
            genetic_test.save()

            GeneticTestLog.objects.create(
                order_date=datetime.datetime.now(),
                genetic_test=genetic_test,
                action="damaged_kit_return",
                billing_price=26000,
                current_times=genetic_test.genetictestlog_set.last().current_times,
                registrant=User.objects.first(),
            )
            JMFSubscriptionPaymentLog.objects.create(
                order_date=datetime.datetime.now(),
                jmf_subscription=sub,
                action="damaged_kit_return",
                billing_price=0,
                current_times=sub.jmfsubscriptionpaymentlog_set.last().current_times,
                registrant=User.objects.first(),
            )
        # 과금 - 검사 시작 후 취소 시 분석비 청구
        elif charge_type == "3":
            genetic_test.kit_status = "test_start_cancel"
            genetic_test.status = "damaged_kit_return"
            genetic_test.save()
            
            GeneticTestLog.objects.create(
                order_date=datetime.datetime.now(),
                genetic_test=genetic_test,
                action="normal_kit_return",
                billing_price=40000,
                current_times=genetic_test.genetictestlog_set.last().current_times,
                registrant=User.objects.first(),
            )
            JMFSubscriptionPaymentLog.objects.create(
                order_date=datetime.datetime.now(),
                jmf_subscription=sub,
                action="damaged_kit_return",
                billing_price=0,
                current_times=sub.jmfsubscriptionpaymentlog_set.last().current_times,
                registrant=User.objects.first(),
            )
        return JsonResponse({"data":{"client_key": client_key, "charge_type": charge_type}, "msg":"success"}, status=200)


    # 해당 api는 키트 신청 - 키트 발송 전까지만 호출할 수 있는 기능.
    def delete(self, request, *args, **kwargs):
        status = request.POST.get("status")
        client_key = request.POST.get("client_key")
        process = request.POST.get("process")
        kit_status = request.POST.get("kit_status")
        prev_status = request.POST.get("prev_status")
        charge_type = request.POST.get("charge_type")
        
        customers = Customer.objects.filter(username=client_key)
        if len(customers) == 1:
            customer = customers.first()
        else:
            return JsonResponse({"msg":"customer does not exist."}, status=403)

        genetic_tests = GeneticTest.objects.filter(customer=customer)
        if len(genetic_tests) == 1:
            genetic_test = genetic_tests.first()
        else:
            return JsonResponse({"msg":"genetic test does not exist."}, status=403)

        subs = JMFSubscription.objects.filter(coupon=genetic_test.coupon)
        if len(subs) == 1:
            sub = subs.first()
        else:
            return JsonResponse({"msg":"jmf subscription does not exist."}, status=403)

        genetic_test_last_log = genetic_test.genetictestlog_set.last()
        if genetic_test_last_log:
            test_current_time = genetic_test_last_log.current_times
        else:
            test_current_time = 0

        GeneticTestLog.objects.create(
            order_date=datetime.datetime.now(),
            genetic_test=genetic_test,
            action="cancel_request",
            billing_price=0,
            current_times=test_current_time,
            registrant=User.objects.first(),
        )

        sub_last_log = genetic_test.genetictestlog_set.last()
        if sub_last_log:
            sub_current_time = sub_last_log.current_times
        else:
            sub_current_time = 0

        JMFSubscriptionPaymentLog.objects.create(
            order_date=datetime.datetime.now(),
            jmf_subscription=sub,
            action="cancel_request",
            billing_price=0,
            current_times=sub_current_time,
            registrant=User.objects.first(),
        )

        if status == "success":
            # process : ing
            if process == "ing":
                genetic_test.kit_status = "cancel_request"
                genetic_test.save()
                return JsonResponse({"msg":"success"}, status=200)
            else:
                # process : end

                response_data = shopman_order_cancel(customer.username)
                if response_data == None:
                    return JsonResponse({"msg":"shopman order not found"}, status=503)
                
                #1번 상황 - 키트 발송 전 : 무과금
                if charge_type == "0":
                    genetic_test.kit_status = "cancel"
                    genetic_test.status = "cancel"
                    genetic_test.save()

                    #쿠폰 사용 취소 (고도몰)
                    jmf_coupon_cancel(genetic_test.customer.username, genetic_test.coupon)

                    genetic_test_last_log = genetic_test.genetictestlog_set.last()
                    if genetic_test_last_log:
                        test_current_time = genetic_test_last_log.current_times
                    else:
                        test_current_time = 0

                    GeneticTestLog.objects.create(
                        order_date=datetime.datetime.now(),
                        genetic_test=genetic_test,
                        action="normal_kit_cancel",
                        billing_price=0,
                        current_times=test_current_time,
                        registrant=User.objects.first(),
                    )

                    sub_last_log = genetic_test.genetictestlog_set.last()
                    if sub_last_log:
                        sub_current_time = sub_last_log.current_times
                    else:
                        sub_current_time = 0

                    JMFSubscriptionPaymentLog.objects.create(
                        order_date=datetime.datetime.now(),
                        jmf_subscription=sub,
                        action="normal_kit_cancel",
                        billing_price=0,
                        current_times=sub_current_time,
                        registrant=User.objects.first(),
                    )
                # 과금 - 키트 발송 후 정상 키트 반송 시 배송비만 청구
                elif charge_type == "1":
                    genetic_test.kit_status = "normal_kit_return"
                    genetic_test.status = "cancel"
                    genetic_test.save()

                    genetic_test_last_log = genetic_test.genetictestlog_set.last()
                    if genetic_test_last_log:
                        test_current_time = genetic_test_last_log.current_times
                    else:
                        test_current_time = 0

                    GeneticTestLog.objects.create(
                        order_date=datetime.datetime.now(),
                        genetic_test=genetic_test,
                        action="normal_kit_return",
                        billing_price=6000,
                        current_times=test_current_time,
                        registrant=User.objects.first(),
                    )

                    sub_last_log = genetic_test.genetictestlog_set.last()
                    if sub_last_log:
                        sub_current_time = sub_last_log.current_times
                    else:
                        sub_current_time = 0

                    JMFSubscriptionPaymentLog.objects.create(
                        order_date=datetime.datetime.now(),
                        jmf_subscription=sub,
                        action="normal_kit_return",
                        billing_price=0,
                        current_times=sub_current_time,
                        registrant=User.objects.first(),
                    )
                # 과금 - 키트 발송 후 파손 키트 반송 시 배송비 + 키트비 청구
                elif charge_type == "2":
                    genetic_test.kit_status = "damaged_kit_return"
                    genetic_test.status = "cancel"
                    genetic_test.save()

                    genetic_test_last_log = genetic_test.genetictestlog_set.last()
                    if genetic_test_last_log:
                        test_current_time = genetic_test_last_log.current_times
                    else:
                        test_current_time = 0

                    GeneticTestLog.objects.create(
                        order_date=datetime.datetime.now(),
                        genetic_test=genetic_test,
                        action="damaged_kit_return",
                        billing_price=26000,
                        current_times=test_current_time,
                        registrant=User.objects.first(),
                    )

                    sub_last_log = genetic_test.genetictestlog_set.last()
                    if sub_last_log:
                        sub_current_time = sub_last_log.current_times
                    else:
                        sub_current_time = 0

                    JMFSubscriptionPaymentLog.objects.create(
                        order_date=datetime.datetime.now(),
                        jmf_subscription=sub,
                        action="damaged_kit_return",
                        billing_price=0,
                        current_times=sub_current_time,
                        registrant=User.objects.first(),
                    )
                # 과금 - 검사 시작 후 취소 시 분석비 청구
                elif charge_type == "3":
                    genetic_test.kit_status = "test_start_cancel"
                    genetic_test.status = "damaged_kit_return"
                    genetic_test.save()
                    
                    genetic_test_last_log = genetic_test.genetictestlog_set.last()
                    if genetic_test_last_log:
                        test_current_time = genetic_test_last_log.current_times
                    else:
                        test_current_time = 0

                    GeneticTestLog.objects.create(
                        order_date=datetime.datetime.now(),
                        genetic_test=genetic_test,
                        action="normal_kit_return",
                        billing_price=40000,
                        current_times=test_current_time,
                        registrant=User.objects.first(),
                    )

                    sub_last_log = genetic_test.genetictestlog_set.last()
                    if sub_last_log:
                        sub_current_time = sub_last_log.current_times
                    else:
                        sub_current_time = 0

                    JMFSubscriptionPaymentLog.objects.create(
                        order_date=datetime.datetime.now(),
                        jmf_subscription=sub,
                        action="damaged_kit_return",
                        billing_price=0,
                        current_times=sub_current_time,
                        registrant=User.objects.first(),
                    )
        return JsonResponse({"msg":"success"}, status=200)


class GeneTicPromotionUrlAPIView(APIView):
    permission_classes = (HasAPIKey,)

    def get(self, request, *args, **kwargs):
        return JsonResponse({"url":"https://fruits.d-if.kr/media/noimg_img.png"}, status=202)
