# Generated by Django 3.1.1 on 2022-05-25 10:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0039_merge_20220525_1023'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genetictest',
            name='sno',
        ),
    ]
