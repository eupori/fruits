from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField
from imagekit.models import ProcessedImageField
from imagekit.processors import Thumbnail
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import ugettext_lazy as _
import datetime

from .core import *

from imagekit.models import ImageSpecField
from imagekit import processors
from pilkit.processors import ResizeToFit

from Bio import Entrez, Medline


# class Profile(TimeStampedModel):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     birth_date = models.DateField(null=True, blank=True, default="2000-01-01")
#     image = ProcessedImageField(
#         blank=True,
#         upload_to='profile/images',
#         processors=[Thumbnail(300, 300)],
#         format='JPEG',
#         options={'quality':90},
#         )
#     dc_id = models.CharField(max_length=50)
#     name = models.CharField(max_length=20)
#     phone = PhoneNumberField(
#         null=True, blank=True
#     )
#     SEX_CHOICES = (("Male", _("남성")), ("Female", _("여성")))
#     sex = models.CharField(choices=SEX_CHOICES, max_length=10, null=True)
#     birth_date = models.DateField(null=True, blank=True)
#     email = models.EmailField(null=True, blank=True)

# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(user=instance)


# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     instance.profile.save()


# class Customer(TimeStampedModel):
#     dc_id = models.CharField(max_length=50)
#     name = models.CharField(max_length=20)
#     phone = PhoneNumberField(
#         null=True, blank=True
#     )
#     SEX_CHOICES = (("Male", _("남성")), ("Female", _("여성")))
#     sex = models.CharField(choices=SEX_CHOICES, max_length=10, null=True)
#     birth_date = models.DateField(null=True, blank=True)
#     email = models.EmailField(null=True, blank=True)


# class Shipping(TimeStampedModel):
#     name = models.CharField(max_length=20)
#     zip_code = models.CharField(max_length=10)
#     address = models.CharField(max_length=100)
#     detail_address = models.CharField(max_length=100)
#     phone = PhoneNumberField(
#         null=True, blank=True
#     )
#     is_default = models.BooleanField(default=False)
#     is_dawn = models.BooleanField(default=False)
#     customer = models.ForeignKey(User, on_delete=models.CASCADE, null=True)


class Customer(TimeStampedModel):
    username = models.CharField(max_length=50, unique=True)
    firebase_token = models.TextField()
    birth_date = models.DateField(null=True, blank=True)
    SEX_CHOICES = (("Male", _("남성")), ("Female", _("여성")))
    sex = models.CharField(choices=SEX_CHOICES, max_length=10, null=True, blank=True)
    name = models.CharField(max_length=20, null=True, blank=True)
    app_version = models.CharField(max_length=10, null=True, blank=True)
    is_android = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_jmf_auth = models.BooleanField(default=True)
    is_jmf_join = models.BooleanField(default=False)
    is_genetic = models.BooleanField(default=False)
    is_pass_auth = models.BooleanField(default=False)
    is_choice_agree = models.BooleanField(default=False, null=True, blank=True)
    def __str__(self):
        return self.username


class ShippingDetail(models.Model):
    username = models.CharField(max_length=50)
    sno = models.CharField(max_length=15)
    entrance_password = models.CharField(max_length=100, blank=True, default="")
    request = models.TextField(blank=True, default="")


# 일단 로컬에 저장하는 방향으로
class Trait(models.Model):
    name_ko = models.CharField(max_length=30)
    name_en = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)
    CATEGOTY_CHOICES = (
        ("예방질병", _("예방질병")),
        ("신체 및 건강기록 정보", _("신체 및 건강기록 정보")),
        ("생활목표", _("생활목표")),
    )
    category = models.CharField(choices=CATEGOTY_CHOICES, max_length=30, default="생활목표")

    image = models.FileField(blank=True, null=True, upload_to="trait_image")
    active_image = models.FileField(blank=True, null=True, upload_to="trait_image")

    def __str__(self):
        return self.name_ko


