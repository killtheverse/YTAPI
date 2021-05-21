# Generated by Django 3.0.5 on 2021-05-20 14:10

import api.models
from django.db import migrations
import djongo.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_remove_userquery_videos'),
    ]

    operations = [
        migrations.AddField(
            model_name='userquery',
            name='videos',
            field=djongo.models.fields.ArrayField(default=['checking'], model_container=api.models.YTVideo),
            preserve_default=False,
        ),
    ]
