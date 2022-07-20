from rest_framework.views import APIView

from rest_framework.generics import GenericAPIView
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.exceptions import AuthenticationFailed

from fruitsite.settings import (
    OIDC_OP_AUTHORIZATION_ENDPOINT,
    OIDC_OP_TOKEN_ENDPOINT,
    OIDC_OP_USER_ENDPOINT,
    OIDC_OP_JWKS_ENDPOINT,
    OIDC_OP_SIGNUP_ENDPOINT,
    OIDC_RP_CLIENT_ID,
    OIDC_RP_CLIENT_SECRET,
    FIREBASE_AUTH_TOKEN,
    OIDC_OP_SEARCH_ENDPOINT,
    OIDC_OP_RESETPASSWORD_ENDPOINT,
    OIDC_OP_SECESSION_ENDPOINT,
    DL_API_KEY,
    ALIGO_API_KEY,
    JMF_API_KEY,
    FIREBASE_SEND_MESSAGE_URL,
)

JMF_API_URL = "https://bestf.co.kr/api/ig_member_info.php"
# JMF_API_URL = "http://bestfruit.godomall.com/api/ig_member_info.php"
from rest_framework.response import Response
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from django.http import Http404
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.staticfiles import finders
from django.views.generic import RedirectView

from firebase_dynamic_links import DynamicLinks
from drf_yasg.utils import swagger_auto_schema


import requests
import datetime
import json
import jwt
import base64
import random
import datetime
import hashlib
import xmltodict
import time
from email.mime.image import MIMEImage

from fruitdb.models import *
import fruitdb.serializer as sz

#이메일 방법
def send_order_email(question, request_url="https://fruits.d-if.kr"):
    try:
        email_title= f"[과일궁합 문의] 새 문의가 접수되었습니다."
        email_body = {
            "identifier": question.id,
            "username": question.customer.username,
            "name": question.customer.name,
            "customer": question.customer,
            "email": question.email,
            "content": question.content,
            "created_at": question.created_at,
        }
        html_body = render_to_string('question_email_form.html', email_body)
        email = EmailMultiAlternatives(
            subject=email_title,
            body="",
            from_email='과일궁합 지원팀 <fm.order@d-if.kr>',
            # from_email='wm@d-if.kr',
            to=[settings.ORDER_EMAIL]
        )

        email.attach_alternative(html_body, "text/html")
        email.mixed_subtype = 'related'

        image_names = ['cs-banner']
        for image_name in image_names:
            with open(finders.find(f'images/{image_name}.png'), 'rb') as f:
                image_data = f.read()
                image = MIMEImage(image_data)
                image.add_header('Content-ID', f'<{image_name}>')
                # image.add_header('Content-Disposition', 'inline', filename="image_name")
                email.attach(image)

        res = email.send(fail_silently=False)
        if res in [1, '1']:
            QuestionEmailLog.objects.create(
                question=question,
                status="success",
                message="1"
            )
        else:
            QuestionEmailLog.objects.create(
                question=question,
                status=f"fail",
                message=res
            )
    except Exception as e:
        QuestionEmailLog.objects.create(
            question=question,
            status=f"Exception fail",
            message=str(e)
        )


#노티 발송
def send_notification(firebase_data, title, body, tab, action="FLUTTER_NOTIFICATION_CLICK"):
    headers = {
        "Authorization": FIREBASE_AUTH_TOKEN,
        "Content-Type": "application/json; UTF-8",
    }
    payload = {
        "to": firebase_data,
        "notification": {
            "body": body,  # 메시지 알림 내용 (상단바-알림창에 출력될 내용)
            "title": title,  # 메시지 알림 제목 (상단바-알림창에 출력될 제목)
            "android_channel_id": "1",
            "tag": str(datetime.datetime.now()),
        },
        "data": {
            "body": body,  # 메시지 내용(앱 - 채팅 탭에서 확인 가능)
            "title": title,  # 메시지 제목(앱 - 채팅 탭에서 확인가능 / 없어도 됨)
            "tab": tab,
            "click_action": action,
        },
    }
    if firebase_data is not None:
        response = requests.post(
            FIREBASE_SEND_MESSAGE_URL, data=json.dumps(payload), headers=headers
        )


# 헤더에서 토큰만 반환
def get_payload_from_token(request):
    auth = request.META.get("HTTP_TOKEN", b"").split(".")[1]
    auth += "=" * ((4 - len(auth) % 4) % 4)
    return json.loads(base64.b64decode(auth).decode("utf-8"))


# sat 발급
def get_sat():
    payload = f"client_id={OIDC_RP_CLIENT_ID}&client_secret={OIDC_RP_CLIENT_SECRET}&grant_type=client_credentials"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    sat_response = requests.request(
        "POST", OIDC_OP_TOKEN_ENDPOINT, headers=headers, data=payload
    )
    return json.loads(sat_response.text)["access_token"]


# uat 발급
def get_uat(username, password):
    payload = f"client_id={OIDC_RP_CLIENT_ID}&client_secret={OIDC_RP_CLIENT_SECRET}&username={username}&password={password}&grant_type=password".encode(
        "utf-8"
    )
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    sat_response = requests.request(
        "POST", OIDC_OP_TOKEN_ENDPOINT, headers=headers, data=payload
    )
    return json.loads(sat_response.text), sat_response.status_code


# 소셜로그인시 uat 발급받은 것 처럼 처리하는 함수
# 계정 비활성화 시에도 넘어갈 수 있는 문제가 있음
def get_uat_impersonate(username):
    payload = f"client_id={OIDC_RP_CLIENT_ID}&client_secret={OIDC_RP_CLIENT_SECRET}&requested_subject={username}&grant_type=urn:ietf:params:oauth:grant-type:token-exchange".encode(
        "utf-8"
    )
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    sat_response = requests.request(
        "POST", OIDC_OP_TOKEN_ENDPOINT, headers=headers, data=payload
    )
    return json.loads(sat_response.text), sat_response.status_code


# refresh_token을 이용해서 uat 재발급 (현재 잘 사용하지 않음)
def get_uat_from_refresh_token(refresh_token):
    payload = f"client_id={OIDC_RP_CLIENT_ID}&client_secret={OIDC_RP_CLIENT_SECRET}&grant_type=refresh_token&refresh_token={refresh_token}"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    sat_response = requests.request(
        "POST", OIDC_OP_TOKEN_ENDPOINT, headers=headers, data=payload
    )
    return json.loads(sat_response.text), sat_response.status_code


