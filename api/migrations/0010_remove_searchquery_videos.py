# Generated by Django 3.0.5 on 2021-05-20 15:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_searchquery_videos'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='searchquery',
            name='videos',
        ),
    ]
