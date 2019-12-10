# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-04-15 13:29


import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('lti_edu', '0011_auto_20190408_0337'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserCurrentContextId',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('context_id', models.CharField(max_length=512)),
                ('badge_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='usercurrentcontextid',
            unique_together=set([('badge_user', 'context_id')]),
        ),
    ]
