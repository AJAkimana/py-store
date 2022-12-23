# Generated by Django 2.2.24 on 2022-12-22 15:05

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('houses', '0004_auto_20210912_2052'),
    ]

    operations = [
        migrations.AlterField(
            model_name='house',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
        migrations.AlterField(
            model_name='house',
            name='updated_at',
            field=models.DateTimeField(default=django.utils.timezone.now, null=True),
        ),
    ]