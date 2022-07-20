import requests
import urllib
import json
import csv
import os
import django
import datetime
import pandas as pd


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
    GENETIC_API_HOST,
    GENETIC_API_TOKEN,
)

def macrogen_kit_cancel(genetic_test, client_key):
    kit = genetic_test.genetictestkit_set.first()
    url = f"{GENETIC_API_HOST}/cancel"
    headers={
        'Authorization': f'Bearer {GENETIC_API_TOKEN}',
        'Content-Type': 'application/json;charset=utf-8',
    },
    if kit.invoice_datetime + datetime.timedelta(days=180) > datetime.datetime.now():
        cancel_type = "auto_cancel"
    else:
        cancel_type = "req_cancel"

    data = {
        "client_key" : client_key,
        "cancel_type": cancel_type,
        "cancel_date": str(datetime.datetime.now())
    }
    response = requests.request("PUT", url, headers=headers,data=json.dumps(data))
    if response.status_code == 200:
        return json.loads(response.text)


# 매달 말일 23:59:59에 스크립트 동작
class Command(BaseCommand):
    help = '마크로젠 정산'

    def handle(self, *args, **options):
        tests = GeneticTest.objects.filter(is_active=True, kit_status="normal", status="status")

        for test in tests:
            kits = GeneticTestKit.objects.filter(genetic_test=test)
            if len(kits) > 0:
                kit = kits.first()
            else:
                print("kit does not exist.")
                return
            subs = JMFSubscription.objects.filter(coupon=test.coupon)
            if len(subs) == 1:
                sub = subs.first()
            else:
                print("jmf subscription does not exist.")
                return

            if kit.invoice_datetime + datetime.timedelta(days=180) > datetime.datetime.now():
                response_data = macrogen_kit_cancel(test, test.customer.username)
                if response_data["process"] == "end" and response_data["charge_type"] == "2":
                    GeneticTestLog.objects.create(
                        order_date=datetime.datetime.now(),
                        genetic_test=test,
                        action="normal_kit_cancel",
                        billing_price=0,
                        current_times=tests.genetictestlog_set.last().current_times,
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