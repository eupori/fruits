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


def get_settlement(first_datetime, last_datetime):
    first_date=datetime.datetime.strptime(first_datetime, '%Y-%m-%d %H:%M:%S')
    last_date=datetime.datetime.strptime(last_datetime, '%Y-%m-%d %H:%M:%S')

    cols = ["매출항목명", "이동전화번호", "키트번호(최초)", "키트번호(마지막 재채취)", "가입일", "해지일", "키트 누적 회차", "키트 남은 회차", "검사 누적 회차", "검사 남은 회차"]
    date_cols = []
    start_date = datetime.datetime.strptime("2021-03-01", "%Y-%m-%d").date()
    end_date = datetime.datetime.today().date() - datetime.timedelta(days=1)

    loop_date = start_date
    while loop_date.strftime("%y%m") != end_date.strftime("%y%m"):
        cols.append(loop_date.strftime("%Y년 %m월 청구매출"))
        date_cols.append(loop_date.strftime("%Y-%m"))
        loop_date+= relativedelta(months=1)
    
    genetic_tests = GeneticTest.objects.filter(is_active=True)

    person_data_list = []
    for genetic_test in genetic_tests:
        print(genetic_test.kit_current_times)
        if genetic_test.kit_current_times ==0:
            genetic_test.kit_current_times += 1
            genetic_test.save()
            continue

        person_data = {}
        for each in cols:
            person_data[each] = "-"

        kits = GeneticTestKit.objects.filter(Q(genetic_test=genetic_test))
        if len(kits) == 0:
            first_kit = ""
            last_kit = ""
        elif len(kits) == 1:
            first_kit = kits.first().kit_code
            last_kit = ""
        elif len(kits) > 1:
            first_kit = kits.first().kit_code
            last_kit = kits.last().kit_code

        billing_price = 0
        
        if genetic_test.is_kit_active:
            if genetic_test.kit_current_times == genetic_test.total_times:
                billing_price += 1670
            else:
                billing_price += 1666
        if genetic_test.is_test_active:
            if genetic_test.test_current_times == genetic_test.total_times:
                billing_price += 1670
            else:
                billing_price += 1666


        kit_status = genetic_test.kit_status

        if kit_status == "normal":
            pass
        if kit_status == "cancel":
            billing_price = 0
            genetic_test.is_active = False
        elif kit_status == "damaged_kit_return":
            billing_price = 20000
            genetic_test.is_active = False
        elif kit_status == "normal_kit_return":
            billing_price = 6000
            genetic_test.is_active = False

        person_data["매출항목명"] = "할부" if genetic_test.kit_status == "normal" else genetic_test.get_kit_status_display()
        # person_data["이동전화번호"] = attr_dict["phone"]
        person_data["이동전화번호"] = genetic_test.phone.as_national
        person_data["키트번호(최초)"] = first_kit
        person_data["키트번호(마지막 재채취)"] = last_kit
        person_data["가입일"] = genetic_test.start_datetime.strftime("%Y.%m.%d")
        person_data["해지일"] = genetic_test.end_datetime.strftime("%Y.%m.%d") if genetic_test.end_datetime else "-"
        person_data["키트 누적 회차"] = genetic_test.kit_current_times
        person_data["키트 남은 회차"] = genetic_test.total_times - genetic_test.kit_current_times
        person_data["검사 누적 회차"] = genetic_test.test_current_times
        person_data["검사 남은 회차"] = genetic_test.total_times - genetic_test.kit_current_times
        
        person_logs = genetic_test.genetictestlog_set.all()
        for pl in person_logs:
            person_data[f'{pl.order_date.strftime("%Y")}년 {pl.order_date.strftime("%m")}월 청구매출'] = pl.billing_price

        person_data_list.append(person_data)

        GeneticTestLog.objects.create(
            order_date=datetime.datetime.now(),
            genetic_test=genetic_test,
            action="subscription",
            billing_price=billing_price,
            kit_current_times=genetic_test.kit_current_times,
            test_current_times=genetic_test.test_current_times,
        )

        if genetic_test.current_times == genetic_test.total_times:
            genetic_test.is_kit_active = False
            genetic_test.end_datetime = datetime.datetime.now()

        if genetic_test.is_kit_active:
            genetic_test.kit_current_times += 1
        if genetic_test.is_test_active:
            genetic_test.test_current_times += 1

        genetic_test.save()

    df = pd.DataFrame.from_dict(person_data_list, orient='columns')
    df = df.fillna("-")
    df.to_excel("qwert.xlsx", index=False)
    print(df)


# 매달 말일 23:59:59에 스크립트 동작
class Command(BaseCommand):
    help = '마크로젠 정산'

    def handle(self, *args, **options):
        today = datetime.datetime.today()
        this_month_first = datetime.datetime(today.year, today.month, 1)
        next_month = datetime.datetime(today.year, today.month, 1) + relativedelta(months=1)
        this_month_last = next_month + relativedelta(seconds=-1)

        print('이번달 첫일: ' + this_month_first.strftime('%Y-%m-%d %H:%M:%S'))
        print('이번달 말일: ' + this_month_last.strftime('%Y-%m-%d %H:%M:%S'))

        first_datetime = this_month_first.strftime('%Y-%m-%d %H:%M:%S')
        last_datetime = this_month_last.strftime('%Y-%m-%d %H:%M:%S')
        last_date = this_month_last.strftime('%Y-%m-%d')
        
        # if today.strftime('%Y-%m-%d') == last_date:
        #     get_settlement(first_datetime, last_datetime, macrogen_data_list)
        get_settlement(first_datetime, last_datetime)

        # last_month_first = datetime(today.year, today.month, 1) + relativedelta(months=-1)
        # last_month_last = datetime(today.year, today.month, 1) + relativedelta(seconds=-1)

        # print('지난달 첫일: ' + last_month_first.strftime('%Y-%m-%d %H:%M:%S'))
        # print('지난달 말일: ' + last_month_last.strftime('%Y-%m-%d %H:%M:%S'))