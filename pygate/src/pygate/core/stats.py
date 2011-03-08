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

"""Methods to generate cached statistics from entries."""

import copy
import inspect
import itertools
import logging

class StatsBuilder:
  def __init__(self, entry, previous=None):
    self._entry = entry
    self._logger = logging.getLogger('stats-builder')

    if previous is None:
      previous = {}
    self._previous = previous

    prev_seqn = self._previous.get('_seqn', -1)
    prev_revision = self._previous.get('_revision', -1)

    if prev_seqn == entry.seqn:
      # Skip if asked to regenerate same stats.
      self._logger.debug('skipping: same seqn')
      return
    elif prev_revision != self.REVISION:
      # Invalidate previous stats if builder revisions have changed.
      self._logger.debug('invalidating: older revision')
      self._previous = {}

  def _AllEntries(self):
    raise NotImplementedError

  def _AllStats(self):
    for name, cls in inspect.getmembers(self, inspect.isclass):
      if hasattr(cls, 'STAT_NAME'):
        yield (cls.STAT_NAME, cls)

  def Build(self):
    entries = self._AllEntries()
    result = copy.deepcopy(self._previous)
    for statname, cls in self._AllStats():
      o = cls()
      if statname not in result:
        self._logger.debug('+++ %s (FULL)' % statname)
        result[statname] = o.Full(entries)
      else:
        self._logger.debug('+++ %s (partial)' % statname)
        result[statname] = o.Incremental(self._entry, result[statname])

    result['_revision'] = self.REVISION
    result['_seqn'] = self._entry.seqn
    return result


class Stat:
  def __init__(self):
    pass
  def Full(self, entries):
    raise NotImplementedError
  def Incremental(self, entry, previous):
    raise NotImplementedError


class BaseStatsBuilder(StatsBuilder):
  """Builder which generates a variety of stats from object information."""

  class TotalEntries(Stat):
    STAT_NAME = 'total_count'
    def Full(self, entries):
      return entries.count()
    def Incremental(self, entry, previous):
      return previous + 1

  class EntriesByDayOfweek(Stat):
    STAT_NAME = 'entry_by_day_of_week'
    def Full(self, entries):
      # Note: uses the session's starttime, rather than the drink's. This causes
      # late-night sessions to be reported for the day on which they were
      # started.
      entrymap = dict((str(i), 0) for i in xrange(7))
      for entry in entries:
        weekday = str(entry.starttime.weekday())
        entrymap[weekday] += 1
      return entrymap
    def Incremental(self, entry, previous):
      weekday = str(entry.starttime.weekday())
      previous[weekday] += 1
      return previous

  class EntryByUser(Stat):
    STAT_NAME = 'entry_by_user'
    def Full(self, entries):
      entrymap = {}
      for entry in entries:
        if entry.user:
          u = entry.user.username
        else:
          u = None
        entrymap[u] = entrymap.get(u, 0) + 1
      return entrymap
    def Incremental(self, entry, previous):
      if entry.user:
        u = entry.user.username
      else:
        u = None
      previous[u] = previous.get(u, 0) + 1
      return previous

  class Users(Stat):
    STAT_NAME = 'users'
    def Full(self, entries):
      users = set()
      for entry in entries:
        u = None
        if entry.user:
          u = entry.user.username
        if u not in users:
          users.add(u)
      return list(users)
    def Incremental(self, entry, previous):
      u = None
      if entry.user:
        u = entry.user.username
      if u not in previous:
        previous.append(u)
      return previous

  class RegisteredUsers(Stat):
    STAT_NAME = 'registered_users'
    def Full(self, entries):
      users = set()
      for entry in entries:
        if entry.user and entry.user.username not in users:
          users.add(entry.user.username)
      return list(users)
    def Incremental(self, entry, previous):
      if entry.user and entry.user.username not in previous:
        previous.append(entry.user.username)
      return previous


class SystemStatsBuilder(BaseStatsBuilder):
  """Builder of systemwide stats by drink."""
  REVISION = 1

  def _AllEntries(self):
    qs = self._entry.site.entries.valid().filter(seqn__lte=self._entry.seqn)
    qs = qs.order_by('seqn')
    return qs


class UserStatsBuilder(SystemStatsBuilder):
  """Builder of user-specific stats by drink."""
  REVISION = 1

  def _AllEntries(self):
    qs = SystemStatsBuilder._AllEntries(self)
    qs = qs.filter(user=self._entry.user)
    return qs


class KegStatsBuilder(SystemStatsBuilder):
  """Builder of keg-specific stats."""
  REVISION = 5

  def _AllDrinks(self):
    qs = SystemStatsBuilder._AllDrinks(self)
    qs = qs.filter(keg=self._entry.keg)
    return qs


class SessionStatsBuilder(SystemStatsBuilder):
  """Builder of user-specific stats by drink."""
  REVISION = 5

  def _AllDrinks(self):
    qs = SystemStatsBuilder._AllDrinks(self)
    qs = qs.filter(session=self._entry.session)
    return qs


def main():
  from pygate.core import models
  last_entry = models.Entry.objects.valid().order_by('-seqn')[0]
  builder = KegStatsBuilder(last_entry)

  print "building..."
  stats = builder.Build()
  print "done"
  print stats

  if False:
    for user in models.User.objects.all():
      last_entry = user.entries.valid().order_by('-starttime')
      if not last_entry:
        continue
      last_entry = last_entry[0]
      builder = DrinkerStatsBuilder()
      stats = builder.Build(last_entry)
      print '-'*72
      print 'stats for %s' % user
      for k, v in stats.iteritems():
        print '   %s: %s' % (k, v)
      print ''

if __name__ == '__main__':
  import cProfile
  command = """main()"""
  cProfile.runctx( command, globals(), locals(), filename="stats.profile" )

