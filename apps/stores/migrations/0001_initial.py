# Generated by Django 2.2.10 on 2020-07-11 18:35

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('amount', models.FloatField()),
                ('record_type', models.CharField(choices=[('use', 'Store'), ('debt', 'Debt'), ('online', 'Online')], default='use', max_length=20)),
                ('is_property', models.BooleanField(default=False)),
                ('is_inflow', models.BooleanField(default=False)),
                ('description', models.CharField(default='*Home expense', max_length=200)),
                ('action_date', models.DateField(default=django.utils.timezone.now)),
            ],
            options={
                'ordering': ['action_date'],
            },
        ),
    ]
