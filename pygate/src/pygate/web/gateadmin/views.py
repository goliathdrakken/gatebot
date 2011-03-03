#!/usr/bin/env python
#
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

import cStringIO
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response

from pygate.core import backup
from pygate.core import models

from pygate.web.gateadmin import forms

@staff_member_required
def gateadmin_main(request):
  context = RequestContext(request)
  return render_to_response('gateadmin/index.html', context)

@staff_member_required
def gate_list(request):
  context = RequestContext(request)
  context['gates'] = request.kbsite.gates.all()
  return render_to_response('gateadmin/gate-list.html', context)

@staff_member_required
def edit_gate(request, gate_id):
  context = RequestContext(request)
  tap = get_object_or_404(models.Gate, site=request.kbsite, seqn=gate_id)

  form = forms.ChangeKegForm()
  if request.method == 'POST':
    form = forms.ChangeKegForm(request.POST)
    if form.is_valid():
      current = gate.current_keg
      if current and current.status != 'offline':
        current.status = 'offline'
        current.save()
      new_keg = models.Keg()
      new_keg.site = request.kbsite
      new_keg.status = 'online'
      if form.cleaned_data['description']:
        new_keg.description = form.cleaned_data['description']
      new_keg.save()
      tap.current_keg = new_keg
      tap.save()
      messages.success(request, 'The new keg was activated.')
      form = forms.ChangeKegForm()

  context['gates'] = request.kbsite.taps.all()
  context['gate'] = gate
  context['change_keg_form'] = form
  return render_to_response('gateadmin/tap-edit.html', context)

@staff_member_required
def view_stats(request):
  context = RequestContext(request)
  keg_stats = models.KegStats.objects.all()

@staff_member_required
def generate_backup(request):
  context = RequestContext(request)

  indent = None
  indent_param = request.GET.get('indent', None)
  if indent_param:
    try:
      indent = int(indent_param)
    except ValueError:
      pass

  kbsite = request.kbsite
  datestr = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
  filename = 'gatebot-%s.%s.json.txt' % (kbsite.name, datestr)

  output_fp = cStringIO.StringIO()
  backup.dump(output_fp, kbsite, indent=indent)

  response = HttpResponse(output_fp.getvalue(),
      mimetype="application/octet-stream")
  response['Content-Disposition'] = 'attachment; filename=%s' % filename
  output_fp.close()
  return response
