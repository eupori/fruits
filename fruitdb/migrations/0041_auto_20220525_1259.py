# Generated by Django 3.1.1 on 2022-05-25 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0040_remove_genetictest_sno'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jmfsubscription',
            name='customer',
        ),
        migrations.AddField(
            model_name='jmfsubscription',
            name='user_name',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='사용자 이름'),
        ),
    ]
