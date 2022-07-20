# Copyright 2022 by Heejea Cho, The Insilicogen.

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

class Settlement():
    def __init__(self):
        self.today = datetime.date.today()
        self.url = "https://shopman.d-if.kr"
        self.file_name = "data/settlement.xlsx"

        self.subs = JMFSubscription.objects.filter(
            start_datetime__year=self.today.year,
            start_datetime__month=self.today.month
            )

    # 구독상품 정산
    def subscription_product(self):
        payment_log = JMFSubscriptionPaymentLog.objects.filter(
            action="subscription",
            order_date__year=self.today.year,
            order_date__month=self.today.month
            )
        genetic_test_products = GeneticTestProduct.objects.all()
        datas_list = []

        for genetic_test_product in genetic_test_products:
            in_round_subs = self.subs.filter(
                product=genetic_test_product,
                is_active=True,
                is_coupon_used=True,
                current_times__lte=12
                )
            out_round_subs = self.subs.filter(
                product=genetic_test_product,
                is_active=True,
                is_coupon_used=True,
                current_times__gt=12
                )
            coupon_unused_subs = self.subs.filter(
                    product=genetic_test_product,
                    is_active=True,
                    is_coupon_used=False
                    )
            cancel_subs =  self.subs.filter(
                    product=genetic_test_product,
                    is_active=False,
                    end_datetime__year=self.today.year,
                    end_datetime__month=self.today.month
                    )
            in_round_logs = payment_log.filter(jmf_subscription__in=in_round_subs)
            out_round_logs = payment_log.filter(jmf_subscription__in=out_round_subs)
            coupon_unused_logs = payment_log.filter(jmf_subscription__in=coupon_unused_subs)
            cancel_logs = payment_log.filter(jmf_subscription__in=cancel_subs)

            datas = {}
            datas["구독 플랫폼"] = genetic_test_product.get_connection_client_display()
            datas["구독 상품"] = genetic_test_product.product_name
            datas["구독중 회원"] = len(self.subs.filter(product=genetic_test_product, is_active=True))
            datas["회차 내 회원(12회차 이전)"] = len(in_round_subs)
            datas["회차 내 회원 결제 건수"] = len(in_round_logs)
            datas["회차 내 회원 결제 금액"] = sum(in_round_logs.values_list("billing_price", flat=True))
            datas["회차 완료 회원(12회차 이후)"] = len(out_round_subs)
            datas["회차 완료 회원 결제 건수"] = len(out_round_logs)
            datas["회차 완료 회원 결제 금액"] = sum(out_round_logs.values_list("billing_price", flat=True))
            datas["쿠폰 미사용 회원"] = len(coupon_unused_subs)
            datas["쿠폰 미사용 회원 결제 건수"] = len(coupon_unused_logs)
            datas["쿠폰 미사용 회원 결제 금액"] = sum(coupon_unused_logs.values_list("billing_price", flat=True))
            datas["해지 회원"] = len(cancel_subs)
            datas["해지 회원 결제 건수"] = len(cancel_logs)
            datas["해지 회원 결제 금액"] = sum(cancel_logs.values_list("billing_price", flat=True))
            datas["총 결제 건 수"] = len(in_round_logs) \
                                                                   + len(out_round_logs) \
                                         + len(coupon_unused_logs) \
                                         + len(cancel_logs)
            datas["매출액"] = sum(in_round_logs.values_list("billing_price", flat=True)) \
                                 + sum(out_round_logs.values_list("billing_price", flat=True)) \
                                 + sum(coupon_unused_logs.values_list("billing_price", flat=True)) \
                                 + sum(cancel_logs.values_list("billing_price", flat=True))

            w = sum(in_round_logs.values_list("billing_price", flat=True))*0.07
            x = sum(out_round_logs.values_list("billing_price", flat=True))*0.1
            y = sum(coupon_unused_logs.values_list("billing_price", flat=True))*0.07
            z = sum(cancel_logs.values_list("billing_price", flat=True))*0.07 \
                + sum([ item.current_times*item.product.billing_price for item in cancel_subs ])*0.03
            datas["수수료 정산"] = w+x+y+z
            datas_list.append(datas)

        subscription_product = pd.DataFrame.from_dict(datas_list, orient='columns')
        if not os.path.exists(self.file_name):
            with pd.ExcelWriter(self.file_name, engine='openpyxl', mode='w') as writer:
                subscription_product.to_excel(writer, sheet_name="구독상품", index=False)
        else:
            with pd.ExcelWriter(self.file_name, engine='openpyxl', mode='a') as writer:
                subscription_product.to_excel(writer, sheet_name="구독상품", index=False)

    # 단품상품 정산
    def single_product(self):
        url = self.url
        order_data_list = []

        response = requests.request("GET", f"{url}/product/fruits")
        products = json.loads(response.text)["data"]

        response = requests.request("GET", f"{url}/order/fruits?type=daily")
        order_list = json.loads(response.text)["data"]

        response = requests.request("GET", f"{url}/paymentlog/fruits?type=daily")
        paymentlog_list = json.loads(response.text)["data"]

        ordered_product_ids = list(set([item["product_id"] for item in order_list]))
        ordered_product_list = []
        for product in products:
            if product["id"] in ordered_product_ids:
                ordered_product_list.append(product)
        
        for product in ordered_product_list:
            sell_list = []
            refund_list = []
            sell_price = 0
            refund_price = 0

            for payment in paymentlog_list:
                target_order = None
                for order in order_list:
                    if payment["order_id"] == order["id"]:
                        target_order = order
                if target_order:
                    if target_order["product_id"] == product["id"] \
                            and payment["method"] == "card" \
                            and target_order["price"] != 0 \
                            and payment["payment_name"] == "카드결제":
                        sell_list.append(target_order)
                    elif target_order["product_id"] == product["id"] \
                            and payment["method"] == None \
                            and payment["payment_name"] == "결제 취소":
                        refund_list.append(target_order)

            name = product["name"]
            price = product["price"]
            sell_cnt = len(sell_list)
            sell_price = sum(
                    [int(int(item["price"])/1.1) if item["product_id"]==53 else int(item["price"]) for item in sell_list])
            refund_cnt = len(refund_list)
            refund_price = sum(
                    [int(int(item["price"])/1.1) if item["product_id"]==53 else int(item["price"]) for item in refund_list])

            order_data = {}
            order_data["단품상품"] = name
            order_data["단가"] = price
            order_data["판매 수량"] = sell_cnt
            order_data["환불 건수"] = refund_cnt
            order_data["판매액"] = sell_price
            order_data["매출액(판매 - 환불)"] = sell_price - refund_price
            order_data["수수료 정산"] = int((sell_price - refund_price)/10)
            order_data_list.append(order_data)

        if len(order_data_list) > 0:
            single_product = pd.DataFrame.from_dict(order_data_list, orient='columns')
            if not os.path.exists(self.file_name):
                with pd.ExcelWriter(self.file_name, engine='openpyxl', mode='w') as writer:
                    single_product.to_excel(writer, sheet_name="단품상품", index=False)
            else:
                with pd.ExcelWriter(self.file_name, engine='openpyxl', mode='a') as writer:
                    single_product.to_excel(writer, sheet_name="단품상품", index=False)


    # 계약기간 내(중도 해지) 미쿠폰 사용(+3%)
    def coupon_unused_billing_in_active(self):
        bill_list = []
        genetic_test_products = GeneticTestProduct.objects.all()

        for genetic_test_product in genetic_test_products:
            coupon_unused_subs = self.subs.filter(
                    product=genetic_test_product,
                    is_active=False,
                    # 유전자 검사 상품만을 포함하기 위해 추가
                    coupon__isnull=False,
                    is_coupon_used=False,
                    current_times__lt=12,
                    )

            for sub in coupon_unused_subs:
                product_price = genetic_test_product.price
                count_payments = sub.current_times
                total_product_price = product_price * count_payments
                bill_price = (total_product_price * (3 * 0.7) / 100.0)

                bill_data = {}
                bill_data["client"] = genetic_test_product.connection_client
                bill_data["category"] = "계약기간 내(중도 해지) 미쿠폰 사용(+3%)"
                bill_data["product"] = genetic_test_product.product_name
                bill_data["price"] = bill_price
                bill_list.append(bill_data)


                bill = BillStatus.objects.filter(jmf_sub=sub)
                if len(bill) <= 0:
                    BillStatus.objects.create(
                            jmf_sub=sub,
                            user_name = sub.user_name,
                            status = 'coupon_bill_in_active',
                            price = bill_price
                        )

        if len(bill_list) > 0:
            coupon_not_used_billing = pd.DataFrame.from_dict(bill_list, orient='columns')
            return coupon_not_used_billing


    # 계약기간 내(중도 해지) 쿠폰 사용(-3%)
    def coupon_used_refund_in_active(self):
        refund_list = []
        genetic_test_products = GeneticTestProduct.objects.all()

        for genetic_test_product in genetic_test_products:
            product_price = genetic_test_product.price
            coupon_used_subs = self.subs.filter(
                    product=genetic_test_product,
                    is_active=False,
                    is_coupon_used=True,
                    current_times__lt=12,
                    )

            for sub in coupon_used_subs:
                count_payments = sub.current_times
                total_product_price = product_price * count_payments
                bill = BillStatus.objects.filter(
                            jmf_sub=sub,
                            status='coupon_bill_in_active',    
                            )
                if len(bill) > 0:
                    bill = bill[0]
                    refund_data = {}
                    refund_data["client"] = genetic_test_product.connection_client
                    refund_data["category"] = "계약기간 내(중도 해지) 쿠폰 사용(-3%)"
                    refund_data['product'] = genetic_test_product.product_name
                    refund_data['price'] = -(bill.price)
                    refund_list.append(refund_data)

                    bill.status = 'coupon_refund'
                    bill.save()

        if len(refund_list) > 0:
            coupon_used_refund = pd.DataFrame.from_dict(refund_list, orient='columns')
            return coupon_used_refund
    '''
    - 약정은 기본 12회- 사용자가 비용을 지불 했을 때, 1회차 증가
    - 약정기간 만료 사용자란, 약정회차(12회)를 지난 사용자를 말함
    - 청구서는 지난달 결제를 기준으로 하기에, current_times__gt=12 일 경우, 약정만료 사용자로 설정
      (지난달에 12회차 결제를 하고, 회차가 끝날시점에 청구서를 작성하기 때문)
    '''
    # 계약서 4조 4번 사항
    def coupon_unused_billing(self):
        bill_list = []
        genetic_test_products = GeneticTestProduct.objects.all()

        for genetic_test_product in genetic_test_products:
            coupon_unused_subs = self.subs.filter(
                    product=genetic_test_product,
                    #is_active=False,
                    # 유전자 검사 상품만을 포함하기 위해 추가
                    coupon__isnull=False,
                    is_coupon_used=False,
                    current_times__gt=12,
                    )

            for sub in coupon_unused_subs:
                product_price = genetic_test_product.price
                count_payments = sub.total_times
                total_product_price = product_price * count_payments
                bill_price = (total_product_price * (3 * 0.7) / 100.0)

                bill_data = {}
                bill_data["client"] = genetic_test_product.connection_client
                bill_data["category"] = "계약기간 만료 회차 쿠폰 미사용(+3%)"
                bill_data["product"] = genetic_test_product.product_name
                bill_data["price"] = bill_price
                bill_list.append(bill_data)


                bill = BillStatus.objects.filter(jmf_sub=sub)
                if len(bill) <= 0:
                    BillStatus.objects.create(
                            jmf_sub=sub,
                            user_name = sub.user_name,
                            status = 'coupon_bill',
                            price = bill_price
                        )

        if len(bill_list) > 0:
            coupon_not_used_billing = pd.DataFrame.from_dict(bill_list, orient='columns')
            return coupon_not_used_billing


    # 계약서 4조 5번 사항
    def coupon_used_refund(self):
        refund_list = []
        genetic_test_products = GeneticTestProduct.objects.all()

        for genetic_test_product in genetic_test_products:
            product_price = genetic_test_product.price
            coupon_used_subs = self.subs.filter(
                    product=genetic_test_product,
                    #is_active=False,
                    is_coupon_used=True,
                    current_times__gt=12,
                    )

            for sub in coupon_used_subs:
                count_payments = sub.total_times
                total_product_price = product_price * count_payments
                bill = BillStatus.objects.filter(
                            jmf_sub=sub,
                            status='coupon_bill',    
                            )
                if len(bill) > 0:
                    bill = bill[0]
                    refund_data = {}
                    refund_data["client"] = genetic_test_product.connection_client
                    refund_data["category"] = "계약기간 이후 쿠폰 사용(-3%)"
                    refund_data['product'] = genetic_test_product.product_name
                    refund_data['price'] = -(bill.price)
                    refund_list.append(refund_data)

                    bill.status = 'coupon_refund'
                    bill.save()

        if len(refund_list) > 0:
            coupon_used_refund = pd.DataFrame.from_dict(refund_list, orient='columns')
            return coupon_used_refund


    # 계약서 4조 6번 사항
    def kit_unused_billing(self):
        bill_list = []
        genetic_test_products = GeneticTestProduct.objects.all()

        for genetic_test_product in genetic_test_products:
           product_price = genetic_test_product.price
           kit_unused_subs = self.subs.filter(
                    product=genetic_test_product,
                    #is_active=False,
                    is_coupon_used=True,
                    current_times__gt=12,
                    kit_receive_datetime__isnull=True,
                    )
           for sub in kit_unused_subs:
               count_payments = sub.total_times
               total_product_price = product_price * count_payments
               bill_price = (total_product_price * (1.5 * 0.7) / 100.0)

               bill_data = {}
               bill_data["client"] = genetic_test_product.connection_client
               bill_data["category"] = "키트 미사용(+1.5%)"
               bill_data["product"] = genetic_test_product.product_name
               bill_data["price"] = bill_price
               bill_list.append(bill_data)


               bill = BillStatus.objects.filter(jmf_sub=sub)
               if len(bill) <= 0:
                   BillStatus.objects.create(
                           jmf_sub=sub,
                           user_name = sub.user_name,
                           status = 'kit_bill',
                           price = bill_price
                       )

        if len(bill_list) > 0:
            kit_not_used_billing = pd.DataFrame.from_dict(bill_list, orient='columns')
            return kit_not_used_billing


    # 계약서 4조 7번 사항
    def kit_used_refund(self):
        refund_list = []
        genetic_test_products = GeneticTestProduct.objects.all()

        for genetic_test_product in genetic_test_products:
            product_price = genetic_test_product.price
            kit_used_subs = self.subs.filter(
                    product=genetic_test_product,
                    #is_active=False,
                    is_coupon_used=True,
                    current_times__gt=12,
                    kit_receive_datetime__isnull=False,
                    )

            for sub in kit_used_subs:
                count_payments = sub.total_times
                total_product_price = product_price * count_payments
                bill = BillStatus.objects.filter(
                            jmf_sub=sub,
                            status='kit_bill',    
                            )
                if len(bill) > 0:
                    bill = bill[0]
                    refund_data = {}
                    refund_data["client"] = genetic_test_product.connection_client
                    refund_data["category"] = "키트 사용(-1.5%)"
                    refund_data['product'] = genetic_test_product.product_name
                    refund_data['price'] = -(bill.price)
                    refund_list.append(refund_data)

                    bill.status = 'kit_refund'
                    bill.save()

        if len(refund_list) > 0:
            coupon_used_refund = pd.DataFrame.from_dict(refund_list, orient='columns')
            return coupon_used_refund

    # 계약서 4조 8번 사항
    def kit_refund_billing(self):
        bill_list = []
        genetic_test_products = GeneticTestProduct.objects.all()

        for genetic_test_product in genetic_test_products:
            product_price = genetic_test_product.price
            kit_return_subs = self.subs.filter(
                    product=genetic_test_product,
                    #is_active=False,
                    is_coupon_used=True,
                    current_times__gt=12,
                    kit_receive_datetime__isnull=True,
                    )
            '''
            구독정보(JMFSubscription)의 주문 정보와 
            유전자검사(GeneticTest)의 주문번호가 일치한다고함. (by 이채민 주임)
            구독 정보의 주문번호를 활용하여 GeneticTest 의 정보를 가져와서,
            GeneticTestLog 검색에 사용(키트 반송 정보 확인용도)
            '''
            for sub in kit_return_subs:
                genetic_test = GeneticTest.objects.filter(
                        order_id=sub.order_id,
                        )
                # 주문번호(order_id)는 유일할 것이기 때문에,
                # genetic_test[0] 첫 번째 값만 사용.
                logs = None
                if len(genetic_test) > 0:
                    logs = GeneticTestLog.objects.filter(
                            genetic_test=genetic_test[0]
                            )

                count_payments = sub.total_times
                total_product_price = product_price * count_payments
                bill_price = None
                send_date = None
                
                if logs is not None: 
                    for log in logs:
                        if log.action == 'kit_send':
                            send_date = log.created_at
                            after_two_week = send_date + datetime.timedelta(weeks=2)
                        if log.action == 'normal_kit_return':
                            if (log.created_at > after_two_week):
                                bill_price = (total_product_price * (1.5 * 0.7) / 100.0)
                                bill_data = {}
                                bill_data["client"] = genetic_test_product.connection_client
                                bill_data["category"] = "2주 후 키트 반품(+1.5%)"
                                bill_data["product"] = genetic_test_product.product_name
                                bill_data["price"] = bill_price
                                bill_list.append(bill_data)
                            else:
                                bill_price = (total_product_price * (3.0 * 0.7) / 100.0)
                                bill_data = {}
                                bill_data["client"] = genetic_test_product.connection_client
                                bill_data["category"] = "정상 키트 반품(+3%)"
                                bill_data["product"] = genetic_test_product.product_name
                                bill_data["price"] = bill_price
                                bill_list.append(bill_data)
                        if log.action == 'damaged_kit_return':
                                bill_price = (total_product_price * (1.5 * 0.7) / 100.0)
                                bill_data = {}
                                bill_data["client"] = genetic_test_product.connection_client
                                bill_data["category"] = "파손키트 반품(+1.5%)"
                                bill_data["product"] = genetic_test_product.product_name
                                bill_data["price"] = bill_price
                                bill_list.append(bill_data)

        if len(bill_list) > 0:
            kit_return = pd.DataFrame.from_dict(bill_list, orient='columns')
            return kit_return


    # 결제 내역
    def payment_details(self):
        pass
    
    # 정산 총계
    def total_settlement(self):
        pass

    # 엑셀 시트 스타일 설정
    def set_sheet_style(self):
        pass

    # 정산 엑셀 시트에 저장
    '''
    CLIENT_COICES = (
        ("1", _("카카오")),
        ("2", _("고도몰")),
        ("999", _("과일궁합")),
    )
    '''
    def save_settlement(self):
        genetic_test_product = GeneticTestProduct()
        client_choices = genetic_test_product.CLIENT_COICES
        coupon_unused_billing_in_active = self.coupon_unused_billing_in_active()
        coupon_used_refund_in_active = self.coupon_used_refund_in_active()
        coupon_unused_billing = self.coupon_unused_billing()
        coupon_used_refund = self.coupon_used_refund()
        kit_unused_billing = self.kit_unused_billing()
        kit_used_refund = self.kit_used_refund()
        kit_refund_billing = self.kit_refund_billing()

        settlements = pd.concat([coupon_unused_billing_in_active,
                                coupon_used_refund_in_active,
                                coupon_unused_billing,
                                coupon_used_refund,
                                kit_unused_billing,
                                kit_used_refund,
                                kit_refund_billing])
        clients = set(settlements["client"])
        result = None
        for client in clients:
            data = {}
            data["구독 플랫폼"] = client
            condition = settlements["client"] == client
            client_filter = settlements[condition]
            cols = set(client_filter["product"])
            for col in cols:
                settlements_list = []
                condition = client_filter["product"] == col
                product_filter = client_filter[condition]
                categorys = set(product_filter["category"])
                total_count = 0
                total_price = 0
                for category in categorys:
                    category_filter = product_filter[(product_filter.category == category)]
                    datas = category_filter
                    data["상품명"] = col
                    data[datas["category"].unique()[0]] = datas["category"].count()
                    total_count += datas["category"].count()
                    total_price += datas["price"].sum()
                data["총 발생 건 수"] = total_count
                data["기타 수수료"] = round(total_price)
                settlements_list.append(data)
                settlements_df = pd.DataFrame.from_dict(settlements_list, orient='columns')
                result = pd.concat([result, settlements_df])
                result.fillna(0, inplace=True)

