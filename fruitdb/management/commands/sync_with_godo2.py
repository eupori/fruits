import requests
import urllib
import json
import sys
import csv
import os
import django

from django.core.management.base import BaseCommand, CommandError

from fruitdb.models import Customer
from fruitdb.views.api.auth import jmf_user, jmf_user_check, JMF_API_KEY, jmf_create_sns, get_sat, delete_user, jmf_user_auth_check, jmf_check_sns, change_user_info, search_user, get_uat_impersonate
from fruitsite.settings import OIDC_OP_TOKEN_ENDPOINT, OIDC_OP_SIGNUP_ENDPOINT

SSO_HOST = 'sso.d-if.kr'
CLIENT_ID = 'd.if'
CLIENT_SECRET = '169e3c2a-4385-422d-949c-4f27f947b78a'

def get_token():
    response = requests.post(
        f'https://{SSO_HOST}/auth/realms/d.if/protocol/openid-connect/token',
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials',
        },
    )
    assert(response.status_code == 200)
    result = json.loads(response.text)
    return result['access_token']

def is_in_sso(token, userid):
    response = requests.get(
        f'https://{SSO_HOST}/auth/admin/realms/d.if/users?username={userid}',
        headers={
            'Authorization': f'Bearer {token}',
        },
    )
    assert(response.status_code == 200)
    for user in json.loads(response.text):
        if user['username'] == userid:
            return True
    #sys.stderr.write(f'{userid} is not in SSO\n')
    return False

def create_user_in_godo_sns(memId, memPw, sns):
    response = jmf_user(memId, memPw,)
    if sns:
        if sns == "@k":
            sns = "kakao"
        elif sns == "@n":
            sns = "naver"
        elif sns == "@a":
            sns = "apple"

    jmf_create_sns(memId.split("@")[0], sns, memId)
    assert(response['result'] == '200')

    response = jmf_user_check(memId)
    print(response)
    assert(response['result'] == '200')
    memNo = response['igDataVal']['memNo']
    return memNo

def create_user_in_godo(memId, memPw):
    response = jmf_user(memId, memPw,)

    assert(response['result'] == '200')

    response = jmf_user_check(memId)
    print(response)
    assert(response['result'] == '200')
    memNo = response['igDataVal']['memNo']
    return memNo


def create_user_in_sso(memId, memPw, email, phone, name):
    #signup
    sat = get_sat()
    url = "https://sso.d-if.kr/auth/admin/realms/d.if/users"
    method = "POST"
    header = {
        "Authorization": "Bearer " + sat,
        "Content-Type": "application/json"
    }
    body = {
        "username": memId,
        "email": "",
        "enabled": True,
        "credentials": [
            {"type": "password", "value": memPw, "temporary": False}
        ],
        # "credentials": [
        #     {
        #         "type": "password",
        #         "algorithm": "bcrypt",
        #         "hashedSaltedValue": "qwer1234",
        #         "hashIterations": 10,
        #         "salt": "",
        #         "temporary": False
        #     }
        # ],
        "attributes": {
            "phone": phone,
            "name": name,
        },
    }

    response = requests.request(method, url, headers=header, data=json.dumps(body))
    print(response.text)
    print(response.status_code)

    return response

def create_customer_in_fruit(username, is_jmf_auth, name=None):
    data = {
        "username": username,
        "is_jmf_auth": is_jmf_auth,
    }
    if name:
        data.update({"name":name})
    
    if not Customer.objects.filter(username=username).exists():
        Customer.objects.create(**data)

def delete_user_in_sso(user_pk):
    #signup
    sat = get_sat()
    url = "https://sso.d-if.kr/auth/admin/realms/d.if/users/"+user_pk
    method = "DELETE"
    header = {
        "Authorization": "Bearer " + sat,
        "Content-Type": "application/json"
    }
    response = requests.request(method, url, headers=header)
    print(response.text)
    print(response.status_code)

    return response


