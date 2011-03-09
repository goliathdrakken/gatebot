# Copyright 2010 Mike Wakerly <opensource@hoho.com>
#
# This file is part of the Pykeg package of the Kegbot project.
# For more information on Pykeg or Kegbot, see http://kegbot.org/
#
# Pykeg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Pykeg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pykeg.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls.defaults import *

urlpatterns = patterns('pygate.web.api.views',

    url(r'^auth-token/(?P<auth_device>[\w\.]+)\.(?P<token_value>\w+)/?$',
        'get_auth_token'),
    url(r'^cancel-entry/?$', 'cancel_entry'),
    url(r'^entry/?$', 'all_entries'),
    url(r'^entry/(?P<entry_id>\d+)/?$', 'get_entry'),
    url(r'^event/?$', 'all_events'),
    url(r'^event/html/?$', 'recent_events_html'),
    url(r'^sound-event/?$', 'all_sound_events'),
    url(r'^gate/?$', 'all_gates'),
    url(r'^gate/(?P<gate_id>[\w\.]+)/?$', 'gate_detail'),
    url(r'^thermo-sensor/?$', 'all_thermo_sensors'),
    url(r'^thermo-sensor/(?P<sensor_name>[^/]+)/?$', 'get_thermo_sensor'),
    url(r'^thermo-sensor/(?P<sensor_name>[^/]+)/logs/?$', 'get_thermo_sensor_logs'),
    url(r'^user/(?P<username>\w+)/?$', 'get_user'),
    url(r'^user/(?P<username>\w+)/entries/?$', 'get_user_entries'),
    url(r'^user/(?P<username>\w+)/events/?$', 'get_user_events'),
    url(r'^user/(?P<username>\w+)/stats/?$', 'get_user_stats'),

    url(r'^last-entry-id/?$', 'last_entry_id'),
    url(r'^last-entries/?$', 'last_entries'),
    url(r'^last-entries-html/?$', 'last_entries_html'),

    url(r'^get-access-token/?$', 'get_access_token'),

    url(r'', 'default_handler'),

)
