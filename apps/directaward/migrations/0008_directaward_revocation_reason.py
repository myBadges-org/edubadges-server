# Generated by Django 2.2.14 on 2021-04-01 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('directaward', '0007_directaward_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='directaward',
            name='revocation_reason',
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
    ]