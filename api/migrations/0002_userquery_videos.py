# Generated by Django 3.0.5 on 2021-05-20 14:07

import api.models
from django.db import migrations
import djongo.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userquery',
            name='videos',
            field=djongo.models.fields.ArrayField(model_container=api.models.YTVideo, null=True),
        ),
    ]