def get_username_from_uat(request):
    refresh_token = request.META.get("HTTP_REFRESHTOKEN", None)
    token = request.META.get("HTTP_TOKEN", None)
    context = {}

    # 토근 인증 여부 확인
    if refresh_token == None or token == None:
        raise AuthenticationFailed(detail="token, refresh_token blank")
    payload = get_payload_from_token(request)

    # 사용자 사용 여부 확인
    customer = Customer.objects.filter(
        username=payload["preferred_username"], is_active=False
    )
    if customer.exists():
        raise AuthenticationFailed(detail="user account disabled")

    # expire된 토큰 재발급
    exp = datetime.datetime.fromtimestamp(int(payload["exp"]))
    if datetime.datetime.now() > exp:
        tokens, status = get_uat_from_refresh_token(refresh_token)
        if status == 200:
            context["token"] = tokens["access_token"]
        else:
            raise AuthenticationFailed(detail="token, refresh_token expire")
    else:
        context["token"] = token

    # 사용자 반환
    context["sub"] = payload["sub"]
    context["username"] = payload["preferred_username"]
    return context


def search_user(username, SAT):
    headers = {"Authorization": f"Bearer {SAT}"}
    sat_response = requests.request(
        "GET", OIDC_OP_SEARCH_ENDPOINT + f"?username={username}", headers=headers
    )
    return json.loads(sat_response.text), sat_response.status_code


def change_password(id, password, SAT):
    payload = json.dumps({"type": "password", "value": password, "temporary": False})
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SAT}"}
    sat_response = requests.request(
        "PUT",
        f"{OIDC_OP_RESETPASSWORD_ENDPOINT}/{id}/reset-password",
        headers=headers,
        data=payload,
    )
    return sat_response.status_code


def change_user_info(data, id, SAT):
    headers = {"Authorization": f"Bearer {SAT}", "Content-Type": "application/json"}
    sat_response = requests.request(
        "PUT",
        f"{OIDC_OP_SECESSION_ENDPOINT}/{id}",
        headers=headers,
        data=json.dumps(data),
    )
    return sat_response.text, sat_response.status_code


# 계정 삭제 함수 (사용 안함) => 비활성화 기능으로 대체
def delete_user(id, SAT):
    headers = {"Authorization": f"Bearer {SAT}"}
    sat_response = requests.request(
        "DELETE", f"{OIDC_OP_SECESSION_ENDPOINT}/{id}", headers=headers
    )
    return sat_response.text, sat_response.status_code


# 고도몰 유저 회원가입
# 고도몰 비밀번호 변경시에도 사용
def jmf_user(username, password):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {
        "ig_key": JMF_API_KEY,
        "ig_type": "regMember",
        "memId": username,
        "memPw": password,
    }
    response = requests.request("POST", url, data=data)

    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


# username이 있는 사람 정보 확인
def jmf_user_check(username):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {"ig_key": JMF_API_KEY, "ig_type": "infoMember", "memId": username}
    response = requests.request("POST", url, data=data)

    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


# 비밀번호까지 입력해서 인증 여부 확인
def jmf_user_auth_check(username, password):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {
        "ig_key": JMF_API_KEY,
        "ig_type": "chkMember",
        "memId": username,
        "memPw": password,
    }
    response = requests.request("POST", url, data=data)

    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


# 고도몰의 배송지 정보를 받아오는 함수
# member_no : jmf_user_check를 통해서 받아오는 정보
def jmf_user_shipping(member_no):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {"ig_key": JMF_API_KEY, "ig_type": "dlvinfo", "memNo": member_no}
    response = requests.request("POST", url, data=data)

    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


def jmf_user_shipping_edit(data):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    response = requests.request("POST", url, data=data)

    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


def jmf_user_deposit_edit(id, val):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {
        "ig_key": JMF_API_KEY,
        "ig_type": "memberDeposit",
        "memId": id,
        "deposit": str(int(val) * -1),
        "reasonCd": "01006003",
    }
    response = requests.request("POST", url, data=data)
    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


def jmf_user_mileage_edit(id, val):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {
        "ig_key": JMF_API_KEY,
        "ig_type": "memberMileage",
        "memId": id,
        "mileage": str(int(val) * -1),
        "reasonCd": "01005001",
    }
    response = requests.request("POST", url, data=data)
    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


def jmf_user_mileage_edit_with_etc(id, val, content):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {
        "ig_key": JMF_API_KEY,
        "ig_type": "memberMileage",
        "memId": id,
        "mileage": str(int(val) * -1),
        "reasonCd": "01005011",
        "contents": content,
    }
    response = requests.request("POST", url, data=data)
    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


def jmf_check_sns(uuid, sns):  # 115 반환시 없는거 200 반환시 존재
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {
        "ig_key": JMF_API_KEY,
        "ig_type": "chkSnsMember",
        "uuid": uuid,
        "snsTypeFl": sns,
    }
    response = requests.request("POST", url, data=data)
    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


def jmf_create_sns(uuid, sns, memId):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {
        "ig_key": JMF_API_KEY,
        "ig_type": "chkSnsMemberReg",
        "memId": memId,
        "uuid": uuid,
        "snsTypeFl": sns,
        "accessToken": "1",
        "refreshToken": "1",
    }
    response = requests.request("POST", url, data=data)
    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


def jmf_subscription_check(phone):
    # url = "http://bestfruit.godomall.com/api/ig_member_info.php"
    url = JMF_API_URL
    data = {
        "ig_key": JMF_API_KEY,
        "ig_type": "dnacode",
        "dna_tel": phone.replace("-", ""),
    }
    response = requests.request("POST", url, data=data)

    return json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


# def jmf_user_mileage_edit(id, data):
#     url = "http://bestfruit.godomall.com/api/ig_member_info.php"
#     response = requests.request("POST", url, data=data)
#     return json.loads(json.dumps(xmltodict.parse(response.text)))['igData']


def send_sms(receiver, is_test):
    rand_num = random.choice(range(100000, 999999))
    send_url = "https://apis.aligo.in/send/"  # 요청을 던지는 URL, 현재는 문자보내기
    sms_data = {
        "key": ALIGO_API_KEY,  # api key
        "userid": "bestf2019",  # 알리고 사이트 아이디
        "sender": "1833-5059",  # 발신번호
        # 수신번호 (,활용하여 1000명까지 추가 가능)
        "receiver": receiver.replace("-", ""),
        "msg": f"[과일궁합] 과일궁합 본인확인 인증번호는 [{rand_num}]입니다.",  # 문자 내용
        "msg_type": "SMS",  # 메세지 타입 (SMS, LMS)
        "testmode_yn": is_test,  # 테스트모드 적용 여부 Y/N
    }
    send_response = requests.post(send_url, data=sms_data).json()
    return rand_num, send_response


class SendSMSAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.SendSMSAPIInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()

        rand_num, send_response = send_sms(data["phone"], data["is_test"])

        if send_response["result_code"] != "1":
            return JsonResponse(
                {
                    "result_code": send_response["result_code"],
                    "message": send_response["message"],
                },
                status=400,
            )
        else:
            return JsonResponse(
                {"code": str(rand_num), "now": str(datetime.datetime.now())}, status=200
            )


class SendDLEmailAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.SendDLEmailAPIInputSerializer

    @swagger_auto_schema(
        # responses={200: sz.GetInitDataSerializer},
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        email_title = ""
        users, status = search_user(data["email"], get_sat())
        if data["type"] == "password":
            email_title = "[과일궁합] 비밀번호 변경 인증 메일"
            check = False
            for user in users:
                if user["username"] == data["email"] or user["email"] == data["email"]:
                    check = True
                    break
            if check == False:
                return JsonResponse({}, status=404)
        else:
            email_title = "[과일궁합] 가입 인증 메일"
            check = False
            for user in users:
                if user["username"] == data["email"] or user["email"] == data["email"]:
                    check = True
                    break
            if check == True:
                return JsonResponse(
                    {"email": data["email"], "msg": "유저가 이미 존재합니다."}, status=409
                )
        rand_num = random.choice(range(100000, 999999))
        api_key = DL_API_KEY
        domain = "https://fruitsdif.page.link"
        dl = DynamicLinks(api_key, domain)
        params = {
            "androidInfo": {
                "androidPackageName": "kr.dif.fruits",
            },
            "iosInfo": {
                "iosBundleId": "kr.dif.fruits",
                "iosAppStoreId": "1551060796",
            },
        }
        short_link = dl.generate_dynamic_link(
            f"https://fruitsdif.page.link/vaild-email?code={rand_num}&efr=1",
            True,
            params,
        )
        html_body = render_to_string(
            "email_form.html",
            {
                "short_link": short_link,
                "serial_number": rand_num,
            },
        )
        email = EmailMultiAlternatives(
            subject=email_title,
            body="",
            from_email="과일궁합 지원팀 <support@d-if.kr>",
            to=[
                data["email"],
            ],
        )

        email.attach_alternative(html_body, "text/html")
        email.mixed_subtype = "related"

        image_names = ["cs-banner"]
        for image_name in image_names:
            with open(finders.find(f"images/{image_name}.png"), "rb") as f:
                image_data = f.read()
                image = MIMEImage(image_data)
                image.add_header("Content-ID", f"<{image_name}>")
                email.attach(image)

        email.send(fail_silently=False)

        return JsonResponse(
            {
                "code": str(rand_num),
                "short_link": short_link,
                "now": str(datetime.datetime.now()),
            },
            status=200,
        )


class UserAPIView(GenericAPIView):  # 유저 생성
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.UserCreateInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        username = data["username"]
        customer = Customer.objects.filter(username=username, is_active=False)
        if customer.exists():
            return JsonResponse(
                {
                    "msg": "user account disabled",
                },
                status=403,
            )

        jmf_check = jmf_user_check(username)
        if jmf_check["result"] == "200":
            return JsonResponse({"msg": "already jmf exists"}, status=409)
        # email = request.POST.get('email')
        password = data["password"]
        phone = data["phone"]
        name = data["name"]
        headers = {
            "Authorization": f"Bearer {get_sat()}",
            "Content-Type": "application/json",
        }
        user_dict = {
            "username": username,
            "firstName": "",
            "lastName": "",
            "email": "",
            "enabled": True,
            "credentials": [
                {"type": "password", "value": password, "temporary": False}
            ],
            "attributes": {
                "phone": phone,
                "name": name,
                "fruit_match": True,
            },
        }

        response = requests.request(
            "POST", OIDC_OP_SIGNUP_ENDPOINT, headers=headers, data=json.dumps(user_dict)
        )
        if response.status_code != 409:
            tokens, status = get_uat(username, password)

            res = jmf_user_check(username)
            if res["result"] == "108":
                res = jmf_user(username, password)
            if not Customer.objects.filter(username=username).exists():
                Customer.objects.create(username=username)
            return JsonResponse(
                {
                    "token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_type": "Bearer",
                    "is_jmf_auth": True,
                },
                status=201,
            )
        else:
            return JsonResponse({}, status=response.status_code)

    def delete(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        SAT = get_sat()

        customer = Customer.objects.filter(username=context["username"], is_active=True)
        if customer.exists():
            customer.update(
                **{
                    "firebase_token": "",
                    "birth_date": None,
                    "sex": "",
                    "name": "",
                    "is_active": False,
                }
            )
            context, status = change_user_info({"enabled": False}, context["sub"], SAT)
            if status == 204:
                return JsonResponse({}, status=204)
            else:
                return JsonResponse({"msg": context}, status=400)
        else:
            return JsonResponse({}, status=404)


class UserLoginAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.UserInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        start = datetime.datetime.now()
        data = self.get_serializer(data=request.data).get_data_or_response()
        username = data["username"]
        password = data["password"]

        customer = Customer.objects.filter(username=username, is_active=False)
        if customer.exists():
            return JsonResponse(
                {
                    "msg": "user account disabled",
                },
                status=403,
            )
        customer = Customer.objects.filter(username=username, is_active=True)
        customer_check = True
        if customer.exists():
            if Customer.objects.filter(username=username, is_jmf_auth=False).exists():
                tokens, status = get_uat(username, password)
                if status == 401:
                    return JsonResponse(
                        {"status": "fail", "msg": "login failed"}, status=401
                    )
                elif status == 400:
                    return JsonResponse(
                        {"status": "fail", "msg": "user account disabled"},
                        status=403,  # 200
                    )
                else:
                    end = datetime.datetime.now()
                    print("#############################")
                    print(end-start)
                    print(start)
                    print(end)
                    print("#############################")
                    return JsonResponse(
                        {
                            "token": tokens["access_token"],
                            "refresh_token": tokens["refresh_token"],
                            "token_type": "Bearer",
                            "is_jmf_auth": False,
                        },
                        status=status,  # 200
                    )
        else:
            customer_check = False

        if jmf_user_check(username)["result"] == "200":
            if jmf_user_auth_check(username, password)["result"] == "200":
                if not customer_check:
                    Customer.objects.create(username=username, is_jmf_auth=True, is_jmf_join=True)

                tokens, status = get_uat_impersonate(username)
                if status == 403:
                    return JsonResponse(
                        {"status": "fail", "msg": "login failed"}, status=401
                    )
                end = datetime.datetime.now()
                print("#############################")
                print(end-start)
                print(start)
                print(end)
                print("#############################")

                return JsonResponse(
                    {
                        "token": tokens["access_token"],
                        "refresh_token": tokens["refresh_token"],
                        "token_type": "Bearer",
                        "is_jmf_auth": True,
                    },
                    status=status,  # 200
                )
        return JsonResponse({"status": "fail", "msg": "login failed"}, status=401)
        # 실패
        # tokens, status = get_uat(username, password)
        # if status == 401:
        #     return JsonResponse({"status": "fail", "msg": "login failed"}, status=401)
        # elif status == 400:
        #     return JsonResponse(
        #         {"status": "fail", "msg": "user account disabled"}, status=403  # 200
        #     )
        # else:
        #     return JsonResponse(
        #         {
        #             "token": tokens["access_token"],
        #             "refresh_token": tokens["refresh_token"],
        #             "token_type": "Bearer",
        #         },
        #         status=status,  # 200
        #     )


def get_shipping_detail(username, sno):
    sd = ShippingDetail.objects.filter(username=username, sno=sno)
    pw = ""
    request = ""
    if sd.exists():
        pw = sd[0].entrance_password
        request = sd[0].request
    return pw, request


class UserInfoAPIView(APIView):
    permission_classes = (HasAPIKey,)

    def get(self, request, *args, **kwargs):
        start = datetime.datetime.now()

        refresh_token = request.META.get("HTTP_REFRESHTOKEN", b"")
        token = request.META.get("HTTP_TOKEN", b"")
        firebase_token = request.META.get("HTTP_FCMTOKEN", b"")
        # OIDC_OP_USER_ENDPOINT
        if refresh_token == b"" or token == b"":
            return JsonResponse(
                {"status": "blank", "msg": "token, refresh_token blank"}, status=401
            )

        context = get_username_from_uat(request)

        # exp = datetime.datetime.fromtimestamp(int(get_payload_from_token(request)['exp']))
        # if datetime.datetime.now() > exp:
        #     tokens, status = get_uat_from_refresh_token(refresh_token)
        #     if status == 200:
        #         refresh_token = tokens['refresh_token']
        #         token = tokens['access_token']
        #     else:
        #         ServiceAPILog.objects.create(
        #             username = get_payload_from_token(request)["preferred_username"],
        #             api="UserInfoAPI",
        #             method="GET",
        #             status=401
        #         )
        #         return JsonResponse({"status":"expire", "msg":"token, refresh_token expire"}, status=401)
        headers = {"Authorization": f"Bearer {token}"}

        info_response = requests.request(
            "POST", OIDC_OP_USER_ENDPOINT, headers=headers, data={}
        )
        if info_response.status_code == 401:
            ServiceAPILog.objects.create(
                username=context["username"],
                api="UserInfoAPI",
                method="GET",
                status=info_response.status_code,
            )
            return JsonResponse(
                {"status": "token invalid", "msg": "token invalid"},
                status=info_response.status_code,
            )  # 401
        else:
            info = json.loads(info_response.text)

            user = Customer.objects.filter(username=context["username"])
            is_aos = False
            if request.GET.get("target") == "aos":
                is_aos = True
            if not user.exists():
                user = Customer.objects.create(
                    username=context["username"],
                    firebase_token=firebase_token,
                    is_android=is_aos,
                )
            else:
                user = user[0]
                user.firebase_token = firebase_token
                user.is_android = is_aos
                user.save()

            SAT = get_sat()
            users, status = search_user(context["username"], SAT)
            attr_dict = {
                "name": "",
                "phone": "",
            }
            is_fruit_match = False
            for item in users:
                if item["id"] == info["sub"]:
                    if "attributes" in item:
                        if "name" in item["attributes"]:
                            attr_dict["name"] = item["attributes"]["name"][0]
                        if "phone" in item["attributes"]:
                            attr_dict["phone"] = item["attributes"]["phone"][0]
                        if "fruit_match" in item["attributes"]:
                            is_fruit_match = True
                    break

            if not is_fruit_match:
                attr_dict.update({"fruit_match": True})
                tmp_context, status = change_user_info(
                    {"attributes": attr_dict}, context["sub"], SAT
                )
            res = jmf_user_check(context["username"])
            mileage = 0.0
            deposit = 0.0
            member_no = None
            shippings = []
            if res["result"] == "200":
                mileage = float(res["igDataVal"]["mileage"])
                deposit = float(res["igDataVal"]["deposit"])
                member_no = res["igDataVal"]["memNo"]

                response = jmf_user_shipping(member_no)
                if response["result"] == "200":
                    shipping_res = response["igDataVal"]["igDataValArray"]
                    if isinstance(shipping_res, list):
                        items = shipping_res
                    else:
                        items = [shipping_res]

                    for item in items:
                        pw, shipping_request = get_shipping_detail(
                            context["username"], item["sno"]
                        )
                        shippings.append(
                            {
                                "sno": item["sno"],
                                "name": item["shippingName"],
                                "shipping_name": item["shippingTitle"],
                                "phone": item["shippingCellPhone"],
                                "zip_code": item["shippingZonecode"],
                                "address": item["shippingAddress"],
                                "detail_adress": item["shippingAddressSub"],
                                "pw": pw,
                                "request": shipping_request,
                            }
                        )

            res = {
                "status": "success",
                "token": context["token"],
                "data": {
                    "username": context["username"],
                    "phone": attr_dict["phone"],
                    "name": attr_dict["name"],
                    "is_pass_auth": user.is_pass_auth,
                    "is_jmf_join": user.is_jmf_join,
                    "mileage": mileage,
                    "deposit": deposit,
                    "shippings": shippings,
                },
            }
            ServiceAPILog.objects.create(
                username=context["username"],
                api="UserInfoAPI",
                method="GET",
                status=info_response.status_code,
            )

            end = datetime.datetime.now()

            start = datetime.datetime.now()

            excute_list = ["카페인대사 관리", "심장건강 관리", "두통 개선", "혈당 관리", "혈압 관리", "고지혈 관리", "혈행 개선"]
            traits = list(
                Trait.objects.exclude(name_ko__in=excute_list).filter(category="예방질병").values_list(
                    "name_ko", "image", "active_image"
                )
            )
            res["data"]["trait_dis"] = list(
                map(
                    lambda x: {
                        "name": x[0],
                        "image": f"{request.scheme}://{request.get_host()}/media/"
                        + str(x[1]),
                        "active_image": f"{request.scheme}://{request.get_host()}/media/"
                        + str(x[2]),
                    },
                    traits,
                )
            )

            traits = list(
                Trait.objects.filter(category="생활목표").values_list(
                    "name_ko", "image", "active_image"
                )
            )
            res["data"]["trait_goal"] = list(
                map(
                    lambda x: {
                        "name": x[0],
                        "image": f"{request.scheme}://{request.get_host()}/media/"
                        + str(x[1]),
                        "active_image": f"{request.scheme}://{request.get_host()}/media/"
                        + str(x[2]),
                    },
                    traits,
                )
            )

            end = datetime.datetime.now()

            return JsonResponse(res, status=info_response.status_code)  # 200

    def patch(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        return JsonResponse({}, status=204)  # 200


class UserAttributeAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)

    def patch(self, request, *args, **kwargs):
        refresh_token = request.META.get("HTTP_REFRESHTOKEN", b"")
        token = request.META.get("HTTP_TOKEN", b"")
        if refresh_token == b"" or token == b"":
            return JsonResponse(
                {"status": "blank", "msg": "token, refresh_token blank"}, status=401
            )

        context = get_username_from_uat(request)

        SAT = get_sat()
        users, status = search_user(context["username"], SAT)
        user = next(
            (item for item in users if item["id"] == context["sub"]), None
        )  # 딕셔너리 서치로 찾아야함,
        attr_dict = {"name": "", "phone": "", "fruit_match": True}
        if user:
            if "attributes" in user:
                if "name" in user["attributes"]:
                    attr_dict["name"] = user["attributes"]["name"][0]
                if "phone" in user["attributes"]:
                    attr_dict["phone"] = user["attributes"]["phone"][0]
        else:
            return JsonResponse({"msg": "user not found"}, status=404)

        for target in ["name", "phone"]:
            attr_dict[target] = request.POST.get(target, attr_dict[target])
            customer = Customer.objects.get(username=context["username"])
            customer.name = request.POST.get(target, customer.name)
            customer.save()
        context, status = change_user_info(
            {"attributes": attr_dict}, context["sub"], SAT
        )
        return JsonResponse(context, status=status, safe=False)


class UserPaymentInfoAPIView(APIView):
    def get(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        res = jmf_user_check(context["username"])
        mileage = 0.0
        deposit = 0.0
        shippings = []
        if res["result"] == "200":
            mileage = float(res["igDataVal"]["mileage"])
            deposit = float(res["igDataVal"]["deposit"])

            response = jmf_user_shipping(res["igDataVal"]["memNo"])
            if response["result"] == "200":
                shipping_res = response["igDataVal"]["igDataValArray"]
                if isinstance(shipping_res, list):
                    items = shipping_res
                else:
                    items = [shipping_res]

                for item in items:
                    pw, shipping_request = get_shipping_detail(
                        context["username"], item["sno"]
                    )
                    shippings.append(
                        {
                            "sno": item["sno"],
                            "name": item["shippingName"],
                            "shipping_name": item["shippingTitle"],
                            "phone": item["shippingCellPhone"],
                            "zip_code": item["shippingZonecode"],
                            "address": item["shippingAddress"],
                            "detail_adress": item["shippingAddressSub"],
                            "pw": pw,
                            "request": shipping_request,
                        }
                    )
        res = {
            "status": "success",
            "token": context["token"],
            "data": {
                "mileage": mileage,
                "deposit": deposit,
                "shippings": shippings,
            },
        }
        return JsonResponse(res, status=200)  # 200


class ShippingUpdateAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.ShippingInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        data = self.get_serializer(data=request.data).get_data_or_response()
        reg_type = "up" if data["type"] == "update" else "add"
        request_data = {
            "ig_key": JMF_API_KEY,
            "ig_type": "dlvinfoData",
            "regType": reg_type,
            "shippingTitle": data["shipping_name"],
            "shippingName": data["name"],
            "shippingPhone": data["phone"],
            "shippingCellPhone": data["phone"],
            "shippingZonecode": data["zip_code"],
            "shippingAddress": data["address"],
            "shippingAddressSub": data["detail_address"],
            "memId": context["username"],
        }
        sno = request.POST.get("sno")
        response = None
        if reg_type == "up":
            request_data["sno"] = data["sno"]
            response = jmf_user_shipping_edit(request_data)
        else:
            res = jmf_user_check(context["username"])
            if res["result"] == "200":
                member_no = res["igDataVal"]["memNo"]
                response = jmf_user_shipping(member_no)
                if response["result"] == "200":
                    shipping_res = response["igDataVal"]["igDataValArray"]
                    if isinstance(shipping_res, list):
                        items = shipping_res
                    else:
                        items = [shipping_res]
                    duplication_check = False
                    input_dict = {
                        "name": data["name"],
                        "shipping_name": data["shipping_name"],
                        "phone": data["phone"],
                        "zip_code": data["zip_code"],
                        "address": data["address"],
                        "detail_address": data["detail_address"],
                    }
                    for item in items:
                        item_dict = {
                            "name": item["shippingName"],
                            "shipping_name": item["shippingTitle"],
                            "phone": item["shippingCellPhone"],
                            "zip_code": item["shippingZonecode"],
                            "address": item["shippingAddress"],
                            "detail_address": item["shippingAddressSub"],
                        }
                        if input_dict == item_dict:
                            duplication_check = True
                            break
                    if duplication_check == True:
                        res = {
                            "status": "success",
                            "token": context["token"],
                            "data": "중복된 정보가 이미 입력되어 있습니다.",
                        }
                        return JsonResponse(res, status=200)

                response = jmf_user_shipping_edit(request_data)
                if response["result"] != "200":
                    res = {
                        "status": "success",
                        "token": context["token"],
                        "data": response,
                    }
                    return JsonResponse(res, status=200)
                response = jmf_user_shipping(member_no)
                if response["result"] == "200":
                    shipping_res = response["igDataVal"]["igDataValArray"]
                    if isinstance(shipping_res, list):
                        items = shipping_res
                    else:
                        items = [shipping_res]
                else:
                    res = {
                        "status": "success",
                        "token": context["token"],
                        "data": response["result"],
                    }
                    return JsonResponse(res, status=200)
                sno = items[-1]["sno"]
        if sno != None:
            sd = ShippingDetail.objects.filter(username=context["username"], sno=sno)
            if not sd.exists():
                ShippingDetail.objects.create(
                    username=context["username"],
                    sno=sno,
                    entrance_password=data["pw"],
                    request=data["request"],
                )
            else:
                sd.update(
                    **{"entrance_password": data["pw"], "request": data["request"]}
                )
            res = {"status": "success", "token": context["token"], "data": response}
            return JsonResponse(res, status=200)
        else:
            res = {"status": "success", "token": context["token"], "data": response}
            return JsonResponse(res, status=400)


class MileageUpdateAPIView(APIView):
    def put(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        value = request.POST.get("value")
        res = jmf_user_mileage_edit(context["username"], value)
        if res["result"] != "200":
            return JsonResponse(
                {"status": "fail", "token": context["token"], "data": res}, status=400
            )
        else:
            return JsonResponse(
                {"status": "success", "token": context["token"], "data": {}}, status=200
            )


class DepositUpdateAPIView(APIView):
    def put(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        value = request.POST.get("value")
        res = jmf_user_deposit_edit(context["username"], value)
        if res["result"] != "200":
            return JsonResponse(
                {"status": "fail", "token": context["token"], "data": res}, status=400
            )
        else:
            return JsonResponse(
                {"status": "success", "token": context["token"], "data": {}}, status=200
            )


class SocialLoginAPIView(APIView):
    permission_classes = (HasAPIKey,)

    def post(self, request, *args, **kwargs):
        id = request.POST.get("id")
        sns = request.POST.get("sns")
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        res_id = id
        if sns not in ["kakao", "naver", "apple"]:
            return JsonResponse(
                {"msg": "sns value error ex) ['kakao', 'naver', 'apple']"}, status=400
            )
        else:
            res_id += "@" + sns[0]
        customer = Customer.objects.filter(username=res_id, is_active=False)
        if customer.exists():
            return JsonResponse(
                {"status": "fail", "msg": "user account disabled"}, status=403  # 200
            )
        tokens, status = get_uat_impersonate(res_id)
        if status == 403:  # 회원가입 필요
            return JsonResponse({"msg": "해당 소셜로그인의 유저가 존재하지 않습니다."}, status=302)
        else:
            return JsonResponse(
                {
                    "token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_type": "Bearer",
                },
                status=status,  # 200
            )


class SocialLoginAPIV1View(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.SocialLoginInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()

        context = jmf_check_sns(data["id"], data["sns"])
        if context["result"] == "200":
            username = context["igDataVal"]["memId"]
        else:  # 115
            return JsonResponse({"msg": "해당 소셜로그인의 유저가 존재하지 않습니다. jmf"}, status=302)

        customer = Customer.objects.filter(username=username, is_active=False)
        if customer.exists():
            return JsonResponse(
                {"status": "fail", "msg": "user account disabled"}, status=403  # 200
            )
        tokens, status = get_uat_impersonate(username)
        if status == 403:  # 회원가입 필요
            return JsonResponse({"msg": "해당 소셜로그인의 유저가 존재하지 않습니다. sso"}, status=302)
        else:
            if not Customer.objects.filter(username=username).exists():
                Customer.objects.create(username=username, is_jmf_auth=True, is_jmf_join=True)
            
            return JsonResponse(
                {
                    "token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_type": "Bearer",
                },
                status=status,  # 200
            )


class SocialRegistrationAPIView(APIView):
    permission_classes = (HasAPIKey,)

    def post(self, request, *args, **kwargs):
        id = request.POST.get("id")
        sns = request.POST.get("sns")
        name = request.POST.get("name")
        phone = request.POST.get("phone")
        res_id = id

        if name == "":
            return JsonResponse({"msg": "Invalid parameter."}, status=400)

        if sns not in ["kakao", "naver", "apple"]:
            return JsonResponse(
                {"msg": "sns value error ex) ['kakao', 'naver', 'apple']"}, status=400
            )
        else:
            res_id += "@" + sns[0]

        customer = Customer.objects.filter(username=res_id, is_active=False)
        if customer.exists():
            return JsonResponse(
                {"status": "fail", "msg": "user account disabled"}, status=403  # 200
            )
        enc = hashlib.md5()
        enc.update(f"{res_id}dif".encode("utf-8"))
        password = enc.hexdigest()
        tokens, status = get_uat_impersonate(res_id)
        if status == 403:  # 회원가입 필요
            headers = {
                "Authorization": f"Bearer {get_sat()}",
                "Content-Type": "application/json",
            }
            user_dict = {
                "username": res_id,
                "firstName": "",
                "lastName": "",
                "email": "",
                "enabled": True,
                "credentials": [
                    {"type": "password", "value": password, "temporary": False}
                ],
                "attributes": {
                    "name": name if name is not None else "",
                    "phone": phone if phone is not None else "",
                    "fruit_match": True,
                },
            }
            res = jmf_user_check(res_id)
            if res["result"] == "200":
                return JsonResponse({"msg": "already jmf exists"}, status=409)
            response = requests.request(
                "POST",
                OIDC_OP_SIGNUP_ENDPOINT,
                headers=headers,
                data=json.dumps(user_dict),
            )
            if response.status_code != 409:
                if res["result"] == "108":
                    res = jmf_user(res_id, password)
                    jmf_create_sns(id, sns, res_id)
                tokens, status = get_uat_impersonate(res_id)

                return JsonResponse(
                    {
                        "token": tokens["access_token"],
                        "refresh_token": tokens["refresh_token"],
                        "token_type": "Bearer",
                    },
                    status=201,
                )
            else:
                return JsonResponse({}, status=response.status_code)
        else:
            return JsonResponse(
                {
                    "token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_type": "Bearer",
                },
                status=status,  # 200
            )


class SocialRegistrationAPIV1View(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.SocialRegistrationInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        id = data["id"]
        sns = data["sns"]
        name = data["name"]
        phone = data["phone"]
        username = data["username"]
        if username == "":
            username += id + "@" + sns[0]

        context = jmf_check_sns(id, sns)
        if context["result"] == "200":
            return JsonResponse({"msg": "해당 소셜로그인의 유저가 이미 존재합니다."}, status=409)

        customer = Customer.objects.filter(username=username, is_active=False)
        if customer.exists():
            return JsonResponse(
                {"status": "fail", "msg": "user account disabled"}, status=403  # 200
            )
        enc = hashlib.md5()
        enc.update(f"{username}dif".encode("utf-8"))
        password = enc.hexdigest()
        tokens, status = get_uat_impersonate(username)
        if status == 403:  # 회원가입 필요
            headers = {
                "Authorization": f"Bearer {get_sat()}",
                "Content-Type": "application/json",
            }
            user_dict = {
                "username": username,
                "firstName": "",
                "lastName": "",
                "email": "",
                "enabled": True,
                "credentials": [
                    {"type": "password", "value": password, "temporary": False}
                ],
                "attributes": {
                    "name": name if name is not None else "",
                    "phone": phone if phone is not None else "",
                    "fruit_match": True,
                },
            }
            res = jmf_user_check(username)
            if res["result"] == "200":
                return JsonResponse({"msg": "already jmf exists"}, status=409)
            response = requests.request(
                "POST",
                OIDC_OP_SIGNUP_ENDPOINT,
                headers=headers,
                data=json.dumps(user_dict),
            )
            if response.status_code != 409:
                if res["result"] == "108":
                    res = jmf_user(username, password)
                    # 일단 토큰 2개는 안보내는걸로
                    jmf_create_sns(id, sns, username)
                tokens, status = get_uat_impersonate(username)

                if not Customer.objects.filter(username=username).exists():
                    Customer.objects.create(username=username)

                return JsonResponse(
                    {
                        "token": tokens["access_token"],
                        "refresh_token": tokens["refresh_token"],
                        "token_type": "Bearer",
                    },
                    status=201,
                )
            else:
                return JsonResponse({}, status=response.status_code)
        else:
            return JsonResponse({}, status=409)  # 200


class ResetPasswordCheckAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.ResetPasswordCheckInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()

        username = data["username"]
        receiver = data["phone"]

        users, status = search_user(username, get_sat())
        check = False
        for user in users:
            if user["username"] == username:
                check = True
                break
        if check == False:
            return JsonResponse(
                {
                    "status": "fail",
                    "msg": "user not exists",
                },
                status=200,
            )
        else:
            phone = ""
            if "attributes" in user:
                if "phone" in user["attributes"]:
                    phone = user["attributes"]["phone"][0]
            print(phone, receiver)
            if phone != receiver:
                return JsonResponse(
                    {
                        "status": "fail",
                        "msg": "User information does not match",
                    },
                    status=200,
                )
        return JsonResponse({"status": "success"}, status=200)
        # rand_num, send_response = send_sms(receiver, is_test)

        # if send_response['result_code'] != '1':
        #     return JsonResponse(
        #         {
        #             "result_code":send_response['result_code'],
        #             "message":send_response['message'],
        #         },
        #         status=400
        #     )
        # else:
        #     return JsonResponse(
        #         {"code":str(rand_num),
        #         "now":str(datetime.datetime.now())},
        #         status=200
        #     )


class ChangePasswordAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.ChangePasswordInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def put(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        SAT = get_sat()
        username = data["username"]
        password = data["password"]
        users, status = search_user(username, SAT)

        check = False
        ind = 0
        user = next((item for item in users if item["username"] == username), None)
        if user:
            check = True
        # for user in users:
        #     if user["username"] == username:
        #         check = True
        #         break
        #     ind += 1
        if check == False:
            return JsonResponse(
                {
                    "msg": "user not exists",
                },
                status=404,
            )
        elif check == True:
            status = change_password(user["id"], password, SAT)
            tokens, status = get_uat(username, password)
            res = jmf_user(username, password)
            customer = Customer.objects.filter(username=username)
            if customer.exists():
                customer = customer.first()
                customer.is_jmf_auth = True
                customer.save()
            return JsonResponse(
                {
                    "token": tokens["access_token"],
                    "refresh_token": tokens["refresh_token"],
                    "token_type": "Bearer",
                    "is_jmf_auth": True,
                },
                status=status,  # 200
            )


class CustomerDetailAPI(APIView):
    permission_classes = (HasAPIKey,)

    def get_object(self, username):
        try:
            return Customer.objects.get(username=username)
        except Customer.DoesNotExist:
            raise Http404

    def get(self, request, username, format=None):
        return JsonResponse(
            sz.CustomerSerializer(self.get_object(username)).data, status=200
        )


class QuestionAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.QuestionInputSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        context = get_username_from_uat(request)

        data["customer"] = Customer.objects.get(username=context["username"])
        question = Question.objects.create(**data)
        send_order_email(question)
        return JsonResponse(
            {"status": "success", "token": context["token"], "data": {}}, status=200
        )


class AppstoreRedirectView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.Android == True:
            return "https://play.google.com/store/apps/details?id=kr.dif.fruits"
        elif self.request.iOS == True:
            return "https://apps.apple.com/app/id1551060796"
        else:  # 모바일이 아닌경우 그냥 플레이 스토어로
            return "https://play.google.com/store/apps/details?id=kr.dif.fruits"


# 클라이언트에서 post로 전송해달라고 별도 요청
class SubscriptionAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.PhoneNumberSerializer

    @swagger_auto_schema(
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        response = jmf_subscription_check(data["phone"])
        if response["result"] == "200":
            return Response(True)
        else:
            return Response(False)


class TestNotification(GenericAPIView):
    permission_classes = (HasAPIKey,)
    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        customer = Customer.objects.get(username="testcode520")
        send_notification(customer.firebase_token,"메시지 타이틀","테스트 노티",1, action)
        return JsonResponse({"msg": "success"}, status=200)


class PassAuthenticationAPIView(GenericAPIView):
    permission_classes = (HasAPIKey,)
    @swagger_auto_schema()
    def post(self, request, *args, **kwargs):

        #bootpay access token 발급
        headers = {"Content-Type": "application/json"}
        data = '{"application_id": "5ffd22185b294800202a17fc", "private_key": "XNUYmHvVSUhY6nxtbqoLsOQL11ZuLm9cKOEXJZCR1Xc="}'
        response = requests.post("https://api.bootpay.co.kr/request/token", headers=headers, data=data)
        response = json.loads(response.text)
        if response["status"] == "500":
            return JsonResponse({"msg": response["message"], "data": "invalid data"}, status=500)
            
        access_token = response['data']['token']

        #본인인증 검증
        receipt_id=request.POST.get("receipt_id")
        headers = {"Authorization": access_token}
        response = requests.request("GET", "https://api.bootpay.co.kr/certificate/"+receipt_id, headers=headers)
        response_text = json.loads(response.text)
        response_data = response_text["data"]
        print(response_text)

        if response_text['status'] == 200:
            return JsonResponse({"msg": response_text["message"], "data": response_data}, status=200)
        else:
            return JsonResponse({"msg": response_text["message"], "data": "invalid data"}, status=500)


class Feedback(APIView):
    permission_classes = [permissions.AllowAny,]
    def post(self, request, *args, **kwargs):
        return HttpResponse("OK", content_type='text/plain')


class LifeLogUseAPIView(APIView):
    permission_classes = [permissions.AllowAny,]
    def get(self, request, *args, **kwargs):
        return JsonResponse({"data":False}, status=200)


class GodomallSubscriptionURLAPIView(APIView):
    permission_classes = (HasAPIKey,)
    def get(self, request, *args, **kwargs):
        return JsonResponse({"data":"https://on.kakao.com/search?q=%ec%a7%84%eb%a7%9b%ea%b3%bc+%ec%9c%a0%ec%a0%84%ec%9e%90"}, status=200)


class JMFSubscriptionURLAPIView(APIView):
    permission_classes = (HasAPIKey,)
    def get(self, request, *args, **kwargs):
        return JsonResponse({"data":"https://m.bestf.co.kr/goods/goods_list.php?cateCd=003"}, status=200)


class PassCheckAPIView(APIView):
    permission_classes = (HasAPIKey,)
    def get(self, request, *args, **kwargs):
        username = request.GET.get("username")
        
        customer = Customer.objects.filter(username=str(username))
        if len(customer) == 0:
            return JsonResponse({"data":"", "msg":"customer dose not exist."}, status=200)
        customer = customer.first()

        return JsonResponse({"is_pass_auth":customer.is_pass_auth, "msg":"success"}, status=200)

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username")
        customer = Customer.objects.filter(username__icontains=str(username))
        if len(customer) == 0:
            return JsonResponse({"data":str(username), "msg":"customer dose not exist."}, status=200)
        customer = customer.first()
        customer.is_pass_auth = True
        customer.save()
        return JsonResponse({"data":customer.is_pass_auth, "msg":"success"}, status=200)

    def patch(self, request, *args, **kwargs):
        username = request.POST.get("username")
        name = request.POST.get("name")
        gender = request.POST.get("gender")

        refresh_token = request.META.get("HTTP_REFRESHTOKEN", b"")
        token = request.META.get("HTTP_TOKEN", b"")
        if refresh_token == b"" or token == b"":
            return JsonResponse(
                {"status": "blank", "msg": "token, refresh_token blank"}, status=401
            )

        context = get_username_from_uat(request)

        SAT = get_sat()
        users, status = search_user(context["username"], SAT)
        user = next(
            (item for item in users if item["id"] == context["sub"]), None
        )  # 딕셔너리 서치로 찾아야함,
        attr_dict = {"name": "", "phone": "", "fruit_match": True}
        if user:
            if "attributes" in user:
                if "name" in user["attributes"]:
                    attr_dict["name"] = user["attributes"]["name"][0]
                if "phone" in user["attributes"]:
                    attr_dict["phone"] = user["attributes"]["phone"][0]
        else:
            return JsonResponse({"msg": "user not found"}, status=404)

        for target in ["name", "phone"]:
            attr_dict[target] = request.POST.get(target, attr_dict[target])
            customer = Customer.objects.get(username=context["username"])
            customer.name = request.POST.get(target, customer.name)
            customer.sex = "Male" if gender == "1" else "Female"
            customer.save()
        context, status = change_user_info(
            {"attributes": attr_dict}, context["sub"], SAT
        )
        return JsonResponse(context, status=status, safe=False)


class AcceptChoiceAgreeAPIView(APIView):
    permission_classes = [permissions.AllowAny,]
    def post(self, request, *args, **kwargs):
        username = request.POST.get("username")
        is_agree = request.POST.get("is_agree")

        customer = Customer.objects.filter(username__icontains=username)
        if len(customer) > 0:
            customer = customer.first()
            customer.is_choice_agree = is_agree
            return JsonResponse({"data":"success", "msg":"success"}, status=200)
        else:
            return JsonResponse({"data":"fail", "msg":f"{username} 사용자가 존재하지 않습니다."}, status=500)


class AppVersionAPIView(APIView):
    permission_classes = (HasAPIKey,)

    def get(self, request, *args, **kwargs):
        username = request.GET.get("username")
        app_version = request.GET.get("app_version")
        
        customer = Customer.objects.filter(username=str(username))
        if len(customer) == 0:
            return JsonResponse({"data":"", "msg":"customer dose not exist."}, status=400)
        customer = customer.first()

        #요청 앱 버전과 서버의 사용자 앱버전이 같은 경우
        if customer.app_version == app_version:
            return JsonResponse({"data":True, "msg":"version matched."}, status=200)
        else:
            #버전 정보가 일치하지 않음 (요청 앱 버전이 더 높은 경우)
            customer.app_version = app_version
            customer.save()
            return JsonResponse({"data":False, "msg":"version not matched."}, status=200)


class AppVersionCheckAPIView(APIView):
    permission_classes = (HasAPIKey,)

    def get(self, request, *args, **kwargs):
        username = request.GET.get("username")
        user_app_version = request.GET.get("app_version")
        
        customer = Customer.objects.filter(username=str(username))
        if len(customer) == 0:
            return JsonResponse({"data":"", "msg":"customer dose not exist."}, status=200)
        customer = customer.first()

        app_version = AppVersion.objects.filter(target="ANDROID"if customer.is_android else "IOS")
        if len(app_version) > 0:
            customer_app_version = customer.app_version

            if user_app_version:
                customer.app_version = user_app_version
                customer.save()
                
            return JsonResponse({"customer_version":customer_app_version, "recent_version":app_version.last().version,  "msg":"success"}, status=200)
        else:
            return JsonResponse({"msg":"version data not found."}, status=403)