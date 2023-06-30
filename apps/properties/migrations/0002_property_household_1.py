# Generated by Django 2.2.28 on 2023-06-30 13:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('households', '0001_initial'),
        ('properties', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='household',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='properties', to='households.Household'),
        ),
    ]
