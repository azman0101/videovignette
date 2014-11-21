# -*- coding: utf-8 -*-

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.views.generic import ListView
from datetime import timedelta
from PIL import Image
import re
import StringIO
import zipfile
import os
from django.conf import settings
from django.core.urlresolvers import reverse
from django.views import generic
import json
from django.core.files.uploadedfile import SimpleUploadedFile
from taggit.models import Tag

from django.views.decorators.http import require_POST, require_GET
from jfu.http import upload_receive, UploadResponse, JFUResponse
import logging
import subprocess
import uuid
import time
from multiprocessing import Pool


logger = logging.getLogger('videovignette')
logger.setLevel('ERROR')

from frontend.models import VideoUploadModel, ApplicationSetting, CroppedFrame, Box


class Home(generic.TemplateView):
    template_name = 'base.html'

    def get_context_data(self, **kwargs):
        context = super(Home, self).get_context_data(**kwargs)
        context['accepted_mime_types'] = ['video/*']
        return context


class VideoListView(ListView):
    model = VideoUploadModel

    def get_context_data(self, **kwargs):
        context = super(VideoListView, self).get_context_data(**kwargs)
        # context['url_to_processed_folder'] = self.video
        logger.warning("VIDEOLISTVIEW: " + str(context))
        return context

        #def get_queryset(self):
        #    self.video = get_object_or_404(VideoUploadModel, name=self.args[0])
        #    return self.video.processed_folder


def ffmpeg_info(output, err):
    filters_str = {'duration': "(Duration\:\s?)(\d{2}:[0-5][0-9]:[0-5][0-9]\.\d{1,3})",
                   'fps': "(Stream #\d.\d.*?: Video:\s?).*?([0-9]+.?[0-9]+)\s?fps"}

    if output == '':
        output = err
    # Split in lines
    data = {}
    for key, filter in filters_str.iteritems():
        value = re.search(filter, output)
        #Warning: this is always the same group number in the two filter
        if value is not None:
            data[key] = value.group(2)
            if key == 'duration':
                parse_time = re.search(r'(\d{2}):([0-5][0-9]):([0-5][0-9])\.(\d{1,3})', data[key])
                data['hours'] = int(parse_time.group(1))
                data['minutes'] = int(parse_time.group(2))
                data['seconds'] = int(parse_time.group(3))
                data['microseconds'] = int(parse_time.group(4))

            logger.warning("Info ffmpeg: " + str(data))
    return data


def start_ffmpeg(filepath, file_instance, configuration_name, abs_pathname, folder_name):
    try:
        encodage_setting = get_object_or_404(ApplicationSetting, configuration_name=configuration_name)
    except Http404 as e:
        # TODO: find a way to push message to Interface via AJAX
        logger.error("Generation process will stop here, check db ApplicationSetting", str(e))
        file_instance.ready = False
        file_instance.save()
        return

    # TODO: check if file exists ! Really ... this is FOR DEBUG ONLY
    logger.warning("Check if exits yet... " + filepath)
    while not os.path.exists(filepath):
        time.sleep(1)
        logger.warning("File don't exits yet... " + filepath)

    #TO REMOVE : basename unused.
    #basename = os.path.basename(filepath)
    file_instance.processed_folder = folder_name
    if configuration_name == 'full_res':
        prefix = 'full_'
    else:
        prefix = 'low_'
    #TODO: dynamically choose the right decoding app (ffmpeg or avconv)
    bash_command = settings.DEMUXER + ' -i ' + filepath + ' ' + encodage_setting.resize_ffmpeg_parameter +\
                   ' -an -f image2 ' + abs_pathname + '/' + prefix + 'output_%05d.jpg'
    logger.warning('start_ffmpeg: ' + bash_command)
    #TODO: What about to use stdout to pipe response to main process ?
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = process.communicate()
    #TODO: evaluate computation time of FFMPEG for wait timeout.
    process.wait()

    #Parse fps and total duration from output
    info_ffmpeg = ffmpeg_info(output, err)
    tm = timedelta(hours=info_ffmpeg['hours'], minutes=info_ffmpeg['minutes'],
                                       seconds=info_ffmpeg['seconds'], microseconds=info_ffmpeg['microseconds'])
    logger.warning('Float seconds: ' + str(tm.total_seconds()))
    file_instance.duration = tm.total_seconds()
    file_instance.frame_per_second = info_ffmpeg['fps']

    #if a process already set file_instance.ready to True then it's useless to count again
    if file_instance.ready is not True:
        file_instance.ready = True
        logger.warning('PATH.. ' + abs_pathname)

        path, dirs, files = os.walk(abs_pathname).next()
        #Count only the files with prefix
        files_count = len([f for f in files if f.startswith(prefix)])
        logger.warning('LENGTH.. ' + str(files_count))
        file_instance.generated_images_count = files_count
    #Save instance for modification made on processed_folder and ready
    file_instance.save()
    return output, err


