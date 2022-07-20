from django.db.models import F, IntegerField, Value

from rest_framework import serializers
import fruitdb.models as models
import pandas as pd
import json
import time


class FruitTraitSerializer(serializers.ModelSerializer):
    name_ko = serializers.SerializerMethodField()
    name_en = serializers.SerializerMethodField()

    class Meta:
        model = models.FruitTrait
        fields = (
            "name_ko",
            "name_en",
        )
        examples = {"name_ko": "체중감량", "name_en": "body weight loss"}

    def get_name_ko(self, obj):
        return obj.trait.name_ko

    def get_name_en(self, obj):
        return obj.trait.name_en


class FruitSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    if_id = serializers.SerializerMethodField()
    # traits = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    image_thumbnail = serializers.SerializerMethodField()
    season = serializers.SerializerMethodField()

    class Meta:
        model = models.SurveyFruit
        fields = (
            "name",
            "if_id",
            # "traits",
            "description",
            "image",
            "image_thumbnail",
            "season",
        )
        examples = {
            "name": "아로니아",
            "if_id": "IFCP3790",
            "traits": [
                {"name_ko": "혈압", "name_en": "Hypertension"},
                {"name_ko": "혈당", "name_en": "Type 2 diabetes"},
                {"name_ko": "흡연유무", "name_en": "Lung cancer"},
                {"name_ko": "키/몸무게", "name_en": "Body mass index"},
            ],
        }

    def get_name(self, obj):
        return obj.fruit.name

    def get_if_id(self, obj):
        return obj.fruit.if_id

    # def get_traits(self, obj):
    #     fruit_trait = models.FruitTrait.objects.filter(fruit=obj.fruit).filter(trait__in=list(obj.survey.traits.all()))
    #     return FruitTraitSerializer(fruit_trait, many=True).data

    def get_description(self, obj):
        return obj.fruit.efficacy

    def get_season(self, obj):
        return obj.fruit.season.split(",")

    def get_image_thumbnail(self, obj):
        if obj.fruit.image != None and obj.fruit.image != "":
            temp = obj.fruit.image_thumbnail.path
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(obj.fruit.image_thumbnail)
            )
        else:
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(models.Setting.load().default_image)
            )

    def get_image(self, obj):
        if obj.fruit.image != None and obj.fruit.image != "":
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(obj.fruit.image)
            )
        else:
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(models.Setting.load().default_image)
            )


class SurveySerializer(serializers.ModelSerializer):
    goals = serializers.SerializerMethodField()
    dis = serializers.SerializerMethodField()
    allergies = serializers.SerializerMethodField()

    class Meta:
        model = models.Survey
        fields = (
            "id",
            "name",
            "height",
            "weight",
            "sm",
            "bs",
            "bp",
            "sex",
            "goals",
            "dis",
            "allergies",
            "birth_date",
            "is_all",
        )
        examples = {
            "id": 120,
            "name": "홍길",
            "height": 170.0,
            "weight": 70.0,
            "sm": "2",
            "bs": "2",
            "sex": "Male",
        }

    def get_goals(self, obj):
        goals = list(
            models.Trait.objects.filter(category="생활목표").values_list(
                "name_ko", flat=True
            )
        )
        tmp_list = []
        for item in list(
            obj.traits.all().filter(is_default=False).values_list("name_ko", flat=True)
        ):
            if item in goals:
                tmp_list.append(item)
        return tmp_list

    def get_dis(self, obj):
        goals = list(
            models.Trait.objects.filter(category="생활목표").values_list(
                "name_ko", flat=True
            )
        )
        tmp_list = []
        print(
            list(
                obj.traits.all()
                .filter(is_default=False)
                .values_list("name_ko", flat=True)
            )
        )
        for item in list(
            obj.traits.all().filter(is_default=False).values_list("name_ko", flat=True)
        ):
            if item not in goals:
                tmp_list.append(item)
        return tmp_list

    def get_allergies(self, obj):
        return list(obj.allergies.all().values_list("if_id", flat=True))


