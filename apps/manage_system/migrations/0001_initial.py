# Generated by Django 2.2.24 on 2021-09-24 08:09

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Salary',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('pension', models.FloatField()),
                ('maternity', models.FloatField()),
                ('tax', models.FloatField()),
                ('net_salary', models.FloatField()),
                ('gross_salary', models.FloatField()),
                ('net_pay', models.FloatField()),
                ('deleted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'salaries',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Facility',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('is_constant', models.FloatField()),
                ('amount', models.FloatField()),
                ('percent_amount', models.FloatField()),
                ('percent_field', models.FloatField()),
                ('deleted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'facilities',
                'ordering': ['-created_at'],
            },
        ),
    ]