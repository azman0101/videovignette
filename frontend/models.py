from django.db import models


class VideoUploadModel(models.Model):
    video_file = models.FileField()
    filename = models.CharField(max_length=100)
    size = models.IntegerField()

    #TODO: Think to saved it as UUID4
    processed_folder = models.CharField(max_length=50)

    generated_images_count = models.BigIntegerField(null=True)
    ready = models.BooleanField(default=False)