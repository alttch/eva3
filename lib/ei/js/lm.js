/*
 * Author: Altertech Group, https://www.altertech.com/
 * Copyright: (C) 2012-2021 Altertech Group
 * License: Apache License 2.0
 * Version: 3.4.2
 */

var items = new Object();
var dm_rules = new Object();
var master = false;
var lvars_loaded = false;
var macros_loaded = false;
var cycles_loaded = false;
var log_loaded = false;
var log_subscribed = false;
var log_first_load = true;
var log_level = 20;
var log_autoscroll = true;
var page = '';
var toolmenu_opened = false;
var max_log_records = 100;
var debug_mode = false;

var lvar_state_labels = {'-1': 'expired', '0': 'disabled', '1': 'enabled'};

var cycle_state_labels = {'2': 'stopping', '0': 'stopped', '1': 'running'};

var dm_rule_for_props = ['status', 'value', 'nstatus', 'nvalue'];

var dm_rule_item_types = ['#', 'unit', 'sensor', 'lvar'];

var dm_rule_for_initial = ['skip', 'only', 'any'];

var dm_rule_break = {'0': 'NO', '1': 'YES'};

var dm_rule_conditions = ['none', 'range', 'equals', 'set', 'expire'];

var tsdiff = 0;

// array to keep entries while JSON log is being read and parsed
// entries then are added to log viewer
var lr2p = new Array();

var toolbars = ['blank', 'lvars', 'macros', 'cycles', 'rules', 'log'];
var boards = ['blank', 'keyform', 'lvars', 'macros', 'cycles', 'rules', 'log'];

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

function reset_lvar(i) {
  $.getJSON('/lm-api/reset?k=' + apikey + '&i=' + i, function(data) {
    if (data && data.result == 'OK') {
    } else {
      popup('error', 'ERROR', 'Reset command failed for ' + i);
    }
  }).fail(function() {
    popup('error', 'ERROR', 'Server error. Reset command failed for ' + i);
  });
}

function reset_cycle_stats(i) {
  $.getJSON('/lm-api/reset_cycle_stats?k=' + apikey + '&i=' + i, function(
    data
  ) {
    if (data && data.result == 'OK') {
      redraw_cycle_state(i)
    } else {
      popup('error', 'ERROR', 'Reset stats command failed for<br />' + i);
    }
  }).fail(function() {
    popup(
      'error',
      'ERROR',
      'Server error. Reset stats command failed for<br />' + i
    );
  });
}

function start_cycle(i) {
  $.getJSON('/lm-api/start_cycle?k=' + apikey + '&i=' + i, function(data) {
    if (data && data.result == 'OK') {
      items[i].status = 1
      redraw_cycle_state(i)
    } else {
      popup('error', 'ERROR', 'Start command failed for<br />' + i);
    }
  }).fail(function() {
    popup('error', 'ERROR', 'Server error. Start command failed for<br />' + i);
  });
}

function stop_cycle(i) {
  $.getJSON('/lm-api/stop_cycle?k=' + apikey + '&i=' + i, function(data) {
    if (data && data.result == 'OK') {
      items[i].status = 0
      redraw_cycle_state(i)
    } else {
      popup('error', 'ERROR', 'Stop command failed for<br />' + i);
    }
  }).fail(function() {
    popup('error', 'ERROR', 'Server error. Stop command failed for<br />' + i);
  });
}

