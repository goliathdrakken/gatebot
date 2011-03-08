# -*- coding: latin-1 -*-
# Copyright 2010 Mike Wakerly <opensource@hoho.com>
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

import datetime
import os
import random

from django.conf import settings
from django.core import urlresolvers
from django.db import models
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.contrib.sites.models import Site
from django.contrib.auth.models import User

from autoslug import AutoSlugField

from pygate.core import kb_common
from pygate.core import fields
from pygate.core import stats
from pygate.core import units
from pygate.core import util

"""Django models definition for the gatebot database."""

def mugshot_file_name(instance, filename):
  rand_salt = random.randrange(0xffff)
  new_filename = '%04x-%s' % (rand_salt, filename)
  return os.path.join('mugshots', instance.user.username, new_filename)

def misc_file_name(instance, filename):
  rand_salt = random.randrange(0xffff)
  new_filename = '%04x-%s' % (rand_salt, filename)
  return os.path.join('misc', new_filename)

def _set_seqn_pre_save(sender, instance, **kwargs):
  if instance.seqn:
    return
  prev = sender.objects.filter(site=instance.site).order_by('-seqn')
  if not prev.count():
    seqn = 1
  else:
    seqn = prev[0].seqn + 1
  instance.seqn = seqn


class GatebotSite(models.Model):
  name = models.CharField(max_length=64, unique=True,
      help_text='A short single-word name for this site, eg "default" or "sfo"')
  title = models.CharField(max_length=64, blank=True, null=True,
      help_text='The title of this site, eg "San Francisco"')
  description = models.TextField(blank=True, null=True,
      help_text='Description of this site')
  background_image = models.ImageField(blank=True, null=True,
      upload_to=misc_file_name,
      help_text='Background for this site.')

  def __str__(self):
    return '%s %s' % (self.name, self.description)


class UserPicture(models.Model):
  def __str__(self):
    return "%s UserPicture" % (self.user,)

  user = models.ForeignKey(User)
  image = models.ImageField(upload_to=mugshot_file_name)
  active = models.BooleanField(default=True)


class UserProfile(models.Model):
  """Extra per-User information."""
  GENDER_CHOICES = (
    ('male', 'male'),
    ('female', 'female'),
  )
  def __str__(self):
    return "profile for %s" % (self.user,)

  def MugshotUrl(self):
    if self.mugshot:
      img_url = self.mugshot.image.url
    else:
      args = ('images/unknown-drinker.png',)
      img_url = urlresolvers.reverse('site-media', args=args)
    return img_url

  def GetStats(self):
    if hasattr(self, '_stats'):
      return self._stats
    qs = self.user.stats.all()
    if qs:
      self._stats = qs[0].stats
    else:
      self._stats = {}
    return self._stats

  def RecomputeStats(self):
    self.user.stats.all().delete()
    last_d = self.user.entries.valid().order_by('-starttime')
    if last_d:
      last_d[0]._UpdateUserStats()

  user = models.OneToOneField(User)
  gender = models.CharField(max_length=8, choices=GENDER_CHOICES)
  weight = models.FloatField()
  mugshot = models.ForeignKey(UserPicture, blank=True, null=True)

def user_post_save(sender, instance, **kwargs):
  defaults = {
    'weight': kb_common.DEFAULT_NEW_USER_WEIGHT,
    'gender': kb_common.DEFAULT_NEW_USER_GENDER,
  }
  profile, new = UserProfile.objects.get_or_create(user=instance,
      defaults=defaults)
post_save.connect(user_post_save, sender=User)

class Gate(models.Model):
  """A physical gate"""
  site = models.ForeignKey(GatebotSite, related_name='gates')
  seqn = models.PositiveIntegerField(editable=False)
  name = models.CharField(max_length=128)
  description = models.TextField(blank=True, null=True)

  def __str__(self):
    return "%s: %s" % (self.name, self.description)

pre_save.connect(_set_seqn_pre_save, sender=Gate)

class EntryManager(models.Manager):
  def valid(self):
    return self.filter(status='valid')

class Entry(models.Model):
  """ Table of entry records """
  class Meta:
    unique_together = ('site', 'seqn')
    get_latest_by = 'starttime'
    ordering = ('-starttime',)

  def PourDuration(self):
    return self.duration

  def __str__(self):
    return "Entry %s:%i by %s" % (self.site.name, self.seqn, self.user)

  objects = EntryManager()

  site = models.ForeignKey(GatebotSite, related_name='entries')
  seqn = models.PositiveIntegerField(editable=False)

  starttime = models.DateTimeField()
  duration = models.PositiveIntegerField(blank=True, default=0)
  user = models.ForeignKey(User, null=True, blank=True, related_name='entries')
  status = models.CharField(max_length=128, choices = (
     ('valid', 'valid'),
     ('invalid', 'invalid'),
     ('deleted', 'deleted'),
     ), default = 'valid')
  auth_token = models.CharField(max_length=256, blank=True, null=True)

  def _UpdateSystemStats(self):
    stats, created = SystemStats.objects.get_or_create(site=self.site)
    stats.Update(self)

  def _UpdateUserStats(self):
    if self.user:
      defaults = {
        'site': self.site,
      }
      stats, created = self.user.stats.get_or_create(defaults=defaults)
      stats.Update(self)

  def PostProcess(self):
    self._UpdateSystemStats()
    self._UpdateUserStats()
    SystemEvent.ProcessEntry(self)

