var tbar_active = 'remote-items';

var api_responses = {
  0: 'OK',
  1: 'Not found',
  2: 'Forbidden',
  3: 'API error',
  4: 'Unknown error',
  5: 'Not ready',
  6: 'Function unknown',
  7: 'Server error',
  8: 'Server timeout',
  9: 'Bad data',
  10: 'Function failed',
  11: 'Invalid parameters'
};

function $log(msg, level) {
  console.log(msg);
  var l = {};
  if (level) {
    l['l'] = level;
  } else {
    l['l'] = 20;
  }
  l['t'] = Math.round(new Date().getTime() / 1000);
  l['h'] = 'webclient';
  l['p'] = 'cloudmanager';
  l['mod'] = 'client';
  l['th'] = 'current-session';
  l['msg'] = msg;
  eva_sfa_process_log_record(l);
}

function $log_warning(msg) {
  $log(msg, 30);
}

function $log_error(msg) {
  $log(msg, 40);
}

function time_converter(UNIX_timestamp) {
  var a = new Date(UNIX_timestamp * 1000);
  var year = a.getFullYear();
  var month = a.getMonth() + 1;
  var date = a.getDate();
  var hour = a.getHours();
  var min = a.getMinutes();
  var sec = a.getSeconds();
  var time =
    year +
    '-' +
    pad(month, 2) +
    '-' +
    pad(date, 2) +
    ' ' +
    pad(hour, 2) +
    ':' +
    pad(min, 2) +
    ':' +
    pad(sec, 2);
  return time;
}

function pad(num, size) {
  var s = num + '';
  while (s.length < size) s = '0' + s;
  return s;
}

function format_log_record(l) {
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
    eva_sfa_log_level_name(l.l) +
    ' ' +
    l.mod +
    ' ' +
    l.th +
    ': ' +
    l.msg +
    '</div>'
  );
}

function tbar_show(tbar_id) {
  tbar_active = tbar_id;
  reload_data();
  $('.tbar').hide();
  $('#tbar-' + tbar_id).show();
  var t = $('#tbl-' + tbar_id).DataTable();
  t.columns.adjust().draw();
}

function start() {
  $('#main').show();
  $('#i_version').html(eva_sfa_server_info.version);
  $('#i_build').html(eva_sfa_server_info.product_build);
  eva_sfa_process_log_record = function(l) {
    $('#logr').append(format_log_record(l));
    while ($('.logentry').length > eva_sfa_log_records_max) {
      $('#logr')
        .find('.logentry')
        .first()
        .remove();
    }
    $('#logr').scrollTop($('#logr').prop('scrollHeight'));
  };
  eva_sfa_log_records_max = 100;
  eva_sfa_log_start(10);
  reload_data();
}

var tbar_reload_func = {
  'remote-items': reload_remote_items,
  'remote-macros': reload_remote_macros,
  'remote-cycles': reload_remote_cycles
};

function reload_data() {
  if (eva_sfa_logged_in) {
    reload_controllers_data();
    f = tbar_reload_func[tbar_active];
    if (f) f();
  }
}

function show_login_form() {
  $('#main').hide();
  var login = read_cookie('login');
  var password = read_cookie('password');
  if (login && password) {
    do_login(login, password);
    return;
  }
  $('#loginform').show();
  if (login) {
    $('#f_login').prop('value', login);
    $('#f_password').focus();
  } else {
    $('#f_login').focus();
  }
}

function $popup(pclass, title, msg, params) {
  eva_sfa_popup('popup', pclass, title, msg, params);
}

function $call(controller_id, func, params, cb_success, cb_error) {
  eva_sfa_call(
    'management_api_call',
    {i: controller_id, f: func, p: params},
    function(data) {
      if (data.code != 0) {
        var err = api_responses[data.code];
        $log_error(
          'Unable to access ' + controller_id + '. API code=' + data.code
        );
        $popup(
          'error',
          controller_id + ' access error',
          'Unable to access controller<br />API code=' +
            data.code +
            ' (' +
            err +
            ')'
        );
      } else {
        cb_success(data);
      }
    },
    cb_error
  );
}

