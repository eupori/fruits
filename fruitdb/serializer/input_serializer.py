from django.db.models import F, IntegerField, Value
from django.http import JsonResponse
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError, ParseError, NotFound

from rest_framework import serializers
import fruitdb.models as models

from raven.contrib.django.raven_compat.models import client
import json
import time
import raven
import sys
import re


def get_exc_info():
    exc_info = sys.exc_info()
    if exc_info[0] is None:
        return None
    return exc_info


def capture_exception(error):
    exc_info = get_exc_info()
    if exc_info:
        client.captureException(exc_info)
    else:
        client.captureMessage(error)


class BaseInputSerializer(serializers.Serializer):
    class Meta:
        abstract = True

    def get_data_or_response(self):
        if not self.is_valid():
            capture_exception(self.errors)
            raise ValidationError(self.errors)
        return self.data


class BaseInputModelSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True

    def get_data_or_response(self):
        if not self.is_valid():
            capture_exception(self.errors)
            raise ValidationError(self.errors)
        return self.data


class SendSMSAPIInputSerializer(BaseInputSerializer):
    phone = serializers.CharField(max_length=15)
    is_test = serializers.ChoiceField(choices=[("Y", "Y"), ("N", "N")])


class SendDLEmailAPIInputSerializer(BaseInputSerializer):
    email = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(
        choices=[("registration", "registration"), ("password", "password")]
    )


class UserCreateInputSerializer(BaseInputSerializer):
    username = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=200)
    name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=15)


class UserInputSerializer(BaseInputSerializer):
    username = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=200)


class ShippingInputSerializer(BaseInputSerializer):
    shipping_name = serializers.CharField(max_length=200)
    name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=20)
    zip_code = serializers.CharField(max_length=20)
    address = serializers.CharField(max_length=200)
    detail_address = serializers.CharField(max_length=200)
    sno = serializers.CharField(max_length=20, required=False)
    type = serializers.ChoiceField(choices=["update", "add"])
    request = serializers.CharField(max_length=500, default="")
    pw = serializers.CharField(max_length=100, default="")


class SocialLoginInputSerializer(BaseInputSerializer):
    id = serializers.CharField(max_length=200)
    sns = serializers.ChoiceField(choices=["kakao", "naver", "apple"])


class SocialRegistrationInputSerializer(BaseInputSerializer):
    id = serializers.CharField(max_length=200)
    sns = serializers.ChoiceField(choices=["kakao", "naver", "apple"])
    phone = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=200, required=False, default="")
    username = serializers.CharField(max_length=200, required=False, default="")


class ResetPasswordCheckInputSerializer(BaseInputSerializer):
    username = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=20)


class ChangePasswordInputSerializer(BaseInputSerializer):
    username = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=200)


class QuestionInputSerializer(BaseInputModelSerializer):
    class Meta:
        model = models.Question
        fields = ["email", "content"]


class SurveyCreateInputSerializer(BaseInputModelSerializer):
    allergies = serializers.CharField(max_length=200)
    traits = serializers.CharField(max_length=200)

    class Meta:
        model = models.Survey
        fields = [
            "height",
            "weight",
            "bs",
            "bp",
            "sm",
            "sex",
            "birth_date",
            "name",
            "allergies",
            "traits",
        ]


class EventInputSerializer(BaseInputSerializer):
    event_code = serializers.CharField(max_length=10)


class SurveyInputSerializer(BaseInputSerializer):
    survey_id = serializers.IntegerField()

    def validate_survey_id(self, value):
        if not models.Survey.objects.filter(id=value).exists():
            raise NotFound("survey not exists")
        return value


class GetVersionInputSerializer(BaseInputSerializer):
    target = serializers.ChoiceField(choices=["ios", "aos"])


class GetLogInputSerializer(BaseInputSerializer):
    target = serializers.ChoiceField(
        choices=["range_total", "daily_active_user", "active_user", "new_user"]
    )
    first_date = serializers.DateField()
    last_date = serializers.DateField()


class PhoneNumberSerializer(BaseInputSerializer):
    phone = serializers.CharField(max_length=13)

    def validate_phone(self, value):
        if re.match("(010|011)-\d{3,4}-\d{4}", value):
            return value
        else:
            raise ValidationError("The format of the phone number is incorrect.")

class CouponSerializer(BaseInputSerializer):
    coupon = serializers.CharField(max_length=6)

    def validate_coupon(self, value):
        if len(value) <= 6:
            return value
        else:
            raise ValidationError("The format of the coupon is incorrect.")

class CouponDateSerializer(BaseInputSerializer):
    from_date = serializers.DateField()
    to_date = serializers.DateField()