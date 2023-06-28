# Generated by Django 2.2.24 on 2023-03-22 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('households', '0006_household_members'),
    ]

    operations = [
        migrations.AlterField(
            model_name='household',
            name='members',
            field=models.ManyToManyField(related_name='household_members', through='household_members.HouseholdMember', to='users.User'),
        ),
    ]
