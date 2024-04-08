# Generated by Django 5.0.2 on 2024-04-08 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_alter_receipt_address'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='equipment',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='equipment',
            name='description',
            field=models.CharField(default='Replace', max_length=50),
        ),
        migrations.AlterUniqueTogether(
            name='equipment',
            unique_together={('address', 'component', 'description')},
        ),
        migrations.AlterUniqueTogether(
            name='maintenance',
            unique_together={('component', 'dateCompleted', 'maintenance_price')},
        ),
    ]
