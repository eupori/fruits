# Generated by Django 3.1.1 on 2022-04-06 13:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0003_auto_20220406_1329'),
    ]

    operations = [
        migrations.AlterField(
            model_name='macrogensettlement',
            name='order_id',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='주문번호'),
        ),
    ]
