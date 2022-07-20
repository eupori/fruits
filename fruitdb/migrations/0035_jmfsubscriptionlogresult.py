# Generated by Django 3.1.1 on 2022-05-23 16:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0034_questionemaillog'),
    ]

    operations = [
        migrations.CreateModel(
            name='JMFSubscriptionLogResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('result_file_excel', models.FileField(blank=True, null=True, upload_to='macrogen_settlement_result', verbose_name='정산 결과')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]