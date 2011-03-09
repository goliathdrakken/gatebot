#!/usr/bin/env python
#
# Copyright 2008 Mike Wakerly <opensource@hoho.com>
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

"""Kegweb main views."""

import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.cache import cache_page
from django.views.generic.list_detail import object_detail
from django.views.generic.list_detail import object_list
from django.views.generic.simple import redirect_to

from pygate.core import models
from pygate.core import units

from pygate.web.gateweb import forms
from pygate.web.gateweb import models as gateweb_models
from pygate.web.gateweb import view_util

### main views

@cache_page(30)
def index(request):
  context = RequestContext(request)
  try:
    page = gateweb_models.Page.objects.get(name__exact='MainPage',
                                          status__exact='published')
  except gateweb_models.Page.DoesNotExist:
    page = None
  context['page_node'] = page
  context['taps'] = request.kbsite.gates.all()
  return render_to_response('index.html', context)

@cache_page(30)
def system_stats(request):
  context = RequestContext(request)

  stats_qs = request.kbsite.systemstats_set.all()
  if stats_qs:
    stats = stats_qs[0].stats
  else:
    stats = {}
  context['stats'] = stats

  top_drinkers = []
  for username, vol in stats.get('entry_by_user', {}).iteritems():
    username = str(username)
    vol = float(vol)
    try:
      user = models.User.objects.get(username=username)
    except models.User.DoesNotExist:
      continue  # should not happen
    volume = units.Quantity(vol)
    top_drinkers.append((volume, user))
  top_drinkers.sort(reverse=True)

  context['top_drinkers'] = top_drinkers[:10]

  return render_to_response('gateweb/system-stats.html', context)


### object lists and detail (generic views)

def user_list(request):
  user_list = models.User.objects.all()
  return object_list(request,
      queryset=user_list,
      template_object_name='user',
      template_name='gateweb/user_list.html')

def user_detail(request, username):
  user = get_object_or_404(models.User, username=username)
  stats = user.get_profile().GetStats()

  context = RequestContext(request, {
      'stats': stats,
      'user': user})
  return render_to_response('gateweb/user_detail.html', context)

def user_detail_by_id(request, user_id):
  try:
    user = models.User.objects.get(pk=user_id)
  except models.User.DoesNotExist:
    raise Http404
  return redirect_to(request, url='/user/'+user.username)

def entry_list(request):
  all_entries = request.kbsite.entries.valid()
  return object_list(request,
      queryset=all_entries,
      template_name='gateweb/entry_list.html',
      template_object_name='entry')

def entry_detail(request, entry_id):
  entry = get_object_or_404(models.Entry, site=request.kbsite, seqn=entry_id)
  context = RequestContext(request, {'entry': entry})
  return render_to_response('gateweb/entrydr_detail.html', context)

### auth

def webauth(request):
  context = {}
  return render_to_response('gateweb/webauth.html', context)

@login_required
def claim_token(request):
  if request.method == 'POST':
    form = forms.ClaimTokenForm(request.POST)

    if form.is_valid():
      user = form.cleaned_data['user']
      token = form.cleaned_data['token']
      # TODO(mikey): non-superusers should only be able to claim tokens for
      # their own account.
      token.user = user
      token.save()
  else:
    form = forms.ClaimTokenForm()

  context = RequestContext(request)
  context['form'] = form
  return render_to_response('gateweb/claim_token.html', context)