function reload_controllers_data() {
  eva_sfa_call('list_controllers', null, update_controllers, function() {
    load_error('controllers');
  });
}

function reload_remote_items() {
  eva_sfa_call('list_remote', null, update_remote_items, function() {
    load_error('remote data');
  });
}

function reload_remote_cycles() {
  eva_sfa_call('list_cycles', null, update_remote_cycles, function() {
    load_error('cycles');
  });
}

function reload_remote_macros() {
  eva_sfa_call('list_macros', null, update_remote_macros, function() {
    load_error('macros');
  });
}

function update_remote_items(data) {
  var tbl = $('#tbl-remote-items').DataTable();
  tbl.clear();
  $.each(data, function(k, v) {
    var datarow = $('<tr />');
    datarow.addClass('item-status-' + (v.status > 2 ? 1 : v.status));
    datarow.append($('<td />').html(v.controller_id));
    datarow.append($('<td />').html(v.type));
    datarow.append(
      $('<td />').html(
        v.full_id +
          (v.description
            ? '<br /><span class="item-descr">(' + v.description + ')</span>'
            : '')
      )
    );
    var ae = '';
    if (v.action_enabled === true) {
      ae = 'Y';
    } else if (v.action_enabled == false) {
      ae = 'N';
    }
    datarow.append($('<td />').html(ae));
    datarow.append($('<td />').html(v.status));
    datarow.append($('<td />').html(v.value));
    tbl.rows.add(datarow);
  });
  tbl.columns.adjust().draw();
}

function update_remote_cycles(data) {
  var tbl = $('#tbl-remote-cycles').DataTable();
  tbl.clear();
  $.each(data, function(k, v) {
    var datarow = $('<tr />');
    datarow.addClass('cycle-status-' + v.status);
    datarow.append($('<td />').html(v.controller_id));
    datarow.append(
      $('<td />').html(
        v.full_id +
          (v.description
            ? '<br /><span class="item-descr">(' + v.description + ')</span>'
            : '')
      )
    );
    datarow.append(
      $('<td />').html(['stopped', 'running', 'stopping'][v.status])
    );
    datarow.append($('<td />').html(v.interval.toFixed(4)));
    datarow.append($('<td />').html(parseFloat(v.value).toFixed(4)));
    tbl.rows.add(datarow);
  });
  tbl.columns.adjust().draw();
}

function update_remote_macros(data) {
  var tbl = $('#tbl-remote-macros').DataTable();
  tbl.clear();
  $.each(data, function(k, v) {
    var datarow = $('<tr />');
    datarow.append($('<td />').html(v.controller_id));
    datarow.append(
      $('<td />').html(
        v.full_id +
          (v.description
            ? '<br /><span class="item-descr">(' + v.description + ')</span>'
            : '')
      )
    );
    datarow.append($('<td />').html(v.action_enabled ? 'Y' : 'N'));
    $('#tbl-remote-macros-body').append(datarow);
    datarow.addClass('item-status-' + (v.action_enabled ? '1' : '0'));
    tbl.rows.add(datarow);
  });
  tbl.columns.adjust().draw();
}

function set_controller_masterkey(controller_id, masterkey) {
  eva_sfa_call(
    'set_controller_prop',
    {i: controller_id, p: 'masterkey', v: masterkey, save: 1},
    reload_controllers_data,
    function() {
      set_error(controller_id + ' masterkey');
    }
  );
}

function set_controller_static(controller_id) {
  eva_sfa_call(
    'set_controller_prop',
    {i: controller_id, p: 'static', v: 1},
    reload_controllers_data,
    function() {
      set_error(controller_id + ' static');
    }
  );
}

function remove_controller(controller_id) {
  eva_sfa_call(
    'remove_controller',
    {i: controller_id},
    reload_controllers_data,
    function() {
      remove_error(controller_id);
    }
  );
}

