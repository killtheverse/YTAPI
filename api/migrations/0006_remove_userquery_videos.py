# Generated by Django 3.0.5 on 2021-05-20 14:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_userquery_videos'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userquery',
            name='videos',
        ),
    ]
