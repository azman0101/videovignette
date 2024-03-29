# -*- coding: utf-8 -*-

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseServerError
from django.views.generic import ListView
from django.contrib.auth.decorators import permission_required

from os.path import split
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
from django.utils.translation import ugettext as _

from django.views.decorators.http import require_POST, require_GET
from jfu.http import upload_receive, UploadResponse, JFUResponse
import subprocess

import uuid
import time
from multiprocessing import Pool, Manager, Lock
from threading import ThreadError
import redis

redis_db = redis.StrictRedis(host='localhost', port=6379, db=15)
redis_db.flushdb()
import logging

logger = logging.getLogger('videovignette')
logger.setLevel('INFO')

# l = logging.getLogger('django.db.backends')
# l.setLevel(logging.DEBUG)
# l.addHandler(logging.StreamHandler())

lock_ffmpeg_launch = Lock()

from frontend.models import VideoUploadModel, ApplicationSetting, CroppedFrame, Box


class Home(generic.TemplateView):
	template_name = 'base.html'

	def get_context_data(self, **kwargs):
		context = super(Home, self).get_context_data(**kwargs)
		context['accepted_mime_types'] = ['video/*']
		return context


class VideoListView(ListView):
	model = VideoUploadModel

	def get(self, request, *args, **kwargs):
		return super(VideoListView, self).get(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super(VideoListView, self).get_context_data(**kwargs)
		# context['url_to_processed_folder'] = self.video
		cropped_frames_video = dict()
		for video in self.object_list:
			cropped_frames_video[str(video.pk)] = CroppedFrame.objects.filter(video_upload_file=video)
		context['cropped_frames_video'] = cropped_frames_video
		return context

	# def get_queryset(self):
	#	self.video = get_object_or_404(VideoUploadModel, name=self.args[0])
	#	return self.video.processed_folder


@require_GET
def delete_cropped_frame(request, pk):
	frame = CroppedFrame.objects.get(pk=pk)
	logger.error("DELETION OF: " + str(frame.id))
	frame.delete()
	return HttpResponseRedirect('/#list_video')


@require_GET
def download_cropped_frame(request, pk):
	cropped_frame = get_object_or_404(CroppedFrame, pk=pk)
	video_original = cropped_frame.video_upload_file

	response = HttpResponse()

	cropped_frame.cropped_frame_file.open('rb')
	# let nginx determine the correct content type
	response['Content-Type'] = ""
	response['Content-Disposition'] = 'attachment; filename="' + filename('Extrait_de_' +
	                                                                      video_original.filename.split('.')[
		                                                                      0]) + '_' + cropped_frame.to_time() + '"'
	response.write(cropped_frame.cropped_frame_file.read())
	return response


def filename(obj):
	head, tail = split(obj)
	return tail


def ffmpeg_info(output, err, resolution=None):
	filters_str = {'duration': "(Duration\:\s?)(\d{2}:[0-5][0-9]:[0-5][0-9]\.\d{1,3})",
	               'fps': "(Stream #\d.\d.*?: Video:\s?).*?([0-9]+.?[0-9]+)\s?fps"}

	if output == '' or output is None:
		output = err
	# Split in lines
	data = {}
	for key, filter in filters_str.iteritems():
		value = re.search(filter, output)
		# Warning: this is always the same group number in the two filter
		if value is not None:
			data[key] = value.group(2)
			if resolution is not None:
				width, height = resolution.split('x')
				data['width'] = width
				data['height'] = height
			if key == 'duration':
				parse_time = re.search(r'(\d{2}):([0-5][0-9]):([0-5][0-9])\.(\d{1,3})', data[key])
				# TODO: Handle error when parse_time is not
				data['hours'] = int(parse_time.group(1))
				data['minutes'] = int(parse_time.group(2))
				data['seconds'] = int(parse_time.group(3))
				data['microseconds'] = int(parse_time.group(4))

	tm = timedelta(hours=data['hours'], minutes=data['minutes'],
	               seconds=data['seconds'], microseconds=data['microseconds'])
	data['timedelta'] = tm
	logger.error("TOTAL SECONDS: " + str(tm.total_seconds()))
	logger.error("FPS: " + str(float(data['fps'])))

	data['frame_count'] = int(tm.total_seconds() * float(data['fps']))
	return data


def start_ffmpeg(param):
	filepath = param['filepath']
	file_pk = param['file_pk']
	configuration_ffmpeg, resize_ffmpeg_parameter = param['configuration_ffmpeg_tuple']
	abs_pathname = param['abs_pathname']
	folder_name = param['folder_name']
	lock = param['lock']
	# Acquire non blocking lock for getting the two ffmpeg process begins in the same time
	lock.acquire(blocking=False)

	# TODO: check if file exists ! Really ... this is FOR DEBUG ONLY
	logger.error("Check if exits yet... " + str(filepath))
	while not os.path.exists(filepath):
		time.sleep(1)
		logger.error("File don't exits yet... " + str(filepath))

	# TO REMOVE : basename unused.
	# basename = os.path.basename(filepath)
	VideoUploadModel.objects.filter(pk=file_pk).update(processed_folder=folder_name)
	if configuration_ffmpeg == 'full_res':
		prefix = 'full_'
	else:
		prefix = 'low_'
	# TODO: dynamically choose the right decoding app (ffmpeg or avconv)
	"""
	TODO: Find a better way for "ffmpeg filters" Ex: ffmpeg -i input.mpg -vf "movie=watermark.png [logo]; [in][logo]
	overlay=W-w-10:H-h-10, fade=in:0:20 [out]" output.mpg
	"""
	try:

		logger.error("settings.DEMUXER: " + str(type(settings.DEMUXER)))
		logger.error("filepath: " + str(type(filepath)))
		logger.error("encodage_setting.resize_ffmpeg_parameter: " + str(type(resize_ffmpeg_parameter)))
		logger.error("abs_pathname: " + str(type(abs_pathname)))
		logger.error("prefix: " + str(type(prefix)))
		bash_command = settings.DEMUXER + ' -i ' + filepath + ' -q:v 1 ' + resize_ffmpeg_parameter + \
		               '-vf showinfo -an -f image2 ' + abs_pathname + '/' + prefix + 'output_%05d.jpg'
		logger.error('start_ffmpeg: ' + bash_command)
	except TypeError as e:
		logger.error('TypeError !!!!: ' + str(e.message))
	# TODO: What about to use stdout to pipe response to main process ?
	process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1,
	                           close_fds=True)
	header_output_ffmpeg = []
	redis_db.rpush('pid', process.pid)
	infoheader_passed = False
	while process.poll() is None:
		if process.stdout is not None:
			err = str(process.stderr.readline())
			# While there is no 'showinfo' in the line, then, we are in the header
			if 'showinfo' not in err:
				header_output_ffmpeg.append(err)
			if 'showinfo' in err:

				# EXEMPLE: [Parsed_showinfo_0 @ 0x1c5c0a0] n:64 pts:66 pts_time:2.64 pos:522970 fmt:yuv420p sar:1/1
				# s:1920x1072 i:P iskey:0 type:P checksum:BC04CF1A plane_checksum:[1ABBF73C 4E648C19 D8B04BB6]
				# mean:[171 125 128 ] stdev:[66.1 9.6 11.5]

				# Regex for match on hex showinfo identifier and n which is probable the frame count
				current_frame = re.search(
					r'\[Parsed_showinfo_\d\s?@\s?(0x[0-9a-f]+)\]\s?n:\s*(\d+)\w?.*?s:\s*(\d+x\d+)\s?', err)
				if current_frame is None:
					# Frame output undecodable
					logger.error("CURRENT_FRAME_REGEX: " + str(type(current_frame)))
					logger.error("Not match for: " + str(err))
					task_ffmpeg = None
					resolution = None
					frame_number = None
				else:
					# Frame output decodable
					#logger.error("Match for: " + str(err))
					task_ffmpeg = current_frame.group(1)
					resolution = current_frame.group(3)
					frame_number = current_frame.group(2)
					logger.info("IN WHILE: task_ffmpeg: %s | resolution: %s | frame_number: %s" %(task_ffmpeg, resolution, frame_number))
				# Push each value in the line containing showinfo and matching to regex

				if task_ffmpeg is not None:
					redis_db.rpush(task_ffmpeg, frame_number)

				if infoheader_passed is False and resolution is not None:  # and not redis_db.exists('info_ffmpeg')
					info_ffmpeg = ffmpeg_info('\n'.join(header_output_ffmpeg), '', resolution=resolution)
					redis_db.hmset('info_ffmpeg', info_ffmpeg)
					logger.error("FRAMES COUNT: " + str(info_ffmpeg['frame_count']))
					infoheader_passed = True
				# sys.stdout.write("FFMPEG ER: " + err)
				# sys.stdout.flush()

	process.wait()
	# FFMPEG process just finish (one process)

	# Remove my PID from the tasks list (REDIS)
	i_am = redis_db.lpop('pid')
	logger.error("TASKS_PID JUST END: " + str(i_am))
	logger.error("TASKS_PID LEN: " + str(redis_db.llen('pid')))

	while redis_db.llen('pid') != 0:
		# Waiting second process until it's remove it's PID from the tasks list (REDIS)
		time.sleep(1)

	try:
		# First process release the lock, second will raise ThreadError
		lock.release()
		logger.error("I'have release the Kraken : " + str(i_am))
	except ThreadError as e:
		# Second process is the last one, we don't need redis db anymore.
		logger.error("Let's flush db, I'm: " + str(i_am))

		redis_db.flushdb()

	err = ''
	try:
		header_output_ffmpeg = '\n'.join(header_output_ffmpeg)
		tm = info_ffmpeg['timedelta']
		if configuration_ffmpeg == 'full_res' and 'width' in info_ffmpeg.keys():
			logger.error("ALL DATA info_ffmpeg: " + str(info_ffmpeg))
			VideoUploadModel.objects.filter(pk=file_pk).update(width=info_ffmpeg['width'], height=info_ffmpeg['height'])

		logger.error('Float seconds: ' + str(tm.total_seconds()))
		VideoUploadModel.objects.filter(pk=file_pk).update(duration=tm.total_seconds(), frame_per_second=info_ffmpeg['fps'])

		# if a process already set file_instance.ready to True then it's useless to count again
		if VideoUploadModel.objects.get(pk=file_pk).ready is not True:
			VideoUploadModel.objects.filter(pk=file_pk).update(ready=True)
			logger.error('PATH.. ' + str(abs_pathname))

			path, dirs, files = os.walk(abs_pathname).next()
			# Count only the files with prefix
			files_count = len([f for f in files if f.startswith(prefix)])
			logger.error('GENERATED FRAMES COUNT.. ' + str(files_count))
			VideoUploadModel.objects.filter(pk=file_pk).update(generated_images_count=files_count)
		# Save instance for modification made on processed_folder and ready
	except Exception as e:
		logger.error('EXCEPTION WTF.. ' + str(e))
	logger.error('RETURN start_ffmpeg.. %s | %s ' % (str(header_output_ffmpeg), str(err)))
	return header_output_ffmpeg, err


