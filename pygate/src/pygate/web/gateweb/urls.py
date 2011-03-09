from django.conf.urls.defaults import *

try:
  from registration.views import register
  from pygate.web.gateweb.forms import KegbotRegistrationForm
  USE_DJANGO_REGISTRATION = True
except ImportError:
  USE_DJANGO_REGISTRATION = False

urlpatterns = patterns('pygate.web.gateweb.views',
      ### main page
      (r'^$', 'index'),

      ### accountpage
      (r'^claim_token/$', 'claim_token'),

      ### all-time stats
      (r'^stats/$', 'system_stats'),
      (r'^leaders/$', 'redirect_to', {'url': '/stats/'}),

      ### drinkers
      (r'^users/$', 'user_list'),
      url(r'^users/(?P<username>\w+)', 'user_detail', name='user'),
      (r'^drinkers/(?P<user_id>\d+)', 'user_detail_by_id'),
      # redirects to the above for compatibility
      (r'^user/(?P<user_id>\d+)', 'redirect_to', {'url': '/users/%(user_id)s'}),
      (r'^user/(?P<username>\w+)', 'redirect_to', {'url': '/users/%(username)s'}),

      ### drink related
      (r'^entries/$', 'entry_list'),
      url(r'^entries/(?P<entry_id>\d+)', 'entry_detail', name='entry'),
      # redirects to the above for compatibility
      (r'^entry/(?P<entry_id>\d+)', 'redirect_to', {'url': '/entries/%(entry_id)s'}),
      (r'^d/(?P<entry_id>\d+)', 'redirect_to', {'url': '/entries/%(entry_id)s'}),

)

### accounts and registration
# uses the stock django-registration views, except we need to override the
# registration class for acocunt/register
if USE_DJANGO_REGISTRATION:
  from django.contrib.auth import views as auth_views
  urlpatterns += patterns('',
    url(r'^accounts/register/$', register,
      {'form_class':KegbotRegistrationForm},
      name='registration_register',
    ),
   (r'^accounts/', include('registration.urls')),
  )

