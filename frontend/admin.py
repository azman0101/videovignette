from django.contrib import admin
from django.forms import ImageField, FileInput
from django.conf import settings

from frontend.models import VideoUploadModel, ApplicationSetting, CroppedFrame, Box, TaggedFrame

from django import forms
from django.utils.safestring import mark_safe

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

class CroppedFrameAdmin(admin.ModelAdmin):

    form = CroppedFrameForm
    #filter_horizontal = ("languages",)
    list_display = ('created_at', 'video_upload_file', 'frame_number', 'get_cropped_frame_file', 'get_tags',)

    #exclude = ('languages',)

    def get_cropped_frame_file(self, obj):
        res = AdminImageWidget()
        return res.render(name='test', value=obj.cropped_frame_file)

    def get_tags(self, obj):
        resp = obj.tags.values()
        #logger.warning(str(dir(resp)))
        #logger.warning(str(type(resp)))
        resp = [r['name'] for r in resp]
        return ", ".join(resp)


class VideoUploadModelAdmin(admin.ModelAdmin):

    list_display = ('video_file', 'filename', 'size', 'frame_per_second', 'processed_folder')

admin.site.register(VideoUploadModel, VideoUploadModelAdmin)
admin.site.register(ApplicationSetting)
admin.site.register(CroppedFrame, CroppedFrameAdmin)
admin.site.register(TaggedFrame)
#admin.site.register(Box)