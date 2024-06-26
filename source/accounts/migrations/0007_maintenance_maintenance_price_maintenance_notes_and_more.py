# Generated by Django 5.0.2 on 2024-04-05 00:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_equipment_component'),
    ]

    operations = [
        migrations.AddField(
            model_name='maintenance',
            name='maintenance_price',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name='maintenance',
            name='notes',
            field=models.CharField(blank=True, default='No Notes', max_length=300),
        ),
        migrations.AlterField(
            model_name='address',
            name='address',
            field=models.CharField(max_length=100),
        ),
    ]
