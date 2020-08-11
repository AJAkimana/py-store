# Generated by Django 2.2.13 on 2020-08-11 16:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('houses', '0002_house_owner'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='house',
            name='owner',
        ),
        migrations.AddField(
            model_name='house',
            name='user_id',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='owner', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]
