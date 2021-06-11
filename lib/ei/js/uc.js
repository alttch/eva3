/*
 * Author: Altertech Group, https://www.altertech.com/
 * Copyright: (C) 2012-2021 Altertech Group
 * License: Apache License 2.0
 * Version: 3.4.0
 */

var items = new Object();
var as_labels = new Object();
var master = false;
var units_loaded = false;
var sensors_loaded = false;
var log_loaded = false;
var log_subscribed = false;
var sensor_first_load = true;
var log_first_load = true;
var log_level = 20;
var log_autoscroll = true;
var page = '';
var toolmenu_opened = false;
var max_log_records = 100;
var debug_mode = false;

// array to keep entries while JSON log is being read and parsed
// entries then are added to log viewer
var lr2p = new Array();

var toolbars = ['blank', 'units', 'sensors', 'log'];
var boards = ['blank', 'keyform', 'units', 'sensors', 'log'];

function show_toolbar(name) {
  $.each(toolbars, function(n, v) {
    if (v != name) $('#toolbar_' + v).hide();
  });
  $('#toolbar_' + name).show();
}

function show_board(name) {
  $.each(boards, function(n, v) {
    if (v != name) $('#b_' + v).hide();
  });
  $('#b_' + name).show();
}

function btn_action(oid, s) {
  var btn = $('[id="btn_' + escape_oid(oid) + '_' + s + '"]');
  btn.attr('disabled', 'disabled');
  btn.addClass('disabled');
  $.getJSON(
    '/uc-api/action?k=' + apikey + '&i=' + oid + '&s=' + s + '&w=120',
    function(data) {
      if (data.status == 'completed') {
        $('button[id^=btn_' + escape_oid(oid) + '_]').removeClass('active');
        btn.removeAttr('disabled');
        btn.removeClass('disabled');
        btn.addClass('active');
      } else {
        var r = 'error';
        if (data.status == 'running') {
          r = 'confirm';
        }
        popup(r, 'ACTION RESULT', 'Action result: ' + data.status);
        btn.removeAttr('disabled');
        btn.removeClass('disabled');
      }
    }
  );
}

function ask_kill(oid) {
  popup(
    'confirm',
    'KILL ' + oid,
    'Terminate ALL running<br />and queued actions?',
    'YES',
    'NO',
    'kill_unit("' + oid + '")',
    ''
  );
}

function kill_unit(oid) {
  $.getJSON('/uc-api/kill?k=' + apikey + '&i=' + oid, function(data) {
    if (data && data.result == 'OK') {
      var msg = 'All actions of ' + oid + ' killed';
      var title = 'KILLED ' + oid;
      var popt = 'info';
      if ('pt' in data && data.pt == 'denied') {
        msg =
          'Current action can not be terminated<br />' +
          'because action_allow_termination<br /> is false';
        title = 'WARNING';
        popt = 'warning';
      }
      popup(popt, title, msg + '.<br /><br /> Action queue cleared.');
    } else {
      popup(
        'error',
        'ERROR',
        'Kill command failed for ' + oid + '. Result: ' + data.result
      );
    }
  }).fail(function() {
    popup('error', 'ERROR', 'Server error');
  });
}

function enable_disable_actions(oid, e) {
  $.getJSON('/uc-api/' + e + '_actions?k=' + apikey + '&i=' + oid, function(
    data
  ) {
    if (data && data.result == 'OK') {
      items[oid].action_enabled = e == 'enable' ? true : false;
      redraw_unit(oid);
    } else {
      popup('error', 'ERROR', 'Parameter not changed. Result: ' + data.result);
    }
  }).fail(function() {
    popup('error', 'ERROR', 'Server error');
  });
}

// redraw unit buttons
function redraw_unit(oid) {
  eoid = escape_oid(oid);
  $('button[id^=btn_' + eoid + '_]').removeClass('active');
  $('[id="btn_' + eoid + '_' + items[oid].status + '"]').addClass('active');
  if (items[oid].status != -1) {
    $('[id="uname_' + eoid + '"]').removeClass('device-error');
  } else {
    $('[id="uname_' + eoid + '"]').addClass('device-error');
  }
  var eb = $('[id="btn_enable_' + eoid + '"]');
  if (items[oid].action_enabled) {
    eb.html('ENABLED');
    eb.addClass('active');
    eb.attr('onclick', 'enable_disable_actions("' + oid + '", "disable")');
    $('button[id^=btn_' + eoid + '_]').removeAttr('disabled');
  } else {
    eb.html('DISABLED');
    eb.removeClass('active');
    eb.attr('onclick', 'enable_disable_actions("' + oid + '", "enable")');
    $('button[id^=btn_' + eoid + '_]').attr('disabled', 'disabled');
  }
}

