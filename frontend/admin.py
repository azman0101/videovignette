from django.contrib import admin


from frontend.models import VideoUploadModel, ApplicationSetting, CroppedFrame, Box

admin.site.register(VideoUploadModel)
admin.site.register(ApplicationSetting)
admin.site.register(CroppedFrame)
admin.site.register(Box)