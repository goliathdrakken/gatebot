import os.path

from pygate.core import features

from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib.auth.views import password_reset
from django.contrib.auth.views import password_reset_done
from django.contrib.auth.views import password_reset_confirm
from django.contrib.auth.views import password_reset_complete
from django.contrib import admin
admin.autodiscover()

def basedir():
  """ Get the pwd of this module, eg for use setting absolute paths """
  return os.path.abspath(os.path.dirname(__file__))

urlpatterns = patterns('',
    ### django admin site
    (r'^admin/(.*)', admin.site.root),

    ### static media
    url(r'^site_media/(.*)$',
      'django.views.static.serve',
      {'document_root': os.path.join(basedir(), 'media')},
      name='site-media'),

    url(r'^media/(.*)$',
     'django.views.static.serve',
     {'document_root': settings.MEDIA_ROOT, 'show_indexes': True},
     name='media'),

    ### RESTful api
    (r'^api/', include('pygate.web.api.urls')),

    ### account
    (r'^account/', include('pygate.web.account.urls')),
    (r'^accounts/password/reset/$', password_reset, {'template_name':
     'registration/password_reset.html'}),
    (r'^accounts/password/reset/done/$', password_reset_done, {'template_name':
     'registration/password_reset_done.html'}),
    (r'^accounts/password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', password_reset_confirm, {'template_name':
     'registration/password_reset_confirm.html'}),
    (r'^accounts/password/reset/complete/$', password_reset_complete, {'template_name':
     'registration/password_reset_complete.html'}),

    ### charts
    (r'^charts/', include('pygate.web.charts.urls')),

    ### kegadmin
    (r'^gateadmin/', include('pygate.web.gateadmin.urls')),

    ### main kegweb urls
    (r'', include('pygate.web.gateweb.urls')),
)