// reload sysinfo
function load_sys_info() {
  if (!apikey) return;
  if (ws_mode && ws !== null) ws.send(JSON.stringify({s: 'ping'}));
  $.getJSON('/uc-api/test?k=' + apikey, function(data) {
    if ('debug' in data && data.debug != debug_mode) {
      debug_mode = data.debug;
      show_debug_info();
      if ('db_update' in data) {
        show_db_save(data.db_update);
      }
      if ('polldelay' in data) {
        $('#i_polldelay').html(', poll delay: ' + data.polldelay + 's');
      }
    }
  });
}

function load_unit_state() {
  if (!apikey) return;
  if (!units_loaded) {
    return;
  }
  $.getJSON(
    '/uc-api/state?k=' + apikey + '&g=' + $('#s_unit_group').val() + '&p=U',
    function(data) {
      $.each(data, function(_k) {
        var val = data[_k];
        var oid = data[_k]['oid'];
        if (!(oid in items)) {
          load_unit_data();
          return;
        }
        if (
          items[oid].status != val.status ||
          items[oid].action_enabled != val.action_enabled
        ) {
          items[oid] = val;
          redraw_unit(oid);
        }
      });
    }
  );
}

function load_sensor_state() {
  if (!apikey) return;
  if (!sensors_loaded) {
    return;
  }
  $.getJSON(
    '/uc-api/state?k=' + apikey + '&g=' + $('#s_sensor_group').val() + '&p=S',
    function(data) {
      $.each(data, function(_k) {
        var val = data[_k];
        var oid = data[_k]['oid'];
        if (!(oid in items)) {
          load_sensor_data();
          return;
        }
        if (items[oid].status != val.status || items[oid].value != val.value) {
          items[oid] = val;
          redraw_sensor_state(oid);
        }
      });
    }
  );
}

function load_unit_data() {
  if (!apikey) return;
  if (page == 'units') {
    show_board('units');
    load_animation('b_units');
  }
  $.getJSON('/uc-api/groups?k=' + apikey + '&p=U', function(data) {
    $('#s_unit_group')
      .find('option')
      .remove()
      .end();
    $('#s_unit_group').show();
    var ng = false;
    var gf = false;
    $.each(data, function(uid, val) {
      if (val != 'nogroup') {
        $('#s_unit_group').append('<option>' + val + '</option');
        gf = true;
      } else {
        ng = true;
      }
    });
    if (ng) {
      $('#s_unit_group').append('<option value="nogroup">no group</option');
    }
    if (gf || ng) {
      if (page == 'units') show_toolbar('units');
      load_units();
    } else {
      $('#s_unit_group').hide();
      $('#b_units').html('<div class="notavail">No units available</div>');
    }
  });
}

function load_sensor_data() {
  if (!apikey) return;
  if (page == 'sensors') {
    show_board('sensors');
    load_animation('b_sensors');
  }
  $.getJSON('/uc-api/groups?k=' + apikey + '&p=S', function(data) {
    $('#s_sensor_group')
      .find('option')
      .remove()
      .end();
    $('#s_sensor_group').show();
    var ng = false;
    var gf = false;
    $.each(data, function(uid, val) {
      if (val != 'nogroup') {
        $('#s_sensor_group').append('<option>' + val + '</option');
        gf = true;
      } else {
        ng = true;
      }
    });
    if (ng) {
      $('#s_sensor_group').append('<option value="nogroup">no group</option');
    }
    if (gf || ng) {
      if (page == 'sensors') show_toolbar('sensors');
      load_sensors();
    } else {
      $('#s_sensor_group').hide();
      $('#b_sensors').html('<div class="notavail">No sensors available</div>');
    }
  });
}

function update_unit_state(oid) {
  var s = $('#unit_status').val();
  var v = $('#unit_value').val();
  $.getJSON(
    '/uc-api/update?k=' + apikey + '&i=' + oid + '&s=' + s + '&v=' + v,
    function(data) {
      if (data && data.result == 'OK') {
        items[oid].status = s;
        items[oid].value = v;
        redraw_unit(oid);
      } else {
        popup(
          'error',
          'ERROR',
          'Unit state not changed. Result: ' + data.result
        );
      }
    }
  ).fail(function() {
    popup('error', 'ERROR', 'Server error');
  });
}

