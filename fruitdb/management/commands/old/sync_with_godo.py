import requests
import urllib
import json
import sys
import csv
import os
import django

from django.core.management.base import BaseCommand, CommandError

from fruitdb.views.api.auth import jmf_user, jmf_user_check, JMF_API_KEY

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

def create_user_in_godo(memId, memPw):
    response = jmf_user({
        'ig_key': JMF_API_KEY,
        'ig_type': 'regMember',
        'memId': memId,
        'memPw': 'diftest',
    })
    assert(response['result'] == '200')

    response = jmf_user_check(memId)
    assert(response['result'] == '200')
    memNo = response['igDataVal']['memNo']
    return memNo


class Command(BaseCommand):
    help = '과일궁합-고도몰 데이터 통기화: 고도몰 고객테이블 덤프자료에서 SSO에 등록된 고객정보를 확인하고, 이를 다시 API로 고도몰에 등록함. 해당 사용자의 정보를 csv로 다시 저장하여, 이를 참고로 비밀번호 변경할 수 있도록 함'

    def add_arguments(self, parser):
        parser.add_argument('godo_dump_sql')

    def handle(self, *args, **options):
        godo_dump_sql = options['godo_dump_sql']
        token = get_token()

        # test
        #memNo = create_user_in_godo('diftest2', 'abcd')
        #print('memNo...', memNo)

        writer = csv.writer(sys.stdout)
        writer.writerow(['memNo', 'memId', 'memPw', 'mileage'])
        with open(godo_dump_sql) as ifile:
            for record in csv.reader(ifile):
                memId = record[2].replace("'", '').replace('"', '').strip()
                memPw = record[9].replace("'", '').replace('"', '').strip()
                mileage = record[39].replace("'", '').replace('"', '').strip()

                if is_in_sso(token, memId):
                    memNo = create_user_in_godo(memId, memPw)
                    writer.writerow([memNo, memId, memPw, mileage])

