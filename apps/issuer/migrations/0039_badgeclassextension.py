# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2018-01-08 16:57


import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('issuer', '0038_badgeinstance_expires_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='BadgeClassExtension',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=254)),
                ('original_json', models.TextField(blank=True, default=None, null=True)),
                ('badgeclass', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='issuer.BadgeClass')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
