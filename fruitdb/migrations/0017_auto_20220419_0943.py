# Generated by Django 3.1.1 on 2022-04-19 09:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0016_auto_20220418_1802'),
    ]

    operations = [
        migrations.AddField(
            model_name='genetictestlog',
            name='current_times',
            field=models.SmallIntegerField(default=0, verbose_name='결제 회차'),
        ),
        migrations.AlterField(
            model_name='genetictestproduct',
            name='month_range',
            field=models.SmallIntegerField(default=1, verbose_name='월 배송 주기'),
        ),
    ]
