# Generated by Django 2.2.13 on 2020-08-30 08:26

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('properties', '0009_auto_20200813_1418'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='property',
            unique_together={('name', 'owner')},
        ),
    ]