function select_unit_state(oid) {
  var html =
    '<form class="form-horizontal">' +
    '<div class="form-group">' +
    '<label class="col-xs-6 control-label"' +
    ' for="unit_status">Status</label>' +
    '<div class="col-xs-6">' +
    '<select class="form-control" id="unit_status">';
  $.each(as_labels[oid], function(_k, v) {
    html += '<option value="' + _k + '"';
    if (_k == items[oid].status) html += ' selected';
    html += '>' + v + '</option>';
  });
  var val = items[oid].value;
  if (val == '') val = '';
  html +=
    '</select></div></div>' +
    '<div class="form-group">' +
    '<label class="col-xs-6 control-label"' +
    ' for="unit_value">Value</label>' +
    '<div class="col-xs-6">' +
    '<input class="form-control" type="text" size="5"' +
    'id="unit_value" value="' +
    val +
    '" /></div></div></form>';
  popup(
    'confirm',
    'SET STATE OF ' + oid,
    html,
    'SET',
    'CANCEL',
    'update_unit_state("' + oid + '")'
  );
  $('#unit_status').focus();
}

function reload_units() {
  load_unit_data();
}

function load_units() {
  $.getJSON(
    '/uc-api/state?k=' +
      apikey +
      '&full=1&g=' +
      $('#s_unit_group').val() +
      '&p=U',
    function(data) {
      var bg = 1;
      $('#b_units').html('');
      $.each(Object(data).sort(dynamic_sort('id')), function(_k) {
        var uid = data[_k]['id'];
        var oid = data[_k]['oid'];
        var eoid = escape_oid(oid);
        var val = data[_k];
        _unit = $('<div />', {
          class: 'col-md-5 col-sm-8 col-xs-2btn col-xs-12'
        });
        _unit_actions = $('<div />', {
          class: 'col-md-3 col-sm-2 col-xs-btn col-xs-12'
        });
        items[oid] = val;
        as_labels[oid] = new Object();
        $.each(data[_k].status_labels, function(_i, _s) {
          var st = parseInt(_s.status);
          var lb = _s.label;
          as_labels[oid][st] = lb;
          $('<button />', {
            class: 'st0' + (val.status == st ? ' active' : ''),
            id: 'btn_' + eoid + '_' + st,
            html: lb
          })
            .click(function() {
              btn_action(oid, st);
            })
            .appendTo(_unit_actions);
        });
        _unit_buttons = $('<div />', {
          class: 'col-md-4 col-sm-2 col-xs-btn col-xs-12'
        });
        if (val.action_enabled) {
          $('<button />', {
            class: 'st0 active',
            id: 'btn_enable_' + eoid,
            html: 'ENABLED'
          })
            .attr('onclick', 'enable_disable_actions("' + oid + '", "disable")')
            .appendTo(_unit_buttons);
        } else {
          $('<button />', {
            class: 'st0',
            id: 'btn_enable_' + eoid,
            html: 'DISABLED'
          })
            .attr('onclick', 'enable_disable_actions("' + oid + '", "enable")')
            .appendTo(_unit_buttons);
        }
        $('<button />', {
          class: 'st0',
          html: 'SET'
        })
          .attr('onclick', 'select_unit_state("' + oid + '")')
          .appendTo(_unit_buttons);
        $('<button />', {
          class: 'st0',
          html: 'KILL'
        })
          .attr('onclick', 'ask_kill("' + oid + '")')
          .appendTo(_unit_buttons);
        var _r = $('<div />', {class: 'row row-device bg' + bg});
        var iname = uid;
        $('<div />', {
          class: 'device' + (val.status == -1 ? ' device-error' : ''),
          id: 'uname_' + oid,
          html: iname
        }).appendTo(_unit);
        $('<div />', {
          class: 'device-descr',
          html: val['description']
        }).appendTo(_unit);
        _unit.appendTo(_r);
        _unit_actions.appendTo(_r);
        _unit_buttons.appendTo(_r);
        _r.appendTo('#b_units');
        if (!val.action_enabled) {
          $('button[id^=btn_' + eoid + '_]').attr('disabled', 'disabled');
        }
        if (bg == 1) bg = 0;
        else bg = 1;
      });
      units_loaded = true;
    }
  );
}

