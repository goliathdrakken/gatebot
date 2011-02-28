# -*- coding: latin-1 -*-
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

"""Django models definition for the kegbot database."""

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


class KegbotSite(models.Model):
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
    last_d = self.user.drinks.valid().order_by('-starttime')
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

  site = models.ForeignKey(KegbotSite, related_name='tokens')
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

  site = models.ForeignKey(KegbotSite, related_name='relaylogs')
  seqn = models.PositiveIntegerField(editable=False)
  name = models.CharField(max_length=128)
  status = models.CharField(max_length=32)
  time = models.DateTimeField()

pre_save.connect(_set_seqn_pre_save, sender=RelayLog)


class Config(models.Model):
  def __str__(self):
    return '%s=%s' % (self.key, self.value)

  site = models.ForeignKey(KegbotSite, related_name='configs')
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
  site = models.ForeignKey(KegbotSite)
  date = models.DateTimeField(default=datetime.datetime.now)
  stats = fields.JSONField()

  def Update(self, drink, force=False):
    previous = self.stats
    if force:
      previous = None
    builder = self.STATS_BUILDER(drink, previous)
    self.stats = builder.Build()
    self.save()


class SystemStats(_StatsModel):
  STATS_BUILDER = stats.SystemStatsBuilder

  def __str__(self):
    return 'SystemStats for %s' % self.site


class UserStats(_StatsModel):
  STATS_BUILDER = stats.DrinkerStatsBuilder
  user = models.ForeignKey(User, unique=True, related_name='stats')

  def __str__(self):
    return 'UserStats for %s' % self.user


class SystemEvent(models.Model):
  class Meta:
    ordering = ('-when', '-id')
    get_latest_by = 'when'

  KINDS = (
      ('drink_poured', 'Drink poured'),
      ('session_started', 'Session started'),
      ('session_joined', 'User joined session'),
      ('keg_tapped', 'Keg tapped'),
      ('keg_ended', 'Keg ended'),
  )

  site = models.ForeignKey(KegbotSite, related_name='events')
  seqn = models.PositiveIntegerField(editable=False)
  kind = models.CharField(max_length=255, choices=KINDS,
      help_text='Type of event.')
  when = models.DateTimeField(help_text='Time of the event.')
  user = models.ForeignKey(User, blank=True, null=True,
      related_name='events',
      help_text='User responsible for the event, if any.')
  drink = models.ForeignKey(Drink, blank=True, null=True,
      related_name='events',
      help_text='Drink involved in the event, if any.')
  keg = models.ForeignKey(Keg, blank=True, null=True,
      related_name='events',
      help_text='Keg involved in the event, if any.')
  session = models.ForeignKey(DrinkingSession, blank=True, null=True,
      related_name='events',
      help_text='Session involved in the event, if any.')

  def __str__(self):
    if self.kind == 'drink_poured':
      ret = 'Drink %i poured' % self.drink.seqn
    elif self.kind == 'session_started':
      ret = 'Session %i started by drink %i' % (self.session.seqn,
          self.drink.seqn)
    elif self.kind == 'session_joined':
      ret = 'Session %i joined by %s (drink %i)' % (self.session.seqn,
          self.user.username, self.drink.seqn)
    elif self.kind == 'keg_tapped':
      ret = 'Keg %i tapped' % self.keg.seqn
    elif self.kind == 'keg_ended':
      ret = 'Keg %i ended' % self.keg.seqn
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
  def ProcessDrink(cls, drink):
    keg = drink.keg
    session = drink.session
    site = drink.site
    user = drink.user

    if keg:
      q = keg.events.filter(kind='keg_tapped')
      if q.count() == 0:
        e = keg.events.create(site=site, kind='keg_tapped', when=drink.starttime,
            keg=keg, user=user, drink=drink, session=session)
        e.save()

    if session:
      q = session.events.filter(kind='session_started')
      if q.count() == 0:
        e = session.events.create(site=site, kind='session_started',
            when=session.starttime, drink=drink, user=user)
        e.save()

    if user:
      q = user.events.filter(kind='session_joined', session=session)
      if q.count() == 0:
        e = user.events.create(site=site, kind='session_joined',
            when=drink.starttime, session=session, drink=drink, user=user)
        e.save()

    q = drink.events.filter(kind='drink_poured')
    if q.count() == 0:
      e = drink.events.create(site=site, kind='drink_poured',
          when=drink.starttime, drink=drink, user=user, keg=keg,
          session=session)
      e.save()

pre_save.connect(_set_seqn_pre_save, sender=SystemEvent)