pre_save.connect(_set_seqn_pre_save, sender=Entry)

class AuthenticationToken(models.Model):
  """A secret token to authenticate a user, optionally pin-protected."""
  class Meta:
    unique_together = ('site', 'seqn', 'auth_device', 'token_value')

  def __str__(self):
    ret = "%s: %s" % (self.auth_device, self.token_value)
    if self.user is not None:
      ret = "%s (%s)" % (ret, self.user.username)
    if self.nice_name:
      ret = "[%s] %s" % (self.nice_name, ret)
    return ret

  site = models.ForeignKey(GatebotSite, related_name='tokens')
  seqn = models.PositiveIntegerField(editable=False)
  auth_device = models.CharField(max_length=64)
  token_value = models.CharField(max_length=128)
  nice_name = models.CharField(max_length=256, blank=True, null=True,
      help_text='A human-readable alias for the token (eg "Guest Key").')
  pin = models.CharField(max_length=256, blank=True, null=True)
  user = models.ForeignKey(User, blank=True, null=True)
  created = models.DateTimeField(auto_now_add=True)
  enabled = models.BooleanField(default=True)
  expires = models.DateTimeField(blank=True, null=True)

  def IsAssigned(self):
    return self.user is not None

  def IsActive(self):
    if not self.enabled:
      return False
    if not self.expires:
      return True
    return datetime.datetime.now() < self.expires

pre_save.connect(_set_seqn_pre_save, sender=AuthenticationToken)


class RelayLog(models.Model):
  """ A log from an IRelay device of relay events/ """
  class Meta:
    unique_together = ('site', 'seqn')

  site = models.ForeignKey(GatebotSite, related_name='relaylogs')
  seqn = models.PositiveIntegerField(editable=False)
  name = models.CharField(max_length=128)
  status = models.CharField(max_length=32)
  time = models.DateTimeField()

pre_save.connect(_set_seqn_pre_save, sender=RelayLog)


class Config(models.Model):
  def __str__(self):
    return '%s=%s' % (self.key, self.value)

  site = models.ForeignKey(GatebotSite, related_name='configs')
  key = models.CharField(max_length=255, unique=True)
  value = models.TextField()

  @classmethod
  def get(cls, key, default=None):
    try:
      return cls.objects.get(key=key)
    except cls.DoesNotExist:
      return default


class _StatsModel(models.Model):
  STATS_BUILDER = None
  class Meta:
    abstract = True
  site = models.ForeignKey(GatebotSite)
  date = models.DateTimeField(default=datetime.datetime.now)
  stats = fields.JSONField()

  def Update(self, entry, force=False):
    previous = self.stats
    if force:
      previous = None
    builder = self.STATS_BUILDER(entry, previous)
    self.stats = builder.Build()
    self.save()


class SystemStats(_StatsModel):
  STATS_BUILDER = stats.SystemStatsBuilder

  def __str__(self):
    return 'SystemStats for %s' % self.site


class UserStats(_StatsModel):
  STATS_BUILDER = stats.UserStatsBuilder
  user = models.ForeignKey(User, unique=True, related_name='stats')

  def __str__(self):
    return 'UserStats for %s' % self.user


class SystemEvent(models.Model):
  class Meta:
    ordering = ('-when', '-id')
    get_latest_by = 'when'

  KINDS = (
      ('entry', 'Entry confirmed'),
  )

  site = models.ForeignKey(GatebotSite, related_name='events')
  seqn = models.PositiveIntegerField(editable=False)
  kind = models.CharField(max_length=255, choices=KINDS,
      help_text='Type of event.')
  when = models.DateTimeField(help_text='Time of the event.')
  user = models.ForeignKey(User, blank=True, null=True,
      related_name='events',
      help_text='User responsible for the event, if any.')
  entry = models.ForeignKey(Entry, blank=True, null=True,
      related_name='events',
      help_text='Entry involved in the event, if any.')

  def __str__(self):
    if self.kind == 'entry':
      ret = 'Entry %i confirmed' % self.entry.seqn
    else:
      ret = 'Unknown event type (%s)' % self.kind
    return 'Event %i: %s' % (self.seqn, ret)

  @classmethod
  def ProcessKeg(cls, keg):
    site = keg.site
    if keg.status == 'online':
      q = keg.events.filter(kind='keg_tapped')
      if q.count() == 0:
        e = keg.events.create(site=site, kind='keg_tapped', when=keg.startdate,
            keg=keg)
        e.save()

    if keg.status == 'offline':
      q = keg.events.filter(kind='keg_ended')
      if q.count() == 0:
        e = keg.events.create(site=site, kind='keg_ended', when=keg.enddate,
            keg=keg)
        e.save()

  @classmethod
  def ProcessEntry(cls, entry):
    site = entry.site
    user = entry.user

    q = entry.events.filter(kind='entry')
    if q.count() == 0:
      e = entry.events.create(site=site, kind='entry',
          when=entry.starttime, entry=entry, user=user)
      e.save()

pre_save.connect(_set_seqn_pre_save, sender=SystemEvent)
