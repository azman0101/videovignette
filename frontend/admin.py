from django.contrib import admin
from django.utils.translation import ugettext as _

from frontend.models import VideoUploadModel, ApplicationSetting, CroppedFrame, Box, TaggedFrame
from django.conf import settings

import shutil
import os.path

from django import forms
from django.utils.safestring import mark_safe
import logging

logger = logging.getLogger('videovignette')

admin.site.disable_action('delete_selected')


class AdminImageWidget(forms.FileInput):
    """
    A ImageField Widget for admin that shows a thumbnail.
    """

    def __init__(self, attrs={}):
        super(AdminImageWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None):
        output = []
        if value and hasattr(value, "url"):
            output.append(('<a target="_blank" href="%s">'
                           '<img src="%s" style="height: 100px;" /></a> '
                           % (value.url, value.url)))
        output.append(super(AdminImageWidget, self).render(name, value, attrs))
        return mark_safe(u''.join(output))



class CroppedFrameForm(forms.ModelForm):

    class Meta:
        model = CroppedFrame

    cropped_frame_file = forms.ImageField(label='Cropped frame', widget=AdminImageWidget)

class VideoUploadModelForm(forms.ModelForm):

    class Meta:
        model = VideoUploadModel

    video_file = forms.FileField(label=_('Related Video'), required=False)

class CroppedFrameAdmin(admin.ModelAdmin):

    form = CroppedFrameForm
    #filter_horizontal = ("languages",)
    list_display = ('created_at', 'video_upload_file', 'frame_number', 'get_cropped_frame_file', 'get_tags',)

    #exclude = ('languages',)

    def get_cropped_frame_file(self, obj):
        # Show personalized Widget to the list display like the detail view
        res = AdminImageWidget()
        return res.render(name='get_cropped_frame_file', value=obj.cropped_frame_file)

    def get_tags(self, obj):
        resp = obj.tags.values()
        #logger.warning(str(dir(resp)))
        #logger.warning(str(type(resp)))
        resp = [r['name'] for r in resp]
        return ", ".join(resp)


def remove_video_file_action(modeladmin, request, queryset):
    for q in queryset:
        logger.warning("remove_video_file_action: " + str(q.video_file))
        q.video_file.delete()

def remove_videoupload_completely_action(modeladmin, request, queryset):
    for q in queryset:
        q.delete()



remove_video_file_action.short_description = _("Remove related video file (will not delete processed files neither selected entry)")
remove_videoupload_completely_action.short_description = _("Remove video upload model and all attached files")


class VideoUploadModelAdmin(admin.ModelAdmin):

    form = VideoUploadModelForm

    list_display = ('video_file', 'filename', 'size', 'frame_per_second', 'processed_folder')
    actions = [remove_video_file_action, remove_videoupload_completely_action]




admin.site.register(VideoUploadModel, VideoUploadModelAdmin)
admin.site.register(ApplicationSetting)
admin.site.register(CroppedFrame, CroppedFrameAdmin)
admin.site.register(TaggedFrame)
#admin.site.register(Box)