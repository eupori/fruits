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

    cols = ["매출항목명", "이동전화번호", "구분", "키트번호(최초)", "키트번호(마지막 재채취)", "가입일", "해지일", "진맛과 비고", "마크로젠 비고", "키트상태",  "키트발송일",  "키트반송일",  "분석시작일",  "분석완료일", "누적 회차", "남은 회차"]
    etc = ["키트", "분석"]
    date_cols = []
    start_date = datetime.datetime.strptime("2022-05-23", "%Y-%m-%d").date()
    end_date = datetime.datetime.today().date() - datetime.timedelta(days=1)

    loop_date = start_date
    while loop_date.strftime("%y%m") != end_date.strftime("%y%m"):
        cols.append(loop_date.strftime("%Y년 %m월 청구매출"))
        date_cols.append(loop_date.strftime("%Y-%m"))
        loop_date+= relativedelta(months=1)
    
    genetic_tests = GeneticTest.objects.all()

    person_data_list = []
    for genetic_test in genetic_tests:
        if genetic_test.current_times ==0:
            genetic_test.current_times += 1
            genetic_test.save()
            continue

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

        kit_status = genetic_test.kit_status
        if genetic_test.current_times == genetic_test.total_times:
            billing_price = 1674
        else:
            billing_price = 1666

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

        for each in etc:
            person_data = {}
            for col in cols:
                person_data[col] = "-"
            person_data["매출항목명"] = "할부" if genetic_test.kit_status == "normal" else "해지"
            # person_data["이동전화번호"] = attr_dict["phone"]
            person_data["이동전화번호"] = genetic_test.phone.as_national
            person_data["구분"] = each
            person_data["키트번호(최초)"] = first_kit
            person_data["키트번호(마지막 재채취)"] = last_kit
            person_data["가입일"] = genetic_test.start_datetime.strftime("%Y.%m.%d")
            person_data["해지일"] = genetic_test.end_datetime.strftime("%Y.%m.%d") if genetic_test.end_datetime else "-"
            person_data["진맛과 비고"] = ""
            person_data["마크로젠 비고"] = ""
            person_data["키트상태"] = ""
            person_data["키트발송일"] = ""
            person_data["키트반송일"] = ""
            person_data["분석시작일"] = ""
            person_data["분석완료일"] = ""
            person_data["누적 회차"] = genetic_test.current_times
            person_data["남은 회차"] = genetic_test.total_times - genetic_test.current_times
            
            person_logs = genetic_test.genetictestlog_set.all()
            for pl in person_logs:
                person_data[f'{pl.order_date.strftime("%Y")}년 {pl.order_date.strftime("%m")}월 청구매출'] = pl.billing_price

            person_data_list.append(person_data)

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