class Fruit(TimeStampedModel):
    name = models.CharField(max_length=30)
    if_id = models.CharField(max_length=20)
    variety = models.TextField(blank=True)
    efficacy = models.TextField(blank=True)
    season = models.CharField(max_length=30, blank=True)  # -로 구분
    storage_method = models.TextField(blank=True)
    selection_method = models.TextField(blank=True)
    infant = models.BooleanField(default=False)
    pet = models.BooleanField(default=False)
    is_circulated = models.BooleanField(default=False)  ## 진맛과 유통 여부
    calorie = models.FloatField(default=0)
    total_sugar = models.FloatField(default=0)
    potassium = models.FloatField(default=0)
    vitamin_c = models.FloatField(default=0)
    scientific_name = models.CharField(max_length=100, null=True, blank=True)

    image = models.ImageField(null=True, blank=True, upload_to="fruit")
    detail_image = models.ImageField(null=True, blank=True, upload_to="fruit")
    image_thumbnail = ImageSpecField(
        source="image",  # 원본 ImageField 명
        processors=[processors.Transpose(), ResizeToFit(400)],  # 사이즈 조정
        format="JPEG",  # 최종 저장 포맷
        options={"quality": 60},
    )  # 저장 옵션

    def __str__(self):
        return self.name


class Survey(TimeStampedModel):
    name = models.CharField(max_length=20)
    height = models.FloatField()
    weight = models.FloatField()
    bs = models.CharField(max_length=10)
    bp = models.CharField(max_length=10)
    sm = models.CharField(max_length=10)
    SEX_CHOICES = (("Male", _("남성")), ("Female", _("여성")))
    sex = models.CharField(choices=SEX_CHOICES, max_length=10, null=True)
    # is_me = models.BooleanField(default=True)
    # user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    username = models.CharField(max_length=30, null=True)
    birth_date = models.DateField(null=True, blank=True, default="2000-01-01")
    traits = models.ManyToManyField(Trait, related_name="traits")
    # cal_traits = models.ManyToManyField(Trait, related_name="cal_traits")
    allergies = models.ManyToManyField(Fruit, related_name="allergies")
    fruits = models.ManyToManyField(Fruit, through="SurveyFruit", related_name="fruits")

    is_active = models.BooleanField(default=True)  # 삭제시 비활성화로
    is_all = models.BooleanField(default=False)

    lifelog = models.JSONField(null=True, default=None)
    genetic = models.JSONField(null=True, default=None)
    cal_traits = ArrayField(models.CharField(max_length=100), default=list)

    class Meta:
        ordering = (
            "-is_all",
            "id",
        )


@receiver(pre_delete, sender=Customer)
def pre_delete_customer(sender, instance, **kwargs):
    surveys = Survey.objects.filter(username=instance.username)
    if surveys.exists():
        surveys.delete()


class SurveyFruit(models.Model):
    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, verbose_name="survey_id"
    )
    fruit = models.ForeignKey(Fruit, on_delete=models.CASCADE, verbose_name="fruit_id")
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ("order",)


class FruitTrait(models.Model):
    fruit = models.ForeignKey(Fruit, on_delete=models.CASCADE, verbose_name="fruit_id")
    trait = models.ForeignKey(Trait, on_delete=models.CASCADE, verbose_name="trait_id")
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ("order",)


class Metabolite(models.Model):
    name_en = models.CharField(max_length=100)
    unit = models.CharField(max_length=10)
    if_id = models.CharField(max_length=10)

    def __str__(self):
        return self.if_id


class MetaboliteTrait(models.Model):
    metabolite = models.ForeignKey(
        Metabolite, on_delete=models.CASCADE, verbose_name="metabolite_id"
    )
    trait = models.ForeignKey(Trait, on_delete=models.CASCADE, verbose_name="trait_id")
    value = models.IntegerField()

    class Meta:
        ordering = ("value",)


class FruitMetaboliteContent(models.Model):
    fruit = models.ForeignKey(Fruit, on_delete=models.CASCADE, verbose_name="fruit_id")
    metabolite = models.ForeignKey(
        Metabolite, on_delete=models.CASCADE, verbose_name="metabolite_id"
    )
    content = models.FloatField()


