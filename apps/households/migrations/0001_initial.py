# Generated by Django 2.2.28 on 2023-06-29 06:18

from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Household',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, null=True)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('name', models.CharField(default='Our house', max_length=255)),
                ('description', models.CharField(default='Our family', max_length=255)),
            ],
            options={
                'db_table': 'households',
                'ordering': ['name'],
            },
        ),
    ]
