# Generated by Django 3.2.20 on 2024-03-17 08:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('budgeting', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='budgetitem',
            unique_together={('name', 'amount', 'budget')},
        ),
    ]