# Generated by Django 2.2.10 on 2020-02-26 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0004_auto_20200226_0823'),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]