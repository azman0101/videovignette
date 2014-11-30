# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import taggit.managers

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
        ('taggit', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('configuration_name', models.CharField(default=b'low_res', max_length=100)),
                ('resize_ffmpeg_parameter', models.CharField(default=b'-vf scale=320:-1', max_length=100, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Box',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('h', models.IntegerField()),
                ('w', models.IntegerField()),
                ('x', models.IntegerField()),
                ('y', models.IntegerField()),
                ('x2', models.IntegerField()),
                ('y2', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CroppedFrame',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now, auto_now_add=True)),
                ('frame_number', models.IntegerField(verbose_name='Number of cropped frame')),
                ('cropped_frame_file', models.ImageField(upload_to=b'cropped')),
                ('box', models.ForeignKey(to='frontend.Box', null=True)),
            ],
            options={
                'ordering': ['created_at'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TaggedFrame',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content_object', models.ForeignKey(to='frontend.CroppedFrame')),
                ('tag', models.ForeignKey(related_name='frontend_taggedframe_items', to='taggit.Tag')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VideoUploadModel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now, auto_now_add=True)),
                ('video_file', models.FileField(upload_to=b'')),
                ('filename', models.CharField(max_length=100)),
                ('size', models.IntegerField()),
                ('frame_per_second', models.FloatField(null=True, verbose_name='FPS')),
                ('duration', models.FloatField(null=True, verbose_name='Duration')),
                ('height', models.IntegerField(null=True, verbose_name='Height in px')),
                ('width', models.IntegerField(null=True, verbose_name='Width in px')),
                ('processed_folder', models.CharField(max_length=50)),
                ('generated_images_count', models.BigIntegerField(null=True)),
                ('ready', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='croppedframe',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='frontend.TaggedFrame', help_text='A comma-separated list of tags.', verbose_name='Tags'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='croppedframe',
            name='video_upload_file',
            field=models.ForeignKey(to='frontend.VideoUploadModel', null=True),
            preserve_default=True,
        ),
        migrations.RunPython(
            forwards_func,
        ),
    ]
