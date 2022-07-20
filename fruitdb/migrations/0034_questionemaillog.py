# Generated by Django 3.1.1 on 2022-05-20 10:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fruitdb', '0033_jmfsubscription_sno'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionEmailLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(blank=True, max_length=100, null=True, verbose_name='상태')),
                ('message', models.TextField(blank=True, verbose_name='메시지')),
                ('question', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='fruitdb.question', verbose_name='order id')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
