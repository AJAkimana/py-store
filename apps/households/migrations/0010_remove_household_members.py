# Generated by Django 2.2.28 on 2023-04-07 06:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('households', '0009_household_members'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='household',
            name='members',
        ),
    ]
