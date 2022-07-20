from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import JsonResponse
from django.http import Http404
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey

from drf_yasg.utils import swagger_auto_schema

import fruitdb.serializer as sz
from fruitdb.models import *

import jwt
import datetime
import json
import pandas as pd
import numpy as np
import requests


from .auth import get_username_from_uat


class APIStatisticsAPIView(APIView):  # 설문조사 및 식품추천 API
    permission_classes = (HasAPIKey, )

    def create_month_cnt(self, qs, cnt):
        cnt_dict = {}
        dates = list(map(lambda x: str(x), list(
            qs.values_list("created_at__date", flat=True))))
        for i in range(cnt):
            date = str(datetime.datetime.now().date() -
                       datetime.timedelta(cnt-i))
            cnt_dict[date] = dates.count(date)
        return cnt_dict

    def create_month_name_cnt(self, qs, cnt):
        cnt_dict = {}
        dates = list(qs.values_list("created_at__date", "username"))
        for i in range(cnt):
            date = str(datetime.datetime.now().date() -
                       datetime.timedelta(cnt-i))
            date_usernames = list(filter(lambda x: str(x[0]) == date, dates))
            cnt_dict[date] = set(list(map(lambda x: x[1], date_usernames)))
        return cnt_dict

    def get(self, request, *args, **kwargs):
        goal_traits = list(Trait.objects.filter(
            is_default=False, category="예방질병").values_list("id", flat=True))
        disease_traits = list(Trait.objects.filter(
            is_default=False, category="생활목표").values_list("id", flat=True))
        goal_res = {}
        disease_res = {}
        trait_name_dict = {}
        for name, id in list(Trait.objects.all().values_list("name_ko", "id")):
            trait_name_dict[id] = name

        for id in list(Survey.objects.all().values_list("traits", flat=True)):
            if id in goal_traits:
                if trait_name_dict[id] not in goal_res:
                    goal_res[trait_name_dict[id]] = 1
                else:
                    goal_res[trait_name_dict[id]] += 1
            elif id in disease_traits:
                if trait_name_dict[id] not in disease_res:
                    disease_res[trait_name_dict[id]] = 1
                else:
                    disease_res[trait_name_dict[id]] += 1
        goal_res_list = []
        disease_res_list = []
        for key in goal_res.keys():
            goal_res_list.append([key, goal_res[key]])
        for key in disease_res.keys():
            disease_res_list.append([key, disease_res[key]])
        cnt_dict = self.create_month_cnt(  # 가입 유저
            ServiceAPILog.objects.filter(
                created_at__date__gte=datetime.datetime.now().date() - datetime.timedelta(57)
            ), 58
        )
        name_cnt_dict = self.create_month_name_cnt(  # 가입 유저
            ServiceAPILog.objects.filter(
                created_at__date__gte=datetime.datetime.now().date() - datetime.timedelta(57)
            ), 58
        )

        monthly_active_dict = {}
        weekly_active_dict = {}
        daily_active_dict = {}

        date_list = list(name_cnt_dict.keys())
        daily_active_list = []
        for i in range(28):
            monthly_active_dict[date_list[30+i]] = set()
            for date in date_list[1+i:31+i]:
                monthly_active_dict[date_list[30+i]
                                    ].update(name_cnt_dict[date])

            weekly_active_dict[date_list[30+i]] = set()
            for date in date_list[24+i:31+i]:
                weekly_active_dict[date_list[30+i]].update(name_cnt_dict[date])

            daily_active_list.append(
                [date_list[30+i], len(name_cnt_dict[date_list[30+i]])])

        monthly_active_list = []
        weekly_active_list = []
        for i in range(28):
            monthly_active_list.append(
                [date_list[30+i], len(monthly_active_dict[date_list[30+i]])])
            weekly_active_list.append(
                [date_list[30+i], len(weekly_active_dict[date_list[30+i]])])

        response = requests.request(
            "GET", "https://shopman.d-if.kr/statistics")
        shopman_data = json.loads(response.text)
        user_dicts = shopman_data['user_total']
        customers = Customer.objects.filter(username__in=user_dicts.keys())
        user_gen_count_list = [
            ["남성", customers.filter(sex="Male").count()],
            ["여성", customers.filter(sex="Female").count()]
        ]
        android_user_names = customers.filter(is_android=True)
        ios_user_names = customers.filter(is_android=False)
        android_sum = 0
        ios_sum = 0

        for username in android_user_names.values_list("username", flat=True):
            android_sum += user_dicts[username]

        for username in ios_user_names.values_list("username", flat=True):
            ios_sum += user_dicts[username]

        if android_user_names.exists():
            android_sum /= android_user_names.count()
        if ios_user_names.exists():
            ios_sum /= ios_user_names.count()
        device_average = [
            ["iOS", int(ios_sum)],
            ["Android", int(android_sum)],
        ]
        new_users = self.create_month_cnt(  # 가입 유저
            Customer.objects.filter(
                created_at__date__gte=datetime.datetime.now().date() - datetime.timedelta(27)
            ), 28
        )
        new_users = list(map(lambda x: [x, new_users[x]], new_users.keys()))
        age_users = [
            ["70대 이상", 0],
            ["60대", 0],
            ["50대", 0],
            ["40대", 0],
            ["30대", 0],
            ["20대", 0],
            ["20대 미만", 0],
        ]

        for customer in customers:
            if customer.birth_date is not None:
                cal_date = datetime.datetime.now().date()-customer.birth_date
                # print(cal_date)
                if cal_date >= datetime.timedelta(365*70):
                    age_users[0][1] += 1
                elif cal_date >= datetime.timedelta(365*60):
                    age_users[1][1] += 1
                elif cal_date >= datetime.timedelta(365*50):
                    age_users[2][1] += 1
                elif cal_date >= datetime.timedelta(365*40):
                    age_users[3][1] += 1
                elif cal_date >= datetime.timedelta(365*30):
                    age_users[4][1] += 1
                elif cal_date >= datetime.timedelta(365*20):
                    age_users[5][1] += 1
                else:
                    age_users[6][1] += 1

        # response = requests.request("GET", "https://shopman.d-if.kr/statistics"+"?first_date=2021-01-01"+"&last_date=2021-04-01")
        # shopman_data = json.loads(response.text)
        # print(shopman_data['range_total'])
        return JsonResponse(
            {
                "daily_active_user": daily_active_list,
                "weekly_active_user": weekly_active_list,
                "monthly_active_user": monthly_active_list,
                "new_user": new_users,
                "goal": goal_res_list,
                "disease": disease_res_list,
                # 일별 액수
                "total_prices": list(map(lambda x: [x, shopman_data['date_total'][x]], shopman_data['date_total'].keys())),
                "total_price": shopman_data['total_list'],  # 총 액수
                "total_prices_per_sex": user_gen_count_list,  # 각 성별별 액수
                # 각 상품별 액수
                "product": list(map(lambda x: [x, shopman_data['product'][x]], shopman_data['product'].keys())),
                "device_average": device_average,
                "purchasing_user_per_age": age_users,
            },
            status=200
        )