def get_or_create_dir():
	folder_name = str(uuid.uuid4())
	seq_path = settings.MEDIA_ROOT + folder_name
	if not os.path.exists(seq_path):
		os.makedirs(seq_path)
	return seq_path, folder_name


@require_GET
def get_progress(request):
	data = dict()
	if redis_db.exists('info_ffmpeg'):
		info_ffmpeg_redis = redis_db.hgetall('info_ffmpeg')
		frame_count_redis = float(info_ffmpeg_redis['frame_count'])
		keys = redis_db.keys(pattern='0x*')
		count = 0.0
		for key in keys:
			count += float(redis_db.llen(key))
		# Adjustment to stick to reality ;)
		count = ((count / 2.0 + 2) / frame_count_redis) * 100.0
		logger.error("GETPROG %: " + str(count))
		data['progress'] = int(count)
		if count >= 100:
			data['progress'] = 100
	else:
		data['progress'] = 100

	data = json.dumps(data)
	mimetype = 'application/json'
	return HttpResponse(data, mimetype)


@require_POST
def upload(request):
	# The assumption here is that jQuery File Upload
	# has been configured to send files one at a time.
	# If multiple files can be uploaded simultaneously,
	# 'file' may be a list of files.
	video = upload_receive(request)

	if not 'video/' in video.content_type:
		# TODO: handle error for report to user interface
		return HttpResponseBadRequest(content='Please send only video')
	else:
		# TODO: if correct header, check content itself ! “trust but verify.”
		pass
	instance = VideoUploadModel(video_file=video, size=video.size, filename=video.name)
	logger.debug(str(dir(video)))
	logger.debug(str(video.name))
	logger.debug(str(video.content_type))
	logger.debug(str(video.size))
	logger.debug(str(instance))
	instance.save()
	filepath = instance.video_file.path
	logger.error("File PATH: " + str(type(filepath)))
	assert isinstance(filepath, basestring)

	basename = os.path.basename(filepath)

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
	logger.info("Redis: " + str(redis_db))
	redis_db.hset(folder_name, 'upload', True)
	configuration_to_apply = ['low_res', 'full_res']
	encodage_settings = list()
	for config in configuration_to_apply:
		configuration_ffmpeg = ApplicationSetting.objects.get(configuration_name=config)
		configuration_ffmpeg_tuple = tuple()
		configuration_ffmpeg_tuple = (config, configuration_ffmpeg.resize_ffmpeg_parameter)
		encodage_settings.append(configuration_ffmpeg_tuple)

	manager = Manager()
	lock = manager.Lock()
	lock_ffmpeg_launch.acquire()
	logger.info("Lock acquiered" + str(lock_ffmpeg_launch))
	results = pool.map(start_ffmpeg, [{'filepath': filepath, 'file_pk': instance.pk,
	                                   'configuration_ffmpeg_tuple': configuration_ffmpeg_tuple,
	                                   'abs_pathname': abs_pathname,
	                                   'folder_name': folder_name, 'lock': lock} for configuration_ffmpeg_tuple in
	                                  encodage_settings])
	try:
		for result in results:
			try:
				if hasattr(result, 'get'):
					output, err = result.get()
					logger.info(output)
					logger.error(err)
				else:
					logger.error('Result: %s' % str(result))
			except OSError as e:
				# TODO: Handle this error by sending a message to interface.
				# TODO: Retry process with another decoding app (ffmpeg or avconv)
				logger.error("Error: FFMPEG" + str(e))
				return HttpResponseServerError(content='FFMPEG Error ' + str(e))
	except Exception as e:
		logger.error("Result Exception: %s" % str(e))
	lock_ffmpeg_launch.release()
	logger.info("Lock released" + str(lock_ffmpeg_launch))
	logger.error("BEFOR UPLOAD POST RESPONSE: " + str(request))
	logger.error("BEFOR UPLOAD POST RESPONSE: " + str(file_dict))
	return UploadResponse(request, file_dict)