class Matrix(SingletonModel):
    fm = models.FileField(blank=True)
    mt = models.FileField(blank=True)
    ft = models.FileField(blank=True)
    version = models.CharField(max_length=10)


class Setting(SingletonModel):
    default_image = models.FileField(blank=True, upload_to="default_image")
    detail_default_image = models.FileField(blank=True, upload_to="default_image")
    version = models.CharField(max_length=10)
    subscription_animation_text = models.TextField(blank=True)
    survey_animation_text = models.TextField(blank=True)
    signup_animation_text = models.TextField(blank=True)
    subscription_animation_text_detail = models.TextField(blank=True)
    survey_animation_text_detail = models.TextField(blank=True)
    signup_animation_text_detail = models.TextField(blank=True)
    is_fm_detail = models.BooleanField(default=False)
    is_visible_jmf_link = models.BooleanField(default=False)


class TOS(SingletonModel):
    personal_info = models.TextField(null=True, blank=True)
    service = models.TextField(null=True, blank=True)


### 브런치
class Post(TimeStampedModel):
    url = models.TextField(blank=True)
    title = models.CharField(max_length=100, blank=True)
    # image = models.ImageField(upload_to="post/images", blank=True)
    image = models.TextField(blank=True)  # path
    fruit = models.ForeignKey(Fruit, on_delete=models.SET_NULL, null=True)
    header = models.TextField(blank=True)
    content = models.TextField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title

    def time_since_ko(self):
        result_date = datetime.datetime.now() - self.created_at
        if result_date.days >= 365:
            return f"{int(result_date.days/365)}년전"
        elif result_date.days >= 30:
            return f"{int(result_date.days)/30}달전"
        elif result_date.days >= 1:
            return f"{result_date.days}일전"
        elif result_date.seconds >= 3600:
            return f"{int(result_date.seconds/3600)}시간전"
        elif result_date.seconds >= 60:
            return f"{int(result_date.seconds/60)}분전"
        else:
            return f"{result_date.seconds}초전"


def make_chunk(alist):
    chunk_size = 10
    while alist:
        yield alist[:chunk_size]
        alist = alist[chunk_size:]


class ReferenceManager(models.Manager):
    def get_or_crawling(self, pubmed_ids):
        if isinstance(pubmed_ids, str):
            pubmed_ids = pubmed_ids.split(",")
            print(pubmed_ids)
        pmids_in_db = self.filter(pubmed_id__in=pubmed_ids).values_list(
            "pubmed_id", flat=True
        )
        set_pmids_in_db = set(list(pmids_in_db))
        crawling_pmids = list(set(pubmed_ids) - set_pmids_in_db)
        print("to_crawl:", crawling_pmids)

        invalid_ids = []
        if crawling_pmids:
            for chunk_ids in make_chunk(crawling_pmids):
                print(chunk_ids)
                invalid_ids.append(self.save_references(chunk_ids))

        return self.filter(pubmed_id__in=pubmed_ids), invalid_ids

    def save_references(self, pubmed_ids):
        """pmid와 biopython을 이용하여 paper 정보 크롤링"""
        Entrez.email = "dsc@insilicogen.com"
        handle = Entrez.efetch(
            db="pubmed", id=pubmed_ids, rettype="medline", retmode="text"
        )

        def returning(x):
            return "|".join(x) if x else None

        invalid_ids = []
        for record in Medline.parse(handle):

            if "id:" in record and record["id:"]:
                invalid_ids.append(record["id:"])
                continue

            pmid = record["PMID"]
            journal = record.get("TA", None)
            title = record.get("TI", None)
            author = returning(record.get("AU", None))
            author_info = returning(record.get("AD", None))
            abstract = record.get("AB", None)
            copyright = returning(record.get("CI", None))
            ids = returning(record.get("AID", None))
            year_month = record.get("DP", None)
            page = record.get("IS", None)

            paper_dic = {
                "pubmed_id": pmid,
                "journal": journal,
                "title": title,
                "author": author,
                "author_info": author_info,
                "abstract": abstract,
                "copyright": copyright,
                "ids": ids,
                "year_month": year_month,
                "page": page,
            }
            # print(paper_dic)
            reference = self.create(**paper_dic)
            reference.save()
        return invalid_ids


