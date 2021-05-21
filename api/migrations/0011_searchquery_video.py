# Generated by Django 3.0.5 on 2021-05-20 15:51

from django.db import migrations
import django.db.models.deletion
import djongo.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_remove_searchquery_videos'),
    ]

    operations = [
        migrations.AddField(
            model_name='searchquery',
            name='video',
            field=djongo.models.fields.ArrayReferenceField(default=['temp'], on_delete=django.db.models.deletion.CASCADE, to='api.YTVideo'),
        ),
    ]
