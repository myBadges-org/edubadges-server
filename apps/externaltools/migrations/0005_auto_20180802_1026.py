# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-08-02 17:26
from __future__ import unicode_literals

from django.db import migrations
import django.db.models.manager


class Migration(migrations.Migration):

    dependencies = [
        ('externaltools', '0004_auto_20180411_0653'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='externaltool',
            managers=[
                ('cached', django.db.models.manager.Manager()),
            ],
        ),
    ]