class Reference(models.Model):
    pubmed_id = models.CharField(
        _("PubMed ID"), max_length=100, null=False, blank=False, db_index=True
    )
    journal = models.CharField(
        _("Journal"),
        max_length=200,
        null=True,
        blank=True,
    )
    title = models.TextField(
        _("Title"),
        null=True,
        blank=True,
    )
    author = models.TextField(
        _("Author"),
        null=True,
        blank=True,
    )
    author_info = models.TextField(
        _("Author Information"),
        null=True,
        blank=True,
    )
    abstract = models.TextField(
        _("Abstract Text"),
        null=True,
        blank=True,
    )
    copyright = models.TextField(
        _("Copyright"),
        null=True,
        blank=True,
    )
    ids = models.CharField(
        _("IDs"),
        max_length=200,
        null=True,
        blank=False,
    )
    year_month = models.CharField(
        _("Year & Month"),
        max_length=200,
        null=True,
    )
    page = models.CharField(
        _("Page"),
        max_length=200,
        null=True,
    )

    objects = ReferenceManager()


class MetaboliteTraitPmid(models.Model):
    metabolite = models.ForeignKey(Metabolite, null=True, on_delete=models.CASCADE)
    trait = models.ForeignKey(Trait, null=True, on_delete=models.CASCADE)
    pmids = models.TextField(null=True, blank=True)
    count = models.IntegerField(null=True, blank=True)


class ServiceAPILog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    username = models.CharField(max_length=50)
    api = models.CharField(max_length=50)
    method = models.CharField(max_length=10)
    status = models.PositiveIntegerField()


class AppVersion(TimeStampedModel):
    version = models.CharField(_("Version"), max_length=15)
    created_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    TARGET_CHOICES = (
        ("ANDROID", _("Android")),
        ("IOS", _("iOS")),
    )
    target = models.CharField(
        _("Target"),
        choices=TARGET_CHOICES,
        max_length=15,
    )
    is_recent = models.BooleanField(default=True)


class Question(TimeStampedModel):
    customer = models.ForeignKey(Customer, null=True, on_delete=models.CASCADE)
    email = models.CharField(max_length=50)
    content = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.customer.username


class Notice(TimeStampedModel):
    title = models.CharField(max_length=100)
    content = models.TextField(blank=True)

    def __str__(self):
        return self.title


class EventAPILog(TimeStampedModel):
    customer = models.ForeignKey(Customer, null=True, on_delete=models.CASCADE)
    event_code = models.CharField(max_length=30)
    event_text = models.TextField(blank=True)
    phone = models.CharField(max_length=30)
    is_success = models.BooleanField(default=True)


# class GeneticPromotion(TimeStampedModel):
#     coupon = models.CharField(_('쿠폰 번호'), max_length=100, unique=True, primary_key=True)
#     customer = models.ForeignKey(Customer, null=True, on_delete=models.SET_NULL)
#     # customer_name = models.CharField(_('고객명'), max_length=100, blank=True)
#     # customer_id = models.CharField(_('아이디'), max_length=100, blank=True)
#     order_id = models.CharField(_('주문번호'), max_length=100, blank=True, null=True)
#     phone_number = PhoneNumberField(_('전화번호'), blank=True)
#     total_times = models.SmallIntegerField(_('약정 회차'), default=12)
#     left_times = models.SmallIntegerField(_('남은 회차'), default=12)
#     sign_datetime = models.DateTimeField(_('가입일'), auto_now=False, auto_now_add=False)
#     termination_datetime = models.DateTimeField(_('해지일'), auto_now=False, auto_now_add=False, blank=True, null=True)
#     promotion_product = models.ForeignKey(GeneticPromotionProduct, verbose_name=_("프로모션 상품"), on_delete=models.SET_NULL, null=True, blank=True)

