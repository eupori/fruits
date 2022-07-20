from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import fruitdb.serializer as sz
from fruitdb.models import *

from drf_yasg.utils import swagger_auto_schema

import jwt
import datetime
import json
import pandas as pd
import numpy as np
import random
import time
import statistics
import multiprocessing
import copy
from functools import partial

from django.http import JsonResponse
from django.http import Http404

from .auth import get_username_from_uat


convert_trait_dict = {
    "전립선 건강": "전립선 건강",
    "장 건강": "장 건강",
    "인지능력 개선": "인지능력 향상",
    "인지능력 향상": "인지능력 향상",
    "위 건강": "위 건강",
    "간 건강": "간 건강",
    "중성지방농도 개선": "혈중 중성지방 개선",
    "혈중 중성지방 개선": "혈중 중성지방 개선",
    "콜레스테롤 개선": "혈중 콜레스테롤 개선",
    "혈중 콜레스테롤 개선": "혈중 콜레스테롤 개선",
    "소화불량": "소화불량 개선",
    "소화불량 개선": "소화불량 개선",
    "숙취": "숙취 해소",
    "숙취 해소": "숙취 해소",
    "면역력 강화": "면역 기능 개선",
    "면역 기능 개선": "면역 기능 개선",
    "과민성 대장 완화": "과민성 대장 완화",
    "항산화": "항산화",
    "체중감량": "체중 관리",
    "체중 관리": "체중 관리",
    "갱년기 극복": "갱년기 건강관리",
    "갱년기 건강관리": "갱년기 건강관리",
    "만성피로 회복": "피로 개선",
    "피로 개선": "피로 개선",
}


def get_user_from_jwt_token(request):  # 헤더에서 토큰만 반환
    auth = request.META.get("HTTP_AUTHORIZATION", b"")
    payload = jwt.decode(
        auth.split(" ")[1], settings.JWT_SECRET_KEY, algorithms=["HS256"]
    )
    return User.objects.get(username=payload["username"])


def get_username_from_token(request):  # 헤더에서 토큰만 반환
    auth = request.META.get("HTTP_AUTHORIZATION", b"")
    payload = jwt.decode(
        auth.split(" ")[1], settings.JWT_SECRET_KEY, algorithms=["HS256"]
    )
    return payload["username"]


def h_data_to_dict(hdata):
    result = {}
    cal_traits = []
    # bmi 계산 0.75, 1.25, 1.75, 2.25, 1
    bmi = hdata["weight"] / ((hdata["height"] / 100.0) ** 2)
    if bmi >= 25:
        result["Body mass index"] = 1
        cal_traits.append("Body mass index")
    else:
        result["Body mass index"] = 0

    if hdata["sm"] == 0:
        result["Lung cancer"] = 0
    elif hdata["sm"] == 1:
        cal_traits.append("Lung cancer")
        result["Lung cancer"] = 0.5
    else:
        cal_traits.append("Lung cancer")
        result["Lung cancer"] = 1

    if hdata["bs"] == 3:
        result["Type 2 diabetes"] = 1
    elif hdata["bs"] == 2:
        result["Type 2 diabetes"] = 0
    elif hdata["bs"] == 1:
        cal_traits.append("Type 2 diabetes")
        result["Type 2 diabetes"] = 0.5
    elif hdata["bs"] == 0:
        cal_traits.append("Type 2 diabetes")
        result["Type 2 diabetes"] = 1
    else:
        result["Type 2 diabetes"] = 0

    if hdata["bp"] == 3:
        result["Hypertension"] = 1
    elif hdata["bp"] == 2:
        result["Hypertension"] = 0
    elif hdata["bp"] == 1:
        cal_traits.append("Hypertension")
        result["Hypertension"] = 0.5
    elif hdata["bp"] == 0:
        cal_traits.append("Hypertension")
        result["Hypertension"] = 1
    else:
        result["Hypertension"] = 0
    return result, cal_traits


def h_data_to_df(hdata, index):
    result, cal_traits = h_data_to_dict(hdata)

    user_matrix = np.zeros((len(index), len(index)))
    for ind, trait in enumerate(list(index)):
        if trait.split("|")[0] in result:
            user_matrix[ind][ind] = result[trait.split("|")[0]]
        else:
            user_matrix[ind][ind] = 0

    return pd.DataFrame(user_matrix, columns=index, index=index), cal_traits


