# Generated by Django 2.2.28 on 2023-04-08 19:10

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('households', '0010_remove_household_members'),
    ]

    operations = [
        migrations.AddField(
            model_name='household',
            name='members',
            field=models.ManyToManyField(related_name='house_members', to=settings.AUTH_USER_MODEL),
        ),
    ]