#     def __str__(self):
#         return f"{self.customer.name}_{self.coupon}"


# class GeneticPromotionKit(TimeStampedModel):
#     kit_code = models.CharField(_('키트 번호'),max_length=100, blank=True)
#     coupon = models.CharField(_('쿠폰 번호'),max_length=100, blank=True)
#     order_id = models.CharField(_('주문번호'), max_length=100, blank=True)
#     genetic_promotion = models.ForeignKey(GeneticPromotion, verbose_name=_("프로모션"), on_delete=models.SET_NULL, null=True, blank=True)

#     def __str__(self):
#         return f"{kit_code}"


# class GeneticPromotionLog(TimeStampedModel):
#     ACTION_CHOICES = (
#         ("order_request", _("주문")),
#         ("order_confirmed", _("주문확정 수신")),
#         ("subscription", _("정기 결제 ")),
#         ("test_agree", _("유전자검사 동의")),
#         ("test_request", _("유전자검사 신청")),
#         ("kit_send", _("유전자검사 키트발송")),
#         ("kit_recept", _("유전자검사 키트수신")),
#         ("result_regist", _("유전자검사 결과등록")),
#         ("cancel_request", _("취소 접수")),
#         ("normal_kit_return", _("정상 키트 반송")),
#         ("damaged_kit_return", _("파손 키트 반송")),
#         ("subscription_cancel", _("구독 해지"))
#     )
    
#     order_date = models.DateField(_('주문 날짜'), auto_now=False, auto_now_add=False)
#     order_time = models.TimeField(_('주문 시간'), auto_now=False, auto_now_add=False)
#     genetic_promotion = models.ForeignKey(GeneticPromotion, verbose_name=_("프로모션"), on_delete=models.SET_NULL, null=True, blank=True)
#     # promotion_kit_id = models.CharField(max_length=100, blank=True)
#     # promotion_kit = models.ForeignKey(GeneticPromotionKit, verbose_name=_("프로모션 키트"), on_delete=models.SET_NULL, null=True, blank=True)
#     action = models.CharField(_('이벤트'), choices=ACTION_CHOICES, max_length=100)
#     current_month_times = models.SmallIntegerField(_('결제 회차'), default=0)
#     accumulate_times = models.SmallIntegerField(_('월별 누적'), default=0)
#     billing_price = models.SmallIntegerField(_('청구 금액'), default=0)

#     def __str__(self):
#         if self.genetic_promotion:
#             return f"{self.genetic_promotion.customer.name}_{self.created_at}"
#         else:
#             return f"{self.created_at}"


# class GeneticPromotionLogResult(TimeStampedModel):
#     result_file_excel = models.FileField(_("정산 결과"), blank=True, null=True, upload_to="macrogen_settlement_result")
    
#     def __str__(self):
#         return f"{self.result_file_excel}"


# class MacrogenSettlement(TimeStampedModel):
#     STSTUS_COICES = (
#         ("normal_proceeding", _("할부")),
#         ("cancel_normal", _("해지(일시납)")),
#         ("kit_open", _("키트개봉")),
#         ("kit_delivery", _("키트배송")),
#     )

#     customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
#     phone_number = PhoneNumberField(_('고객 전화번호'), blank=True)
#     # product_id = models.CharField(_('상품 id'), max_length=100, blank=True)
#     genetic_promotion = models.ForeignKey(GeneticPromotion, verbose_name=_("프로모션"), on_delete=models.SET_NULL, null=True, blank=True)
#     order_id = models.CharField(_('주문번호'), max_length=100, null=True, blank=True)
#     start_datetime = models.DateTimeField(_('시작일시'), auto_now=False, auto_now_add=False, blank=True, null=True)
#     end_datetime = models.DateTimeField(_('종료일사'), auto_now=False, auto_now_add=False, blank=True, null=True)
#     total_times = models.SmallIntegerField(_('약정 회차'), default=12)
#     kit_current_times = models.SmallIntegerField(_('당월 회차'), default=1)
#     status = models.CharField(_('상태'), choices=STSTUS_COICES, max_length=100, default="normal_proceeding")
#     is_active = models.BooleanField(_("사용 여부"), default=True)