def dict_to_df(result, index):
    user_matrix = np.zeros((len(index), len(index)))
    for ind, trait in enumerate(list(index)):
        if trait.split("|")[0] in result:
            user_matrix[ind][ind] = result[trait.split("|")[0]]
        else:
            user_matrix[ind][ind] = 0

    return pd.DataFrame(user_matrix, columns=index, index=index)


def survey_to_dict(servey):
    return {
        "height": float(servey.height),
        "weight": float(servey.weight),
        "bs": float(servey.bs),
        "bp": float(servey.bp),
        "sm": float(servey.sm),
    }


def create_servey_fruit(survey, res):
    survey_fruits = []
    fruit_ids = list(res.sum(axis=1).sort_values(ascending=False).index)
    fruit_ids = [
        fruit
        for fruit in fruit_ids
        if fruit not in list(survey.allergies.values_list("if_id", flat=True))
    ]
    # 필터로 과일 목록 가져와서 필터로 정렬해서 하나씩 넣기로 하자
    fruits = Fruit.objects.filter(if_id__in=fruit_ids)
    fruit_list = fruits.values_list("if_id", flat=True)
    sorted_fruit_list = list(filter(lambda x: x in list(fruit_list), fruit_ids))
    sorted_list = sorted(list(fruits), key=lambda d: sorted_fruit_list.index(d.if_id))
    circul_count = 0
    non_circul_count = 0
    for ind, fruit in enumerate(sorted_list):
        if fruit.is_circulated == True and circul_count < 12:
            survey_fruits.append(SurveyFruit(survey=survey, fruit=fruit, order=ind + 1))
            circul_count += 1
        elif fruit.is_circulated == False and non_circul_count < 3:
            survey_fruits.append(SurveyFruit(survey=survey, fruit=fruit, order=ind + 1))
            non_circul_count += 1

        if circul_count == 12 and non_circul_count == 3:
            break
    SurveyFruit.objects.bulk_create(survey_fruits)


def create_servey_all_fruit(ft, username):
    survey_list = Survey.objects.filter(username=username, is_all=False)
    if survey_list.count() >= 2:
        survey = Survey.objects.filter(username=username, is_all=True)
        if survey.exists():
            survey = survey[0]
            survey.traits.clear()
            survey.allergies.clear()
            SurveyFruit.objects.filter(survey=survey).delete()
            survey.save()
        else:
            survey = Survey.objects.create(
                username=username,
                height=0,
                weight=0,
                bs=0,
                bp=0,
                sm=0,
                sex=0,
                # is_me  = False,
                name="모두",
                is_all=True,
            )
        cnt_dict = {}
        for user_survey in survey_list:
            survey_fruits = SurveyFruit.objects.filter(survey=user_survey)
            for item in list(survey_fruits.values_list("fruit__if_id", flat=True)):
                if item in cnt_dict:
                    cnt_dict[item] += 1
                else:
                    cnt_dict[item] = 1

        cnt_list = [(key, cnt_dict[key]) for key in cnt_dict.keys()]
        random.seed(10)
        rand_sorted_cnt_list = sorted(
            cnt_list, key=lambda v: (v[1], random.random()), reverse=True
        )
        random.seed(int(1000 * time.time()) % 2 ** 32)
        circul_count = 0
        non_circul_count = 0
        survey_fruits = []
        for ind, item in enumerate(rand_sorted_cnt_list):
            if_id, cnt = item
            fruit = Fruit.objects.get(if_id=if_id)
            if fruit.is_circulated == True and circul_count < 12:
                survey_fruits.append(
                    SurveyFruit(survey=survey, fruit=fruit, order=ind + 1)
                )
                circul_count += 1
            elif fruit.is_circulated == False and non_circul_count < 3:
                survey_fruits.append(
                    SurveyFruit(survey=survey, fruit=fruit, order=ind + 1)
                )
                non_circul_count += 1

            if circul_count == 12 and non_circul_count == 3:
                break
        SurveyFruit.objects.bulk_create(survey_fruits)

    else:
        survey = Survey.objects.filter(username=username, is_all=True)
        if survey.exists():
            survey.delete()