@require_POST
@csrf_exempt
def upload_delete(request, pk):
	success = True
	try:
		instance = VideoUploadModel.objects.get(pk=pk)
		try:
			os.unlink(instance.video_file.path)
		except Exception as e:
			logger.error("FILE IS NOT DELETED!!!!!!!!!!!!!!!!!!" + str(e))
		time.sleep(1)
		if os.path.isfile(instance.video_file.path):
			raise Exception('File is not deleted')
		logger.error("Have to delete %s" % str(instance.video_file.path))
		instance.delete()
	except VideoUploadModel.DoesNotExist:
		success = False

	return JFUResponse(request, success)


class VideoPreview(generic.TemplateView):
	template_name = 'videopreview.html'

	# First GET then get_context_data
	def get(self, request, *args, **kwargs):
		# Capture count parameter send in URL by the javascript listener_videolisting
		self.start_count = self.request.GET.get('count')
		self.fastforward = self.request.GET.get('fastforward', False)
		# TODO: move this after image creation for count and put to DB
		# Capture folder in URL
		self.folder = args[0]
		# Lookup database for Video instance
		video_instance = get_object_or_404(VideoUploadModel, processed_folder=self.folder)
		# Retreive instance's number of frame generated
		self.fps = video_instance.frame_per_second
		self.duration = video_instance.duration
		self.max_count = video_instance.generated_images_count
		self.height = video_instance.height
		self.width = video_instance.width
		return super(VideoPreview, self).get(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context = super(VideoPreview, self).get_context_data(**kwargs)
		logger.error("VideoPreview get_context_data : " + str(context))
		display_per = 6
		file_listing = []
		# If count not yet passed by GET, then start to 1
		if self.start_count is None:
			self.start_count = 1
		# Take only 6 by 6 thumb unless max_count reached
		count_end = int(self.start_count) + display_per
		if count_end > self.max_count:
			count_end = self.max_count + 1
		for number in range(int(self.start_count), count_end):  # self.file_count
			# TODO: parametrize standard res low or full
			low = settings.MEDIA_URL + self.folder + '/low_output_%05d.jpg' % number
			full = settings.MEDIA_URL + self.folder + '/full_output_%05d.jpg' % number
			file_listing.append((full, low))

		# TODO: Present this as dictionary
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
		context['height'] = self.height
		context['width'] = self.width
		return context


def getimgsize(path):
	im = Image.open(path)
	return im.size


@require_POST
@permission_required('taggit.add_tag')
@csrf_exempt
def create_tag(request):
	tag_dict = request.POST.dict()
	tags = Tag.objects.filter(name=tag_dict['term'])
	if tags.exists():
		# #There is only one result in tags because pk is unique
		# tag = tags[0]
		# #Get CroppedFrame to tag (give by data-cropped-id in <div class="ui-widget" id="tags" data-cropped-id="8">
		# cropped_frame = CroppedFrame.objects.get(pk=tag_dict['cropped_id'])
		#
		# cropped_frame.tags.add(tag)
		# cropped_frame.full_clean()
		# cropped_frame.save()
		toastr_json = dict()
		toastr_json['type'] = 'info'
		toastr_json['css'] = 'toast-bottom-left'
		toastr_json['msg'] = _("Tag already exists, just select it by the list")
	else:
		newtag = Tag(name=tag_dict['term'])
		newtag.save()
		toastr_json = dict()
		toastr_json['type'] = 'warning'
		toastr_json['css'] = 'toast-bottom-left'
		toastr_json['msg'] = _("%s created but not attached, re-search it by the list for attaching it"
		                       % newtag.name)
	data = json.dumps(toastr_json)
	mimetype = 'application/json'
	return HttpResponse(data, mimetype)


@require_POST
@csrf_exempt
def attach_tag(request):
	tag_dict = request.POST.dict()
	tags = Tag.objects.filter(pk=tag_dict['id'])
	if tags.exists():
		# There is only one result in tags because pk is unique
		tag = tags[0]
		# Get CroppedFrame to tag (give by data-cropped-id in <div class="ui-widget" id="tags" data-cropped-id="8">
		cropped_frame = CroppedFrame.objects.get(pk=tag_dict['cropped_id'])
		if cropped_frame.tags.filter(name=tag).exists():
			toastr_json = dict()
			toastr_json['type'] = 'error'
			toastr_json['css'] = 'toast-bottom-left'
			toastr_json['msg'] = _("%s tag already attached" % tag)
		else:
			cropped_frame.tags.add(tag)
			cropped_frame.full_clean()
			cropped_frame.save()
			toastr_json = dict()
			toastr_json['type'] = 'success'
			toastr_json['css'] = 'toast-bottom-left'
			toastr_json['msg'] = _("%s tag added" % tag)
	else:
		toastr_json = dict()
		toastr_json['type'] = 'warning'
		toastr_json['css'] = 'toast-bottom-left'
		toastr_json['msg'] = _("No tag attached")
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
			tag_json = dict()
			tag_json['id'] = tag.id
			tag_json['label'] = tag.name
			tag_json['value'] = tag.name
			results.append(tag_json)
		# Check authorization when not tag match to query for inform user about his permission on tags creation
		# This part is just a mean for send permission info to user interface
		if not results:
			logger.info("User authentication: " + str(request.user.is_anonymous()))
			if request.user.is_anonymous() or not request.user.has_perm('taggit.add_tag'):
				tag_json = dict()
				tag_json['id'] = -1
				tag_json['label'] = _("warning")  # Use label as type toastr
				tag_json['value'] = _("Your are not authorized to create tags")
			elif request.user.has_perm('taggit.add_tag'):
				tag_json = dict()
				tag_json['id'] = -2
				tag_json['label'] = _("info")  # Use label as type toastr
				tag_json['value'] = _("You get permission to create your own tags")

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
	assert (not posted_dict.has_key('image_url'))
	try:
		# update dict by casting value to int
		[posted_dict.update({k: int(v)}) for k, v in posted_dict.iteritems()]
	except Exception as e:
		logger.error("CropSelection update posted_dict: %s" % str(e))
		toastr_json = dict()
		toastr_json['type'] = 'error'
		toastr_json['css'] = 'toast-bottom-left'
		toastr_json['msg'] = _("No boxing limits were definied :/")
		data = json.dumps(toastr_json)
		mimetype = 'application/json'
		return HttpResponseServerError(data, mimetype)

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
		cropped_img.save(in_memory_temp, "JPEG", quality=100)
		in_memory_temp.seek(0)
		file_cropped_img = SimpleUploadedFile(
			folder + '_' + str(uuid.uuid4()) + '_' + str(image_number.group(1)) + '.jpeg',
			in_memory_temp.read(), content_type='image/jpeg')
	else:
		file_cropped_img = None

	instance_croppedframe = CroppedFrame(video_upload_file=instance_video, frame_number=int(image_number.group(1)),
	                                     box=box, cropped_frame_file=file_cropped_img)

	instance_croppedframe.save()
	logger.error(str(posted_dict))
	return HttpResponse(content=instance_croppedframe.id)


@require_GET
def archivegenerator(request, folder):
	logger.error("archivegenerator FOLDER: " + str(folder))
	instance = get_object_or_404(VideoUploadModel, processed_folder=folder)
	seq_path = settings.MEDIA_ROOT + folder
	logger.error("archivegenerator FOLDER ABS: " + str(seq_path))
	path, dirs, files = os.walk(seq_path).next()
	filenames = [seq_path + '/' + f for f in files if f.startswith('full_')]
	logger.error("archivegenerator FOLDER: " + str(filenames))

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
