# Generated by Django 2.2.13 on 2020-08-13 14:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0008_property_cover_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='propdetail',
            name='property',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prop_details', to='properties.Property'),
        ),
    ]
