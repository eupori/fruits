import requests
import urllib
import json
import csv
import os
import django
import datetime
import pandas as pd

from io import BytesIO as IO

from django.db.models import Sum
from django.core.management.base import BaseCommand, CommandError
from rest_framework import serializers
from fruitdb.models import *

# class SettlementSerializer(serializers.ModelSerializer):
#     month_price = serializers.SerializerMethodField()
#     product_code = serializers.SerializerMethodField()
#     product_name = serializers.SerializerMethodField()
#     kit_number = serializers.SerializerMethodField()
#     month_price = serializers.SerializerMethodField()

#     class Meta:
#         model = models.GeneticPromotionLog
#         fields = (
#             "item_name",
#             "connection_client",
#             "product_code",
#             "product_name",
#             "customer_name",
#             "customer_id",
#             "phone_number",
#             "kit_number",
#             "sign_datetime",
#             "current_month_times",
#             "left_times",
#             "accumulate_times",
#             "termination_datetime",
#             "month_price",
#             "coupon",
#         )
#         examples = {}

#     def month_price(self, obj):
#         return ""
#     def product_code(self, obj):
#         return ""
#     def product_name(self, obj):
#         return ""
#     def kit_number(self, obj):
#         return ""
#     def month_price(self, obj):
#         return ""

def get_settlement(first_datetime, last_datetime, macrogen_data_list):
    ###################################################
    ###################################################
    GeneticPromotionLog.objects.all().delete()
    ###################################################
    ###################################################
    test_list = []
    for each in [item["coupon"] for item in macrogen_data_list]:
        if each not in test_list:
            test_list.append(each)

    settlement_list = []
    for macrogen_data in macrogen_data_list:
        genetic_promotion_product, status = GeneticPromotionProduct.objects.get_or_create(
            product_code=macrogen_data["product_code"],
            connection_client=macrogen_data["connection_client"],
            product_name=macrogen_data["product_name"]
        )

        left_times = int(macrogen_data["total_times"]) - int(macrogen_data["current_month_times"])
        order_time = macrogen_data["order_time"].split(" ")[1] if len(macrogen_data["order_time"].split(" ")) > 1 else macrogen_data["order_time"]
        billing_price = macrogen_data["billing_price"] if macrogen_data["billing_price"] != "" else 0

        data = {
            "coupon": macrogen_data["coupon"],
            "order_date": macrogen_data["order_date"].split(" ")[0],
            "order_time": order_time,
            "item_name": macrogen_data["type"],
            "promotion_product": genetic_promotion_product,
            "customer_name": macrogen_data["customer_name"],
            "customer_id": macrogen_data["customer_id"],
            "phone_number": macrogen_data["phone_number"],
            "sign_datetime": macrogen_data["sign_datetime"],
            "action": macrogen_data["action"],
            "current_month_times": macrogen_data["current_month_times"],
            "left_times": left_times,
            "total_times": macrogen_data["total_times"],
            "accumulate_times": macrogen_data["accumulate_times"],
            "billing_price": billing_price
        }
        settlement_list.append(GeneticPromotionLog(**data))

    if len(settlement_list) > 0:
        GeneticPromotionLog.objects.bulk_create(settlement_list)

    first_date=datetime.datetime.strptime(first_datetime, '%Y-%m-%d %H:%M:%S')
    last_date=datetime.datetime.strptime(last_datetime, '%Y-%m-%d %H:%M:%S')
    settlements = GeneticPromotionLog.objects.filter(order_date__gte=first_date, order_date__lte=last_date)
    coupons = settlements.values_list("coupon", flat=True).distinct()

    person_data_list = []
    for coupon in coupons:
        person_objects = settlements.filter(coupon=coupon)
        person_data = person_objects.aggregate(정산금액=Sum("billing_price"))
        person_object = person_objects.last()
        person_data["쿠폰번호"] = coupon
        person_data["매출 항목명"] = person_object.item_name
        person_data["거래처"] = person_object.promotion_product.connection_client
        person_data["상품코드"] = person_object.promotion_product.product_code
        person_data["상품명"] = person_object.promotion_product.product_name
        person_data["고객명"] = person_object.customer_name
        person_data["아이디"] = person_object.customer_id
        person_data["이동전화번호"] = person_object.phone_number
        person_data["키트번호"] = person_object.promotion_kit.kit_code if person_object.promotion_kit else ""
        person_data["가입일"] = person_object.sign_datetime
        person_data["당월 배송 회차"] = person_object.current_month_times
        person_data["남은 회차"] = person_object.left_times
        person_data["월별 누적"] = person_object.accumulate_times
        person_data["해지일"] = person_object.termination_datetime if person_object.termination_datetime else ""
        person_data_list.append(person_data)

    df = pd.DataFrame.from_dict(person_data_list, orient='columns')

    # datatoexcel = pd.ExcelWriter('정산데이터.xlsx')
    # df.to_excel(datatoexcel, # directory and file name to write
    #     sheet_name = 'Sheet1', 
    #     na_rep = '', 
    #     header = True, 
    #     index = True, 
    #     index_label = "순번", 
    #     startrow = 0, 
    #     startcol = 0, 
    #     ) 
    # datatoexcel.save()

    excel_file = IO()
    xlwriter = pd.ExcelWriter(excel_file, engine='xlsxwriter')

    df.to_excel(xlwriter, 'sheet')

    xlwriter.save()
    # xlwriter.close()
    excel_file.seek(0)

    result = GeneticPromotionLogResult()
    today = datetime.datetime.now()
    
    result.result_file_excel.save('data'+today.strftime('%Y-%m-%d %H:%M:%S')+'.xlsx', excel_file, save=True)
    result.save()

    # GeneticPromotionLogResult.objects.create(result)
    
    # for each in settlements:
    #     print(each)

    

class Command(BaseCommand):
    help = '마크로젠 정산'

    def add_arguments(self, parser):
        parser.add_argument('macrogen_data')

    def handle(self, *args, **options):
        macrogen_data = options['macrogen_data']

        with open(macrogen_data, 'r') as f:
            macrogen_data_list = json.load(f)

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
        get_settlement(first_datetime, last_datetime, macrogen_data_list)

        # last_month_first = datetime(today.year, today.month, 1) + relativedelta(months=-1)
        # last_month_last = datetime(today.year, today.month, 1) + relativedelta(seconds=-1)

        # print('지난달 첫일: ' + last_month_first.strftime('%Y-%m-%d %H:%M:%S'))
        # print('지난달 말일: ' + last_month_last.strftime('%Y-%m-%d %H:%M:%S'))