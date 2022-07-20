import requests
import urllib
import json
import csv
import os
import django
import datetime
import pandas as pd

import xmltodict
import openpyxl
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.db.models import Sum
from django.db.models import Q
from fruitdb.views.api.auth import get_username_from_uat, get_sat, search_user
from fruitdb.models import *
from dateutil.relativedelta import relativedelta
from rest_framework import serializers
from io import BytesIO as IO

from fruitsite.settings import (
    JMF_API_KEY,
)

JMF_API_URL = "https://bestf.co.kr/api/ig_member_info.php"


# 매일 08:00에 스크립트 동작
class Command(BaseCommand):
    help = '인실리코젠-진맛과 정산'

    def handle(self, *args, **options):
        today = datetime.datetime.today()
        # today = datetime.datetime.strptime("2021-05-16", '%Y-%m-%d')
        start_date = datetime.datetime.strftime(today, "%Y-%m-%d 00:00:01")
        # today = datetime.datetime.strptime("2022-05-16", '%Y-%m-%d')
        end_date = datetime.datetime.strftime(today, "%Y-%m-%d 23:59:59")

        url =f'{JMF_API_URL}?ig_type=dnacode&ig_key={JMF_API_KEY}&start_date={start_date}&end_date={end_date}'
        response = requests.request("GET", url)
        order_list = json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]


        if "igDataVal" in order_list.keys():
            for order in order_list["igDataVal"]:
                product, created = GeneticTestProduct.objects.get_or_create(product_code=order["buy_goodscd"], connection_client=order["mall"], product_name=order["buy_goodsnm"])
                sub, created = JMFSubscription.objects.get_or_create(sno=order["sno"])
                data = {
                    "sno": order["sno"],
                    "phone": order["tel"],
                    "customer": Customer.objects.filter(username=order["username"]).first(),
                    "coupon": order["use_code"],
                    "product": product,
                    "order_id": order["buy_orderno"],
                    "start_datetime": order["buy_date"],
                    "current_times": order["buy_cnt"],
                    "total_times": order["buy_cnt_total"],
                    "is_active":  True if order["canceldate"] == "0000-00-00 00:00:00" else False,
                    "is_coupon_used": True if order["use_yn"] == "0" else False,
                    # is_event=True if order["promotion"] == "1" else False,
                }

                targets = JMFSubscription.objects.filter(id=sub.id)
                targets.update(**data)

        # today = datetime.datetime.strptime("2021-05-16", '%Y-%m-%d')
        # start_date = datetime.datetime.strftime(today, "%Y-%m-%d 00:00:01")
        # today = datetime.datetime.strptime("2022-05-16", '%Y-%m-%d')
        # end_date = datetime.datetime.strftime(today, "%Y-%m-%d 23:59:59")
    
        url =f'{JMF_API_URL}?ig_type=dnacode_buy&ig_key={JMF_API_KEY}&start_date={start_date}&end_date={end_date}'
        response = requests.request("GET", url)
        payment_list = json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]

        if "es_dna_pay_info" in payment_list.keys():
            for payment in payment_list["es_dna_pay_info"]:
                print(payment)
                data = {
                    "order_date": payment["buy_date"],
                    "jmf_subscription": JMFSubscription.objects.filter(order_id=payment["buy_orderno"]).first(),
                    "action": "subscription",
                    "billing_price": payment["buy_price"],
                    "current_times": payment["buy_cnt"],
                    "registrant": User.objects.first(),
                }
                payment, created = JMFSubscriptionPaymentLog.objects.get_or_create(**data)