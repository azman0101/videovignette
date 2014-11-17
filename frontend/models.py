from django.db import models


class VideoUploadModel(models.Model):
    video_file = models.FileField()
    filename = models.CharField(max_length=100)
    size = models.IntegerField()
    frame_per_second = models.FloatField(verbose_name='FPS', null=True)
    duration = models.DateTimeField(verbose_name='Duration', null=True)

    #TODO: Think to saved it as UUID4
    processed_folder = models.CharField(max_length=50)

    generated_images_count = models.BigIntegerField(null=True)
    ready = models.BooleanField(default=False)


class ApplicationSetting(models.Model):
    configuration_name = models.CharField(max_length=100, default='low_res')
    resize_ffmpeg_parameter = models.CharField(max_length=100, default='-vf scale=320:-1', null=True)
    captured_frame_parameter = models.CharField(max_length=100, null=True)
