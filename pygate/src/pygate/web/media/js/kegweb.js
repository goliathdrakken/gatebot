/**
 * Copyright 2011 Mike Wakerly <opensource@hoho.com>
 *
 * This file is part of the Pykeg package of the Kegbot project.
 * For more information on Pykeg or Kegbot, see http://kegbot.org/
 *
 * Pykeg is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * Pykeg is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Pykeg.  If not, see <http://www.gnu.org/licenses/>.
 */

//
// gateweb namespace setup
//

var gateweb = {};

// API Endpoints.
gateweb.API_BASE = '/api/';
gateweb.API_GET_EVENTS = 'event/';
gateweb.API_GET_EVENTS_HTML = 'event/html/';

// Misc globals.
gateweb.lastEventId = -1;
gateweb.eventsLoaded = false;

//
// gateweb functions.
//

/**
 * Based gateweb onReady function, called when any gateweb page is loaded.
 */
gateweb.onReady = function() {
  gateweb.refreshCallback();
  setInterval(gateweb.refreshCallback, 10000);
};

/**
 * Fetches the latest events in pre-processed HTML format.
 *
 * @param {function(Array)} callback A callback function to process the events.
 * @param {number} since Fetch only events that are newer than this event id.
 */
gateweb.getEventsHtml = function(callback, since) {
  var url = gateweb.API_BASE + gateweb.API_GET_EVENTS_HTML;
  if (since) {
    url += '?since=' + since;
  }
  $.getJSON(url, function(data) {
    if (data['result'] && data['result']['events']) {
      callback(data['result']['events']);
    }
  });
}

/**
 * Interval callback that will refresh all items on the page.
 */
gateweb.refreshCallback = function() {
  // Events table.
  if ($("#kb-recent-events")) {
    if (gateweb.lastEventId >= 0) {
      gateweb.getEventsHtml(gateweb.updateEventsTable, gateweb.lastEventId);
    } else {
      gateweb.getEventsHtml(gateweb.updateEventsTable);
    }
  }
}

/**
 * Updates the kb-recent-events table from a list of events.
 */
gateweb.updateEventsTable = function(events) {
  for (var rowId in events) {
    var row = events[rowId];
    var animate = gateweb.eventsLoaded;
    var eid = row['id'];
    if (eid > gateweb.lastEventId) {
      gateweb.lastEventId = eid;
    }

    var newDivName = 'kb-event-' + row['id'];
    var newDiv = '<div id="' + newDivName + '">';
    newDiv += row['html'];
    newDiv += '</div>';
    $('#kb-recent-events').prepend(newDiv);
    $('#' + newDivName).find("abbr.timeago").timeago();

    if (animate) {
      $('#' + newDivName).css("display", "none");
      $('#' + newDivName).css("background-color", "#ffc800");
      $('#' + newDivName).show("slide", { direction: 'up' }, 1000, function() {
          $('#' + newDivName).animate({ backgroundColor: "#ffffff" }, 1500);
      });
    }
  }
  if (!gateweb.eventsLoaded) {
    gateweb.eventsLoaded = true;
  }
}
