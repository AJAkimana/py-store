# Generated by Django 2.2.24 on 2021-09-20 16:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0004_store_property'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='store',
            name='property',
        ),
    ]