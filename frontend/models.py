from django.db import models

class VideoUploadModel(models.Model):
	fichier = models.FileField()
