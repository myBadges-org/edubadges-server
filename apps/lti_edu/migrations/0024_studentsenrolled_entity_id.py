# Generated by Django 2.2.8 on 2019-12-25 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lti_edu', '0023_auto_20191203_0250'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentsenrolled',
            name='entity_id',
            field=models.CharField(default=None, max_length=254, unique=False, null=True),
        ),
    ]