# Generated by Django 3.1.1 on 2022-04-25 15:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0022_auto_20220425_1034'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='genetictest',
            name='is_kit_active',
        ),
        migrations.RemoveField(
            model_name='genetictest',
            name='is_test_active',
        ),
        migrations.RemoveField(
            model_name='genetictest',
            name='kit_current_times',
        ),
        migrations.RemoveField(
            model_name='genetictest',
            name='test_current_times',
        ),
        migrations.RemoveField(
            model_name='genetictestlog',
            name='kit_current_times',
        ),
        migrations.RemoveField(
            model_name='genetictestlog',
            name='test_current_times',
        ),
        migrations.AddField(
            model_name='genetictest',
            name='current_times',
            field=models.SmallIntegerField(default=0, verbose_name='결제 회차'),
        ),
        migrations.AddField(
            model_name='genetictestlog',
            name='current_times',
            field=models.SmallIntegerField(default=0, verbose_name='결제 회차'),
        ),
    ]