class SurveyFruitSerializer(serializers.Serializer):
    survey = serializers.SerializerMethodField()
    fruits = serializers.SerializerMethodField()
    nc_fruits = serializers.SerializerMethodField()
    status = serializers.CharField(default="success")

    def get_fruits(self, obj):
        survey = self.context["survey"]
        survey_fruits = models.SurveyFruit.objects.filter(
            survey=survey, fruit__is_circulated=True
        )
        return FruitSerializer(
            survey_fruits, context={"request": self.context["request"]}, many=True
        ).data

    def get_nc_fruits(self, obj):
        survey = self.context["survey"]
        survey_fruits = models.SurveyFruit.objects.filter(survey=survey)
        return FruitSerializer(
            survey_fruits, context={"request": self.context["request"]}, many=True
        ).data

    def get_survey(self, obj):
        survey = self.context["survey"]
        return SurveySerializer(survey).data

    def create(self):
        if self.is_valid():
            return self.data
        else:
            return self.errors


class SubscriptionFruitDetailSerializer(serializers.ModelSerializer):
    trait_metabolites = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = models.Fruit
        fields = (
            "name",
            "if_id",
            "image",
            "trait_metabolites",
        )
        examples = {}

    def get_image(self, obj):
        if obj.image != None and obj.image != "":
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(obj.image)
            )
        else:
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(models.Setting.load().default_image)
            )

    def get_trait_metabolites(self, obj):
        start = time.time()
        fm = pd.read_csv(models.Matrix.load().fm, index_col=0)  # context로 받기
        mt = pd.read_csv(models.Matrix.load().mt, index_col=0)
        base_matrix = fm[fm.index == obj.if_id]
        columns = list(base_matrix.columns)
        values = base_matrix.values[0]
        metas = []
        metas_dict = {}
        for i in range(len(columns)):
            if values[i] > 0:
                metas.append((columns[i], values[i]))
                metas_dict[columns[i]] = values[i]

        res_list = []
        surveys = models.Survey.objects.filter(id__in=self.context["survey_ids"])
        meta_all = models.MetaboliteTrait.objects.select_related("trait").all()
        # sstart = time.time()
        res = []
        meta_ids = list(map(lambda x: x[0], metas))
        for survey in surveys:
            selected_mt = meta_all.filter(
                trait__in=survey.traits.all(), metabolite__if_id__in=meta_ids
            )

            res += list(
                selected_mt.annotate(
                    traits=F("trait__name_ko"),
                    traits_en=F("trait__name_en"),
                    meta=F("metabolite__if_id"),
                    metabolite_en=F("metabolite__name_en"),
                    survey=Value(survey.pk, output_field=IntegerField()),
                ).values("traits", "meta", "metabolite_en", "survey", "traits_en")
            )

        res_df = pd.DataFrame(res)
        if len(res_df) == 0:
            res_df = pd.DataFrame(
                columns=["traits", "meta", "metabolite_en", "survey", "traits_en"]
            )
        # print(f"end1 : {time.time()-sstart}")
        added_df = res_df.groupby(["survey", "meta", "metabolite_en"])[
            "traits_en"
        ].apply(list)
        # print(list(added_df))
        res_df = (
            res_df.groupby(["survey", "meta", "metabolite_en"])["traits"]
            .apply(list)
            .reset_index()
        )
        res_df["traits_en"] = list(added_df)
        # print(res_df)

        def get_pmids(row):
            mt_pmids = models.MetaboliteTraitPmid.objects.filter(
                metabolite__if_id=row["meta"], trait__name_ko__in=row["traits"]
            )
            pmids = []
            for pmid in list(mt_pmids.values_list("pmids", flat=True)):
                pmids += json.loads(pmid)
            return pmids

        # res_df['pmids'] = res_df.apply(get_pmids, axis=1)
        # print(f"end2 : {time.time()-sstart}")

        def get_value(row):
            return (
                sum(list(mt[mt.index == row["meta"]][row["traits_en"]].values[0]))
                * metas_dict[row["meta"]]
            )

        if len(res_df) != 0:
            res_df["pmids"] = res_df.apply(get_pmids, axis=1)
            res_df["value"] = res_df.apply(get_value, axis=1)
            res_df = res_df.sort_values("value", ascending=False)

        # res_df['value'] = res_df.apply(get_value, axis=1)
        # res_df = res_df.sort_values('value', ascending=False)
        res_dict = res_df.to_dict()
        # print(f"end3 : {time.time()-sstart}")
        result_dict = {}
        if "value" in res_dict:
            for key in list(res_dict["value"].keys()):
                if res_dict["survey"][key] not in result_dict:
                    result_dict[res_dict["survey"][key]] = []
                s_dict = {
                    "traits": res_dict["traits"][key],
                    "metabolite": res_dict["metabolite_en"][key],
                    "meta": res_dict["meta"][key],
                    "value": res_dict["value"][key],
                    "pmids": res_dict["pmids"][key],
                }
                result_dict[res_dict["survey"][key]].append(s_dict)
        result_list = []
        for key in result_dict.keys():
            result_list.append(
                {"name": models.Survey.objects.get(pk=key).name, "mt": result_dict[key]}
            )
        # print(f"end4 : {time.time()-sstart}")
        return result_list


class ReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Reference
        fields = (
            "author",
            "title",
            "page",
            "journal",
            "year_month",
            "pubmed_id",
        )

    def get_author(self, obj):
        return str(obj.author).replace("|", ", ") + "."


class FruitDetailSerializer(serializers.ModelSerializer):
    trait_metabolites = serializers.SerializerMethodField()
    detail_image = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    scientific_name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    survey_names = serializers.SerializerMethodField()

    class Meta:
        model = models.Fruit
        fields = (
            "name",
            "if_id",
            "scientific_name",
            "variety",
            "efficacy",
            "season",
            "storage_method",
            "selection_method",
            "infant",
            "pet",
            "calorie",
            "total_sugar",
            "potassium",
            "vitamin_c",
            "detail_image",
            "image",
            "username",
            "survey_names",
            "trait_metabolites",
            # "nutrition",
        )
        examples = {}

    def get_username(self, obj):
        return self.context["survey"].username

    def get_survey_names(self, obj):
        return list(
            map(
                lambda x: x[0],
                list(self.context["survey"].traits.all().values_list("name_ko")),
            )
        )

    def get_detail_image(self, obj):
        if obj.detail_image != None and obj.detail_image != "":
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(obj.detail_image)
            )
        else:
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(models.Setting.load().detail_default_image)
            )

    def get_image(self, obj):
        if obj.image != None and obj.image != "":
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(obj.image)
            )
        else:
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(models.Setting.load().default_image)
            )

    def get_scientific_name(self, obj):
        string = obj.scientific_name
        str_arr = string.split("#")
        res_list = []
        for ind, s in enumerate(str_arr):
            if str_arr[ind] == "":
                continue
            text_type = "plain"
            if ind % 2 == 1:
                text_type = "italic"
            res_list.append({"type": text_type, "text": str_arr[ind]})
        return res_list

    def get_trait_metabolites(self, obj):
        fm = pd.read_csv(models.Matrix.load().fm, index_col=0)
        mt = pd.read_csv(models.Matrix.load().mt, index_col=0)
        # mt = mt.to_dict()
        base_matrix = fm[fm.index == obj.if_id]
        columns = list(base_matrix.columns)
        values = base_matrix.values[0]
        metas = []
        metas_dict = {}
        for i in range(len(columns)):
            if values[i] > 0:
                metas.append((columns[i], values[i]))
                metas_dict[columns[i]] = values[i]

        meta_all = models.MetaboliteTrait.objects.select_related("trait").all()
        # sstart = time.time()
        res = []

        if self.context["survey"].is_all == False:
            surveys = [self.context["survey"]]
        else:
            surveys = models.Survey.objects.filter(
                username=self.context["survey"].username, is_all=False
            )

        meta_ids = list(map(lambda x: x[0], metas))

        for survey in surveys:
            selected_mt = meta_all.filter(
                trait__in=models.Trait.objects.filter(name_en__in=survey.cal_traits)
                if survey.cal_traits
                else survey.traits.all(),
                metabolite__if_id__in=meta_ids,
            )

            res += list(
                selected_mt.annotate(
                    traits=F("trait__name_ko"),
                    traits_en=F("trait__name_en"),
                    meta=F("metabolite__if_id"),
                    metabolite_en=F("metabolite__name_en"),
                    survey=Value(survey.pk, output_field=IntegerField()),
                ).values("traits", "meta", "metabolite_en", "survey", "traits_en")
            )
        res_df = pd.DataFrame(res)
        # print(f"end1 : {time.time()-sstart}")
        if len(res_df) == 0:
            res_df = pd.DataFrame(
                columns=["traits", "meta", "metabolite_en", "survey", "traits_en"]
            )

        added_df = res_df.groupby(["survey", "meta", "metabolite_en"])[
            "traits_en"
        ].apply(list)
        # print(list(added_df))
        res_df = (
            res_df.groupby(["survey", "meta", "metabolite_en"])["traits"]
            .apply(list)
            .reset_index()
        )
        res_df["traits_en"] = list(added_df)
        # print(res_df)

        def get_pmids(row):
            mt_pmids = models.MetaboliteTraitPmid.objects.filter(
                metabolite__if_id=row["meta"], trait__name_ko__in=row["traits"]
            )
            pmids = []
            for pmid in list(mt_pmids.values_list("pmids", flat=True)):
                pmids += json.loads(pmid)
            return pmids

        # print(f"end2 : {time.time()-sstart}")

        def get_value(row):
            return (
                sum(list(mt[mt.index == row["meta"]][row["traits_en"]].values[0]))
                * metas_dict[row["meta"]]
            )

        if len(res_df) != 0:
            res_df["pmids"] = res_df.apply(get_pmids, axis=1)
            res_df["value"] = res_df.apply(get_value, axis=1)
            res_df = res_df.sort_values(["value", "survey"], ascending=[False, True])
        res_dict = res_df.to_dict()
        # print(f"end3 : {time.time()-sstart}")
        result_dict = {}
        if "value" in res_dict:
            for key in list(res_dict["value"].keys()):
                if res_dict["survey"][key] not in result_dict:
                    result_dict[res_dict["survey"][key]] = []
                s_dict = {
                    "traits": res_dict["traits"][key],
                    "metabolite": res_dict["metabolite_en"][key],
                    "meta": res_dict["meta"][key],
                    "value": res_dict["value"][key],
                    "pmids": res_dict["pmids"][key],
                }
                result_dict[res_dict["survey"][key]].append(s_dict)
        result_list = []

        for key in list(map(lambda x: x.pk, surveys)):
            result_list.append(
                {
                    "name": models.Survey.objects.get(pk=key).name,
                    "mt": result_dict[key] if key in result_dict else [],
                }
            )
        return result_list

    def add_nutrition(self, data):
        print(self.instance)
        res = [
            {"name": "Energy", "value": self.instance.calorie, "unit": "kcal"},
            {"name": "Total Sugar", "value": self.instance.total_sugar, "unit": "g"},
            {"name": "Potassium", "value": self.instance.potassium, "unit": "mg"},
            {"name": "Vitamin C", "value": self.instance.vitamin_c, "unit": "mg"},
        ]
        # # 여러명이여도 첫번째 사람으로 픽스
        if len(data.get("trait_metabolites")) > 0:
            base = data.get("trait_metabolites")[0]["mt"]
            base = [base[i]["meta"] for i in range(len(base))]

            for if_id in base:
                if if_id not in ["IFDM120", "IFDM2856"]:
                    fmc = models.FruitMetaboliteContent.objects.filter(
                        fruit__if_id=self.instance.if_id, metabolite__if_id=if_id
                    )
                    if fmc.exists():
                        res.append(
                            {
                                "name": fmc[0].metabolite.name_en,
                                "value": fmc[0].content,
                                "unit": fmc[0].metabolite.unit,
                            }
                        )
        data["nutrition"] = res
        return data

    def create(self):
        return self.add_nutrition(self.data)

    # def get_references(self, obj):
    #     survey_traits = self.context['survey'].traits.all()
    #     fm = pd.read_csv(models.Matrix.load().fm, index_col=0)
    #     columns = list(fm[fm.index==obj.if_id].columns)
    #     values = fm[fm.index==obj.if_id].values[0]
    #     metas = []
    #     for i in range(len(columns)):
    #         if values[i] > 0:
    #             metas.append(columns[i])
    #     res_references = None
    #     for trait in survey_traits:
    #         if res_references == None:
    #             res_references = models.MetaboliteTraitPmid.objects.filter(
    #                 metabolite__in=models.Metabolite.objects.filter(if_id__in=metas),
    #                 trait=trait
    #             )
    #         else:
    #             res_references |= models.MetaboliteTraitPmid.objects.filter(
    #                 metabolite__in=models.Metabolite.objects.filter(if_id__in=metas),
    #                 trait=trait
    #             )
    #     pmids = []
    #     for pmid in list(res_references.values_list("pmids", flat=True)):
    #         pmids += json.loads(pmid)
    #     return ReferenceSerializer(models.Reference.objects.filter(pubmed_id__in=pmids), many=True).data


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Customer
        fields = ("username", "firebase_token", "name")


