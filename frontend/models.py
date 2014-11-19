from django.db import models
from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase


class VideoUploadModel(models.Model):
    video_file = models.FileField()
    filename = models.CharField(max_length=100)
    size = models.IntegerField()
    frame_per_second = models.FloatField(verbose_name='FPS', null=True)
    duration = models.FloatField(verbose_name='Duration', null=True)

    #TODO: Think to saved it as UUID4
    processed_folder = models.CharField(max_length=50)

    generated_images_count = models.BigIntegerField(null=True)
    ready = models.BooleanField(default=False)

class TaggedFrame(TaggedItemBase):
    content_object = models.ForeignKey('CroppedFrame')


class Box(models.Model):
    h = models.IntegerField()
    w = models.IntegerField()
    x = models.IntegerField()
    y = models.IntegerField()
    x2 = models.IntegerField()
    y2 = models.IntegerField()

    @classmethod
    def create(cls, box=None):
        assert isinstance(box['h'], int)
        assert isinstance(box['w'], int)
        assert isinstance(box['x'], int)
        assert isinstance(box['y'], int)
        assert isinstance(box['x2'], int)
        assert isinstance(box['y2'], int)
        return cls(h=box['h'], w=box['w'], x=box['x'], y=box['y'], x2=box['x2'], y2=box['y2'])

    def tuple_box(self):
        return self.x, self.y, self.x2, self.y2

class CroppedFrame(models.Model):
    video_upload_file = models.ForeignKey(VideoUploadModel, null=True)
    frame_number = models.IntegerField(verbose_name="Number of cropped frame")
    box = models.ForeignKey(Box, null=True)
    cropped_frame_file = models.ImageField(upload_to='cropped', null=False)
    tags = TaggableManager(through=TaggedFrame)

    def delete(self, using=None):
        if self.box:
            self.box.delete()
        super(CroppedFrame, self).delete(using)


class ApplicationSetting(models.Model):
    configuration_name = models.CharField(max_length=100, default='low_res')
    resize_ffmpeg_parameter = models.CharField(max_length=100, default='-vf scale=320:-1', null=True)
    captured_frame_parameter = models.CharField(max_length=100, null=True)
