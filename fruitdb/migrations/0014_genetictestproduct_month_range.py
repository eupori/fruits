# Generated by Django 3.1.1 on 2022-04-13 17:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0013_auto_20220413_1539'),
    ]

    operations = [
        migrations.AddField(
            model_name='genetictestproduct',
            name='month_range',
            field=models.SmallIntegerField(default=1, verbose_name='약정 회차'),
        ),
    ]