#        cols = set(client_filter["product"])
#        for col in cols:
#            settlements_list = []
#            data = {}
#            condition = settlements["product"] == col
#            product_filter = settlements[condition]
#            categorys = set(settlements[condition]["category"])
#            total_count = 0
#            total_price = 0
#            for category in categorys:
#                category_filter = product_filter[(product_filter.category == category)]
#                datas = category_filter
#                data["상품명"] = col
#                data[datas["category"].unique()[0]] = datas["category"].count()
#                total_count += datas["category"].count()
#                total_price += datas["price"].sum()
#            data["총 발생 건 수"] = total_count
#            data["기타 수수료"] = round(total_price)
#            settlements_list.append(data)
#            settlements_df = pd.DataFrame.from_dict(settlements_list, orient='columns')
#            result = pd.concat([result, settlements_df])
#            result.fillna(0, inplace=True)
        if len(result) > 0:
            if not os.path.exists(self.file_name):
                with pd.ExcelWriter(self.file_name, engine='openpyxl', mode='w') as writer:
                    result.to_excel(writer, sheet_name="과일궁합 정산(기타 수수료)", index=False)
            else:
                with pd.ExcelWriter(self.file_name, engine='openpyxl', mode='a') as writer:
                    result.to_excel(writer, sheet_name="과일궁합 정산(기타 수수료)", index=False)


class Command(BaseCommand):
    help = '인실리코젠-진맛과 정산'

    # 일 주 월 별 정산 가능하게 수정 필요함
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
        settlement = Settlement()
        settlement.save_settlement()