def cal_fruits_detail(fruit, survey, request, survey_ids):
    return sz.SubscriptionFruitDetailSerializer(
        fruit, context={"survey": survey, "request": request, "survey_ids": survey_ids}
    ).data


def create_servey_sub_fruit(request, ft, username, survey_ids):
    start = time.time()
    survey_list = Survey.objects.filter(username=username, id__in=survey_ids)
    if survey_list.count() >= 2:
        survey = Survey.objects.create(
            username="admin@test",
            height=0,
            weight=0,
            bs=0,
            bp=0,
            sm=0,
            sex=0,
            # is_me  = False,
            name="구독",
            is_all=True,
        )
        cnt_dict = {}
        for user_survey in survey_list:
            survey_fruits = SurveyFruit.objects.filter(survey=user_survey)
            for item in list(survey_fruits.values_list("fruit__if_id", flat=True)):
                if item in cnt_dict:
                    cnt_dict[item] += 1
                else:
                    cnt_dict[item] = 1

        cnt_list = [(key, cnt_dict[key]) for key in cnt_dict.keys()]
        random.seed(10)
        rand_sorted_cnt_list = sorted(
            cnt_list, key=lambda v: (v[1], random.random()), reverse=True
        )
        random.seed(int(1000 * time.time()) % 2 ** 32)
        print(rand_sorted_cnt_list)
        circul_count = 0
        non_circul_count = 0
        survey_fruits = []
        for ind, item in enumerate(rand_sorted_cnt_list):
            if_id, cnt = item
            fruit = Fruit.objects.get(if_id=if_id)
            if fruit.is_circulated == True:
                survey_fruits.append(
                    SurveyFruit(survey=survey, fruit=fruit, order=ind + 1)
                )
                circul_count += 1

            if circul_count == 12:
                break

        tmp_list = []
        for survey_fruit in survey_fruits:
            tmp_list.append(
                sz.SubscriptionFruitDetailSerializer(
                    survey_fruit.fruit,
                    context={
                        "survey": survey,
                        "request": request,
                        "survey_ids": survey_ids,
                    },
                ).data
            )
        survey.delete()
        return tmp_list
    else:
        tmp_list = []
        survey_list = Survey.objects.filter(username=username, id__in=survey_ids)
        survey_fruits = SurveyFruit.objects.filter(
            survey=survey_list[0], fruit__is_circulated=True
        )
        for survey_fruit in survey_fruits:
            tmp_list.append(
                sz.FruitDetailSerializer(
                    survey_fruit.fruit,
                    context={"survey": survey_list[0], "request": request},
                ).create()
            )

        return tmp_list


