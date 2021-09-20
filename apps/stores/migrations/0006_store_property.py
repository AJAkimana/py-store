# Generated by Django 2.2.24 on 2021-09-20 17:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0005_remove_property_store'),
        ('stores', '0005_remove_store_property'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='property',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='stores', to='properties.Property'),
        ),
    ]