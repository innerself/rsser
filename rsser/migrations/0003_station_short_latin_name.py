# Generated by Django 2.1.4 on 2019-02-02 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rsser', '0002_program_feed_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='station',
            name='short_latin_name',
            field=models.CharField(default='gm', max_length=30, verbose_name='short latin name'),
            preserve_default=False,
        ),
    ]
