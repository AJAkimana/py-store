# Generated by Django 2.2.28 on 2023-04-08 19:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0009_property_household'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='propdetail',
            name='deleted_by',
        ),
        migrations.RemoveField(
            model_name='property',
            name='deleted_by',
        ),
    ]
