# Generated by Django 5.1.3 on 2024-12-05 08:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opcua_manager', '0003_opcnode_variation_cycle_alter_opcnode_variation_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='opcnode',
            name='decimal_places',
            field=models.IntegerField(default=2, verbose_name='小数位数'),
        ),
    ]
