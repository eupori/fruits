from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.conf.urls.static import static
from django.conf import settings

from rest_framework_jwt import views as jwt_views
from fruitdb.views import *
from .yasg import *


urlpatterns = [
    # api login urls
    path("api/token", jwt_views.obtain_jwt_token, name="get_token"),  # 토큰 발급
    path("api/refresh", jwt_views.refresh_jwt_token),  # 토큰 재발급
    path("api/verify", jwt_views.verify_jwt_token),  # 토큰
    path("test/testpage", TestTemplateView.as_view(), name="testpage"),
    path("post/<int:pk>", PostDetailView.as_view(), name="post-detail"),
    path("tos/service", TOSServiceTemplateView.as_view(), name="tos-service"),
    path("tos/personal", TOSPersonalInfoTemplateView.as_view(), name="tos-personal"),
    path("tos/personal/processing", TOSPersonalProcessingTemplateView.as_view(), name="tos-personal-processing"),
    path("tos/sensitive", TOSSensitiveInfoTemplateView.as_view(), name="tos-sensitive"),
    path("api/survey", SurveyAPIView.as_view(), name="survey-api"),
    path(
        "api/survey/<int:pk>", SurveyDetailAPIView.as_view(), name="survey-detail-api"
    ),
    path("api/survey/name", SurveyEditAPIView.as_view(), name="survey-name-edit-api"),
    path("api/survey/sub", SubscriptionSurveyAPIView.as_view(), name="survey-sub-api"),
    path(
        "api/crm/survey/<str:fruits_id>",
        SurveyCRMUpdateAPIView.as_view(),
        name="survey-sub-api",
    ),
    path("api/v2/survey", SurveyAPIV2View.as_view(), name="survey-api-v2"),
    path(
        "api/v2/survey/<int:pk>",
        SurveyDetailAPIV2View.as_view(),
        name="survey-detail-api-v2",
    ),
    # path("api/surveys", SurveyListAPIView.as_view(), name="surveys-api"),
    path(
        "api/fruit/<str:if_id>", FruitDetailAPIView.as_view(), name="fruit-detail-api"
    ),
    # swagger 사이트 설정
    path("api/user", UserAPIView.as_view(), name="user-token-api"),
    path("api/user/info", UserInfoAPIView.as_view(), name="user-info-api"),
    path("api/user/dl-email", SendDLEmailAPIView.as_view(), name="user-dlemail-api"),
    path("api/payment", UserPaymentInfoAPIView.as_view(), name="payment-info-api"),
    path("api/user/<str:username>", CustomerDetailAPI.as_view(), name="customer-api"),
    path(
        "api/sso/attribute",
        UserAttributeAPIView.as_view(),
        name="sso-attribute",
    ),
    path("api/deposit", DepositUpdateAPIView.as_view(), name="deposit-api"),
    path("api/mileage", MileageUpdateAPIView.as_view(), name="mileage-api"),
    path("api/shipping", ShippingUpdateAPIView.as_view(), name="shipping-api"),
    path("api/auth/sms", SendSMSAPIView.as_view(), name="sms-api"),
    path(
        "api/auth/check", ResetPasswordCheckAPIView.as_view(), name="sms-password-api"
    ),
    path("api/login", UserLoginAPIView.as_view(), name="user-login-api"),
    path("api/password", ChangePasswordAPIView.as_view(), name="change-password-api"),
    path("api/social-login", SocialLoginAPIView.as_view(), name="social-login-api"),
    path(
        "api/social-registration",
        SocialRegistrationAPIView.as_view(),
        name="social-registration-api",
    ),
    path(
        "api/1.0/social-login",
        SocialLoginAPIV1View.as_view(),
        name="social-login-1.0-api",
    ),
    path(
        "api/1.0/social-registration",
        SocialRegistrationAPIV1View.as_view(),
        name="social-registration-1.0-api",
    ),
    path("api/statistics", APIStatisticsAPIView.as_view(), name="stat-api"),
    path("api/statistics/fit", FitDateStatisticsAPIView.as_view(), name="fit-stat-api"),
    path("api/version", VersionAPIView.as_view(), name="stat-api"),
    path("api/question", QuestionAPIView.as_view(), name="question-api"),
    path("api/event", EventAPIView.as_view(), name="event-api"),
    path("appstore", AppstoreRedirectView.as_view(), name="appstore-redirect"),
    path("api/subscription", SubscriptionAPIView.as_view(), name="question-api"),
    path(
        "swagger<str:format>",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("docs/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("api/subscription/on/coupon", SubscriptionOnCouponInfoAPIView.as_view(), name="subscription-coupon-api"),
    path("api/subscription/on/order", SubscriptionOnOrderInfoAPIView.as_view(), name="subscription-order-api"),
    path("api/subscription/on/user", SubscriptionOnUserInfoAPIView.as_view(), name="subscription-user-api"),
    path("api/test/notification", TestNotification.as_view(), name="test-notification"),
    path("api/genetic/promotion", GeneticPromotionAPIView.as_view(), name="genetic-promotion-api"),
    path("api/genetic/promotion/validation", PassAuthenticationAPIView.as_view(), name="genetic-promotion-validation-api"),
    path("api/genetic/promotion/url", GeneTicPromotionUrlAPIView.as_view(), name="genetic-promotion-url-api"),
    path("api/aifruits/test", AifruitsTest.as_view(), name="aifruits-test"),
    path("feedback", Feedback.as_view(), name="feedback"),
    path("api/lifelog/use", LifeLogUseAPIView.as_view(), name="lifelog-use"),
    path("api/godomall/subscription/url", GodomallSubscriptionURLAPIView.as_view(), name="godomall-subscription-url"),
    path("api/jmf/subscription/url", JMFSubscriptionURLAPIView.as_view(), name="jmf-subscription-url"),
    path("api/customer/pass", PassCheckAPIView.as_view(), name="customer-pass"),
    path("api/product/banner", ProductBannerAPIView.as_view(), name="product-banner"),
    path("api/user/agree/choice", AcceptChoiceAgreeAPIView.as_view(), name="user-agree-choice"),
    path("api/user/version/check", AppVersionCheckAPIView.as_view(), name="user-app-verion"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