#     def __str__(self):
#         return f"{self.customer.username}_{self.created_at.date()}"


class GeneticTestProduct(TimeStampedModel):
    CLIENT_COICES = (
        ("1", _("카카오")),
        ("2", _("고도몰")),
        ("999", _("과일궁합")),
    )

    product_code = models.CharField(_('상품코드'), max_length=100)
    connection_client = models.CharField(_('거래처'), choices=CLIENT_COICES, max_length=100)
    product_name = models.CharField(_('상품명'),max_length=100)
    total_times = models.SmallIntegerField(_('약정 회차'), default=12)
    month_range = models.SmallIntegerField(_('월 배송 주기'), default=1)
    price = models.IntegerField(_('상품 금액'), default=0)
    is_active = models.BooleanField(_("사용 여부"), default=True)

    def __str__(self):
        return f"{self.product_code}_{self.product_name}"


class GeneticTest(TimeStampedModel):
    KIT_STATUS_COICES = (
        ("normal", _("정상")),
        ("cancel", _("정상 해지")),
        ("cancel_request", _("키트 취소 신청")),
        ("normal_kit_return", _("정상 키트 반송")),
        ("damaged_kit_return", _("파손 키트 반송 혹은 미반송")),
        ("test_start_cancel", _("검사 시작 후 취소"))
    )
    STATUS_COICES = (
        ("normal", _("정상")),
        ("cancel", _("해지")),
    )

    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    test_product = models.ForeignKey(GeneticTestProduct, verbose_name=_("프로모션 상품"), on_delete=models.SET_NULL, null=True, blank=True)
    phone = PhoneNumberField(null=True, blank=True)
    coupon = models.CharField(_('쿠폰 번호'),max_length=100, blank=True, null=True)
    order_id = models.CharField(_('주문번호'), max_length=100, null=True, blank=True)
    start_datetime = models.DateTimeField(_('시작일시'), auto_now=False, auto_now_add=False, blank=True, null=True)
    end_datetime = models.DateTimeField(_('종료일시'), auto_now=False, auto_now_add=False, blank=True, null=True)
    current_times = models.IntegerField(_('결제 회차'), default=0)
    total_times = models.IntegerField(_('약정 회차'), default=12)
    kit_status = models.CharField(_('이벤트'), choices=KIT_STATUS_COICES, max_length=100, default="normal")
    is_active = models.BooleanField(_("사용 여부"), default=False)
    is_kit_recept = models.BooleanField(_("키트 수신 여부"), default=False)
    status = models.CharField(_('상태'), choices=STATUS_COICES, max_length=100, default="normal")
    is_kit_settlement = models.BooleanField(_("키트 수신 여부"), default=False)

    def __str__(self):
        return f"{self.customer.name}_{self.coupon}"

    #저장 시 kit_status상태에 따른 로그 생성 기능 구현 필요


