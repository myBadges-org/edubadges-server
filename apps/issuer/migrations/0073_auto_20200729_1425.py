# Generated by Django 2.2.13 on 2020-07-29 12:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('issuer', '0072_badgeclass_populate_formal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='badgeclass',
            name='formal',
            field=models.BooleanField(),
        ),
    ]
