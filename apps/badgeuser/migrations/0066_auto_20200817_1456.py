# Generated by Django 2.2.13 on 2020-08-17 12:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('institution', '0028_auto_20200808_1221'),
        ('badgeuser', '0065_auto_20200731_1523'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='terms',
            unique_together={('institution', 'terms_type')},
        ),
    ]
