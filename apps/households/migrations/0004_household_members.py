# Generated by Django 2.2.24 on 2023-03-20 05:02

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('households', '0003_auto_20230319_2110'),
    ]

    operations = [
        migrations.AddField(
            model_name='household',
            name='members',
            field=models.ManyToManyField(related_name='house_members', to=settings.AUTH_USER_MODEL),
        ),
    ]