class SurveyAPIView(GenericAPIView):  # 설문조사 및 식품추천 API
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.SurveyCreateInputSerializer

    @swagger_auto_schema(
        # responses={200: sz.GetInitDataSerializer},
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        context = get_username_from_uat(request)
        data["username"] = context["username"]
        allergies = data["allergies"]
        traits = data["traits"]
        del data["traits"]
        del data["allergies"]

        survey = Survey.objects.create(**data)
        survey.allergies.add(*Fruit.objects.filter(if_id__in=json.loads(allergies)))

        traits = list(
            Trait.objects.filter(
                name_ko__in=list(
                    map(lambda x: convert_trait_dict[x], json.loads(traits))
                )
            ).values_list("name_en", flat=True)
        )
        matrix = Matrix.load()
        ft = pd.read_csv(matrix.ft, index_col=0)
        mt = pd.read_csv(matrix.mt, index_col=0)
        pm, cal_traits = h_data_to_df(survey_to_dict(survey), mt.columns)

        traits += cal_traits
        survey.traits.add(*Trait.objects.filter(name_en__in=traits))
        res = ft.dot(pm)[list(survey.traits.values_list("name_en", flat=True))]
        # 개인 추천
        create_servey_fruit(survey, res)
        # 전체 추천
        create_servey_all_fruit(ft, context["username"])

        surveys = Survey.objects.filter(username=context["username"], is_all=False)
        if survey.pk == surveys.first().pk:
            customer = Customer.objects.get(username=context["username"])
            customer.birth_date = data["birth_date"]
            customer.sex = data["sex"]
            customer.name = data["name"]
            customer.save()
        return JsonResponse(
            {
                "token": context["token"],
                "data": sz.SurveyFruitSerializer(
                    data={}, context={"survey": survey, "request": request}
                ).create(),
            },
            status=200,
        )

    def get(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        survey = Survey.objects.filter(username=context["username"])
        res_list = sz.SurveySerializer(survey, many=True).data

        return JsonResponse(
            {
                "token": context["token"],
                "data": res_list,
            },
            status=200,
            safe=False,
        )


class SurveyAPIV2View(GenericAPIView):  # 설문조사 및 식품추천 API
    permission_classes = (HasAPIKey,)
    parser_classes = (
        FormParser,
        MultiPartParser,
    )
    serializer_class = sz.SurveyCreateInputSerializer

    @swagger_auto_schema(
        # responses={200: sz.GetInitDataSerializer},
        request_body=serializer_class,
    )
    def post(self, request, *args, **kwargs):
        data = self.get_serializer(data=request.data).get_data_or_response()
        context = get_username_from_uat(request)
        data["username"] = context["username"]
        if Survey.objects.filter(username=context["username"]).exists():
            return JsonResponse(
                {"token": context["token"], "msg": "survey already exists"},
                status=409,
            )

        allergies = data["allergies"]
        traits = data["traits"]
        del data["traits"]
        del data["allergies"]
        traits = list(
            Trait.objects.filter(
                name_ko__in=list(
                    map(lambda x: convert_trait_dict[x], json.loads(traits))
                )
            ).values_list("name_en", flat=True)
        )
        survey = Survey.objects.create(**data)
        survey.allergies.add(*Fruit.objects.filter(if_id__in=json.loads(allergies)))
        survey.traits.add(*Trait.objects.filter(name_en__in=traits))

        make_survey_fruits(survey)
        customer = Customer.objects.get(username=context["username"])
        customer.birth_date = data["birth_date"]
        customer.sex = data["sex"]
        customer.name = data["name"]
        customer.save()
        return JsonResponse(
            {
                "token": context["token"],
                "data": sz.SurveyFruitSerializer(
                    data={}, context={"survey": survey, "request": request}
                ).create(),
            },
            status=200,
        )

    def get(self, request, *args, **kwargs):
        context = get_username_from_uat(request)
        survey = Survey.objects.filter(username=context["username"], is_all=False)
        res_list = sz.SurveySerializer(survey, many=True).data

        return JsonResponse(
            {
                "token": context["token"],
                "data": [res_list[0]] if res_list else res_list,
            },
            status=200,
            safe=False,
        )


class SubscriptionSurveyAPIView(APIView):
    permission_classes = (HasAPIKey,)

    def get(self, request, *args, **kwargs):
        description_dict = {}
        fruits = Fruit.objects.filter(is_circulated=True)
        for item in sz.SubcriptionFruitDescriptionSerializer(
            fruits, many=True, context={"request": request}
        ).data:
            description_dict[item["if_id"]] = item
        if request.GET.get("username") is not None:
            survey_ids = json.loads(request.GET.get("survey_ids"))
            matrix = Matrix.load()
            ft = pd.read_csv(matrix.ft, index_col=0)
            return JsonResponse(
                {
                    "data": {
                        "fruits": create_servey_sub_fruit(
                            request, ft, request.GET.get("username"), survey_ids
                        ),
                        "descriptions": description_dict,
                        "survey_ids": survey_ids,
                    }
                },
                status=200,
            )
        else:
            context = get_username_from_uat(request)
            survey_ids = json.loads(request.GET.get("survey_ids"))
            matrix = Matrix.load()
            ft = pd.read_csv(matrix.ft, index_col=0)
            return JsonResponse(
                {
                    "token": context["token"],
                    "data": {
                        "fruits": create_servey_sub_fruit(
                            request, ft, context["username"], survey_ids
                        ),
                        "descriptions": description_dict,
                        "survey_ids": survey_ids,
                        "survey_names": list(
                            Survey.objects.filter(id__in=survey_ids).values_list(
                                "name", flat=True
                            )
                        ),
                    },
                },
                status=200,
            )


class SurveyDetailAPIView(APIView):  # 설문조사 및 식품추천 API
    permission_classes = (HasAPIKey,)

    def get_object(self, pk):
        try:
            return Survey.objects.get(pk=pk)
        except Survey.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        context = get_username_from_uat(request)
        username = context["username"]
        survey = self.get_object(pk)
        if survey.username != username:
            return JsonResponse(
                {"status": "fail", "msg": "매칭되는 survey가 존재하지 않습니다."}, status=404
            )
        # survey.
        return JsonResponse(
            {
                "token": context["token"],
                "data": sz.SurveyFruitSerializer(
                    data={}, context={"survey": survey, "request": request}
                ).create(),
            },
            status=200,
        )

    def delete(self, request, pk, format=None):
        context = get_username_from_uat(request)
        survey = self.get_object(pk)
        survey.delete()

        matrix = Matrix.load()
        ft = pd.read_csv(matrix.ft, index_col=0)
        create_servey_all_fruit(ft, context["username"])
        return JsonResponse(
            {
                "token": context["token"],
                "data": {
                    "status": "success",
                },
            },
            status=204,
        )

    def patch(self, request, pk, format=None):
        context = get_username_from_uat(request)
        try:
            survey = self.get_object(pk)

            update_dict = dict(request.data)
            for key in update_dict.keys():
                update_dict[key] = update_dict[key][0]
            survey.__dict__.update(update_dict)

            SurveyFruit.objects.filter(survey=survey).delete()
            survey.save()
            if "allergies" in request.data:
                survey.allergies.add(
                    *Fruit.objects.filter(
                        if_id__in=json.loads(request.data["allergies"])
                    )
                )
            traits = []
            if "traits" in request.data:
                request_traits = list(
                    map(
                        lambda x: convert_trait_dict[x],
                        json.loads(request.POST.get("traits")),
                    )
                )
                # traits = list(Trait.objects.filter(name_ko__in=json.loads(request.POST.get("traits"))).values_list("name_en", flat=True)) + list(Trait.objects.filter(is_default=True).values_list("name_en", flat=True))
                traits = list(
                    Trait.objects.filter(name_ko__in=request_traits).values_list(
                        "name_en", flat=True
                    )
                )
            else:
                traits = list(
                    survey.traits.all()
                    .filter(is_default=False)
                    .values_list("name_en", flat=True)
                )
            survey.allergies.clear()
            survey.traits.clear()
            matrix = Matrix.load()
            ft = pd.read_csv(matrix.ft, index_col=0)
            mt = pd.read_csv(matrix.mt, index_col=0)
            pm, cal_traits = h_data_to_df(survey_to_dict(survey), mt.columns)

            traits += cal_traits
            survey.traits.add(*Trait.objects.filter(name_en__in=traits))
            res = ft.dot(pm)[list(survey.traits.values_list("name_en", flat=True))]

            # 수정 과정
            survey_fruits = []
            fruit_ids = list(res.sum(axis=1).sort_values(ascending=False).index)
            fruit_ids = [
                fruit
                for fruit in fruit_ids
                if fruit not in list(survey.allergies.values_list("if_id", flat=True))
            ]
            # 필터로 과일 목록 가져와서 필터로 정렬해서 하나씩 넣기로 하자
            fruits = Fruit.objects.filter(if_id__in=fruit_ids)
            fruit_list = fruits.values_list("if_id", flat=True)
            sorted_fruit_list = list(filter(lambda x: x in list(fruit_list), fruit_ids))
            sorted_list = sorted(
                list(fruits), key=lambda d: sorted_fruit_list.index(d.if_id)
            )
            circul_count = 0
            non_circul_count = 0
            for ind, fruit in enumerate(sorted_list):
                if fruit.is_circulated == True and circul_count < 12:
                    survey_fruits.append(
                        SurveyFruit(survey=survey, fruit=fruit, order=ind + 1)
                    )
                    circul_count += 1
                elif fruit.is_circulated == False and non_circul_count < 3:
                    survey_fruits.append(
                        SurveyFruit(survey=survey, fruit=fruit, order=ind + 1)
                    )
                    non_circul_count += 1

                if circul_count == 12 and non_circul_count == 3:
                    break
            SurveyFruit.objects.bulk_create(survey_fruits)

            create_servey_all_fruit(ft, context["username"])
            # survey.

            surveys = Survey.objects.filter(username=context["username"], is_all=False)
            if survey.pk == surveys.first().pk:
                customer = Customer.objects.get(username=context["username"])
                if request.POST.get("birth_date") is not None:
                    customer.birth_date = request.POST.get("birth_date")
                if request.POST.get("sex") is not None:
                    customer.sex = request.POST.get("sex")
                if request.POST.get("name") is not None:
                    customer.name = request.POST.get("name")
                customer.save()
            return JsonResponse(
                {
                    "token": context["token"],
                    "data": sz.SurveyFruitSerializer(
                        data={}, context={"survey": survey, "request": request}
                    ).create(),
                },
                status=201,
            )
        except Exception as e:
            return JsonResponse({"status": "fail", "msg": str(e)}, status=400)


class SurveyDetailAPIV2View(APIView):  # 설문조사 및 식품추천 API
    permission_classes = (HasAPIKey,)

    def get_object(self, pk):
        try:
            return Survey.objects.get(pk=pk)
        except Survey.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        context = get_username_from_uat(request)
        username = context["username"]
        survey = self.get_object(pk)
        if survey.username != username:
            return JsonResponse(
                {"status": "fail", "msg": "매칭되는 survey가 존재하지 않습니다."}, status=404
            )
        # survey.
        print(survey.surveyfruit_set.all().count())
        return JsonResponse(
            {
                "token": context["token"],
                "data": sz.SurveyFruitSerializer(
                    data={}, context={"survey": survey, "request": request}
                ).create(),
            },
            status=200,
        )

    # def delete(self, request, pk, format=None):
    #     context = get_username_from_uat(request)
    #     survey = self.get_object(pk)
    #     survey.delete()

    #     matrix = Matrix.load()
    #     ft = pd.read_csv(matrix.ft, index_col=0)
    #     create_servey_all_fruit(ft, context["username"])
    #     return JsonResponse(
    #         {
    #             "token": context["token"],
    #             "data": {
    #                 "status": "success",
    #             },
    #         },
    #         status=204,
    #     )

    def patch(self, request, pk, format=None):
        context = get_username_from_uat(request)
        try:
            survey = self.get_object(pk)

            update_dict = dict(request.data)
            for key in update_dict.keys():
                update_dict[key] = update_dict[key][0]
            survey.__dict__.update(update_dict)

            SurveyFruit.objects.filter(survey=survey).delete()
            survey.save()
            if "allergies" in request.data:
                survey.allergies.clear()
                survey.allergies.add(
                    *Fruit.objects.filter(
                        if_id__in=json.loads(request.data["allergies"])
                    )
                )
            traits = []
            if "traits" in request.data:
                request_traits = list(
                    map(
                        lambda x: convert_trait_dict[x],
                        json.loads(request.POST.get("traits")),
                    )
                )
                # traits = list(Trait.objects.filter(name_ko__in=json.loads(request.POST.get("traits"))).values_list("name_en", flat=True)) + list(Trait.objects.filter(is_default=True).values_list("name_en", flat=True))
                traits = list(
                    Trait.objects.filter(name_ko__in=request_traits).values_list(
                        "name_en", flat=True
                    )
                )
                survey.traits.clear()
                survey.traits.add(*Trait.objects.filter(name_en__in=traits))

            make_survey_fruits(survey)
            customer = Customer.objects.get(username=context["username"])
            if request.POST.get("birth_date") is not None:
                customer.birth_date = request.POST.get("birth_date")
            if request.POST.get("sex") is not None:
                customer.sex = request.POST.get("sex")
            if request.POST.get("name") is not None:
                customer.name = request.POST.get("name")
            customer.save()
            return JsonResponse(
                {
                    "token": context["token"],
                    "data": sz.SurveyFruitSerializer(
                        data={}, context={"survey": survey, "request": request}
                    ).create(),
                },
                status=201,
            )
        except Exception as e:
            return JsonResponse({"status": "fail", "msg": str(e)}, status=400)


class SurveyEditAPIView(APIView):
    def patch(self, request, *args, **kwargs):
        context = get_username_from_uat(request)

        survey = Survey.objects.get(id=request.POST.get("survey_id"))
        survey.name = request.POST.get("name")
        survey.save()
        return JsonResponse(
            {
                "token": context["token"],
                "data": "sucess",
            },
            status=200,
        )


def survey_to_trait_dict(survey):
    data, trait_list = h_data_to_dict(survey_to_dict(survey))
    res_dict = {key: [data[key]] for key in data}

    for data in [survey.lifelog, survey.genetic]:
        if data:
            for key in filter(lambda x: data["data"][x], data["data"].keys()):
                if key in res_dict:
                    res_dict[key].append(data["data"][key])
                else:
                    res_dict[key] = [data["data"][key]]
            trait_list += [
                key for key in data["trait_flags"] if data["trait_flags"][key]
            ]
    res_mean_dict = {key: statistics.mean(res_dict[key]) for key in res_dict}
    return res_mean_dict, trait_list


def make_survey_fruits(survey):
    res_mean_dict, trait_list = survey_to_trait_dict(survey)
    selected_trait = list(survey.traits.values_list("name_en", flat=True))
    for trait in selected_trait:
        res_mean_dict[trait] = 1

    traits = trait_list + selected_trait
    survey.cal_traits = traits
    survey.save()

    matrix = Matrix.load()
    ft = pd.read_csv(matrix.ft, index_col=0)
    mt = pd.read_csv(matrix.mt, index_col=0)
    res = ft.dot(dict_to_df(res_mean_dict, mt.columns))[survey.cal_traits]

    fruit_ids = list(res.sum(axis=1).sort_values(ascending=False).index)
    fruit_ids = [
        fruit
        for fruit in fruit_ids
        if fruit not in list(survey.allergies.values_list("if_id", flat=True))
    ]
    # 필터로 과일 목록 가져와서 필터로 정렬해서 하나씩 넣기로 하자
    fruits = Fruit.objects.filter(if_id__in=fruit_ids)
    fruit_list = fruits.values_list("if_id", flat=True)
    sorted_fruit_list = list(filter(lambda x: x in list(fruit_list), fruit_ids))
    sorted_list = sorted(list(fruits), key=lambda d: sorted_fruit_list.index(d.if_id))
    circul_count = 0
    non_circul_count = 0
    survey_fruits = []
    nc_survey_fruits = []
    cnt = 0
    for ind, fruit in enumerate(sorted_list):
        if fruit.is_circulated == True and circul_count < 10:
            survey_fruits.append(
                SurveyFruit(
                    survey=survey,
                    fruit=fruit,
                    order=circul_count + 1,
                )
            )
            circul_count += 1
        elif fruit.is_circulated == False and non_circul_count < 5:
            nc_survey_fruits.append(
                SurveyFruit(survey=survey, fruit=fruit, order=non_circul_count + 10 + 1)
            )
            non_circul_count += 1
        if circul_count == 10 and non_circul_count == 5:
            break

    SurveyFruit.objects.filter(survey=survey).delete()
    SurveyFruit.objects.bulk_create(survey_fruits + nc_survey_fruits)


class SurveyCRMUpdateAPIView(APIView):
    def post(self, request, fruits_id, format=None):
        lielog = request.data.get("lifelog")
        genetic = request.data.get("genetic")

        survey = Survey.objects.filter(username=fruits_id, is_all=False)

        if not survey.exists():
            return JsonResponse(
                {
                    "msg": "survey not exists",
                },
                status=404,
            )
        survey = survey.first()
        survey.lifelog = request.data.get("lifelog")
        survey.genetic = request.data.get("genetic")
        survey.save()

        #
        make_survey_fruits(survey)
        return JsonResponse(
            {
                "data": "success",
            },
            status=200,
        )


class AifruitsTest(APIView):
    permission_classes = [permissions.AllowAny,]
    
    def get(self, request, format=None):
        username = request.GET.get("username")
        survey = Survey.objects.get(username=username)
        if survey.username != username:
            return JsonResponse(
                {"status": "fail", "msg": "매칭되는 survey가 존재하지 않습니다."}, status=404
            )
        # survey.
        print(survey.surveyfruit_set.all().count())
        return JsonResponse(
            {
                "data": sz.SurveyFruitSerializer(
                    data={}, context={"survey": survey, "request": request}
                ).create(),
            },
            status=200,
        )