function set_sensor_status(i, st) {
  $.getJSON('/uc-api/update?k=' + apikey + '&i=' + i + '&s=' + st, function(
    data
  ) {
    if (data && data.result == 'OK') {
      items[i].status = st;
      redraw_sensor_state(i);
    } else {
      popup(
        'error',
        'ERROR',
        'Sensor status not changed. Result: ' + data.result
      );
    }
  }).fail(function() {
    popup('error', 'ERROR', 'Server error');
  });
}

function reload_sensors() {
  load_sensor_data();
}

function load_sensors() {
  $.getJSON(
    '/uc-api/state?k=' +
      apikey +
      '&full=1&g=' +
      $('#s_sensor_group').val() +
      '&p=S',
    function(data) {
      var bg = 1;
      $('#b_sensors').html('');
      $.each(Object(data).sort(dynamic_sort('id')), function(_k) {
        var uid = data[_k]['id'];
        var oid = data[_k]['oid'];
        var eoid = escape_oid(oid);
        var val = data[_k];
        items[oid] = val;
        _sensor = $('<div />', {class: 'col-sm-7 col-xs-2btn col-xs-12'});
        _sensor_state = $('<div />', {class: 'col-sm-3 col-xs-btn col-xs-12'});
        $('<span />', {
          id: 'sval_' + eoid,
          class: 'sval',
          html: val.value
        }).appendTo(_sensor_state);
        _sensor_buttons = $('<div />', {
          class: 'col-sm-2 col-xs-btn col-xs-12',
          style: 'text-align:center;'
        });
        $('<button />', {
          id: 'btn_s_enable_' + eoid,
          class: 'st0' + (val.status == 0 ? '' : ' active'),
          onclick:
            'set_sensor_status("' +
            oid +
            '", ' +
            (val.status == 0 ? 1 : 0) +
            ')',
          html: val.status == 0 ? 'DISABLED' : 'ENABLED'
        }).appendTo(_sensor_buttons);
        var _r = $('<div />', {class: 'row row-device bg' + bg});
        var iname = uid;
        $('<div />', {
          id: 'sname_' + eoid,
          class: 'device sensor_s' + val.status,
          html: iname
        }).appendTo(_sensor);
        $('<div />', {
          class: 'device-descr',
          html: val['description']
        }).appendTo(_sensor);
        _sensor.appendTo(_r);
        _sensor_state.appendTo(_r);
        _sensor_buttons.appendTo(_r);
        _r.appendTo('#b_sensors');
        if (bg == 1) bg = 0;
        else bg = 1;
      });
      sensors_loaded = true;
    }
  );
}

function redraw_sensor_state(i) {
  for (a = -1; a <= 1; a++) {
    if (items[i].status != a) {
      $('[id="sname_' + escape_oid(i) + '"]').removeClass('sensor_s' + a);
    } else {
      $('[id="sname_' + escape_oid(i) + '"]').addClass('sensor_s' + a);
    }
  }
  $('[id="sval_' + escape_oid(i) + '"]').html(items[i].value);
  var b = $('[id="btn_s_enable_' + escape_oid(i) + '"]');
  if (items[i].status == 0) {
    b.removeClass('active');
    b.attr('onclick', 'set_sensor_status("' + i + '", 1)');
    b.html('DISABLED');
  } else {
    b.addClass('active');
    b.attr('onclick', 'set_sensor_status("' + i + '", 0)');
    b.html('ENABLED');
  }
}

function process_ws(evt) {
  var data = JSON.parse(evt.data);
  if (data.s == 'state') {
    $.each(data.d, function(i, s) {
      i = s.oid;
      p = s.type;
      if (i in items) {
        if (p == 'unit') {
          if (s.status == s.nstatus && s.value == s.nvalue) {
            items[i] = s;
            redraw_unit(i);
          }
        }
        if (p == 'sensor') {
          items[i] = s;
          redraw_sensor_state(i);
        }
      }
    });
  }
  if (data.s == 'log') {
    $.each(data.d, function(i, l) {
      append_log_entry(log_record(l));
    });
    if (log_autoscroll) {
      $('#logr').scrollTop($('#logr').prop('scrollHeight'));
    }
  }
}

