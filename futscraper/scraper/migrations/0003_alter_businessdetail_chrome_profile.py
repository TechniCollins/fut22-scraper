# Generated by Django 4.0.6 on 2022-07-12 16:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='businessdetail',
            name='chrome_profile',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
