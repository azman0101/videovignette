from django.db import models
from django.conf import settings

from .tasks import delete_path

from taggit.managers import TaggableManager
from taggit.models import TaggedItemBase
from django.utils.translation import ugettext as _
from datetime import datetime
import shutil

import logging
from time import gmtime, strftime
import os.path


logger = logging.getLogger('videovignette')
logger.setLevel('ERROR')

class VideoUploadModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    video_file = models.FileField(null=True)
    filename = models.CharField(max_length=100)
    size = models.IntegerField()
    frame_per_second = models.FloatField(verbose_name=_('FPS'), null=True)
    duration = models.FloatField(verbose_name=_('Duration'), null=True)
    height = models.IntegerField(verbose_name=_('Height in px'), null=True)
    width = models.IntegerField(verbose_name=_('Width in px'), null=True)
    #TODO: Think to saved it as UUID4
    processed_folder = models.CharField(max_length=50)

    generated_images_count = models.BigIntegerField(null=True)
    ready = models.BooleanField(default=False)

    def delete(self, using=None):
        try:
            # You have to prepare what you need before delete the model
            storage, path = self.video_file.storage, self.video_file.path
            # Delete the file after the model
            storage.delete(path)
        except ValueError:
            pass
        finally:
            # Delete the model before the file
            to_delete = settings.MEDIA_ROOT + self.processed_folder
            # if os.path.exists(to_delete):
            #     shutil.rmtree(to_delete)
            delete_path(to_delete)
            super(VideoUploadModel, self).delete(using)




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
    class Meta:
        ordering = ['created_at']

    created_at = models.DateTimeField(auto_now_add=True, editable=True)
    video_upload_file = models.ForeignKey(VideoUploadModel, null=True)
    frame_number = models.IntegerField(verbose_name=_("Number of cropped frame"))
    box = models.ForeignKey(Box, null=True)
    cropped_frame_file = models.ImageField(upload_to='cropped', null=False)
    tags = TaggableManager(through=TaggedFrame)

    def delete(self, using=None):
        if self.box:
            self.box.delete()
        super(CroppedFrame, self).delete(using)

    def clean(self):
        super(CroppedFrame, self).clean()
        errors_tags = {}
        for tag in self.tags.values():
            if len(tag) > 50:
                errors_tags[tag] = _("Tag too long !")
        logger.warning("Clean before tagging: " + str(self.tags.values()))

    def to_time(self):
        frame = self.frame_number
        fps = self.video_upload_file.frame_per_second
        logger.warning("MODEL to_time: " + str(frame) + " x " + str(fps))
        time_float = frame / fps
        return strftime('%H-%M-%S', gmtime(int(time_float)))



class ApplicationSetting(models.Model):
    configuration_name = models.CharField(max_length=100, default='low_res')
    resize_ffmpeg_parameter = models.CharField(max_length=100, default='-vf scale=320:-1 ', null=True)
    #captured_frame_parameter = models.CharField(max_length=100, null=True)
