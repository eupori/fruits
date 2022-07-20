import requests
import urllib
import json
import csv
import os
import django
import datetime
import xmltodict
import pandas as pd

from io import BytesIO as IO

from django.db.models import Sum
from django.core.management.base import BaseCommand, CommandError
from rest_framework import serializers
from fruitdb.models import *

JMF_URL = "https://bestf.co.kr"


def add_coupon(subscription_on_data_list):
    ###################################################
    ###################################################
    GeneticPromotion.objects.all().delete()
    GeneticPromotionLog.objects.all().delete()
    ###################################################
    ###################################################

    test_list = []
    for each in [item["coupon"] for item in subscription_on_data_list]:
        if each not in test_list:
            test_list.append(each)

    genetic_promotion_data_list = []
    for subscription_on_data in subscription_on_data_list:
        genetic_promotion_product, status = GeneticPromotionProduct.objects.get_or_create(
            product_code=subscription_on_data["product_code"],
            connection_client=subscription_on_data["connection_client"],
            product_name=subscription_on_data["product_name"]
        )

        genetic_promotion_data = {
            "coupon": subscription_on_data["coupon"],
            "promotion_product": genetic_promotion_product,
            "customer_name": subscription_on_data["customer_name"],
            "customer_id": subscription_on_data["customer_id"],
            "phone_number": subscription_on_data["phone_number"],
            "total_times": subscription_on_data["total_times"],
            "sign_datetime": subscription_on_data["sign_datetime"],
        }
        
        genetic_promotion_data_list.append(GeneticPromotion(**genetic_promotion_data))

    if len(genetic_promotion_data_list) > 0:
        GeneticPromotion.objects.bulk_create(genetic_promotion_data_list, ignore_conflicts=True)

    genetic_promotion_log_list = []
    for subscription_on in subscription_on_data_list:
        left_times = int(subscription_on["total_times"]) - int(subscription_on["current_month_times"])
        order_time = subscription_on["order_time"].split(" ")[1] if len(subscription_on["order_time"].split(" ")) > 1 else subscription_on["order_time"]
        billing_price = subscription_on["billing_price"] if subscription_on["billing_price"] != "" else 0
        genetic_promotion = GeneticPromotion.objects.get(coupon=subscription_on["coupon"])

        data = {
            "order_date": subscription_on["order_date"].split(" ")[0],
            "order_time": order_time,
            "item_name": subscription_on["type"],
            "genetic_promotion": genetic_promotion,
            "action": subscription_on["action"],
            "current_month_times": subscription_on["current_month_times"],
            "left_times": left_times,
            "accumulate_times": subscription_on["accumulate_times"],
            "billing_price": billing_price
        }
        genetic_promotion_log_list.append(GeneticPromotionLog(**data))

    if len(genetic_promotion_log_list) > 0:
        GeneticPromotionLog.objects.bulk_create(genetic_promotion_log_list)

    

class Command(BaseCommand):
    help = '마크로젠 정산'

    def add_arguments(self, parser):
        parser.add_argument('macrogen_data')

    def handle(self, *args, **options):
        subscription_on_data = options['macrogen_data']

        # today = datetime.datetime.today().strftime('%Y-%m-%d')

        with open(subscription_on_data, 'r') as f:
            subscription_on_data_list = json.load(f)

        user_info_url = "/api/ig_member_info.php"
        url =f'{JMF_URL}{user_info_url}?ig_type=dnacode&ig_key=6372de22646ce93b0a39e3758bd977ce'
        response = requests.request("GET", url)
        orders = json.loads(json.dumps(xmltodict.parse(response.text)))["igData"]["igDataVal"]

        for order in orders:
            product = {
                "product_code", order["buy_goodscd"],
                "connection_client", order["buy_shop"],
                "product_name", order["buy_goodsnm"]
            }
            genetic_promotion_product, status = GeneticPromotionProduct.objects.get_or_create(**product)
            
            genetic_promotion_data = {
                "coupon": order["use_code"],
                "customer_name": order["username"],
                "customer_id": order["use_mem_no"],
                "phone_number": order["tel"],
                "total_times": order["buy_cnt_total"],
                "sign_datetime": order["buy_date"],
                "termination_datetime": order["termination_datetime"],
                "promotion_product": genetic_promotion_product,
            }
            genetic_promotion, status = GeneticPromotion.objects.get_or_create(**genetic_promotion_data)

            action = "order_confirmed" if order["buy_cnt"] == "1" else "subscription"
            log = {
                "order_date": order["buy_datetime"].split(" ")[0],
                "order_time": order["buy_datetime"].split(" ")[1],
                "item_name": order["buy_goods_nm"],
                "action": action,
                "current_month_times": order["buy_cnt"],
                "left_times": int(order["buy_tot_cnt"]) - int(order["buy_cnt"]),
                # "accumulate_times": order[""],
                "genetic_promotion": genetic_promotion,
                "billing_price": order["buy_price"]
            }

        # add_coupon(subscription_on_data_list)