def get_or_create_dir():
    folder_name = str(uuid.uuid4())
    seq_path = settings.MEDIA_ROOT + folder_name
    if not os.path.exists(seq_path):
        os.makedirs(seq_path)
    return seq_path, folder_name


@require_POST
def upload(request):
    # The assumption here is that jQuery File Upload
    # has been configured to send files one at a time.
    # If multiple files can be uploaded simultaneously,
    # 'file' may be a list of files.
    video = upload_receive(request)

    if not 'video/' in video.content_type:
        #TODO: handle error for report to user interface
        return HttpResponseBadRequest(content='Please send only video')
    else:
        #TODO: if correct header, check content itself ! “trust but verify.”
        pass
    instance = VideoUploadModel(video_file=video, size=video.size, filename=video.name)
    logger.warning(str(dir(video)))
    logger.warning(str(video.name))
    logger.warning(str(video.content_type))
    logger.warning(str(video.size))
    logger.warning(str(instance))
    instance.save()

    basename = os.path.basename(instance.video_file.path)

    file_dict = {
        'name': basename,
        'size': video.size,

        'url': settings.MEDIA_URL + basename,
        'thumbnailUrl': settings.STATIC_URL + 'img/video_icon_' + str(settings.ICON_SIZE) + '.png',

        'deleteUrl': reverse('jfu_delete', kwargs={'pk': instance.pk}),
        'deleteType': 'POST',
    }

    pool = Pool()
    abs_pathname, folder_name = get_or_create_dir()
    configuration_to_apply = ['low_res', 'full_res']
    results = [pool.apply_async(start_ffmpeg, (instance.video_file.path, instance, configuration_name, abs_pathname,
                                               folder_name))
               for configuration_name in configuration_to_apply]
    for result in results:
        try:
            output, err = result.get()
            logger.info(output)
            logger.error(err)
        except OSError as e:
            # TODO: Handle this error by sending a message to interface.
            # TODO: Retry process with another decoding app (ffmpeg or avconv)
            logger.error("Error: FFMPEG" + str(e))

    return UploadResponse(request, file_dict)


@require_POST
def upload_delete(request, pk):
    success = True
    try:
        instance = VideoUploadModel.objects.get(pk=pk)
        os.unlink(instance.video_file.path)
        time.sleep(1)
        if os.path.isfile(instance.video_file.path):
            raise Exception('File is not deleted')
        logger.warning("Have to delete %s" % instance.video_file.path)
        instance.delete()
    except VideoUploadModel.DoesNotExist:
        success = False

    return JFUResponse(request, success)


class VideoPreview(generic.TemplateView):
    template_name = 'videopreview.html'

    # First GET then get_context_data
    def get(self, request, *args, **kwargs):
        #Capture count parameter send in URL by the javascript listener_videolisting
        self.start_count = self.request.GET.get('count')
        self.fastforward = self.request.GET.get('fastforward', False)
        #TODO: move this after image creation for count and put to DB
        #Capture folder in URL
        self.folder = args[0]
        #Lookup database for Video instance
        video_instance = get_object_or_404(VideoUploadModel, processed_folder=self.folder)
        #Retreive instance's number of frame generated
        self.fps = video_instance.frame_per_second
        self.duration = video_instance.duration
        self.max_count = video_instance.generated_images_count
        return super(VideoPreview, self).get(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(VideoPreview, self).get_context_data(**kwargs)
        logger.warning("VideoPreview get_context_data : " + str(context))
        display_per = 6
        file_listing = []
        #If count not yet passed by GET, then start to 1
        if self.start_count is None:
            self.start_count = 1
        #Take only 6 by 6 thumb unless max_count reached
        count_end = int(self.start_count) + display_per
        if count_end > self.max_count:
            count_end = self.max_count + 1
        for number in range(int(self.start_count), count_end):  #self.file_count
            #TODO: parametrize standard res low or full
            low = settings.MEDIA_URL + self.folder + '/low_output_%05d.jpg' % number
            full = settings.MEDIA_URL + self.folder + '/full_output_%05d.jpg' % number
            file_listing.append((full, low))
            
        # TODO: Present as dictionary
        context['file_listing'] = file_listing
        context['folder'] = self.folder
        context['max'] = self.max_count
        context['count'] = str(count_end)
        context['display_per'] = -(display_per + 1)
        if count_end > self.max_count:
            context['stop'] = True
            context['display_per'] = -(display_per - (int(self.max_count) - int(self.start_count)))
        context['fastforward'] = self.fastforward
        context['duration'] = self.duration
        context['fps'] = self.fps
        return context

@require_POST
@csrf_exempt
def attach_tag(request):
    tag_dict = request.POST.dict()
    tag = Tag.objects.get(pk=tag_dict['id'])
    cropped_frame = CroppedFrame.objects.get(pk=tag_dict['cropped_id'])
    cropped_frame.tags.add(tag)
    cropped_frame.save()
    toastr_json = {}
    toastr_json['type'] = 'success'
    toastr_json['css'] = 'toast-bottom-left'
    toastr_json['msg'] = "Added"
    data = json.dumps(toastr_json)
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)