function start_ws(reload) {
  if (!apikey) return;
  var loc = window.location,
    uri;
  if (loc.protocol === 'https:') {
    uri = 'wss:';
  } else {
    uri = 'ws:';
  }
  uri += '//' + loc.host;
  ws = new WebSocket(uri + '/ws?k=' + apikey);
  ws.onmessage = function(evt) {
    process_ws(evt);
  };
  ws.onclose = function() {
    $('#i_connection').html(
      '<b><span style="color: red">' + 'WS connecting' + '</span></b>'
    );
    log_first_load = true;
    sensor_first_load = true;
    units_loaded = false;
    sensors_loaded = false;
    log_loaded = false;
    setTimeout(function() {
      start_ws(true);
    }, 3000);
  };
  ws.addEventListener('open', function(event) {
    $('#i_connection').html('<b><span style="color: green">instant</span></b>');
    ws.send(JSON.stringify({s: 'state'}));
    if (log_subscribed) {
      ws.send(JSON.stringify({s: 'log'}));
    }
    if (reload) {
      log_first_load = true;
      login(apikey, false, false, true);
    }
  });
}

function init_dashboard(reload) {
  $('#sysinfo').show();
  show_toolbar('blank');
  $('#controls').show();
  $('#version_info').show();
  if (!reload) {
    items = new Object();
    show_units();
  } else {
    if (page == 'log') show_log();
    if (page == 'sensors') show_sensors();
  }
  if (ws_mode) {
    if (!reload) {
      $('#i_connection').html(
        '<b><span style="color: red">' + 'WS connecting' + '</span></b>'
      );
      start_ws(false);
    }
    load_unit_data();
  } else {
    $('#i_connection').html(
      '<b><span style="color: orange">' +
        jrInterval / 1000 +
        ' sec' +
        '</span></b>'
    );
    if (!reload) {
      setInterval(load_unit_state, jrInterval);
      setInterval(load_sensor_state, jrInterval);
    }
    load_unit_data();
  }
}

function set_debug_mode(mode) {
  $.getJSON(
    '/sys-api/set_debug?k=' + apikey + '&debug=' + (mode ? '1' : '0'),
    function(data) {
      if (data && data.result == 'OK') {
        debug_mode = !debug_mode;
        show_debug_info();
        popup(
          'info',
          'DEBUG',
          'Debug mode is now ' + (debug_mode ? 'enabled' : 'disabled')
        );
      } else {
        popup(
          'error',
          'ERROR',
          'Debug mode not changed<br />Result: ' + data.result
        );
      }
    }
  ).fail(function() {
    popup('error', 'ERROR', 'Server error');
  });
}

function save() {
  $.getJSON('/sys-api/save?k=' + apikey, function(data) {
    if (data && data.result == 'OK') {
      popup('info', 'UPDATED', 'System data updated successfully');
    } else {
      popup(
        'error',
        'ERROR',
        'Unable to update system data<br />Result: ' + data.result
      );
    }
  }).fail(function(data) {
    if (data.status == 403) {
      invalid_api_key();
      return;
    }
    popup('error', 'ERROR', 'Unable to update system data<br />UNKNOWN ERROR');
  });
}

function show_debug_info(d) {
  if (debug_mode) {
    $('#i_debug')
      .css('color', 'orange')
      .css('font-weight', 'bold')
      .html('Debug mode: ON');
    if (master) {
      $('#i_debug')
        .css('cursor', 'pointer')
        .attr('onclick', 'set_debug_mode(false)');
    }
  } else {
    $('#i_debug')
      .css('color', '#4D4D4D')
      .css('font-weight', 'normal')
      .html('Debug mode: OFF');
    if (master) {
      $('#i_debug')
        .css('cursor', 'pointer')
        .attr('onclick', 'set_debug_mode(true)');
    }
  }
}

function show_db_save(mode) {
  if (mode == 1) {
    $('#i_dbsave').html(', db updates: instant');
  } else if (mode == 2) {
    $('#i_dbsave').html(', db updates: on exit');
  } else {
    $('#i_dbsave').html(', db updates: on request');
  }
}

function disable_sys_func() {
  $('#tbtn_log')
    .addClass('disabled')
    .attr('onclick', null);
  $('#tbtn_save')
    .addClass('disabled')
    .attr('onclick', null);
}

function enable_sys_func() {
  $('#tbtn_log')
    .removeClass('disabled')
    .attr('onclick', 'safe_close_tool_menu();show_log()');
  $('#tbtn_save')
    .removeClass('disabled')
    .attr('onclick', 'safe_close_tool_menu();save()');
}

