from django.contrib import admin
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse
from django.contrib.admin import SimpleListFilter
from django.urls import path
from bs4 import BeautifulSoup
from io import BytesIO as IO

import fruitdb.models as models
import datetime
import requests
import os
import random
import pandas as pd
import io



class PostAdmin(admin.ModelAdmin):
    model = models.Post
    # list_display = (
    #     "title",
    #     "view_type",
    #     "is_active",
    # )
    readonly_fields = ["content", "header", "title", "image", "description", "created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        # if not obj.pk:
        #     obj.user = request.user
        # else:
        #     obj.modify_at = timezone.now()
        #     obj.modifier = request.user
        page = ""
        post_qs = models.Post.objects.all()
        page_name = 0
        rnd = str(random.randrange(1000000, 10000000))
        if post_qs.exists():
            page_name = post_qs.last().pk
        os.system(f'phantomjs phantom.js {obj.url} brunch/{page_name}_{rnd}.html')
        with open(f"brunch/{page_name}_{rnd}.html") as f:
            page = f.read()
        soup = BeautifulSoup(page, 'html.parser')
        obj.content =  str(soup.find(class_='wrap_body_frame'))
        obj.header = str(soup.find('head'))
        obj.title = soup.find("meta",  property="og:title")['content']
        obj.image = "https:"+soup.find("meta",  property="og:image")['content']
        obj.description = soup.find("meta",  property="og:description")['content']
        # print(obj)
        obj.save()
        # super().save_model(request, obj, form, change)


class MatrixAdmin(admin.ModelAdmin):
    model = models.Matrix
    # list_display = (
    #     "title",
    #     "view_type",
    #     "is_active",
    # )
    readonly_fields = ["ft"]

    def save_model(self, request, obj, form, change):
        fm = pd.read_csv(obj.fm, index_col=0)
        mt = pd.read_csv(obj.mt, index_col=0)
        # hp = pd.read_csv(obj.hp, index_col=0)
        # print(fm.index)
        # print(fm.shape, mt.shape, hp.shape)
        ft = fm.dot(mt)
        s = io.StringIO()
        ft.to_csv(s)
        
        obj.ft.save("matrix/ft.csv", ContentFile(s.getvalue()))

        models.FruitTrait.objects.all().delete()
        # res_df = ft.dot(hp)
        res_df = ft
        fruit_traits = []
        for ind in res_df.index:
            tmp_df = res_df[res_df.index==ind].sort_values(by=ind, axis=1, ascending=False)
            inds = list(tmp_df.columns)
            values = list(tmp_df.iloc[0])
            fruit = models.Fruit.objects.get(if_id=ind)
            for i in range(len(inds)):
                if values[i] > 0:
                    fruit_traits.append(
                        models.FruitTrait(
                            fruit=fruit,
                            trait=models.Trait.objects.get(name_en=inds[i]),
                            order=i+1
                        )
                    )
        models.FruitTrait.objects.bulk_create(fruit_traits)
        # for ind, row in ft.iterrows():
        #     (by=1, ascending=False, axis=1)
        # FruitTrait.
        # if not obj.pk:
        #     obj.user = request.user
        # else:
        #     obj.modify_at = timezone.now()
        #     obj.modifier = request.user
        metabolite_traits = []
        models.MetaboliteTrait.objects.all().delete()
        for ind, row in mt.iterrows():
            metabolite = models.Metabolite.objects.get(if_id=ind)
            for column in mt.columns:
                if row[column] > 0:
                    metabolite_traits.append(
                        models.MetaboliteTrait(
                            metabolite=metabolite,
                            trait=models.Trait.objects.get(name_en=column),
                            value=row[column]
                        )
                    )
        models.MetaboliteTrait.objects.bulk_create(metabolite_traits)   
        super().save_model(request, obj, form, change)


class TraitAdmin(admin.ModelAdmin):
    model = models.Trait
    list_display = (
        "name_ko",
        "name_en",
        "is_default",
        "category",
        "image",
        "active_image"
    )


class FruitAdmin(admin.ModelAdmin):
    model = models.Trait
    list_display = (
        "name",
        "if_id"
    )


class TestCustomerFilter(SimpleListFilter):
    """
    This filter is being used in django admin panel in profile model.
    """
    title = '계정 유형'
    parameter_name = 'customer__username'

    def lookups(self, request, model_admin):
        return (
            ('tester', 'Test ID'),
            ('non_tester', '실사용자')
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        if self.value() == "tester":
            return queryset.filter(username__icontains="test")
        else:
            return queryset.exclude(username__icontains="test")


class CustomCustomerJoinFilter(SimpleListFilter):
    """
    This filter is being used in django admin panel in profile model.
    """
    title = '가입경로'
    parameter_name = 'customer__is_jmf_join'

    def lookups(self, request, model_admin):
        return (
            (True, "진맛과"),
            (False, "과일궁합")
        )

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        if self.value() == "True":
            return queryset.filter(is_jmf_join=True)
        else:
            return queryset.filter(is_jmf_join=False)


class CustomerAdmin(admin.ModelAdmin):
    change_list_template = "admin/api/customer/change_list.html"
    model = models.Customer
    list_display = (
        "username",
        "name",
        "sex",
        "is_active",
        "is_jmf_join",
        "is_genetic",
        "created_at"
    )
    list_filter = (CustomCustomerJoinFilter, TestCustomerFilter, 'sex', 'is_active', 'is_genetic')
    search_fields = ("username", "name")

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('excel/', self.export_excel),
        ]
        return my_urls + urls

    def export_excel(self, request):
        col_names = [
            "ID",
            "생년월일",
            "성별",
            "이름",
            "안드로이드 사용 여부",
            "사용 여부",
            "진맛과 인증 여부",
            "진맛과를 통한 가입 여부",
            "유전자 검사 동의 여부",
        ]

        rows = [
            (
                customer.username,
                customer.birth_date,
                customer.sex,
                customer.name,
                customer.is_android,
                customer.is_active,
                customer.is_jmf_auth,
                customer.is_jmf_join,
                customer.is_genetic
            )
            for customer in models.Customer.objects.all()  # noqa
        ]
        df = pd.DataFrame(columns=col_names, data=rows)

        now = datetime.datetime.now()
        now_str = datetime.datetime.strftime(now, "%Y-%m-%d")
        response = HttpResponse(content_type="application/vnd.ms-excel")
        response[
            "Content-Disposition"
        ] = f"attachment; filename=customer-{now_str}.xlsx"

        excel_file = IO()

        xlwriter = pd.ExcelWriter(excel_file, engine="xlsxwriter")

        df.to_excel(xlwriter, "customer")

        xlwriter.save()
        xlwriter.close()
        excel_file.seek(0)

        response.write(excel_file.read())
        return response


class ServiceAPILogAdmin(admin.ModelAdmin):
    model = models.ServiceAPILog
    list_display = (
        "username",
        "api",
        "method",
        "status",
        "created_at"
    )
    readonly_fields = ["username", "api", "method", "status", "created_at"]


class AppVersionAdmin(admin.ModelAdmin):
    model = models.AppVersion
    list_display = (
        "version",
        "target",
        "is_active"
    )

class QuestionAdmin(admin.ModelAdmin):
    model = models.Question
    list_display = [
        'customer', 'email', 'created_at'
    ]
    readonly_fields = [
        'customer', 'email', 'created_at', 'content'
    ]


class EventAPILogAdmin(admin.ModelAdmin):
    model = models.EventAPILog
    list_display = [
        'customer', 'event_code', 'phone', 'is_success', 'event_text', 'created_at' 
    ]
    list_filter = ('event_code', 'is_success')
    search_fields = ('phone', 'customer__username', 'event_code',)


class GeneticTestProductAdmin(admin.ModelAdmin):
    model = models.GeneticTestProduct
    list_display = [
        "product_code", "connection_client", "product_name", "total_times", "month_range"
    ]

    list_filter = ('connection_client',)
    search_fields = ('product_code', 'connection_client',)


class GeneticTestAdmin(admin.ModelAdmin):
    model = models.GeneticTest
    list_display = [
        'customer', 'test_product', 'coupon', 'current_times', 'kit_status', 'is_active', 'start_datetime' 
    ]
    ordering = [
        'created_at', 'updated_at'
    ]
    
    def save_model(self, request, obj, form, change):
        if "kit_status" in form.changed_data:
            print(form.cleaned_data["kit_status"])
            if form.cleaned_data["kit_status"] == "normal":
                status = "subscription"
                billing_price = 3333
            elif form.cleaned_data["kit_status"] == "cancel":
                status = "subscription_cancel"
                billing_price = 0
            elif form.cleaned_data["kit_status"] == "normal_kit_return":
                status = "normal_kit_return"
                billing_price = 6000
            elif form.cleaned_data["kit_status"] == "damaged_kit_return":
                status = "damaged_kit_return"
                billing_price = 20000

            models.GeneticTestLog.objects.create(
                order_date=datetime.datetime.now(),
                genetic_test=obj,
                action=status,
                billing_price=billing_price,
                registrant=request.user,
            )
        super().save_model(request, obj, form, change)


class GeneticTestLogAdmin(admin.ModelAdmin):
    model = models.GeneticTestLog
    list_display = [
        'order_date', 'get_customer', 'genetic_test', 'action', 'billing_price', 'current_times', 'created_at' 
    ]
    search_fields = [
        "genetic_test__customer__name", "genetic_test__customer__username"
    ]
    ordering = [
        'created_at', 'updated_at'
    ]
    
    def save_model(self, request, obj, form, change):
        obj.registrant = request.user
        super().save_model(request, obj, form, change)

    def get_customer(self, obj):
        return obj.genetic_test.customer.name
    get_customer.short_description = '고객명'


class GeneticTestKitAdmin(admin.ModelAdmin):
    model = models.GeneticTestKit
    list_display = [
        "kit_code","order_id","genetic_test","registrant"
    ]
    search_fields = ('kit_code', 'genetic_test__coupon', 'order_id', 'registrant')


class JMFSubscriptionAdmin(admin.ModelAdmin):
    model = models.JMFSubscription
    list_display = [
        "product","user_name","coupon","order_id","start_datetime","end_datetime","current_times","is_active","is_coupon_used","is_event"
    ]


class JMFSubscriptionPaymentLogAdmin(admin.ModelAdmin):
    model = models.JMFSubscriptionPaymentLog
    list_display = [
        "order_date","jmf_subscription", "get_name", "action","billing_price","current_times","registrant",
    ]
    def get_name(self, obj):
        if obj.jmf_subscription:
            return obj.jmf_subscription.user_name
        else:
            return ""




# class GeneticPromotionProductAdmin(admin.ModelAdmin):
#     model = models.GeneticPromotionProduct
#     list_display = [
#         'product_code', 'product_name', 'connection_client'
#     ]
#     list_filter = ('connection_client',)
#     search_fields = ('product_code', 'connection_client', 'event_code',)


# class GeneticPromotionAdmin(admin.ModelAdmin):
#     model = models.GeneticPromotion
#     list_display = [
#         'coupon', 'customer', 'total_times', 'left_times', 'sign_datetime', 'promotion_product'
#     ]
#     readonly_fields = ['coupon', 'customer', 'total_times', 'sign_datetime', 'promotion_product']
#     list_filter = ("promotion_product__product_name", "promotion_product__connection_client")
#     search_fields = ('coupon', 'customer__username', 'customer__name', 'promotion_product__product_name', 'promotion_product__connection_client')


# class GeneticPromotionKitAdmin(admin.ModelAdmin):
#     model = models.GeneticPromotionKit
#     list_display = [
#         'kit_code', 'coupon', 'order_id', 'genetic_promotion'
#     ]
#     search_fields = ('kit_code', 'coupon', 'order_id',)


# class GeneticPromotionLogAdmin(admin.ModelAdmin):
#     model = models.GeneticPromotionLog
#     list_display = [
#         'order_date', 'order_time', 'genetic_promotion', 'action', 'current_month_times', 'billing_price'
#     ]
#     list_filter = ('action',)


# class MacrogenSettlementAdmin(admin.ModelAdmin):
#     model = models.MacrogenSettlement
#     list_display = [
#         'customer', 'phone_number', 'genetic_promotion', 'order_id', 'start_datetime', 'kit_current_times', "status", 'is_active'
#     ]
#     readonly_fields = ['customer', 'phone_number', 'genetic_promotion', 'order_id', 'start_datetime']
#     list_filter = ('status', 'is_active')
#     search_fields = ('customer__username', 'customer__name', 'order_id', 'genetic_promotion__coupon',)

class GeneticTestLogResultAdmin(admin.ModelAdmin):
    model = models.GeneticTestLogResult
    list_display = [
        'result_file_excel', 'created_at', 'updated_at'
    ]
    ordering = [
        '-created_at', 'updated_at'
    ]

class JMFSubscriptionLogResultAdmin(admin.ModelAdmin):
    model = models.JMFSubscriptionLogResult
    list_display = [
        'result_file_excel', 'created_at', 'updated_at'
    ]
    ordering = [
        '-created_at', 'updated_at'
    ]


class ProductBannerAdmin(admin.ModelAdmin):
    model = models.ProductBanner
    list_display = ["image", "title", "description", "url", "is_active", "ordering", "is_url", 
    ]
    ordering = [
        '-ordering',
    ]

class BillStatusAdmin(admin.ModelAdmin):
    model = models.BillStatus
    list_display = [
            "user_name","status", "price" 
    ]

admin.site.register(models.Post, PostAdmin)
admin.site.register(models.Fruit, FruitAdmin)
admin.site.register(models.Matrix, MatrixAdmin)
admin.site.register(models.Survey)
admin.site.register(models.Trait, TraitAdmin)
admin.site.register(models.FruitTrait)
admin.site.register(models.MetaboliteTrait)
admin.site.register(models.Metabolite)
admin.site.register(models.Setting)
admin.site.register(models.FruitMetaboliteContent)
admin.site.register(models.TOS)
admin.site.register(models.Customer, CustomerAdmin)
admin.site.register(models.ServiceAPILog, ServiceAPILogAdmin)
admin.site.register(models.AppVersion, AppVersionAdmin)
admin.site.register(models.Question, QuestionAdmin)
admin.site.register(models.ShippingDetail)
admin.site.register(models.EventAPILog, EventAPILogAdmin)
# admin.site.register(models.GeneticPromotionProduct, GeneticPromotionProductAdmin)
# admin.site.register(models.GeneticPromotion, GeneticPromotionAdmin)
# admin.site.register(models.GeneticPromotionKit, GeneticPromotionKitAdmin)
# admin.site.register(models.GeneticPromotionLog, GeneticPromotionLogAdmin)
# admin.site.register(models.MacrogenSettlement, MacrogenSettlementAdmin)
# admin.site.register(models.GeneticPromotionLogResult)
admin.site.register(models.GeneticTestProduct, GeneticTestProductAdmin)
admin.site.register(models.GeneticTest, GeneticTestAdmin)
admin.site.register(models.GeneticTestKit)
admin.site.register(models.GeneticTestLog, GeneticTestLogAdmin)
admin.site.register(models.GeneticTestLogResult, GeneticTestLogResultAdmin)
admin.site.register(models.JMFSubscriptionLogResult, JMFSubscriptionLogResultAdmin)
#admin.site.register(models.GeneticTestLogResult)
admin.site.register(models.ProductBanner, ProductBannerAdmin)
admin.site.register(models.JMFSubscription, JMFSubscriptionAdmin)
admin.site.register(models.JMFSubscriptionPaymentLog, JMFSubscriptionPaymentLogAdmin)
admin.site.register(models.QuestionEmailLog)
admin.site.register(models.BillStatus, BillStatusAdmin)






