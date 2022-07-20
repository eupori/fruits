# Generated by Django 3.1.1 on 2022-04-08 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0005_auto_20220407_1326'),
    ]

    operations = [
        migrations.AlterField(
            model_name='geneticpromotionkit',
            name='coupon',
            field=models.CharField(blank=True, max_length=100, verbose_name='쿠폰 번호'),
        ),
        migrations.AlterField(
            model_name='macrogensettlement',
            name='status',
            field=models.CharField(choices=[('normal_proceeding', '할부'), ('cancel_normal', '해지(일시납)'), ('kit_open', '키트개봉'), ('kit_delivery', '키트배송')], default='normal_proceeding', max_length=100, verbose_name='상태'),
        ),
    ]