from django.views.generic import TemplateView
from rest_framework import permissions


class TOSServiceTemplateView(TemplateView):  # 설문조사 및 식품추천 API
    permission_classes = (permissions.AllowAny, )
    template_name = "service.html"


class TOSPersonalInfoTemplateView(TemplateView):  # 설문조사 및 식품추천 API
    permission_classes = (permissions.AllowAny, )
    template_name = "personal_info.html"


class TOSPersonalProcessingTemplateView(TemplateView):  # 설문조사 및 식품추천 API
    permission_classes = (permissions.AllowAny, )
    template_name = "personal_processing.html"


class TOSSensitiveInfoTemplateView(TemplateView):  # 설문조사 및 식품추천 API
    permission_classes = (permissions.AllowAny, )
    template_name = "sensitive_info.html"