@require_GET
def get_tags(request):
    if request.is_ajax():
        q = request.GET.get('term', '')
        tags = Tag.objects.filter(name__icontains=q)[:20]
        results = []
        for tag in tags:
            tag_json = {}
            tag_json['id'] = tag.id
            tag_json['label'] = tag.name
            tag_json['value'] = tag.name
            results.append(tag_json)
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)

def extract_path_folder_img(posted_dict):
    image_url = posted_dict['image_url']
    del posted_dict['image_url']
    path, folder, image = image_url.strip('/').split('/')
    return path, folder, image

@require_POST
@csrf_exempt
def cropselection(request):
    """

    :param request: POST message with box JCrop format
    :return: Ok string for now
    """
    posted_dict = request.POST.dict()
    path, folder, image = extract_path_folder_img(posted_dict)
    assert(not posted_dict.has_key('image_url'))
    #update dict by casting value to int
    [posted_dict.update({k: int(v)}) for k, v in posted_dict.iteritems()]
    box = Box.create(box=posted_dict)

    instance_video = VideoUploadModel.objects.get(processed_folder=folder)
    # image example name: full_output_00005.jpg
    image_number = re.search(r'full_output_([0-9]+)\.jpg', image)
    image_path = settings.MEDIA_ROOT + folder + '/' + image
    if os.path.isfile(image_path):
        im = Image.open(image_path)
        box.save()
        cropped_img = im.crop(box.tuple_box())
        in_memory_temp = StringIO.StringIO()
        cropped_img.save(in_memory_temp, "JPEG")
        in_memory_temp.seek(0)
        file_cropped_img = SimpleUploadedFile(folder + '_' + str(uuid.uuid4()) + '_' + str(image_number.group(1)) + '.jpeg',
                                              in_memory_temp.read(), content_type='image/jpeg')
    else:
        file_cropped_img = None

    instance_croppedframe = CroppedFrame(video_upload_file=instance_video, frame_number=int(image_number.group(1)),
                                         box=box, cropped_frame_file=file_cropped_img)

    instance_croppedframe.save()
    logger.warning(str(posted_dict))
    return HttpResponse(content=instance_croppedframe.id)

@require_GET
def archivegenerator(request, folder):
    logger.warning("archivegenerator FOLDER: " + str(folder))
    instance = get_object_or_404(VideoUploadModel, processed_folder=folder)
    seq_path = settings.MEDIA_ROOT + folder
    logger.warning("archivegenerator FOLDER ABS: " + str(seq_path))
    path, dirs, files = os.walk(seq_path).next()
    filenames = [seq_path + '/' + f for f in files if f.startswith('full_')]
    logger.warning("archivegenerator FOLDER: " + str(filenames))

    # Folder name in ZIP archive which contains the above files
    # E.g [thearchive.zip]/somefiles/file2.txt
    # FIXME: Set this to something better
    zip_subdir = instance.filename
    zip_filename = "%s.zip" % zip_subdir

    # Open StringIO to grab in-memory ZIP contents
    s = StringIO.StringIO()

    # The zip compressor
    zf = zipfile.ZipFile(s, "w")

    for fpath in filenames:
        # Calculate path for file in zip
        fdir, fname = os.path.split(fpath)
        zip_path = os.path.join(zip_subdir, fname)

        # Add file, at correct path
        zf.write(fpath, zip_path)

    # Must close zip for all contents to be written
    zf.close()

    # Grab ZIP file from in-memory, make response with correct MIME-type
    resp = HttpResponse(s.getvalue(), content_type="application/x-zip-compressed")
    # ..and correct content-disposition
    resp['Content-Disposition'] = 'attachment; filename=%s' % zip_filename

    return resp