# Generated by Django 3.1.1 on 2022-05-27 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0042_auto_20220526_1414'),
    ]

    operations = [
        migrations.RenameField(
            model_name='jmfsubscription',
            old_name='test_start_datetime',
            new_name='kit_receive_datetime',
        ),
        migrations.AddField(
            model_name='jmfsubscription',
            name='is_extra_billing',
            field=models.BooleanField(default=False, verbose_name='기타 청구 금액 여부'),
        ),
    ]
