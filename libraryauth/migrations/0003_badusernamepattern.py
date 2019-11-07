# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-12-06 17:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('libraryauth', '0002_auto_20160727_2214'),
    ]

    operations = [
        migrations.CreateModel(
            name='BadUsernamePattern',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pattern', models.CharField(max_length=100)),
                ('last', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
    ]
