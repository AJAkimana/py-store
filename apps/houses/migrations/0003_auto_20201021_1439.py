# Generated by Django 2.2.13 on 2020-10-21 14:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('houses', '0002_house_user_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='house',
            old_name='user_id',
            new_name='user',
        ),
    ]