class VersionListSerializer(serializers.Serializer):
    versions = serializers.SerializerMethodField()
    recent_version = serializers.SerializerMethodField()
    animation_text = serializers.SerializerMethodField()
    is_fm_detail = serializers.SerializerMethodField()
    is_visible_jmf_link = serializers.SerializerMethodField()

    def get_versions(self, obj):
        return list(
            models.AppVersion.objects.filter(
                target=self.context["target"], is_active=True
            )
            .order_by("pk")
            .values_list("version", flat=True)
        )

    def get_recent_version(self, obj):
        versions = models.AppVersion.objects.filter(
            target=self.context["target"], is_active=True, is_recent=True
        ).order_by("pk")
        if versions.exists():
            return versions.last().version
        else:
            return list(
                models.AppVersion.objects.filter(
                    target=self.context["target"], is_active=True
                )
                .order_by("pk")
                .values_list("version", flat=True)
            )[-1]

    def get_animation_text(self, obj):
        setting = models.Setting.load()
        return {
            "subscription_animation_text": setting.subscription_animation_text,
            "survey_animation_text": setting.survey_animation_text,
            "signup_animation_text": setting.signup_animation_text,
            "subscription_animation_text_detail": setting.subscription_animation_text_detail,
            "survey_animation_text_detail": setting.survey_animation_text_detail,
            "signup_animation_text_detail": setting.signup_animation_text_detail,
        }

    def get_is_fm_detail(self, obj):
        return models.Setting.load().is_fm_detail

    def get_is_visible_jmf_link(self, obj):
        return models.Setting.load().is_visible_jmf_link

    def create(self):
        if self.is_valid():
            return self.data
        else:
            return self.errors


