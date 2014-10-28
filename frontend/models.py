from django.db import models

class VideoUploadModel(models.Model):
	video_file = models.FileField()
	filename = models.CharField(max_length=100)
	size =	models.IntegerField()
	