function login(k, remember_k, initial, reload) {
  if (initial) {
    show_board('blank');
    load_animation('b_blank');
  }
  $.getJSON('/uc-api/test?k=' + k, function(data) {
    apikey = k;
    if (initial && !reload) {
      if (remember_k) {
        create_cookie('apikey', k, 365 * 20, '/uc-ei/');
      } else {
        erase_cookie('apikey', '/uc-ei/');
      }
    }
    $('#i_system').html('<b>' + data.system + '</b>');
    document.title = data.system + ' UC EI';
    master = data.acl.master;
    $('#i_key').html('<b>' + data.acl.key_id + '</b>');
    var setup_mode = '';
    if ('setup_mode' in data && data.setup_mode) {
      setup_mode = ' <b><span style="color: red">' + ' [SETUP MODE]</span>';
    }
    $('#i_master').html(
      (data.acl.master ? '<font color="red"><b>yes</b></font>' : 'no') +
        setup_mode
    );
    $('#i_version').html(data.version);
    var dev = '';
    if ('development' in data && data.development) {
      dev = ' <b><span style="color: red">' + 'DEVELOPMENT MODE</span>';
    }
    $('#i_build').html(data.product_build + dev);
    if ('debug' in data) {
      $('#i_sysinfo').show();
      debug_mode = data.debug;
      if (initial && debug_mode) {
        log_level = 10;
        $('#s_log_level').val(10);
      }
      show_debug_info();
    }
    if ('db_update' in data) {
      show_db_save(data.db_update);
    }
    if ('polldelay' in data) {
      $('#i_polldelay').html(', poll delay: ' + data.polldelay + 's');
    }
    if (initial || reload) {
      if (data.acl.master || ('sysfunc' in data.acl && data.acl.sysfunc)) {
        enable_sys_func();
      } else {
        disable_sys_func();
      }
      init_dashboard(reload);
    }
  }).error(function(data) {
    if (data.status == 403) {
      invalid_api_key();
      return;
    }
    popup('error', 'UNABLE TO LOGIN', 'UNKNOWN ERROR');
  });
}

function invalid_api_key() {
  popup(
    'error',
    'ACCESS DENIED',
    'INVALID API KEY',
    'OK',
    '',
    'show_login_form()',
    ''
  );
}

function show_units() {
  page = 'units';
  show_board('units');
  show_toolbar('units');
}

function show_sensors() {
  page = 'sensors';
  show_board('sensors');
  show_toolbar('sensors');
  if (!sensors_loaded) {
    load_sensor_data();
  }
}

function show_login_form() {
  try {
    ws.onclose = null;
    ws.send(JSON.stringify({s: 'bye'}));
    ws.close();
  } catch (err) {}
  sensor_first_load = true;
  log_first_load = true;
  units_loaded = false;
  sensors_loaded = false;
  log_loaded = false;
  $('#keyform').html('');
  $('#b_units').html('');
  $('#logr').html('');
  $('#i_debug').html('');
  $('#i_dbsave').html('');
  $('#i_polldelay').html('');
  $('#sysinfo').hide();
  $('#i_sysinfo').hide();
  $('#controls').hide();
  $('#version_info').hide();
  apikey = '';
  $('#apikey').val('');
  show_board('keyform');
  var form =
    '<div>' +
    '<input class="st0 input" type="password" ' +
    'id="apikey" placeholder="API KEY" />' +
    '</div>' +
    '<div style="width: 150px; margin-right: 60px">' +
    '<input class="chBox" type="checkbox" ' +
    'onchange="perform_login()" id="apikey_remember" value="true">' +
    '<label class="chk-settings" for="apikey_remember">' +
    'remember API key</label>' +
    '</div>';
  $('#keyform').append(form);
  $('#apikey').on('keydown', function(e) {
    if (e.which == 13) {
      perform_login();
      e.preventDefault();
    }
  });
  $('#apikey').focus();
}

function perform_login() {
  var k = $('#apikey').val();
  var keep = $('#apikey_remember').is(':checked');
  $('#keyform').html('');
  login(k, keep, true, false);
}

function logout() {
  safe_close_tool_menu();
  erase_cookie('apikey', '/uc-ei/');
  show_login_form();
}

setInterval(load_sys_info, srInterval);