class FitDateStatisticsAPIView(GenericAPIView):
    permission_classes = (HasAPIKey, )
    parser_classes = (FormParser, MultiPartParser, )
    serializer_class = sz.GetLogInputSerializer

    def create_month_cnt(self, qs, first_date, last_date):
        cnt_dict = {}
        dates = list(map(lambda x: str(x), list(
            qs.values_list("created_at__date", flat=True))))
        date_range = pd.period_range(first_date, last_date, freq='d')
        for date in date_range:
            cnt_dict[str(date)] = dates.count(str(date))
        return cnt_dict

    def create_month_name_cnt(self, qs, first_date, last_date):
        cnt_dict = {}
        dates = list(qs.values_list("created_at__date", "username"))
        date_range = pd.period_range(first_date, last_date, freq='d')
        for date in date_range:
            date_usernames = list(
                filter(lambda x: str(x[0]) == str(date), dates))
            cnt_dict[str(date)] = set(
                list(map(lambda x: x[1], date_usernames)))
        return cnt_dict

    @swagger_auto_schema(
        query_serializer=serializer_class,
    )
    def get(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.GET).get_data_or_response()
        first_date = data['first_date']
        last_date = data['last_date']

        res_dict = {}
        if data['target'] == "range_total":
            response = requests.request(
                "GET", f"https://shopman.d-if.kr/statistics?first_date={first_date}&last_date={last_date}")
            shopman_data = json.loads(response.text)['range_total']
            res_list = []
            for key in shopman_data.keys():
                res_list.append([key, shopman_data[key]])
            res_dict['range_total'] = res_list
        else:
            if data['target'] == "daily_active_user":
                name_cnt_dict = self.create_month_name_cnt(  # 가입 유저
                    ServiceAPILog.objects.filter(
                        created_at__date__gte=first_date, created_at__date__lte=last_date
                    ), first_date, last_date
                )
                print(name_cnt_dict)
                date_list = name_cnt_dict.keys()
                daily_active_list = []
                for date in date_list:
                    daily_active_list.append([date, len(name_cnt_dict[date])])
                res_dict['daily_active_user'] = daily_active_list
            elif data['target'] == "active_user":
                added_first_date = datetime.datetime.strptime(
                    first_date, "%Y-%m-%d").date() - datetime.timedelta(30)
                name_cnt_dict = self.create_month_name_cnt(  # 가입 유저
                    ServiceAPILog.objects.filter(
                        created_at__date__gte=added_first_date, created_at__date__lte=last_date
                    ), added_first_date, last_date
                )

                date_list = list(name_cnt_dict.keys())

                daily_active_list = []
                monthly_active_dict = {}
                weekly_active_dict = {}
                # required_date_list = pd.period_range(first_date, last_date, freq='d')
                for i in range(len(date_list)-30):
                    monthly_active_dict[date_list[30+i]] = set()
                    for date in date_list[1+i:31+i]:
                        monthly_active_dict[date_list[30+i]
                                            ].update(name_cnt_dict[date])

                    weekly_active_dict[date_list[30+i]] = set()
                    for date in date_list[24+i:31+i]:
                        weekly_active_dict[date_list[30+i]
                                           ].update(name_cnt_dict[date])

                    daily_active_list.append(
                        [date_list[30+i], len(name_cnt_dict[date_list[30+i]])])

                monthly_active_list = []
                weekly_active_list = []
                for i in range(len(date_list)-30):
                    monthly_active_list.append(
                        [date_list[30+i], len(monthly_active_dict[date_list[30+i]])])
                    weekly_active_list.append(
                        [date_list[30+i], len(weekly_active_dict[date_list[30+i]])])
                res_dict['daily_active_user'] = daily_active_list
                res_dict['monthly_active_user'] = monthly_active_list
                res_dict['weekly_active_user'] = weekly_active_list
            elif data['target'] == "new_user":
                new_users = self.create_month_cnt(  # 가입 유저
                    Customer.objects.filter(
                        created_at__date__gte=first_date, created_at__date__lte=last_date
                    ), first_date, last_date
                )
                new_users = list(
                    map(lambda x: [x, new_users[x]], new_users.keys()))
                res_dict['new_user'] = new_users
        return JsonResponse(
            res_dict,
            status=200
        )