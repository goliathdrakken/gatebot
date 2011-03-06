# -*- coding: latin-1 -*-
# Copyright 2009 Mike Wakerly <opensource@hoho.com>
#
# This file is part of the Pygate package of the Gatebot project.
# For more information on Pygate or Gatebot, see http://gatebot.org/
#
# Pygate is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Pygate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pygate.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib import admin

from pygate.core import models
from pygate.core import util

admin.site.register(models.UserPicture)
admin.site.register(models.UserProfile)

admin.site.register(models.GatebotSite)

class AuthenticationTokenAdmin(admin.ModelAdmin):
  list_display = ('auth_device', 'user', 'token_value', 'nice_name', 'enabled', 'IsActive')
  list_filter = ('auth_device', 'enabled')
  search_fields = ('user__username', 'token_value', 'nice_name')
admin.site.register(models.AuthenticationToken, AuthenticationTokenAdmin)

admin.site.register(models.RelayLog)

class ConfigAdmin(admin.ModelAdmin):
  list_display = ('key', 'value')
  search_fields = ('key', 'value')
admin.site.register(models.Config, ConfigAdmin)

class SystemEventAdmin(admin.ModelAdmin):
  list_display = ('seqn', 'kind', 'when', 'user', 'entry')
  list_filter = ('kind', 'when')
admin.site.register(models.SystemEvent, SystemEventAdmin)
