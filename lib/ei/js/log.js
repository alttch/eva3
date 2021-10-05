/*
 * Author: Altertech Group, https://www.altertech.com/
 * Copyright: (C) 2012-2021 Altertech Group
 * License: Apache License 2.0
 * Version: 3.4.2
 */

var log_level_name = {
  10: 'DEBUG',
  20: 'INFO',
  30: 'WARNING',
  40: 'ERROR',
  50: 'CRITICAL'
};

function load_log_entries(r, scroll) {
  if (apikey == '') return;
  if (ws_mode) lr2p = new Array();
  if (log_first_load) load_animation('logr');
  $.getJSON(
    '/sys-api/log_get?l=' +
      log_level +
      '&n=' +
      max_log_records +
      '&k=' +
      apikey,
    function(data) {
      if (ws_mode && log_first_load) {
        set_ws_log_level(log_level);
      }
      var _l = '';
      $.each(data, function(t, l) {
        _l = _l + log_record(l);
      });
      var t = $('#logr');
      t.html(_l);
      if (!log_loaded) {
        log_loaded = true;
        show_toolbar('log');
      }
      $.each(lr2p, function(i, v) {
        t.append(v);
      });
      if (scroll || log_autoscroll) t.scrollTop(t.prop('scrollHeight'));
      if ((!ws_mode && log_first_load) || r) {
        setTimeout(function() {
          load_log_entries(true, false);
        }, lrInterval);
      }
      if (log_first_load) {
        log_first_load = false;
      }
    }
  ).error(function(data) {
    if ((!ws_mode && log_first_load) || r) {
      setTimeout(function() {
        load_log_entries(true, false);
      }, lrInterval);
    }
  });
}

function toggle_log_as() {
  if (log_autoscroll) {
    $('#btn_log_as').removeClass('active');
    log_autoscroll = false;
  } else {
    $('#btn_log_as').addClass('active');
    log_autoscroll = true;
  }
}

function show_log() {
  page = 'log';
  show_board('log');
  if (!ws_mode || log_first_load) {
    log_loaded = false;
    show_toolbar('blank');
    load_log_entries(false, true);
  } else {
    show_toolbar('log');
    if (log_autoscroll) {
      $('#logr').scrollTop($('#logr').prop('scrollHeight'));
    }
  }
}

function set_ws_log_level(l) {
  if (ws_mode) ws.send(JSON.stringify({s: 'log', l: l}));
  log_subscribed = true;
}

function log_record(l) {
  return (
    '<div class="logentry logentry_color_' +
    l.l +
    '">' +
    time_converter(l.t) +
    ' ' +
    l.h +
    ' ' +
    l.p +
    ' ' +
    log_level_name[l.l] +
    ' ' +
    l.mod +
    ' ' +
    l.th +
    ': ' +
    l.msg +
    '</div>'
  );
}

function append_log_entry(l) {
  if (log_loaded) {
    $('#logr').append(l);
    while ($('.logentry').length > max_log_records) {
      $('#logr')
        .find('.logentry')
        .first()
        .remove();
    }
  } else {
    lr2p.push(l);
  }
}

function ask_debug_mode() {
  if (master && !debug_mode && log_level <= 10) {
    popup(
      'confirm',
      'Enable DEBUG',
      'Server is not in the DEBUG MODE<br />Enable DEBUG?',
      'YES',
      'NO',
      'set_debug_mode(true)',
      ''
    );
  }
}
