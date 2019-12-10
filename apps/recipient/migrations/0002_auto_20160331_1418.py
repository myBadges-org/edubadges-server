# -*- coding: utf-8 -*-


import autoslug.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipient', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipientgroup',
            name='slug',
            field=autoslug.fields.AutoSlugField(default=None, unique=True, max_length=254, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='recipientgroupmembership',
            name='slug',
            field=autoslug.fields.AutoSlugField(default=None, unique=True, max_length=254, editable=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='recipientprofile',
            name='slug',
            field=autoslug.fields.AutoSlugField(default=None, unique=True, max_length=254, editable=False),
            preserve_default=False,
        ),
    ]