class SubcriptionFruitDescriptionSerializer(serializers.ModelSerializer):
    detail_image = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    nutrition = serializers.SerializerMethodField()

    class Meta:
        model = models.Fruit
        fields = (
            "name",
            "if_id",
            "storage_method",
            "selection_method",
            "calorie",
            "total_sugar",
            "potassium",
            "vitamin_c",
            "detail_image",
            "image",
            "nutrition",
        )
        examples = {}

    def get_detail_image(self, obj):
        if obj.detail_image != None and obj.detail_image != "":
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(obj.detail_image)
            )
        else:
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(models.Setting.load().detail_default_image)
            )

    def get_image(self, obj):
        if obj.image != None and obj.image != "":
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(obj.image)
            )
        else:
            return (
                f"{self.context['request'].scheme}://{self.context['request'].get_host()}/media/"
                + str(models.Setting.load().default_image)
            )

    def get_nutrition(self, obj):
        fm = pd.read_csv(models.Matrix.load().fm, index_col=0)
        base_matrix = fm[fm.index == obj.if_id]
        columns = list(base_matrix.columns)
        values = base_matrix.values[0]
        metas = []
        # metas_dict = {}
        for i in range(len(columns)):
            if values[i] > 0:
                metas.append(columns[i])
                # metas_dict[columns[i]] = values[i]
        res = [
            {"name": "energy", "value": obj.calorie, "unit": "kcal"},
            {"name": "total Sugar", "value": obj.total_sugar, "unit": "g"},
            {"name": "potassium", "value": obj.potassium, "unit": "mg"},
            {"name": "vitamin C", "value": obj.vitamin_c, "unit": "mg"},
        ]
        # # 여러명이여도 첫번째 사람으로 픽스
        for if_id in metas:
            if if_id not in ["IFDM120", "IFDM2856"]:
                fmc = models.FruitMetaboliteContent.objects.filter(
                    fruit__if_id=obj.if_id, metabolite__if_id=if_id
                )
                if fmc.exists():
                    res.append(
                        {
                            "name": fmc[0].metabolite.name_en,
                            "value": fmc[0].content,
                            "unit": fmc[0].metabolite.unit,
                        }
                    )
        return res

class ProductBannerSerializers(serializers.ModelSerializer):
    class Meta:
        model = models.ProductBanner
        fields = (
            "image",
            "title",
            "description",
            "url",
            "is_active",
            "ordering",
            "is_url",
        )