class GeneticTestKit(TimeStampedModel):
    kit_code = models.CharField(_('키트 번호'),max_length=100, blank=True)
    order_id = models.CharField(_('주문번호'), max_length=100, blank=True, null=True)
    genetic_test = models.ForeignKey(GeneticTest, verbose_name=_("프로모션"), on_delete=models.SET_NULL, null=True, blank=True)
    invoice_datetime = models.DateTimeField(_('발송일시'), auto_now=False, auto_now_add=False, blank=True, null=True)
    registrant = models.ForeignKey(User, verbose_name=_("담당자"), on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f"{self.kit_code}"

        
class GeneticTestLog(TimeStampedModel):
    ACTION_CHOICES = (
        ("order_request", _("주문")),
        ("order_confirmed", _("주문확정 수신")),
        ("subscription", _("할부")),
        ("test_agree", _("유전자검사 동의")),
        ("test_request", _("유전자검사 신청")),
        ("cancel_request", _("키트 취소 신청")),
        ("test_cancel", _("유전자검사 취소")),
        ("kit_send", _("유전자검사 키트발송")),
        ("kit_recept", _("유전자검사 키트수신")),
        ("analyze_fail", _("유전자검사 실패")),
        ("kit_resend", _("유전자검사 키트 재발송")),
        ("result_regist", _("유전자검사 결과등록")),
        ("cancel_request", _("취소 접수")),
        ("normal_kit_cancel", _("정상 키트 취소")),
        ("normal_kit_return", _("정상 키트 반송")),
        ("damaged_kit_return", _("파손 키트 반송 혹은 미반송")),
        ("test_start_cancel", _("검사 시작 후 취소")),
        ("subscription_cancel", _("구독 해지"))
    )
    
    order_date = models.DateTimeField(_('주문 일시'), auto_now=False, auto_now_add=False)
    genetic_test = models.ForeignKey(GeneticTest, verbose_name=_("프로모션"), on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(_('이벤트'), choices=ACTION_CHOICES, max_length=100)
    billing_price = models.IntegerField(_('청구 금액'), default=0)
    current_times = models.IntegerField(_('결제 회차'), default=0)
    registrant = models.ForeignKey(User, verbose_name=_("담당자"), on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        if self.genetic_test:
            return f"{self.genetic_test.customer.name}_{self.created_at}"
        else:
            return f"{self.created_at}"

    def save(self, *args, **kwargs):
        print(self)
        # self.registrant = self.request.user
        super().save(*args, **kwargs)

    def get_action(self):
        return self.get_action_display()


class GeneticTestLogResult(TimeStampedModel):
    result_file_excel = models.FileField(_("정산 결과"), blank=True, null=True, upload_to="macrogen_settlement_result")
    
    def __str__(self):
        return f"{self.result_file_excel}"


class JMFSubscription(TimeStampedModel):
    SUB_TYPE_COICES = (
        ("0", _("유전자 프로모션 관련 구독")),
        ("1", _("이벤트 쿠폰(특정금액 구매)")),
        ("2", _("고도몰 구독상품")),
        ("3", _("쿠폰 임의발급 상품")),
    )
    sno = models.CharField(_('고도몰 일련번호'),max_length=100)
    # customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    user_name = models.CharField(_('사용자 이름'),max_length=100, blank=True, null=True)
    product = models.ForeignKey(GeneticTestProduct, verbose_name=_("프로모션 상품"), on_delete=models.SET_NULL, null=True, blank=True)
    phone = PhoneNumberField(null=True, blank=True)
    coupon = models.CharField(_('쿠폰 번호'),max_length=100, blank=True, null=True)
    order_id = models.CharField(_('주문번호'), max_length=100, null=True, blank=True)
    start_datetime = models.DateTimeField(_('시작일시'), auto_now=False, auto_now_add=False, blank=True, null=True)
    end_datetime = models.DateTimeField(_('종료일시'), auto_now=False, auto_now_add=False, blank=True, null=True)
    current_times = models.IntegerField(_('결제 회차'), default=0)
    total_times = models.IntegerField(_('약정 회차'), default=12)
    is_active = models.BooleanField(_("사용 여부"), default=False)
    is_coupon_used = models.BooleanField(_("쿠폰 사용 여부"), default=False)
    is_event = models.BooleanField(_("이벤트 쿠폰 여부"), default=False)
    sub_type = models.CharField(_('구독 타입'), choices=SUB_TYPE_COICES, max_length=100)
    is_extra_billing = models.BooleanField(_("기타 청구 금액 여부"), default=False)
    coupon_end_datetime = models.DateTimeField(_('쿠폰 만료일시'), auto_now=False, auto_now_add=False, blank=True, null=True)
    kit_end_datetime = models.DateTimeField(_('쿠폰 만료일시'), auto_now=False, auto_now_add=False, blank=True, null=True)
    kit_receive_datetime = models.DateTimeField(_('검사 시작일시'), auto_now=False, auto_now_add=False, blank=True, null=True)

    def __str__(self):
        return f"{self.sno}-{self.user_name}-{self.coupon}"


class BillStatus(TimeStampedModel):
    BILL_STATUS_CHOICE = (
        ("contract", _("약정 진행중")),
        ("coupon_bill_in_active", _("중도 해지 쿠폰 미사용 청구")),
        ("coupon_refund_in_active", _("중도 해지 쿠폰 사용 환급")),
        ("coupon_bill", _("쿠폰 미사용 청구")),
        ("coupon_refund", _("쿠폰 사용 환급")),
        ("kit_bill", _("키트 미사용 청구")),
        ("kit_refund", _("키트 사용 환급")),
    )
    jmf_sub = models.ForeignKey(JMFSubscription, null=True, blank=True, on_delete=models.SET_NULL)    
    user_name = models.CharField(_('사용자 이름'),max_length=100, blank=True, null=True)
    status = models.CharField(_('상태'), choices=BILL_STATUS_CHOICE, max_length=100, default="contract")
    price = models.IntegerField(_('금액'), default=0)


class JMFSubscriptionPaymentLog(TimeStampedModel):
    ACTION_CHOICES = (
        ("order_request", _("주문")),
        ("order_confirmed", _("주문확정 수신")),
        ("subscription", _("정기결제")),
        ("test_agree", _("유전자검사 동의")),
        ("test_request", _("유전자검사 신청")),
        ("kit_send", _("유전자검사 키트발송")),
        ("kit_recept", _("유전자검사 키트수신")),
        ("analyze_fail", _("유전자검사 실패")),
        ("kit_resend", _("유전자검사 키트 재발송")),
        ("result_regist", _("유전자검사 결과등록")),
        ("cancel_request", _("취소 접수")),
        ("normal_kit_cancel", _("정상 키트 취소")),
        ("normal_kit_return", _("정상 키트 반송")),
        ("damaged_kit_return", _("파손 키트 반송 혹은 미반송")),
        ("subscription_cancel", _("구독 해지"))
    )

    STATUS_CHOICES = (
        ("paid", _("정상결제")),
        ("refund", _("환불")),
    )
    
    order_date = models.DateTimeField(_('주문 일시'), auto_now=False, auto_now_add=False)
    jmf_subscription = models.ForeignKey(JMFSubscription, verbose_name=_("프로모션"), on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(_('이벤트'), choices=ACTION_CHOICES, max_length=100, null=True, blank=True)
    status = models.CharField(_('지불 상태'), choices=STATUS_CHOICES, max_length=100, default="paid")
    billing_price = models.IntegerField(_('청구 금액'), default=0)
    current_times = models.IntegerField(_('결제 회차'), default=0)
    registrant = models.ForeignKey(User, verbose_name=_("담당자"), on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f"{self.order_date}-{self.jmf_subscription}"


class ProductBanner(TimeStampedModel):
    image = models.CharField(_('이미지 URL'), max_length=100, null=True, blank=True)
    title = models.CharField(_('제목'), max_length=100, null=True, blank=True)
    description = models.CharField(_('설명'), max_length=100, null=True, blank=True)
    url = models.CharField(_("이동 URL"), max_length=100, null=True, blank=True)
    is_active = models.BooleanField(_("사용 여부"), default=False)
    ordering = models.IntegerField(_('정렬순서'))
    is_url = models.BooleanField(_("링크 이동 여부"), default=True)


class QuestionEmailLog(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.SET_NULL, verbose_name="order id", null=True)
    status = models.CharField(_("상태"), max_length=100, null=True, blank=True)
    message = models.TextField(_("메시지"), blank=True)    


class JMFSubscriptionLogResult(TimeStampedModel):
    result_file_excel = models.FileField(_("정산 결과"), blank=True, null=True, upload_to="jmf_settlement_result")
    
    def __str__(self):
        return f"{self.result_file_excel}"
