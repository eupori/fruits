# Generated by Django 3.1.1 on 2022-05-16 16:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0028_jmfsubscription_jmfsubscriptionpaymentlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductBanner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('image', models.CharField(blank=True, max_length=100, null=True, verbose_name='이미지 URL')),
                ('title', models.CharField(blank=True, max_length=100, null=True, verbose_name='제목')),
                ('description', models.CharField(blank=True, max_length=100, null=True, verbose_name='설명')),
                ('url', models.CharField(blank=True, max_length=100, null=True, verbose_name='이동 URL')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='customer',
            name='is_pass_auth',
            field=models.BooleanField(default=False),
        ),
    ]