class Command(BaseCommand):
    help = '과일궁합-고도몰 데이터 통기화: 고도몰 고객테이블 덤프자료와 SNS 덤프 자료를 이용하여 고도몰에만 있는 사용자는 SSO, Fruits 서버에 추가하고, SSO에만 있는 사용자는 고도몰에 추가함'

    def add_arguments(self, parser):
        parser.add_argument('godo_member_dump_sql')
        parser.add_argument('godo_sns_dump_sql')
        parser.add_argument('sso_member_dump_json')
        parser.add_argument('godo_member_dev_sql')
        parser.add_argument('godo_sns_dev_sql')

    def handle(self, *args, **options):
        member_dump = options['godo_member_dump_sql']
        sns_dump = options['godo_sns_dump_sql']
        sso_dump = options['sso_member_dump_json']
        member_dev = options['godo_member_dev_sql']
        sns_dev = options['godo_sns_dev_sql']

        with open(sso_dump, 'r') as f:
            sso_users=json.load(f)

        sso_members = []
        for ind, each in enumerate(sso_users):
            sso_data = {"sub": each["id"],"id": each["username"],"name": each["attributes"]["name"][0] if "attributes" in each and "name" in each["attributes"] else "","phone":  each["attributes"]["phone"][0] if "attributes" in each and "phone" in each["attributes"] else "","password": json.loads(each["credentials"][0]["secretData"])["value"] if len(each["credentials"]) > 0 else "","salt": json.loads(each["credentials"][0]["secretData"])["salt"] if len(each["credentials"]) > 0 else "","hashIterations": json.loads(each["credentials"][0]["credentialData"])["hashIterations"] if len(each["credentials"]) > 0 else "","algorithm": json.loads(each["credentials"][0]["credentialData"])["algorithm"] if len(each["credentials"]) > 0 else "","credentials":each["credentials"],"attributes": each["attributes"] if "attributes" in each else None,}
            sso_members.append(sso_data)

        token = get_token()

        clean = lambda x: x.replace("'", '').replace('(', '').replace(')', '')
        
        members = {}
        godo_members = []
        with open(member_dump) as file:
            for ind, line in enumerate(file):
                if line.startswith('('):
                    words = clean(line).split(',')
                    words = [w.strip() for w in words]
                    mem_id = words[2]
                    members[mem_id] = words
                    data = {
                        "pk": words[0],
                        "id": words[2],
                        "name": words[6],
                        "email": words[20],
                        "phone": words[28],
                        "password": words[9],
                    }
                    godo_members.append(data)

        godo_dev_members = []
        with open(member_dev) as file:
            for ind, line in enumerate(file):
                if line.startswith('('):
                    words = clean(line).split(',')
                    words = [w.strip() for w in words]
                    mem_id = words[2]
                    data = {
                        "pk": words[0],
                        "id": words[2],
                        "name": words[6],
                        "email": words[20],
                        "phone": words[28],
                        "password": words[9],
                    }
                    godo_dev_members.append(data)

        godo_pk_name_table = {item["pk"]:item["id"] for item in godo_dev_members }
        godo_pk_person_name_table = {item["pk"]:item["name"] for item in godo_dev_members }
        godo_sns_members = []
        with open(sns_dev) as file:
            for ind, line in enumerate(file):
                if line.startswith('('):
                    words = clean(line).split(',')
                    words = [w.strip() for w in words]
                    if words[2] != '0':
                        mem_id = words[2]
                        data = {
                            "username": godo_pk_name_table[words[2]],
                            "id": words[4],
                            "sns": words[6],
                            "name": godo_pk_person_name_table[words[2]]
                        }
                        godo_sns_members.append(data)

        exist_members = []
        exist_table_godo = {item["id"]:item for item in godo_members}
        godo_ids = [item['id'] for item in godo_members]
        for sso in sso_members:
            if sso["id"] in godo_ids:
                exist_members.append(sso)

        sso_ids = [item['id'] for item in sso_members]
        exist_ids = [item['id'] for item in exist_members]

        print("SSO 계정 : " + str(len(sso_members)))
        print("고도몰 계정 : " + str(len(godo_members)))
        print("#####################################")
        print("고도몰에만 있는 계정 : " + str(len(set(godo_ids) - set(exist_ids))))
        print("SSO에만 있는 계정 : " + str(len(set(sso_ids) - set(exist_ids))))
        print("중복 계정 : " + str(len(exist_members)))
        print("SNS 계정 : " + str(len(godo_sns_members)))

        # # 고도몰에만 있는 계정 (SSO에 등록)
        # print("고도몰에만 있는 계정 (SSO에 등록)")
        # # for godo in godo_members:
        # #     if godo["id"] in (set(godo_ids) - set(exist_ids)):
        # #         print("create_user_in_sso : ", godo["id"], godo["password"], godo["email"], godo["phone"], godo["name"])
        # #         create_user_in_sso(godo["id"], godo["password"], godo["email"], godo["phone"], godo["name"])
        # #         create_customer_in_fruit(godo["id"], True, godo["name"])


        # # SSO 계정
        # print("SSO계정")
        # em_table = {item['id']:item for item in exist_members}
        # for sso in sso_members:
        #     # SSO에만 있는 계정(godomall에 등록)
        #     print("SSO에만 있는 계정(godomall에 등록)")
        #     if sso["id"] in (set(sso_ids) - set(exist_ids)):
        #         if sso["id"][-2:] in ["@k", "@n", "@a"]:
        #             print("create_user_in_godo_sns : ", sso["id"], sso["password"], sso["id"][-2:])
        #             create_user_in_godo_sns(sso["id"], sso["password"], sso["id"][-2:])
        #         else:
        #             print("create_user_in_godo : ", sso["id"], sso["password"])
        #             create_user_in_godo(sso["id"], sso["password"])

        #         if not Customer.objects.filter(username=sso["id"]).exists():
        #             print("create_customer_in_fruit : ", sso["id"], False, sso["name"])
        #             create_customer_in_fruit(sso["id"], False, sso["name"])

        #     # 중복 계정
        #     print("중복계정")
        #     if sso["id"] in em_table.keys():
        #         exist = em_table[sso["id"]] # exist
        #         godo = exist_table_godo[sso["id"]]
        #         if godo["password"] == "":
        #             godo["password"] = "q1w2e3r4t5y6u7i8o9p0"
        #         if sso["phone"] == godo["phone"]:
        #             # 동일 사용자 계정이 양측에 있을 경우
        #             # 우리쪽 데이터 고도몰에 전달
        #             #커스터머 확인 후 생성
        #             if not Customer.objects.filter(username=godo["id"]).exists():
        #                 print("동일 사용자일 경우 Customer 생성")
        #                 create_customer_in_fruit(godo["id"], False, sso["name"])
        #         else:
        #             #id만 같은 다른 사용자가 있을 경우
        #             #sso계정 삭제
        #             print("sso계정 삭제")
        #             delete_user_in_sso(sso["sub"])
        #             #고도몰 데이터를 sso에 등록
        #             print("고도몰 데이터를 sso에 등록")
        #             create_user_in_sso(godo["id"], godo["password"], godo["email"], godo["phone"], godo["name"])

        #             #커스터머 확인 후 생성
        #             if Customer.objects.filter(username=godo["id"]).exists():
        #                 print("Customer 확인 후 생성")
        #                 Customer.objects.filter(username=godo["id"]).delete()
        #             create_customer_in_fruit(godo["id"], True, godo["name"])

        # sso_members_ids = [ item["id"] for item in sso_members ]
        # sso_sns_filtered = list(filter(lambda x: (x["username"] in sso_members_ids) and ("@" not in x["username"]), godo_sns_members))


        # # SSO에만 있는 계정 중 @가 없는 SNS 계정 추가
        # print("SSO에만 있는 계정 중 @가 없는 SNS 계정")
        # exist_sns_list = []
        # for item in sso_sns_filtered:
        #     res = jmf_check_sns(item["id"], item["sns"])
        #     if res["result"] == "200":
        #         print("pass")
        #         exist_sns_list.append({
        #             "memId": res["igDataVal"]["memId"],
        #             "username": item["username"],
        #             })
        #     else:
        #         print("jmf_create_sns: ", item["id"], item["sns"], item["username"])
        #         jmf_create_sns(item["id"], item["sns"], item["username"])
        #         if not Customer.objects.filter(username=item["username"]).exists():
        #             print("Customer 확인 후 생성")
        #             create_customer_in_fruit(item["username"], False, item["name"])

        sso_ids = [item['id'] for item in sso_members]
        exist_ids = [item['id'] for item in exist_members]
        only_sso_ids = list(filter(lambda x: x not in exist_ids, sso_ids))
        godo_dev_member_ids = [item['id'] for item in godo_dev_members]


        target_ids = list(set(only_sso_ids) & set(godo_dev_member_ids))
        # for sso in only_sso_members:
        sso_table = {item['id']:item for item in sso_members}
        flag = False
        for each in sso_table:
            if sso_table[each]["id"] == "service-account-d.if":
                flag = True
                continue
            if not flag:
                continue
            print(sso_table[each]["id"])
            sat = get_sat()
            data = {"credentials":sso_table[each]["credentials"]}
            if sso_table[each]["attributes"]:
                data["attributes"] = sso_table[each]["attributes"]

            # sub = sso_table[each]["sub"]
            users, status = search_user(sso_table[each]['id'], sat)
            user = next(
            (item for item in users if item["username"] == sso_table[each]["id"]), None)
            if user:
                delete_user(user["id"], sat)

            headers = {
                "Authorization": f"Bearer {sat}",
                "Content-Type": "application/json",
            }
            user_dict = {
                "username": sso_table[each]["id"],
                "firstName": "",
                "lastName": "",
                "email": "",
                "enabled": True,
                "credentials": sso_table[each]["credentials"]
            }
            if sso_table[each]["attributes"]:
                user_dict["attributes"] = sso_table[each]["attributes"]

            response = requests.request(
                "POST", OIDC_OP_SIGNUP_ENDPOINT, headers=headers, data=json.dumps(user_dict)
            )
            print(response.status_code)
            print(response.text)