function reload_controller(controller_id) {
  eva_sfa_call(
    'reload_controller',
    {i: controller_id},
    reload_controllers_data,
    function() {
      reload_error(controller_id);
    }
  );
}

function test_controller(controller_id) {
  eva_sfa_call(
    'test_controller',
    {i: controller_id},
    function() {
      var msg = controller_id + ' test passed';
      $log(msg);
      $popup('info', 'PASSED', msg, {ct: 2});
    },
    function() {
      var msg = controller_id + ' test failed';
      $log_error(msg);
      $popup('error', 'FAILED', msg);
    }
  );
}

function enable_controller(controller_id) {
  eva_sfa_call(
    'enable_controller',
    {i: controller_id},
    reload_controllers_data,
    function() {
      set_error(controller_id + ' enabled');
    }
  );
}

function disable_controller(controller_id) {
  eva_sfa_call(
    'disable_controller',
    {i: controller_id},
    reload_controllers_data,
    function() {
      set_error(controller_id + ' disabled');
    }
  );
}

function manage_controller(controller_type, controller_id) {
  if (controller_type == 'remote_uc') {
    manage_uc(controller_id);
  } else if (controller_type == 'remote_lm') {
    manage_lm(controller_id);
  }
}

function manage_uc(controller_id) {
  console.log('UC ' + controller_id);
  $call(controller_id, 'test', null, $log);
}

function manage_lm(controller_id) {
  console.log('LM ' + controller_id);
  $call(controller_id, 'test', null, $log);
}

function edit_controller_props(controller_id) {
  eva_sfa_call(
    'list_controller_props',
    {i: controller_id},
    function(data) {
      var form = $('<div />');
      var e = $('<div />');
      e.append($('<span />').html('Masterkey: '));
      var it = 'password';
      if (!data.masterkey || data.masterkey.startsWith('$')) {
        it = 'text';
      }
      var i = $('<input />', {
        id: 'controller_masterkey',
        size: 30,
        type: it,
        value: data.masterkey
      });
      e.append(i);
      form.append(e);
      e = $('<div />');
      e.append(
        $('<label />', {for: 'controller_masterkey_local'}).html(
          'Use local masterkey'
        )
      );
      var cb = $('<input />', {
        id: 'controller_masterkey_local',
        type: 'checkbox'
      })
        .on('change', function() {
          $('#controller_masterkey').prop('disabled', $(this).is(':checked'));
        })
        .appendTo(e);
      if (data.masterkey == '$masterkey') {
        cb.prop('checked', true);
        i.prop('disabled', true);
      }
      form.append(e);
      $popup('!confirm', 'Edit ' + controller_id, form, {
        btn1a: function() {
          var val = '$masterkey';
          if (!$('#controller_masterkey_local').is(':checked')) {
            val = $('#controller_masterkey').val();
          }
          set_controller_masterkey(controller_id, val);
        },
        btn2: 'Cancel'
      });
      i.focus();
    },
    function() {
      load_error('controller ' + controller_id + ' properties');
    }
  );
}