// reload sysinfo
function load_sys_info() {
  if (!apikey) return;
  if (ws_mode && ws !== null) ws.send(JSON.stringify({s: 'ping'}));
  $.getJSON('/lm-api/test?k=' + apikey, function(data) {
    tsdiff = new Date().getTime() / 1000 - data.time;
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

function redraw_lvar_state(i) {
  var eoid = escape_oid(i);
  for (a = -1; a <= 1; a++) {
    if (items[i].status != a) {
      $('[id="lname_' + eoid + '"]').removeClass('lvar_s' + a);
    } else {
      $('[id="lname_' + eoid + '"]').addClass('lvar_s' + a);
    }
  }
  $('[id="lval_' + eoid + '"]').html(items[i].value);
  var _e_label = '';
  var rb = $('[id="lval_rb_' + eoid + '"]');
  if (items[i].expires > 0) {
    _e_label = '<span class="hidden-xs">E: </span>';
    rb.show();
  } else {
    rb.hide();
  }
  $('[id="lval_expires_' + eoid + '"]').html(format_expire_time(items[i]));
  $('[id="lval_expires_e_' + eoid + '"]').html(_e_label);
}

function redraw_cycle_state(i) {
  var eoid = escape_oid(i);
  for (a = 0; a <= 2; a++) {
    if (items[i].status != a) {
      $('[id="cname_' + eoid + '"]').removeClass('cycle_s' + a);
    } else {
      $('[id="cname_' + eoid + '"]').addClass('cycle_s' + a);
    }
  }
  $('[id="cint_' + eoid + '"]').html(
    items[i].interval.toFixed(4) +
      '<br />-<br />' +
      parseFloat(items[i].avg).toFixed(4) +
      '<br />-<br />' +
    items[i].iterations
  );
  if (items[i].status != 0) {
    $('[id="cycle_startb_' + eoid + '"]')
      .addClass('disabled')
      .attr('onclick', null);
  } else {
    $('[id="cycle_startb_' + eoid + '"]')
      .removeClass('disabled')
      .attr('onclick', 'start_cycle("' + i + '")');
  }
}

function load_lvar_state() {
  if (!apikey) return;
  if (!lvars_loaded) {
    return;
  }
  $.getJSON(
    '/lm-api/state?k=' + apikey + '&g=' + $('#s_lvar_group').val(),
    function(data) {
      $.each(data, function(_k) {
        var val = data[_k];
        var oid = data[_k]['oid'];
        if (!(oid in items)) {
          load_lvar_data();
          return;
        }
        if (
          items[oid].status != val.status ||
          items[oid].value != val.value ||
          items[oid].set_time != val.set_time ||
          items[oid].expires != val.expires
        ) {
          items[oid] = val;
          redraw_lvar_state(oid);
        }
      });
    }
  );
}

function load_cycle_state() {
  if (!apikey) return;
  if (!cycles_loaded) {
    return;
  }
  $.getJSON(
    '/lm-api/list_cycles?k=' + apikey + '&g=' + $('#s_cycle_group').val(),
    function(data) {
      $.each(data, function(_k) {
        var val = data[_k];
        var oid = data[_k]['oid'];
        if (!(oid in items)) {
          load_cycle_data();
          return;
        }
        if (
          items[oid].status != val.status ||
          items[oid].value != val.value ||
          items[oid].interval != val.interval
        ) {
          items[oid] = val;
          redraw_cycle_state(oid);
        }
      });
    }
  );
}

function update_lvar_timers() {
  $.each(items, function(k, i) {
    if (i.status == 1 && i.value != '') {
      if (i.expires > 0) {
        $('[id="lval_expires_' + escape_oid(k) + '"]').html(
          format_expire_time(i)
        );
      }
    } else {
      e = $('[id="lval_expires_' + escape_oid(k) + '"]').html();
      if ($.isNumeric(e) && e > 0)
        $('[id="lval_expires_' + escape_oid(k) + '"]').html(
          Number(0).toFixed(1)
        );
    }
  });
}

function load_lvar_data() {
  if (!apikey) return;
  if (page == 'lvars') {
    show_board('lvars');
    load_animation('b_lvars');
  }
  $.getJSON('/lm-api/groups?k=' + apikey + '&p=LV', function(data) {
    $('#s_lvar_group')
      .find('option')
      .remove()
      .end();
    $('#s_lvar_group').show();
    var ng = false;
    var gf = false;
    $.each(data, function(uid, val) {
      if (val != 'nogroup') {
        $('#s_lvar_group').append('<option>' + val + '</option');
        gf = true;
      } else {
        ng = true;
      }
    });
    if (ng) {
      $('#s_lvar_group').append('<option value="nogroup">no group</option');
    }
    if (gf || ng) {
      if (page == 'lvars') show_toolbar('lvars');
      load_lvars();
    } else {
      $('#s_lvar_group').hide();
      $('#b_lvars').html('<div class="notavail">No LVars available</div>');
    }
  });
}

function load_cycle_data() {
  if (!apikey) return;
  if (page == 'cycles') {
    show_board('cycles');
    load_animation('b_cycles');
  }
  $.getJSON('/lm-api/groups_cycle?k=' + apikey, function(data) {
    $('#s_cycle_group')
      .find('option')
      .remove()
      .end();
    $('#s_cycle_group').show();
    var ng = false;
    var gf = false;
    $.each(data, function(uid, val) {
      if (val != 'nogroup') {
        $('#s_cycle_group').append('<option>' + val + '</option');
        gf = true;
      } else {
        ng = true;
      }
    });
    if (ng) {
      $('#s_cycle_group').append('<option value="nogroup">no group</option');
    }
    if (gf || ng) {
      if (page == 'cycles') show_toolbar('cycles');
      load_cycles();
    } else {
      $('#s_cycle_group').hide();
      $('#b_cycles').html('<div class="notavail">No cycles available</div>');
    }
  });
}

function update_rule_groups(groups) {
  var cur = $('#s_rule_group').val();
  $('#s_rule_group')
    .find('option')
    .remove()
    .end();
  $('#s_rule_group').show();
  $('#s_rule_group').append('<option>#:#</option');
  $.each(groups, function(i, v) {
    var o = $('<option />');
    o.html(v);
    if (v == cur) o.attr('selected', 'selected');
    $('#s_rule_group').append(o);
  });
}

function reload_macros() {
  load_macros_data();
}

function load_macros_data() {
  if (!apikey) return;
  if (page == 'macros') {
    show_board('macros');
    load_animation('b_macros');
  }
  $.getJSON('/lm-api/groups_macro?k=' + apikey, function(data) {
    $('#s_macro_group')
      .find('option')
      .remove()
      .end();
    $('#s_macro_group').show();
    var ng = false;
    var gf = false;
    $.each(data, function(uid, val) {
      if (val != 'nogroup') {
        $('#s_macro_group').append('<option>' + val + '</option');
        gf = true;
      } else {
        ng = true;
      }
    });
    if (ng) {
      $('#s_macro_group').append('<option value="nogroup">no group</option');
    }
    if (gf || ng) {
      if (page == 'macros') show_toolbar('macros');
      load_macros();
    } else {
      $('#s_macro_group').hide();
      $('#b_macros').html('<div class="notavail">No macros available</div>');
    }
  });
}

function set_lvar_state(oid) {
  var s = $('#lvar_status').val();
  var v = $('#lvar_value').val();
  $.getJSON(
    '/lm-api/set?k=' + apikey + '&i=' + oid + '&s=' + s + '&v=' + v,
    function(data) {
      if (data && data.result == 'OK') {
        items[oid].status = s;
        items[oid].value = v;
        redraw_lvar_state(oid);
      } else {
        popup('error', 'ERROR', 'LVar not changed. Result: ' + data.result);
      }
    }
  ).fail(function() {
    popup('error', 'ERROR', 'Server error. LVar not changed');
  });
}

function select_lvar_state(oid) {
  var html =
    '<form class="form-horizontal">' +
    '<div class="form-group">' +
    '<label class="col-xs-4 control-label"' +
    ' for="lvar_status">Status</label>' +
    '<div class="col-xs-8 col-sm-6">' +
    '<select class="form-control" id="lvar_status">';
  $.each(lvar_state_labels, function(_k, v) {
    html += '<option value="' + _k + '"';
    if (_k == items[oid].status) html += ' selected';
    html += '>' + v + '</option>';
  });
  var value = items[oid].value;
  if (value == '') value = '';
  html +=
    '</select></div></div>' +
    '<div class="form-group">' +
    '<label class="col-xs-4 control-label"' +
    ' for="lvar_value">Value</label>' +
    '<div class="col-xs-8 col-sm-6">' +
    '<input class="form-control" type="text" size="5"' +
    'id="lvar_value" value="' +
    value +
    '" /></div></div></form>';
  popup(
    'confirm',
    'SET STATE OF ' + oid,
    html,
    'SET',
    'CANCEL',
    'set_lvar_state("' + oid + '")'
  );
}

function format_expire_time(i) {
  if (i.expires == 0) return '';
  if (i.status == 0) return '0.0';
  var t = i.expires - new Date().getTime() / 1000 + tsdiff + i.set_time;
  if (t < 0) return '0.0';
  return Number(Math.round(t * 10) / 10).toFixed(1);
}

function reload_lvars() {
  load_lvar_data();
}

function reload_cycles() {
  load_cycle_data();
}

function load_lvars() {
  $.getJSON(
    '/lm-api/state?k=' + apikey + '&full=1&g=' + $('#s_lvar_group').val(),
    function(data) {
      var bg = 1;
      $('#b_lvars').html('');
      $.each(Object(data).sort(dynamic_sort('id')), function(_k) {
        var uid = data[_k]['id'];
        var oid = data[_k]['oid'];
        var eoid = escape_oid(oid);
        var val = data[_k];
        _lvar = $('<div />', {class: 'col-sm-4 col-xs-2btn col-xs-12'});
        _lvar_expires = $('<div />', {class: 'col-sm-2 col-xs-hid col-xs-12'});
        _lvar_state = $('<div />', {class: 'col-sm-4 col-xs-btn col-xs-12'});
        var _e_label = '';
        if (val.expires > 0) {
          _e_label = '<span class="hidden-xs">E: </span>';
        }
        $('<span />', {
          id: 'lval_expires_e_' + eoid,
          class: 'lval',
          html: _e_label
        }).appendTo(_lvar_expires);
        $('<span />', {
          id: 'lval_expires_' + eoid,
          class: 'lval',
          html: format_expire_time(val)
        }).appendTo(_lvar_expires);
        $('<span />', {
          class: 'lval',
          html: 'V='
        }).appendTo(_lvar_state);
        $('<span />', {
          id: 'lval_' + eoid,
          class: 'lval',
          html: val.value
        }).appendTo(_lvar_state);
        items[oid] = val;
        _lvar_buttons = $('<div />', {
          class: 'col-sm-2 col-xs-btn col-xs-12',
          style: 'text-align:center;'
        });
        $('<button />', {
          class: 'st0',
          html: 'SET'
        })
          .attr('onclick', 'select_lvar_state("' + oid + '")')
          .appendTo(_lvar_buttons);
        var rb = $('<button />', {
          id: 'lval_rb_' + eoid,
          class: 'st0',
          html: 'RESET'
        }).attr('onclick', 'reset_lvar("' + oid + '")');
        if (val.expires <= 0) rb.hide();
        rb.appendTo(_lvar_buttons);
        var _r = $('<div />', {class: 'row row-device bg' + bg});
        var iname = uid;
        $('<div />', {
          class: 'device lvar_s' + val.status,
          id: 'lname_' + eoid,
          html: iname
        }).appendTo(_lvar);
        $('<div />', {
          class: 'device-descr',
          html: val['description']
        }).appendTo(_lvar);
        _lvar.appendTo(_r);
        _lvar_expires.appendTo(_r);
        _lvar_state.appendTo(_r);
        _lvar_buttons.appendTo(_r);
        _r.appendTo('#b_lvars');
        if (bg == 1) bg = 0;
        else bg = 1;
      });
      lvars_loaded = true;
    }
  );
}

function load_cycles() {
  $.getJSON(
    '/lm-api/list_cycles?k=' + apikey + '&g=' + $('#s_cycle_group').val(),
    function(data) {
      var bg = 1;
      $('#b_cycles').html('');
      $.each(Object(data).sort(dynamic_sort('id')), function(_k) {
        var uid = data[_k]['id'];
        var oid = data[_k]['oid'];
        var eoid = escape_oid(oid);
        var val = data[_k];
        _cycle = $('<div />', {class: 'col-sm-4 col-xs-2btn col-xs-12'});
        _cycle_int = $('<div />', {class: 'col-sm-4 col-xs-btn col-xs-12'});
        items[oid] = val;
        _cycle_buttons = $('<div />', {
          class: 'col-sm-2 col-xs-btn col-xs-12',
          style: 'text-align:center;'
        });
        $('<span />', {
          id: 'cint_' + eoid,
          class: 'lval',
          html:
            val.interval.toFixed(4) +
            '<br />-<br />' +
            parseFloat(val.avg).toFixed(4) +
            '<br />-<br />' +
            val.iterations
        }).appendTo(_cycle_int);
        var startb = $('<button />', {
          class: 'st0',
          id: 'cycle_startb_' + eoid,
          html: 'START'
        })
          .attr('onclick', 'start_cycle("' + oid + '")')
          .appendTo(_cycle_buttons);
        if (val.status != 0) {
          startb.addClass('disabled').attr('onclick', null);
        }
        $('<button />', {
          class: 'st0',
          html: 'STOP'
        })
          .attr('onclick', 'stop_cycle("' + oid + '")')
          .appendTo(_cycle_buttons);
        $('<button />', {
          class: 'st0',
          html: 'RESET'
        })
          .attr('onclick', 'reset_cycle_stats("' + oid + '")')
          .appendTo(_cycle_buttons);
        var _r = $('<div />', {class: 'row row-device bg' + bg});
        var iname = uid;
        $('<div />', {
          class: 'device cycle_s' + val.status,
          id: 'cname_' + eoid,
          html: iname
        }).appendTo(_cycle);
        $('<div />', {
          class: 'device-descr',
          html: val['description']
        }).appendTo(_cycle);
        _cycle.appendTo(_r);
        _cycle_int.appendTo(_r);
        _cycle_buttons.appendTo(_r);
        _r.appendTo('#b_cycles');
        if (bg == 1) bg = 0;
        else bg = 1;
      });
      cycles_loaded = true;
    }
  );
}

function prepare_macro_run(i) {
  var html =
    '<form class="form-horizontal">' +
    '<div class="form-group">' +
    '<label class="col-xs-6 control-label"' +
    ' for="lvar_value">Run args:</label>' +
    '<div class="col-xs-6">' +
    '<input class="form-control" type="text" size="5"' +
    'id="macro_run_args" value="" /></div></div></form>';
  popup(
    'confirm',
    'Run macro "' + i + '"',
    html,
    'RUN',
    'CANCEL',
    'run_macro("' + i + '")'
  );
  $('#macro_run_args').focus();
}

function run_macro(i) {
  var btn = $('[id="btn_macro_run_' + i + '"]');
  var args = $('#macro_run_args').val();
  btn.attr('disabled', 'disabled');
  btn.addClass('disabled');
  $.getJSON(
    '/lm-api/run?k=' + apikey + '&i=' + i + '&a=' + args + '&w=120',
    function(data) {
      if (data.status == 'completed') {
        btn.removeAttr('disabled');
        btn.removeClass('disabled');
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

function enable_disable_macro(i, e) {
  $.getJSON(
    '/lm-api/set_macro_prop?k=' +
      apikey +
      '&i=' +
      i +
      '&p=action_enabled&v=' +
      e,
    function(data) {
      if (data && data.result == 'OK') {
        var btn = $('[id="btn_macro_enable_' + i + '"]');
        var runbtn = $('[id="btn_macro_run_' + i + '"]');
        if (e == 1) {
          btn.addClass('active');
          runbtn.removeClass('disabled');
          runbtn.removeAttr('disabled');
        } else {
          btn.removeClass('active');
          runbtn.addClass('disabled');
          runbtn.attr('disabled', 'disabled');
        }
        btn.attr(
          'onclick',
          'enable_disable_macro("' + i + '", ' + (e == 0 ? 1 : 0) + ')'
        );
        btn.html(e == 0 ? 'DISABLED' : 'ENABLED');
      } else {
        popup(
          'error',
          'ERROR',
          'Parameter not changed. Result: ' + data.result
        );
      }
    }
  ).fail(function() {
    popup('error', 'ERROR', 'Server error. Parameter not changed');
  });
}

function enable_disable_rule(i, e) {
  $.getJSON(
    '/lm-api/set_rule_prop?k=' + apikey + '&i=' + i + '&p=enabled&v=' + e,
    function(data) {
      if (data && data.result == 'OK') {
        var btn = $('#btn_rule_enable_' + i);
        if (e == 1) {
          btn.addClass('active');
        } else {
          btn.removeClass('active');
        }
        btn.attr(
          'onclick',
          'enable_disable_rule("' + i + '", ' + (e == 0 ? 1 : 0) + ')'
        );
        btn.html(e == 0 ? 'DISABLED' : 'ENABLED');
      } else {
        popup(
          'error',
          'ERROR',
          'Parameter not changed. Result: ' + data.result
        );
      }
    }
  ).fail(function() {
    popup('error', 'ERROR', 'Server error. Parameter not changed');
  });
}

function load_macros() {
  $.getJSON(
    '/lm-api/list_macros?k=' + apikey + '&g=' + $('#s_macro_group').val(),
    function(data) {
      var bg = 1;
      $('#b_macros').html('');
      $.each(data.sort(dynamic_sort('id')), function(_k) {
        var uid = data[_k]['id'];
        var val = data[_k];
        _macro = $('<div />', {
          class: 'col-md-9 col-sm-8 col-xs-1btn col-xs-12'
        });
        _macro_buttons = $('<div />', {
          class: 'col-md-3 col-sm-4 col-xs-btn col-xs-12',
          style: 'text-align:center;'
        });
        if (master) {
          $('<button />', {
            id: 'btn_macro_enable_' + uid,
            class: 'st0' + (val.action_enabled == 0 ? '' : ' active'),
            onclick:
              'enable_disable_macro("' +
              uid +
              '", ' +
              (val.action_enabled == 0 ? 1 : 0) +
              ')',
            html: val.action_enabled == 0 ? 'DISABLED' : 'ENABLED'
          }).appendTo(_macro_buttons);
        }
        var runbtn = $('<button />', {
          id: 'btn_macro_run_' + uid,
          class: 'st0',
          onclick: 'prepare_macro_run("' + uid + '")',
          html: 'RUN'
        });
        if (val.action_enabled == 0) {
          runbtn.attr('disabled', 'disabled');
          runbtn.addClass('disabled');
        }
        runbtn.appendTo(_macro_buttons);
        var _r = $('<div />', {class: 'row row-device bg' + bg});
        $('<div />', {
          id: 'macro_name_' + uid,
          class: 'device',
          html: uid
        }).appendTo(_macro);
        $('<div />', {
          class: 'device-descr',
          html: val['description']
        }).appendTo(_macro);
        _macro.appendTo(_r);
        _macro_buttons.appendTo(_r);
        _r.appendTo('#b_macros');
        if (bg == 1) bg = 0;
        else bg = 1;
      });
      macros_loaded = true;
    }
  );
}

function rn2a(s) {
  return s == null ? '#' : s;
}

function rs_for_init(s) {
  return s == 'only' || s == 'skip' ? s : 'any';
}

function dm_rule_for_expire(rule) {
  if (
    rule.for_prop == 'status' &&
    rule.in_range_min == null &&
    rule.in_range_max == -1 &&
    rule.in_range_max_eq
  )
    return true;
  return false;
}

function dm_rule_for_set(rule) {
  if (
    rule.for_prop == 'status' &&
    rule.in_range_min == 1 &&
    rule.in_range_max == 1 &&
    rule.in_range_max_eq &&
    rule.in_range_min_eq
  )
    return true;
  return false;
}

function rule_form_condition_switch() {
  $('#l_rule_cond_eq').addClass('hidden');
  $('#d_rule_cond_range').addClass('hidden');
  $('#d_rule_cond_eq').addClass('hidden');
  $('#rule_for_prop').attr('disabled', 'disabled');
  var c = $('#rule_condition').val();
  if (c == 'equals') {
    $('#l_rule_cond_eq').removeClass('hidden');
    $('#d_rule_cond_eq').removeClass('hidden');
    $('#rule_for_prop').removeAttr('disabled');
  } else if (c == 'range') {
    $('#d_rule_cond_range').removeClass('hidden');
    $('#rule_for_prop').removeAttr('disabled');
  } else if (c == 'none') {
    $('#rule_for_prop').removeAttr('disabled');
  }
}

function del_rule(i) {
  $.getJSON('/lm-api/destroy_rule?k=' + apikey + '&i=' + i, function(data) {
    if (data && data.result == 'OK') {
      $('#rule_' + i).remove();
    } else {
      popup('error', 'ERROR', 'Unable to delete rule. Result: ' + data.result);
    }
  }).fail(function() {
    popup('error', 'ERROR', 'Server error. Unable to delete rule');
  });
}

function ask_del_rule(i) {
  popup(
    'warning',
    'DELETE RULE',
    'Rule ' + i + ' will be deleted.<br />Please confirm',
    'DELETE',
    'CANCEL',
    'del_rule("' + i + '")'
  );
}

function rule_from_edit_dialog() {
  var rule = new Object();
  rule.priority = $('#rule_priority').val();
  rule.chillout_time = $('#rule_chillout')
    .val()
    .replace(',', '.');
  rule.description = $('#rule_description').val();
  rule.for_prop = $('#rule_for_prop').val();
  rule.for_item_type = $('#rule_item_type').val();
  rule.for_item_group = $('#rule_for_group').val();
  rule.for_item_id = $('#rule_for_item_id').val();
  if (rule.for_item_group == '') rule.for_item_group = null;
  if (rule.for_item_id == '') rule.for_item_id = null;
  rule.for_initial = $('#rule_for_initial').val();
  if ($('#rule_break').val() == 'YES') {
    rule.break_after_exec = true;
  } else {
    rule.break_after_exec = false;
  }
  rule.macro = $('#rule_macro').val();
  rule.macro_args = $('#rule_macro_args').val();
  rule.macro_kwargs = $('#rule_macro_kwargs').val();
  if (rule.macro == '') rule.macro = null;
  if (rule.macro_args == '') rule.macro_args = null;
  var cond = $('#rule_condition').val();
  rule._cond = cond;
  if (cond == 'expire') {
    rule.for_prop = 'status';
    rule.in_range_max = -1;
    rule.in_range_max_eq = true;
    rule.in_range_min = null;
    rule.in_range_min_eq = false;
  } else if (cond == 'set') {
    rule.for_prop = 'status';
    rule.in_range_max = 1;
    rule.in_range_max_eq = true;
    rule.in_range_min = 1;
    rule.in_range_min_eq = true;
  } else if (cond == 'equals') {
    var m = $('#rule_in_range_min')
      .val()
      .replace(',', '.');
    if (isNumeric(m)) {
      rule.in_range_min = m;
      rule.in_range_max = m;
      rule.in_range_min_eq = true;
      rule.in_range_max_eq = true;
    } else {
      rule.in_range_min = m;
      rule.in_range_max = null;
      rule.in_range_min_eq = true;
      rule.in_range_max_eq = false;
    }
  } else if (cond == 'range') {
    rule.in_range_min = $('#rule_in_range_min_r')
      .val()
      .replace(',', '.');
    rule.in_range_max = $('#rule_in_range_max_r')
      .val()
      .replace(',', '.');
    rule.in_range_min_eq = $('#rule_in_range_min_eq').val() == 1;
    rule.in_range_max_eq = $('#rule_in_range_max_eq').val() == 1;
  } else {
    rule.in_range_min = null;
    rule.in_range_max = null;
    rule.in_range_min_eq = false;
    rule.in_range_max_eq = false;
  }
  return rule;
}

function validate_rule_dialog() {
  var _v = true;
  $('#l_rule_priority').removeClass('device-error');
  $('#l_rule_chillout').removeClass('device-error');
  $('#rule_in_range_min_r').removeClass('device-error');
  $('#rule_in_range_max_r').removeClass('device-error');
  var rule = rule_from_edit_dialog();
  if (!isInt(rule.priority)) {
    $('#l_rule_priority').addClass('device-error');
    $('#rule_priority').focus();
    _v = false;
  }
  if (!isNumeric(rule.chillout_time)) {
    $('#l_rule_chillout').addClass('device-error');
    if (_v) $('#rule_chillout').focus();
    _v = false;
  }
  if (rule._cond == 'range') {
    if (
      rule.in_range_min != '' &&
      (!isNumeric(rule.in_range_min) ||
        (isNumeric(rule.in_range_min) &&
          isNumeric(rule.in_range_max) &&
          Number(rule.in_range_min) > Number(rule.in_range_max)))
    ) {
      $('#rule_in_range_min_r').addClass('device-error');
      if (_v) $('#rule_in_range_min_r').focus();
      _v = false;
    }
    if (
      (rule.in_range_max != '' && !isNumeric(rule.in_range_max)) ||
      (isNumeric(rule.in_range_min) &&
        isNumeric(rule.in_range_max) &&
        Number(rule.in_range_min) > Number(rule.in_range_max))
    ) {
      $('#rule_in_range_max_r').addClass('device-error');
      if (_v) $('#rule_in_range_max_r').focus();
      _v = false;
    }
  }
  return _v;
}

function edit_rule_dialog(i) {
  var _title = 'EDIT RULE ' + i;
  var _priority = 100;
  var _chillout = 0;
  var _description = '';
  var _macro = '';
  var _macro_args = '';
  var _macro_kwargs = '';
  var _prop = 'status';
  var _item_type = '#';
  var _for_group = '#';
  var _for_item_id = '#';
  var _for_initial = 'skip';
  var _break = '0';
  var _condition = 'none';
  var _in_range_min = '';
  var _in_range_max = '';
  var _in_range_min_eq = false;
  var _in_range_max_eq = false;
  if (i === undefined) {
    _title = 'NEW RULE';
  } else {
    _priority = dm_rules[i].priority;
    _chillout = dm_rules[i].chillout_time;
    _description = dm_rules[i].description;
    if (dm_rules[i].macro != null) _macro = dm_rules[i].macro;
    if (dm_rules[i].macro_args != null) {
      var args = '';
      $.each(dm_rules[i].macro_args, function(k, v) {
        if (args != '') {
          args += ' ';
        }
        var _v = String(v);
        if (_v.indexOf(' ') > -1) {
          _v = '&quot;' + v + '&quot;';
        }
        args += _v;
      });
      _macro_args = args;
    }
    if (dm_rules[i].macro_kwargs) {
      var kwargs = '';
      $.each(dm_rules[i].macro_kwargs, function(k, v) {
        if (kwargs != '') {
          kwargs += ',';
        }
        var _v = String(v);
        if (_v.indexOf(' ') > -1) {
          _v = '&quot;' + v + '&quot;';
        }
        kwargs += String(k) + '=' + _v;
      });
      _macro_kwargs = kwargs;
    }
    _prop = dm_rules[i].for_prop;
    _item_type = dm_rules[i].for_item_type;
    if (_item_type == null) _item_type = '#';
    _for_group = dm_rules[i].for_item_group;
    if (_for_group == null) _for_group = '#';
    _for_item_id = dm_rules[i].for_item_id;
    if (_for_item_id == null) _for_item_id = '#';
    _for_initial = rs_for_init(dm_rules[i].for_initial);
    _break = dm_rules[i].break_after_exec ? '1' : '0';
    if (dm_rules[i].in_range_min != null || dm_rules[i].in_range_max != null) {
      if (dm_rule_for_expire(dm_rules[i])) {
        _condition = 'expire';
      } else if (dm_rule_for_set(dm_rules[i])) {
        _condition = 'set';
      } else if (dm_rules[i].condition.indexOf(' == ') > -1) {
        _condition = 'equals';
      } else {
        _condition = 'range';
      }
    }
    if (dm_rules[i].in_range_min != null)
      _in_range_min = dm_rules[i].in_range_min;
    if (dm_rules[i].in_range_max != null)
      _in_range_max = dm_rules[i].in_range_max;
    _in_range_min_eq = dm_rules[i].in_range_min_eq;
    _in_range_max_eq = dm_rules[i].in_range_max_eq;
  }
  // row 1
  var html = '<form class="form-horizontal">';
  html +=
    '<div class="form-group">' +
    '<label class="col-xs-5 col-sm-3 control-label" id="l_rule_priority"' +
    ' for="rule_priority">Priority</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_priority" value="' +
    _priority +
    '">' +
    '</div>';
  html +=
    '' +
    '<label class="col-xs-5 col-sm-3 control-label" id="l_rule_chillout"' +
    ' for="rule_chillout">Chillout</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_chillout" value="' +
    _chillout +
    '" /></div></div>';
  // row 2
  html +=
    '<div class="form-group">' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_description">Descr' +
    '<span class="hidden-xs">iption</span></label>' +
    '<div class="col-xs-7 col-sm-9">' +
    '<input class="form-control" type="text" size="15"' +
    'id="rule_description" value="' +
    _description +
    '">' +
    '</div></div>';
  // row 3
  html +=
    '<div class="form-group">' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_for_prop">Property</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<select class="form-control" id="rule_for_prop">';
  $.each(dm_rule_for_props, function(_k, v) {
    html += '<option value="' + v + '"';
    if (v == _prop) html += ' selected';
    html += '>' + v + '</option>';
  });
  html += '</select></div>';
  html +=
    '' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_item_type">For&nbsp;item</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<select class="form-control" id="rule_item_type">';
  $.each(dm_rule_item_types, function(_k, v) {
    html += '<option value="' + v + '"';
    if (v == _item_type) html += ' selected';
    html += '>' + v + '</option>';
  });
  html += '</select></div></div>';
  // row 4
  html +=
    '<div class="form-group">' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_for_group">Group</label>' +
    '<div class="col-xs-7 col-sm-4">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_for_group" value="' +
    _for_group +
    '" /></div>';
  html +=
    '' +
    '<label class="col-xs-5 col-sm-2 control-label"' +
    ' for="rule_for_item_id">ID</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_for_item_id" value="' +
    _for_item_id +
    '" /></div></div>';
  // row 5
  html +=
    '<div class="form-group">' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_condition">Condition</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<select class="form-control" id="rule_condition"' +
    ' onchange="rule_form_condition_switch()">';
  $.each(dm_rule_conditions, function(_k, v) {
    html += '<option value="' + v + '"';
    if (v == _condition) html += ' selected';
    html += '>' + v + '</option>';
  });
  html += '</select></div>';
  // condition forms
  // equals
  html +=
    '<label class="hidden col-xs-5 col-sm-3 control-label"' +
    ' for="rule_in_range_min" id="l_rule_cond_eq">' +
    'x&nbsp;==</label>' +
    '<div class="hidden col-xs-7 col-sm-3" id="d_rule_cond_eq">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_in_range_min" value="' +
    _in_range_min +
    '"></div>';
  html += '</div>';
  // row 5.5
  // range
  html += '<div class="hidden form-group" id="d_rule_cond_range">';
  html += '<div class="hidden-xs col-sm-3"></div>';
  html +=
    '<div class="col-xs-4 col-sm-2" id="d_rule_cond_range_min">' +
    '<input class="form-control" type="text" size="2"' +
    'id="rule_in_range_min_r" value="' +
    _in_range_min +
    '"></div><div class="col-xs-4 col-sm-2"' +
    ' id="d_rule_cond_range_min_eq">';
  html += '<select class="form-control" id="rule_in_range_min_eq">';
  html += '<option value="0">&lt;</option>';
  html +=
    '<option value="1"' +
    (_in_range_min_eq ? ' selected' : '') +
    '>&lt;=</option>';
  html += '</select>';
  html += '</div>';
  html +=
    '<label class="col-xs-4 visible-xs control-label" ' +
    'id="l_rule_cond_range"  ' +
    'for="rule_in_range_min_r" ' +
    'style="margin-top:7px">x</label>';
  html +=
    '<label class="col-xs-4 col-sm-1 control-label" ' +
    'id="l_rule_cond_range" ' +
    ' for="rule_in_range_max_r">x</label>' +
    '<div class="col-xs-4 col-sm-2"' +
    ' id="d_rule_cond_range_max_eq">';
  html += '<select class="form-control" id="rule_in_range_max_eq">';
  html += '<option value="0">&lt;</option>';
  html +=
    '<option value="1"' +
    (_in_range_max_eq ? ' selected' : '') +
    '>&lt;=</option>';
  html += '</select>';
  html += '</div>';
  html +=
    '<div class="col-xs-4 col-sm-2" id="d_rule_cond_range_max">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_in_range_max_r" value="' +
    _in_range_max +
    '"></div></div>';
  // row 6
  html +=
    '<div class="form-group">' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_for_initial">Initial</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<select class="form-control" id="rule_for_initial">';
  $.each(dm_rule_for_initial, function(_k, v) {
    html += '<option value="' + v + '"';
    if (v == _for_initial) html += ' selected';
    html += '>' + v + '</option>';
  });
  html += '</select></div>';
  html +=
    '' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_break">Break</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<select class="form-control" id="rule_break">';
  $.each(dm_rule_break, function(_k, v) {
    html += '<option value="' + v + '"';
    if (_k == _break) html += ' selected';
    html += '>' + v + '</option>';
  });
  html += '</select></div></div>';
  // row 7
  html +=
    '<div class="form-group">' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_macro">Macro</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_macro" value="' +
    _macro +
    '" /></div>';
  html +=
    '' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_macro_args">Args</label>' +
    '<div class="col-xs-7 col-sm-3">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_macro_args" value="' +
    _macro_args +
    '" /></div></div>';
  // row 8
  html +=
    '<div class="form-group">' +
    '<label class="col-xs-5 col-sm-3 control-label"' +
    ' for="rule_macro_kwargs">Kwargs</label>' +
    '<div class="col-xs-7 col-sm-7">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_macro_kwargs" value="' +
    _macro_kwargs +
    '" /></div></div>';
  // end form
  html += '</form>';
  popup(
    '!confirm',
    _title,
    html,
    'OK',
    'CANCEL',
    'set_rule_props_ae("' + i + '")',
    null,
    validate_rule_dialog
  );
  rule_form_condition_switch();
  $('#rule_priority').focus();
}

function set_rule_props_ae(i) {
  var rule = rule_from_edit_dialog();
  rule.priority = Number(rule.priority);
  rule.chillout_time = Number(rule.chillout_time);
  if (rule._cond == 'equals' && isNumeric(rule.in_range_min)) {
    rule.in_range_min = Number(rule.in_range_min);
    rule.in_range_max = Number(rule.in_range_max);
  } else if (rule._cond == 'range') {
    if (rule.in_range_min != '') {
      rule.in_range_min = Number(rule.in_range_min);
    } else {
      rule.in_range_min = null;
    }
    if (rule.in_range_max != '') {
      rule.in_range_max = Number(rule.in_range_max);
    } else {
      rule.in_range_max = null;
    }
  } else if (rule._cond == 'expire') {
    rule.in_range_max = Number(rule.in_range_max);
  } else if (rule._cond == 'set') {
    rule.in_range_min = Number(rule.in_range_min);
    rule.in_range_max = Number(rule.in_range_max);
  }
  delete rule._cond;
  var d = new Object();
  d.v = rule;
  d.k = apikey;
  var f = 'create_rule';
  if (i !== undefined && i != 'undefined') {
    f = 'set_rule_prop';
    d.i = i;
  }
  $.ajax({
    url: '/lm-api/' + f,
    dataType: 'json',
    type: 'post',
    contentType: 'application/json',
    data: JSON.stringify(d)}).done(
    function(data) {
      if (data && (data.result == 'OK' || data.id)) {
        //popup('info', i + ' reset',
        //       'Reset command completed for ' + i)
      } else {
        popup('error', 'ERROR', 'Unable to process rule');
      }
      load_rules();
    }
  ).fail(function() {
    popup('error', 'ERROR', 'Server error. Unable to process rule');
    load_rules();
  });
}

function reload_rules() {
  load_rules();
}

function load_rules() {
  load_animation('b_rules');
  $.getJSON('/lm-api/list_rules?k=' + apikey, function(data) {
    $('#b_rules').html('');
    var bg = 1;
    var oid_groups = new Array();
    show_toolbar('rules');
    var rule_filter = $('#s_rule_group').val();
    $.each(data.sort(dynamic_sort('priority')), function(_k) {
      var uid = data[_k]['id'];
      var val = data[_k];
      var oid_pg = null;
      var oid_g =
        rn2a(val['for_item_type']) + ':' + rn2a(val['for_item_group']);
      if (oid_g.indexOf('/') != -1) {
        var p = oid_g.split('/');
        p.pop();
        oid_pg = p.join('/');
      }
      var oid = oid_g + '/' + rn2a(val['for_item_id']);
      var oid_p = oid + '/' + rn2a(val['for_prop']);
      if (
        oid_pg &&
        oid_pg.substring(0, 3) != '#:#' &&
        $.inArray(oid_pg, oid_groups) == -1
      ) {
        oid_groups.push(oid_pg);
      }
      if (
        oid_g.substring(0, 3) != '#:#' &&
        $.inArray(oid_g, oid_groups) == -1
      ) {
        oid_groups.push(oid_g);
      }
      if (rule_filter && rule_filter != '#:#') {
        if (oid_p.substring(0, rule_filter.length + 1) != rule_filter + '/') {
          return;
        }
      }
      dm_rules[uid] = val;
      _rule = $('<div />', {class: 'col-md-5 col-sm-6 col-xs-12'});
      _rule_info = $('<div />', {class: 'col-md-3 col-sm-4 col-xs-12'});
      _rule_buttons = $('<div />', {
        class: 'col-md-4 col-sm-2 col-xs-12',
        style: 'text-align:center;'
      });
      $('<button />', {
        id: 'btn_rule_enable_' + uid,
        class: 'st0' + (val.enabled == 0 ? '' : ' active'),
        onclick:
          'enable_disable_rule("' +
          uid +
          '", ' +
          (val.enabled == 0 ? 1 : 0) +
          ')',
        html: val.enabled == 0 ? 'DISABLED' : 'ENABLED'
      }).appendTo(_rule_buttons);
      var editbtn = $('<button />', {
        id: 'btn_rule_edit_' + uid,
        class: 'st0',
        onclick: 'edit_rule_dialog("' + uid + '")',
        html: 'EDIT'
      });
      editbtn.appendTo(_rule_buttons);
      var delbtn = $('<button />', {
        id: 'btn_rule_edit_' + uid,
        class: 'st0',
        onclick: 'ask_del_rule("' + uid + '")',
        html: 'DELETE'
      });
      delbtn.appendTo(_rule_buttons);
      var _r = $('<div />', {
        id: 'rule_' + uid,
        class: 'row row-device bg' + bg
      });
      $('<div />', {
        id: 'rule_priority_' + uid,
        class: 'rule-priority',
        html: val.priority
      }).appendTo(_rule);
      $('<div />', {
        id: 'rule_id_' + uid,
        class: 'rule-id',
        html: uid
      }).appendTo(_rule);
      $('<div />', {
        class: 'rule-desc',
        html: val['description']
      }).appendTo(_rule);
      $('<div />', {
        class: 'device-desc',
        html: oid_p
      }).appendTo(_rule);
      var rem = '';
      if (dm_rule_for_expire(val)) {
        rem = ' (expire)';
      } else if (dm_rule_for_set(val)) {
        rem = ' (set)';
      }
      $('<div />', {
        class: 'rule-condition',
        html: val['condition'] + rem
      }).appendTo(_rule_info);
      $('<div />', {
        class: 'rule-info',
        html:
          'Initial: <b>' +
          rs_for_init(val['for_initial']) +
          '</b>. Break: <b>' + dm_rule_break[val['break_after_exec']?1:0] +
          '</b>'
      }).appendTo(_rule_info);
      $('<div />', {
        class: 'rule-info',
        html: 'Chillout: <b>' + val['chillout_time'] + '</b> sec'
      }).appendTo(_rule_info);
      if (val['macro'] != null) {
        var m = '<b>' + val['macro'] + '</b>(';
        if (val['macro_args'] != null) {
          var args = '';
          $.each(val['macro_args'], function(k, v) {
            if (args != '') {
              args += ', ';
            }
            var _v = String(v);
            if (_v.indexOf(' ') > -1) {
              _v = '"' + v + '"';
            }
            args += _v;
          });
          m += args;
        }
        if (val['macro_kwargs']) {
          m += '| ';
          var kwargs = '';
          $.each(val['macro_kwargs'], function(k, v) {
            if (kwargs != '') {
              kwargs += ',';
            }
            var _v = String(v);
            if (_v.indexOf(' ') > -1) {
              _v = '"' + v + '"';
            }
            kwargs += String(k) + '=' + _v;
          });
          m += kwargs;
        }
        m += ')';
        $('<div />', {
          class: 'rule-info',
          html: 'Macro: ' + m + ''
        }).appendTo(_rule_info);
      }
      _rule.appendTo(_r);
      _rule_info.appendTo(_r);
      _rule_buttons.appendTo(_r);
      _r.appendTo('#b_rules');
      if (bg == 1) bg = 0;
      else bg = 1;
    });
    oid_groups.sort();
    update_rule_groups(oid_groups);
  });
}

function process_ws(evt) {
  var data = JSON.parse(evt.data);
  if (data.s == 'state') {
    $.each(data.d, function(i, s) {
      i = s.oid;
      p = s.type;
      if (i in items) {
        if (p == 'lvar') {
          var value = items[i].value;
          items[i] = s;
          if (s.value == undefined) items[i].value = value;
          redraw_lvar_state(i);
        }
        if (p == 'lcycle') {
          items[i] = s;
          redraw_cycle_state(i);
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
    lvars_loaded = false;
    cycles_loaded = false;
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
    show_lvars();
  } else {
    if (page == 'log') show_log();
  }
  if (ws_mode) {
    if (!reload) {
      $('#i_connection').html(
        '<b><span style="color: red">' + 'WS connecting' + '</span></b>'
      );
      start_ws(false);
    }
    load_lvar_data();
  } else {
    $('#i_connection').html(
      '<b><span style="color: orange">' +
        jrInterval / 1000 +
        ' sec' +
        '</span></b>'
    );
    if (!reload) {
      setInterval(load_lvar_state, jrInterval);
    }
    load_lvar_data();
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

function disable_master_func() {
  $('#tbtn_rules')
    .addClass('disabled')
    .attr('onclick', null);
}

function enable_master_func() {
  $('#tbtn_rules')
    .removeClass('disabled')
    .attr('onclick', 'safe_close_tool_menu();show_rules()');
}

function login(k, remember_k, initial, reload) {
  if (initial) {
    show_board('blank');
    load_animation('b_blank');
  }
  $.getJSON('/lm-api/test?k=' + k, function(data) {
    apikey = k;
    if (initial && !reload) {
      if (remember_k) {
        create_cookie('apikey', k, 365 * 20, '/lm-ei/');
      } else {
        erase_cookie('apikey', '/lm-ei/');
      }
    }
    $('#i_system').html('<b>' + data.system + '</b>');
    document.title = data.system + ' LM PLC EI';
    tsdiff = new Date().getTime() / 1000 - data.time;
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
      if (data.acl.master) {
        enable_master_func();
      } else {
        disable_master_func();
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

function show_lvars() {
  page = 'lvars';
  show_board('lvars');
  show_toolbar('lvars');
}

function show_macros() {
  page = 'macros';
  show_board('macros');
  show_toolbar('macros');
  if (!macros_loaded) {
    load_macros_data();
  }
}

function show_cycles() {
  page = 'cycles';
  show_board('cycles');
  show_toolbar('cycles');
  if (!cycles_loaded) {
    load_cycle_data();
  }
}

function show_rules() {
  page = 'rules';
  show_board('rules');
  show_toolbar('rules');
  load_rules();
}

function show_login_form() {
  try {
    ws.onclose = null;
    ws.send(JSON.stringify({s: 'bye'}));
    ws.close();
  } catch (err) {}
  log_first_load = true;
  lvars_loaded = false;
  log_loaded = false;
  $('#keyform').html('');
  $('#b_lvars').html('');
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
  erase_cookie('apikey', '/lm-ei/');
  show_login_form();
}

setInterval(load_sys_info, srInterval);
setInterval(update_lvar_timers, trInterval);
