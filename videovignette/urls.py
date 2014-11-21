from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.i18n import i18n_patterns

import logging
from frontend.views import Home, VideoListView, VideoPreview


logger = logging.getLogger('videovignette')
logger.setLevel('DEBUG')

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'videovignette.views.home', name='home'),
    # url(r'^blog/', include('blog.urls'))
    # You may optionally define a delete url as well
    url(r'^delete/(?P<pk>\d+)$', 'frontend.views.upload_delete', name='jfu_delete' ),
    url(r'upload/', 'frontend.views.upload', name = 'jfu_upload' ), #name rend obligatoire le POST
    url(r'video_list/', VideoListView.as_view(), name='video_list'),
    url(r'^([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12})/$',
        VideoPreview.as_view()),
    url(r'^([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12})/(?P<count>\d+)$',
        VideoPreview.as_view()),
    url(r'^archive/([a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{12})/$',
        'frontend.views.archivegenerator'),
    url(r'crop_selection', 'frontend.views.cropselection', name='crop_selection'),
    url(r'attach_tag', 'frontend.views.attach_tag', name='attach_tag'),
    url(r'^get_tags', 'frontend.views.get_tags', name='get_tags'),
    url(r'^$', Home.as_view()),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^admin/', include(admin.site.urls)),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()
#logger.debug("URL CONFIG: " + str(urlpatterns))