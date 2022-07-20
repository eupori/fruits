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
from fruitdb.models import MacrogenSettlement
from fruitdb.views.api.auth import send_notification

JMF_URL = "https://bestf.co.kr"


class Command(BaseCommand):
    help = '마크로젠 유전자검사 동의 노티 발송 스크립트'

    def handle(self, *args, **options):
        today = datetime.datetime.today()
        do_d_day = today - datetime.timedelta(days=3)
        print("오늘 날짜")
        print("3일전 날짜")
        # settlements = MacrogenSettlement.objects.filter(created_at__date=do_d_day.date())
        settlements = MacrogenSettlement.objects.all()
        for settlement in settlements:
            send_notification(settlement.customer.firebase_token,"과일궁합 유전자 분석 ","고객님의 유전자를 분석할 수 있도록 동의해주세요.",1)