function append_controller(c, ct) {
  var cdiv = $('<div />');
  var cel = $('<span />');
  if (c.managed && c.connected) {
    cel.click(function() {
      manage_controller(c.type, c.full_id);
    });
    cel.addClass('controller-link');
  } else if (c.connected) {
    cel.addClass('controller-connected');
  } else {
    cel.addClass('controller-disconnected');
  }
  cel.html(c.full_id).appendTo(cdiv);
  $('<button />')
    .addClass('btn-manage-controller')
    .html('test')
    .click(function() {
      test_controller(c.full_id);
    })
    .appendTo(cdiv);
  $('<button />')
    .addClass('btn-manage-controller')
    .html('edit')
    .click(function() {
      edit_controller_props(c.full_id);
    })
    .appendTo(cdiv);
  var btn_reload = $('<button />')
    .addClass('btn-manage-controller')
    .html('reload')
    .click(function() {
      reload_controller(c.full_id);
    })
    .appendTo(cdiv);
  if (c.enabled) {
    $('<button />')
      .addClass('btn-manage-controller')
      .html('disable')
      .click(function() {
        disable_controller(c.full_id);
      })
      .appendTo(cdiv);
  } else {
    $('<button />')
      .addClass('btn-manage-controller')
      .html('enable')
      .click(function() {
        enable_controller(c.full_id);
      })
      .appendTo(cdiv);
    btn_reload.prop('disabled', true);
    btn_reload.addClass('btn-manage-controller-disabled');
  }
  if (c.static) {
    $('<button />')
      .addClass('btn-manage-controller')
      .html('remove')
      .click(function() {
        remove_controller(c.oid);
      })
      .appendTo(cdiv);
  } else {
    $('<button />')
      .addClass('btn-manage-controller')
      .html('make static')
      .click(function() {
        set_controller_static(c.oid);
      })
      .appendTo(cdiv);
  }
  cdiv.appendTo(ct);
}

function update_controllers(data) {
  var ucs = $('#ucs');
  var lms = $('#lms');
  ucs.html('');
  lms.html('');
  $.each(data, function(k, v) {
    var ct = null;
    if (v.group == 'uc') {
      ct = ucs;
    } else if (v.group == 'lm') {
      ct = lms;
    }
    if (ct) append_controller(v, ct);
  });
}

function load_error(msg) {
  var msg = 'Unable to load ' + msg;
  $log_error(msg);
}

function set_error(msg) {
  var msg = 'Unable to set ' + msg;
  $log_error(msg);
  $popup('error', 'Set error', msg);
}

function remove_error(msg) {
  var msg = 'Unable to remove ' + msg;
  $log_error(msg);
  $popup('error', 'Remove error', msg);
}

function reload_error(msg) {
  var msg = 'Unable to reload ' + msg;
  $log_error(msg);
  $popup('error', 'Reload error', msg);
}

function do_login(login, password) {
  if (!login || !password) {
    eva_sfa_login = $('#f_login').val();
    eva_sfa_password = $('#f_password').val();
  } else {
    eva_sfa_login = login;
    eva_sfa_password = password;
  }
  create_cookie('login', eva_sfa_login, 365 * 10, '/cloudmanager/');
  if ($('#f_remember').is(':checked')) {
    create_cookie('password', eva_sfa_password, 365 * 10, '/cloudmanager/');
  }
  $('#f_password').prop('value', '');
  eva_sfa_start();
  $('#loginform').hide();
}

function stop() {
  eva_sfa_stop();
  logout();
}

function logout() {
  erase_cookie('password', '/cloudmanager/');
  show_login_form();
}

$(document).ready(function() {
  $('.tbl').DataTable({
    scrollY: '300px',
    scrollCollapse: true,
    paging: false,
    info: false,
    preDrawCallback: function(settings) {
      pageScrollPos = $('div.dataTables_scrollBody').scrollTop();
    },
    drawCallback: function(settings) {
      $('div.dataTables_scrollBody').scrollTop(pageScrollPos);
    }
  });
  eva_sfa_state_updates = false;
  eva_sfa_init();
  eva_sfa_cb_login_success = function(data) {
    if (!eva_sfa_server_info.acl.master) {
      logout();
      eva_sfa_stop();
      eva_sfa_popup(
        'popup',
        'error',
        'Access denied',
        'User with masterkey ACL is required',
        {ct: 3}
      );
    } else {
      start();
    }
  };
  eva_sfa_cb_login_error = function(data) {
    if (data.status == 403) {
      logout();
      eva_sfa_popup(
        'popup',
        'error',
        'Access denied',
        'Invalid login or password',
        {ct: 3}
      );
    } else {
      setTimeout(eva_sfa_start, 1000);
    }
  };
  setInterval(reload_data, 1000);
  show_login_form();
});
