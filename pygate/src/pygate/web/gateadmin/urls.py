from django.conf.urls.defaults import *

urlpatterns = patterns('pygate.web.gateadmin.views',
      ### main page
      url(r'^$', 'gateadmin_main', name='gateadmin-main'),
      url(r'^taps/$', 'gate_list', name='gateadmin-gate-list'),
      url(r'^taps/(?P<gate_id>\d+)/$', 'edit_gate', name='gateadmin-edit-gate'),
      url(r'^get-backup/$', 'generate_backup', name='gateadmin-get-backup'),
)

