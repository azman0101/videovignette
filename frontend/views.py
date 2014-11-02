from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.http import HttpResponse
from django.views.generic import ListView
from django.utils import timezone
import datetime
import os
from django.conf import settings
from django.core.urlresolvers import reverse
from django.views import generic
from django.views.decorators.http import require_POST
from jfu.http import upload_receive, UploadResponse, JFUResponse
import logging, subprocess
import uuid, time
from multiprocessing import Process


logger = logging.getLogger('videovignette')
logger.setLevel('WARNING')

from frontend.models import VideoUploadModel, ApplicationSetting


class Home(generic.TemplateView):
    template_name = 'base.html'

    def get_context_data(self, **kwargs):
        context = super( Home, self ).get_context_data( **kwargs )
        context['accepted_mime_types'] = ['video/*']
        return context


class VideoListView(ListView):

    model = VideoUploadModel

    def get_context_data(self, **kwargs):
        context = super(VideoListView, self).get_context_data(**kwargs)
        #context['url_to_processed_folder'] = self.video
        logger.warning("VIDEOLISTVIEW: " + str(context))
        return context

    #def get_queryset(self):
    #    self.video = get_object_or_404(VideoUploadModel, name=self.args[0])
    #    return self.video.processed_folder


def start_ffmpeg(filepath, file_instance):
    #TODO: check if file exists ! Really ... this is FOR DEBUG ONLY
    logger.warning("Check if exits yet... " + filepath)
    while not os.path.exists(filepath):
        time.sleep(1)
        logger.warning("File don't exits yet... " + filepath)

    basename = os.path.basename(filepath)
    abs_pathname, foldername = get_or_create_dir()
    file_instance.processed_folder = foldername
    bashcommand = 'ffmpeg -i '+ filepath +' -vf scale=320:-1 -an -f image2 ' + abs_pathname + '/output_%05d.jpg'
    logger.warning("start_ffmpeg: " + bashcommand)
    process = subprocess.Popen(bashcommand.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    logger.warning(output)
    #TODO: evaluate computation time of FFMPEG for wait timeout.
    process.wait()
    file_instance.ready = True
    logger.warning("PATH.. " + abs_pathname)
    path, dirs, files = os.walk(abs_pathname).next()

    logger.warning("LENGTH.. " + str(len(files)))
    file_instance.generated_images_count = len(files)
    file_instance.save()


def get_or_create_dir():
    foldername = str(uuid.uuid4())
    seq_path = settings.MEDIA_ROOT + foldername
    if not os.path.exists(seq_path):
        os.makedirs(seq_path)
    return seq_path, foldername

@require_POST
def upload(request):

    # The assumption here is that jQuery File Upload
    # has been configured to send files one at a time.
    # If multiple files can be uploaded simulatenously,
    # 'file' may be a list of files.
    video = upload_receive(request)

    instance = VideoUploadModel(video_file=video, size=video.size, filename=video.name)
    logger.warning(str(dir(video)))
    logger.warning(str(video.name))
    logger.warning(str(video.content_type))
    logger.warning(str(video.size))
    logger.warning(str(instance))
    
    instance.save()

    basename = os.path.basename(instance.video_file.path)

    file_dict = {
        'name' : basename,
        'size' : video.size,

        'url': settings.MEDIA_URL + basename,
        'thumbnailUrl': settings.STATIC_URL + 'img/video_icon_' + str(settings.ICON_SIZE) + '.png',

        'deleteUrl': reverse('jfu_delete', kwargs = { 'pk': instance.pk }),
        'deleteType': 'POST',
    }

    #start_ffmpeg(instance.video_file.path, file_instance=instance)
    p = Process(target=start_ffmpeg, args=(instance.video_file.path, instance))
    p.start()
    return UploadResponse(request, file_dict)

@require_POST
def upload_delete(request, pk):
    success = True
    try:
        instance = VideoUploadModel.objects.get(pk=pk)
        response = os.unlink(instance.video_file.path)
        logger.warning("Have to delete %s : %s" % (instance.video_file.path, str(response)))
        instance.delete()
    except VideoUploadModel.DoesNotExist:
        success = False

    return JFUResponse(request, success)




class VideoPreview(generic.TemplateView):
    template_name = 'videopreview.html'

    def get(self, request, *args, **kwargs):
        self.start_count = self.request.GET.get('count')
        #logger.warning("A - VideoPreview GET count: " + str(self.count))
        #logger.warning("VideoPreview GET ARGS: " + str(args))
        #TODO: move this after image creation for count and put to DB
        time.sleep(1)
        #logger.warning("VideoPreview GET : " + str(kwargs))
        self.folder = args[0]
        video_instance = get_object_or_404(VideoUploadModel, processed_folder=self.folder)
        logger.warning("VideoPreview GET: " + str(video_instance))
        self.max_count = video_instance.generated_images_count
        return super(VideoPreview, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(VideoPreview, self).get_context_data(**kwargs)
        #logger.warning("VideoPreview get_context_data : " + str(kwargs))

        #logger.warning("Count :: " + str(self.count))

        #logger.warning("VideoPreview COUNT from get_context_data : " + str(self.file_count))
        file_listing = []
        if self.start_count is None:
            self.start_count = 1
        count_end = int(self.start_count) + 6
        if count_end > self.max_count:
            count_end = self.max_count + 1
        for number in range(int(self.start_count), count_end): #self.file_count
            file_listing.append(settings.MEDIA_URL + self.folder + '/output_%05d.jpg' % number)
        context['file_listing'] = file_listing
        context['folder'] = self.folder
        context['count'] =  str(count_end) if count_end <= self.max_count else 'stop'
        return context