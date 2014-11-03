# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    ApplicationSetting = apps.get_model("frontend", "ApplicationSetting")
    db_alias = schema_editor.connection.alias
    ApplicationSetting.objects.using(db_alias).bulk_create([
        ApplicationSetting(),
        ApplicationSetting(configuration_name="full_res", resize_ffmpeg_parameter=""),
    ])

class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('configuration_name', models.CharField(default=b'low_res', max_length=100)),
                ('resize_ffmpeg_parameter', models.CharField(default=b'-vf scale=320:-1', max_length=100, null=True)),
                ('captured_frame_parameter', models.CharField(max_length=100, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VideoUploadModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('video_file', models.FileField(upload_to=b'')),
                ('filename', models.CharField(max_length=100)),
                ('size', models.IntegerField()),
                ('processed_folder', models.CharField(max_length=50)),
                ('generated_images_count', models.BigIntegerField(null=True)),
                ('ready', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RunPython(
            forwards_func,
        ),
    ]
