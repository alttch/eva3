var tbar_active = 'remote-items';
var tbar_reload_func = {};

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
  // $('.tbar').hide();
  // $('#tbar-' + tbar_id).show();
  var t = $('#tbl-' + tbar_id).DataTable();
  t.columns.adjust().draw();
  enableScroll();
}

var autoScrollBottom = true;
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
    if(autoScrollBottom) {
      $('#logr').scrollTop($('#logr').prop('scrollHeight'));
    }
    enableScroll();
    setBodyHeight();
    $('.footer').show();
  };
  eva_sfa_log_records_max = 100;
  eva_sfa_log_start(10);
  reload_data();
  $('#logr').scrollTop($('#logr').prop('scrollHeight'));
  $('#logr').scroll(function() {
    if($('#logr')[0].scrollHeight > $('#logr').scrollTop() + $('#logr').height()) {
      autoScrollBottom = false;
    } else {
      autoScrollBottom = true;
    }
  });
}

function reload_data() {
  if (eva_sfa_logged_in) {
    reload_controllers_data();
    f = tbar_reload_func[tbar_active];
    if (f) f();
  }
}

function show_login_form() {
  $('#main').hide();
  var enter_type = read_cookie('enter_type');
  if(enter_type == "masterkey") {
    var masterkey = read_cookie('masterkey');
    if(masterkey) {
      do_login(enter_type, masterkey);
      return;
    }
  } else {
    var login = read_cookie('login');
    var password = read_cookie('password');
    if (login && password) {
      do_login(enter_type, login, password);
      return;
    }
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
        $popup('error', controller_id + ' access error',
          '<div class="content_msg">' +
          'Unable to access controller<br />API code=' +
          data.code + ' (' + err +')' + '</div>'
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

function reload_remote_units() {
  eva_sfa_call('list_remote', {p: 'unit'}, update_remote_units, function() {
    load_error('remote units');
  });
}

function reload_remote_sensors() {
  eva_sfa_call('list_remote', {p: 'sensor'}, update_remote_sensors, function() {
    load_error('remote sensors');
  });
}

function reload_remote_lvars() {
  eva_sfa_call('list_remote', {p: 'lvar'}, update_remote_lvars, function() {
    load_error('remote lvars');
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

function update_remote_units(data) {
  var tbl = $('#tbl-remote-units').DataTable();
  tbl.clear();
  $.each(data, function(k, v) {
    var datarow = $('<tr />');
    datarow.addClass('unit-status-' + (v.status > 2 ? 1 : v.status));
    datarow.append($('<td />').html(v.controller_id));
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
    datarow.append($('<td />',{class: 'tbl_s'}).html(v.status));
    datarow.append($('<td />',{class: 'tbl_v'}).html(v.value));
    tbl.rows.add(datarow);
  });
  tbl.columns.adjust().draw();
}

function update_remote_sensors(data) {
  var tbl = $('#tbl-remote-sensors').DataTable();
  tbl.clear();
  $.each(data, function(k, v) {
    var datarow = $('<tr />');
    datarow.addClass('sensor-status-' + (v.status > 2 ? 1 : v.status));
    datarow.append($('<td />').html(v.controller_id));
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
    datarow.append($('<td />',{class: 'tbl_s'}).html(v.status));
    datarow.append($('<td />',{class: 'tbl_v'}).html(v.value));
    tbl.rows.add(datarow);
  });
  tbl.columns.adjust().draw();
}

function update_remote_lvars(data) {
  var tbl = $('#tbl-remote-lvars').DataTable();
  tbl.clear();
  $.each(data, function(k, v) {
    var datarow = $('<tr />');
    datarow.addClass('lvar-status-' + (v.status > 2 ? 1 : v.status));
    datarow.append($('<td />').html(v.controller_id));
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
    datarow.append($('<td />',{class: 'tbl_s'}).html(v.status));
    datarow.append($('<td />',{class: 'tbl_v'}).html(v.value));
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
    datarow.addClass('macros-status-' + (v.action_enabled ? '1' : '0'));
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
  $popup('warning', 'Rmoving controller', '<div class="content_msg">' +
    'Do you realy want to remove ' + controller_id + ' controller?</div>', {
    btn1a: function() {
      eva_sfa_call(
        'remove_controller',
        {i: controller_id},
        reload_controllers_data,
        function() {
          remove_error(controller_id);
        }
      )
    },
    btn2: 'Cancel'
  });
}

function reload_controller(controller_id) {
  eva_sfa_call(
    'reload_controller',
    {i: controller_id},
    function() {
      $popup('info', 'Reload requested', '<div class="content_msg">' +
        controller_id + ' reload requested</div>', {
        ct: 2
      });
      reload_controllers_data();
    },
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
      var msg = '<div class="content_msg">' + 
        controller_id + ' test passed</div>';
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
    function() {
      $popup('info', 'Controller enabled', '<div class="content_msg">' +
        controller_id + ' enabled</div>', {
        ct: 2
      });
      reload_controllers_data();
    },
    function() {
      set_error(controller_id + ' enabled');
    }
  );
}

function disable_controller(controller_id) {
  eva_sfa_call(
    'disable_controller',
    {i: controller_id},
    function() {
      var id = $.escapeSelector(controller_id);
      $('#ctrl-' + id).remove();
      $('#save_' + id).remove();
      $('#ctrl_select [value=' + id + ']').remove();
      $popup('warning', 'Controller disabled', '<div class="content_msg">' +
        controller_id + ' disabled</div>', {
        ct: 2
      });
      reload_controllers_data();
    },
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
  $call(controller_id, 'test', null, function(data) {
    $('.content_frame').hide();
    $('.ctrl_block').show();
    $('.ctrl_block .ctrl_content .ctrl_holder').hide();
    $('#ctrl-' + $.escapeSelector(controller_id)).show();
    show_uc_block('uc', controller_id);
    show_debug_info(data);
    $('#mng_btn_' + manage_controllers['current_item']).click();
    if($('.group_holder:visible')[0]) {
      manage_controllers['current_group'] = $('.group_holder:visible')[0].id;
    }
  }, $log);
}

function manage_lm(controller_id) {
  $call(controller_id, 'test', null, function(data) {
    $('.content_frame').hide();
    $('.ctrl_block').show();
    $('.ctrl_block .ctrl_content .ctrl_holder').hide();
    $('#ctrl-' + $.escapeSelector(controller_id)).show();
    show_lm_block('lm', controller_id);
    show_debug_info(data);
    $('#mng_btn_' + manage_controllers['current_item']).click();
    if($('.group_holder:visible')[0]) {
      manage_controllers['current_group'] = $('.group_holder:visible')[0].id;
    }
  }, $log);
}

function get_debug(controller_id, firstTime) {
  $call(controller_id, 'test', null, show_debug_info, $log);
  if(firstTime) {
    setInterval(function() {get_debug(controller_id)}, 10000);
  }
}

function edit_controller_props(controller_id) {
  eva_sfa_call(
    'list_controller_props',
    {i: controller_id},
    function(data) {
      var form = $('<div />');
      var e = $('<div />', {class: 'form-group'});
      e.append($('<label />', {
        for: 'controller_masterkey'
      }).html('Masterkey: '));
      var it = 'password';
      if (!data.masterkey || data.masterkey.startsWith('$')) {
        it = 'text';
      }
      var i = $('<input />', {
        id: 'controller_masterkey',
        class: 'form-control',
        size: 30,
        type: it,
        value: data.masterkey
      });
      e.append(i);
      form.append(e);
      var fc = $('<div />', {class: 'form-group'});
      e = $('<div />', {class: 'custom_chbox_holder'});
      fc.append($('<label />').html('Use custom key'));
      var cb = $('<input />', {
        id: 'controller_masterkey_local',
        type: 'checkbox',
        class: 'custom_chbox',
        checked: true,
      }).on('change', function() {
        $('#controller_masterkey').prop('disabled', !$(this).is(':checked'));
      }).appendTo(e);
      if (data.masterkey == '$masterkey') {
        cb.prop('checked', false);
        i.prop('disabled', 'disabled');
      }
      e.append(
        $('<label />', {for: 'controller_masterkey_local'})
      );
      fc.append(e);
      form.prepend(fc);
      $popup('confirm', 'Edit ' + controller_id, form, {
        btn1a: function() {
          var val = '$masterkey';
          if ($('#controller_masterkey_local').is(':checked')) {
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
  var cb = $('<div />', {class: 'controller_item'});
  var cel = $('<a />', {
    href: 'javascript:void(0)',
    class: 'controller_link'
  }).html(c.full_id);
  if (c.managed && c.connected) {
    if(!$('#ctrl-' + $.escapeSelector(c.full_id))[0]) {
      var oc = $('<option />', {
        value: c.full_id,
        'data-type': c.group
      }).html(c.full_id);
      $('#ctrl_select').append(oc);
      var hc = $('<div />', {
        id: 'ctrl-' + c.full_id,
        class: 'ctrl_holder', 
        role: 'tab-panel'
      });
      $('.ctrl_block .ctrl_content').append(hc);
    }
    cel.click(function() {
      showCurrentController(c.group, c.full_id);
      $('#ctrl_select').val(c.full_id);
    });
    cel.addClass('controller-link');
  } else if (c.connected) {
    cel.click(function() {
      $popup('warning', 'Rights failure', '<div class="content_msg">' +
        'You don\'t have permissions for managing the controller</div>');
    });
    cel.addClass('controller-connected');
  } else {
    cel.click(function() {
      $popup('warning', 'Connection failure', '<div class="content_msg">' +
        'Controller is not connected</div>');
    });
    cb.addClass('controller-disconnected');
  }
  cb.append(cel);
  $('<button />', {class: 'controller_btn test_btn'})
    .html('Test')
    .click(function() {
      test_controller(c.full_id);
    })
    .appendTo(cb)
    .prop('disabled', c.enabled ? '' : 'disabled');
  $('<button />', {class: 'controller_btn edit_btn'})
    .html('Edit')
    .click(function() {
      edit_controller_props(c.full_id);
    })
    .appendTo(cb);
  var btn_reload = $('<button />', { 
      class: 'controller_btn reload_btn'
    })
    .html('Reload')
    .click(function() {
      reload_controller(c.full_id);
    })
    .appendTo(cb);
  if (c.enabled) {
    $('<button />', {class: 'controller_btn disable_btn'})
      .html('Disable')
      .click(function() {
        disable_controller(c.full_id);
      })
      .appendTo(cb);
  } else {
    $('<button />', {class: 'controller_btn disable_btn'})
      .html('Enable')
      .click(function() {
        enable_controller(c.full_id);
      })
      .appendTo(cb);
    btn_reload.prop('disabled', true);
  }
  if (c.static) {
    $('<button />', {class: 'controller_btn remove_btn'})
      .html('Remove')
      .click(function() {
        remove_controller(c.oid);
      })
      .appendTo(cb);
  } else {
    $('<button />', {class: 'controller_btn mk_static_btn'})
      .html('Make static')
      .click(function() {
        set_controller_static(c.oid);
      })
      .appendTo(cb);
  }
  ct.append(cb);
}

var refreshListTime = 2000;
var manage_controllers = [];
manage_controllers['loadFunctions'] = [];
manage_controllers['loadFunctions']['units'] = eva_sfa_list_units;
manage_controllers['loadFunctions']['sensors'] = eva_sfa_list_sensors;
manage_controllers['loadFunctions']['lvars'] = eva_sfa_list_lvars;
manage_controllers['loadFunctions']['macros'] = eva_sfa_list_macros;
manage_controllers['loadFunctions']['cycles'] = eva_sfa_list_cycles;
manage_controllers['status_labels'] = [];
manage_controllers['status_labels']['units'] = {'1': 'ON', '0': 'OFF'};
manage_controllers['status_labels']['lvars'] = {'1': 'Enabled', '0': 'Disabled', '-1': 'Expired'};
manage_controllers['status_labels']['cycles'] = {'2': 'stopping', '0': 'stopped', '1': 'running'};
manage_controllers['items'] = [];
manage_controllers['items']['rule_groups'] = [];
manage_controllers['status_labels']['rule'] = [];
manage_controllers['status_labels']['rule']['for_props'] = ['status', 'value', 'nstatus', 'nvalue'];
manage_controllers['status_labels']['rule']['item_types'] = ['#', 'unit', 'sensor', 'lvar'];
manage_controllers['status_labels']['rule']['for_iniial'] = ['skip', 'only', 'any'];
manage_controllers['status_labels']['rule']['break'] = {'0': 'NO', '1': 'YES'};
manage_controllers['status_labels']['rule']['conditions'] = ['none', 'range', 'equals', 'set', 'expire'];

function showCurrentController(type, id) {
  if(type == -1) {
    $('.ctrl_block').hide();
    $('.content_frame').show();
    if(manage_controllers['current_interval']) {
      clearInterval(manage_controllers['current_interval']);
      manage_controllers['current_interval'] = null;
    }
  } else {
    if(type == 'lm') {
      manage_lm(id);
    } else if(type == 'uc') {
      manage_uc(id);
    }
  }
}
function show_lm_block(type, id) {
  manage_controllers['current_controller'] = id;
  var lm_block = $('#ctrl-' + $.escapeSelector(id));
  if(!lm_block.find('.mng_btn_holder')[0]) {
    $('<button />', {
      id: 'save_' + id,
      class: 'ctrl_reload_btn',
      html: 'Save',
      onclick: 'save("' + id + '")'
    }).insertBefore($('.ctrl_block .ctrl_content'));
    var btn_holder = $('<div />', {
      class: 'mng_btn_holder'
    }).appendTo(lm_block);
    var content_holder = $('<div />', {
      class: 'mng_holder'
    }).appendTo(lm_block);
    var mngBtns = [{
      name: 'Lvars',
      type: 'lvars',
      action: function() {
        manage_controllers['current_item'] = 'lvars';
        hideManageHolders(lm_block);
        showCurrentHolder(type, 'lvars');
        $call(id, 'groups', {p: 'LV'}, function(data) {
          insertGroups(data);
          if(manage_controllers['current_interval']) {
            clearInterval(manage_controllers['current_interval']);
            manage_controllers['current_interval'] = null;
          }
          manage_controllers['current_interval'] = setInterval(function() {
            $call(id, 'groups', {p: 'LV'}, insertGroups, function() {
              load_error('groups lvars');
            });
          }, refreshListTime);
        }, function() {
          load_error('groups lvars');
        });
      }
    }, {
      name: 'Macros',
      type: 'macros',
      action: function() {
        manage_controllers['current_item'] = 'macros';
        hideManageHolders(lm_block);
        showCurrentHolder(type, 'macros');
        $call(id, 'groups_macro', null , function(data) {
          insertGroups(data);
          if(manage_controllers['current_interval']) {
            clearInterval(manage_controllers['current_interval']);
            manage_controllers['current_interval'] = null;
          }
          manage_controllers['current_interval'] = setInterval(function() {
            $call(id, 'groups_macro', null ,insertGroups, function() {
              load_error('groups macros');
            });
          }, refreshListTime);
        }, function() {
          load_error('groups macros');
        });
      }
    }, {
      name: 'Cycles',
      type: 'cycles',
      action: function() {
        manage_controllers['current_item'] = 'cycles';
        hideManageHolders(lm_block);
        showCurrentHolder(type, 'cycles');
        $call(id, 'groups_cycle', null , function(data) {
          insertGroups(data);
          if(manage_controllers['current_interval']) {
            clearInterval(manage_controllers['current_interval']);
            manage_controllers['current_interval'] = null;
          }
          manage_controllers['current_interval'] = setInterval(function() {
            $call(id, 'groups_cycle', null ,insertGroups, function() {
              load_error('groups cycles');
            });
          }, refreshListTime);
        }, function() {
          load_error('groups cycles');
        });
      }
    }, {
      name: 'Rules',
      type: 'rules',
      action: function() {
        manage_controllers['current_item'] = 'rules';
        hideManageHolders(lm_block);
        showCurrentHolder(type, 'rules');
        $call(id, 'list_rules', null , function(data) {
          insertRuleList(data);
          if(manage_controllers['current_interval']) {
            clearInterval(manage_controllers['current_interval']);
            manage_controllers['current_interval'] = null;
          }
          manage_controllers['current_interval'] = setInterval(function() {
            $call(id, 'list_rules', null ,insertRuleList, function() {
              load_error('remote rules');
            });
          }, refreshListTime);
        }, function() {
          load_error('remote rules');
        });
      }
    }, /*{
      name: 'Log',
      type: 'lm_log',
      action: function() {
        hideManageHolders(lm_block);
        showCurrentHolder(type, 'lm_log');
      }
    },*/ 
    ];
    var debug_holder = $('<div />').appendTo(btn_holder);
    $('<div />', {
      id: 'i_debug_' + id,
      class: 'debug_info'
    }).appendTo(debug_holder);
    get_debug(id, true);
    $.each(mngBtns, function(k, v) {
      insertMngButton(btn_holder, v, k);
      $('<div />', {
        id: 'mng_' + v.type,
        class: 'mng_items_holder',
        style: 'display:'+(k == 0 ? 'block' : 'none'),
      }).appendTo(content_holder);
    });
    manage_controllers['current_item'] = 'lvars';
    $call(id, 'groups', {p: 'LV'}, function(data) {
      insertGroups(data);
      if(manage_controllers['current_interval']) {
        clearInterval(manage_controllers['current_interval']);
        manage_controllers['current_interval'] = null;
      }
      manage_controllers['current_interval'] = setInterval(function() {
        $call(id, 'groups', {p: 'LV'}, insertGroups, function() {
          load_error('groups lvars');
        });
      }, refreshListTime);
    }, function() {
      load_error('groups lvars');
    });
  } else {
    manage_controllers['current_item'] = 
      $('.ctrl_content .mng_items_holder:visible')[0].id.substr(4);
  }
  $('.ctrl_block > .ctrl_reload_btn').hide();
  $('#save_' + $.escapeSelector(id)).show();
}
function show_uc_block(type, id) {
  manage_controllers['current_controller'] = id;
  var uc_block = $('#ctrl-' + $.escapeSelector(id));
  if(!uc_block.find('.mng_btn_holder')[0]) {
    $('<button />', {
      id: 'save_' + id,
      class: 'ctrl_reload_btn',
      html: 'Save',
      onclick: 'save("' + id + '")'
    }).insertBefore($('.ctrl_block .ctrl_content'));
    var btn_holder = $('<div />', {
      class: 'mng_btn_holder'
    }).appendTo(uc_block);
    var content_holder = $('<div />', {
      class: 'mng_holder'
    }).appendTo(uc_block);
    var mngBtns = [{
      name: 'Units',
      type: 'units',
      action: function() {
        manage_controllers['current_item'] = 'units';
        hideManageHolders(uc_block);
        showCurrentHolder(type, 'units');
        $call(id, 'groups', {p: 'U'}, function(data) {
          insertGroups(data);
          if(manage_controllers['current_interval']) {
            clearInterval(manage_controllers['current_interval']);
            manage_controllers['current_interval'] = null;
          }
          manage_controllers['current_interval'] = setInterval(function() {
            $call(id, 'groups', {p: 'U'}, insertGroups, function() {
              load_error('groups units');
            });
          }, refreshListTime);
        }, $log);
      }
    }, {
      name: 'Sensors',
      type: 'sensors',
      action: function() {
        manage_controllers['current_item'] = 'sensors';
        hideManageHolders(uc_block);
        showCurrentHolder(type, 'sensors');
        $call(id, 'groups', {p: 'S'}, function(data) {
          insertGroups(data);
          if(manage_controllers['current_interval']) {
            clearInterval(manage_controllers['current_interval']);
            manage_controllers['current_interval'] = null;
          }
          manage_controllers['current_interval'] = setInterval(function() {
            $call(id, 'groups', {p: 'S'}, insertGroups, function() {
              load_error('groups lvars');
            });
          }, refreshListTime);
        }, $log);
      }
    },/* {
      name: 'Log',
      type: 'uc_log',
      action: function() {
        hideManageHolders(uc_block);
        showCurrentHolder(type, 'uc_log');
      }
    },*/ 
    ];
    var debug_holder = $('<div />').appendTo(btn_holder);
    $('<div />', {
      id: 'i_debug_' + id,
      class: 'debug_info'
    }).appendTo(debug_holder);
    get_debug(id, true);
    $.each(mngBtns, function(k, v) {
      insertMngButton(btn_holder, v, k);
      $('<div />', {
        id: 'mng_' + v.type,
        class: 'mng_items_holder',
        style: 'display:'+(k == 0 ? 'block' : 'none'),
      }).appendTo(content_holder);
    });
    manage_controllers['current_item'] = 'units';
    $call(id, 'groups', {p: 'U'}, function(data) {
      insertGroups(data);
      if(manage_controllers['current_interval']) {
        clearInterval(manage_controllers['current_interval']);
        manage_controllers['current_interval'] = null;
      }
      manage_controllers['current_interval'] = setInterval(function() {
        $call(id, 'groups', {p: 'U'}, insertGroups, $log);
      }, refreshListTime);
    }, $log);
  } else {
    manage_controllers['current_item'] = 
      $('.ctrl_content .mng_items_holder:visible')[0].id.substr(4);
  }
  $('.ctrl_block > .ctrl_reload_btn').hide();
  $('#save_' + $.escapeSelector(id)).show();
}
function insertMngButton(block, btn, k) {
  var mngBtn = $('<button />', {
    id: 'mng_btn_'+btn.type,
    class: 'mng_type'+(k==0?' mng_btn_active':'')
  }).html(btn.name);
  if(btn.action) {
    mngBtn.click(btn.action);
  }
  manage_controllers['reload_'+btn.type] = false;
  mngBtn.appendTo(block);
}
function hideManageHolders(block) {
  if(manage_controllers['current_interval']) {
    clearInterval(manage_controllers['current_interval']);
    manage_controllers['current_interval'] = null;
  }
  block.find('.mng_type').removeClass('mng_btn_active');
  block.find('.mng_items_holder').hide();
}
function showCurrentHolder(type, id) {
  $('#mng_btn_' + id).addClass('mng_btn_active');
  $('#mng_' + id).show();
  if($('.group_holder:visible')[0]) {
    manage_controllers['current_group'] = $('.group_holder:visible')[0].id;
  }
}
function insertGroups(result) {
  var ih = $('#mng_' + manage_controllers['current_item']);
  var ig;
  if($('#mng_' + manage_controllers['current_item'] + '_group')[0]) {
    ig = $('#mng_' + manage_controllers['current_item'] + '_group');
    var options = [];
    for(var i = 0; i < ig[0].options.length; i++) {
      options.push(ig[0].options[i].value)
    }
    $.each(result.data, function(k, v) {
      if(!options.includes(v)) {
        $('<option />', {
          value: v
        }).html(v)
        .prop((v == manage_controllers['current_group'] ? 'selected' : ''), 'selected')
        .appendTo(ig);
      }
    });
    $.each(options, function(k,v) {
      if(!result.data.includes(v)) {
        $(ig[0]).find("option[value=" + v + "]").remove();
        $('#' + manage_controllers['current_item'] + "_" + v).remove();
      }
    })
  } else {
    ig = $('<select />', {
      id: 'mng_' + manage_controllers['current_item'] + '_group'
    }).change(function() {
      hideManageGroupHolders(ih);
      showCurrentGroupHolder(this.value);
    });
    $.each(result.data, function(k, v) {
      $('<option />', {
        value: v
      }).html(v)
      .prop((v == manage_controllers['current_group'] ? 'selected' : ''), 'selected')
      .appendTo(ig);
    });
    var ch = $('<div />', {
      class: 'group_ctrl_holder'
    }).appendTo(ih);
    ch.append(ig);
    $('<button />', {
      id: 'mng_' + manage_controllers['current_item'] + '_reload',
      class: 'ctrl_reload_btn'
    }).click(function() {
      var curType = $(this.closest('.ctrl_holder')).find('.mng_btn_active');
      ih.html('');
      manage_controllers['reload_' + manage_controllers['current_item']] = false;
      curType.click();
    })
    .html('Reload')
    .appendTo(ch);
    var f = manage_controllers['create_' + manage_controllers['current_item']];
    if(f) {
      $('<button />', {
        id: 'mng_' + manage_controllers['current_item'] + '_create',
        class: 'ctrl_reload_btn'
      }).click(function() { f(); })
      .html('Create ' + manage_controllers['current_item'].slice(0, -1))
      .appendTo(ch);
    }
  }
  loadItemsList();
}

function loadItemsList() {
  var f = manage_controllers['loadFunctions'][manage_controllers['current_item']];
  if(f) { f(); }
}

function eva_sfa_list_units() {
  $call(manage_controllers['current_controller'], 'state', 
    {p: 'U'}, insertUnitsList, function() {
    load_error('remote units');
  });
}
function eva_sfa_list_sensors() {
  $call(manage_controllers['current_controller'], 'state', 
    {p: 'S'}, insertSensorsList, function() {
    load_error('remote sensors');
  });
}
function eva_sfa_list_lvars() {
  $call(manage_controllers['current_controller'], 'state', 
    {p: 'LV'}, insertLvarsList, function() {
    load_error('remote lvars');
  });
}
function eva_sfa_list_macros() {
  $call(manage_controllers['current_controller'], 'list_macros', 
    null, insertMacrosList, function() {
    load_error('macros');
  });
}
function eva_sfa_list_cycles() {
  $call(manage_controllers['current_controller'], 'list_cycles', 
    null, insertCyclesList, function() {
    load_error('remote cycles');
  });
}

function hideManageGroupHolders(block) {
  block.find('.group_holder').hide();
}
function showCurrentGroupHolder(id) {
  manage_controllers['current_group'] = id;
  $('#' + manage_controllers['current_item'] +
    '_' + $.escapeSelector(id)).show();
}
function insertUnitsList(result) {
  var ih = $('#mng_' + manage_controllers['current_item']);
  var ig = [];
  var units_oid_list = [];
  $.each(result.data, function(k, v) {
    units_oid_list.push(v.oid);
    if(!$('#' + manage_controllers['current_item'] + '_' + v.group)[0]) {
      ig[manage_controllers['current_item'] + '_' + v.group] = 
        $('<div />', {
        class: 'group_holder',
        id: manage_controllers['current_item'] + '_' + v.group
      }).appendTo(ih);
    } else {
      ig[manage_controllers['current_item'] + '_' + v.group] = 
        $('#' + manage_controllers['current_item'] + '_' + v.group);
    }
    if(manage_controllers['reload_units'] && manage_controllers['items'][v.oid] && 
      JSON.stringify(v) == JSON.stringify(manage_controllers['items'][v.oid])) {
      return true;
    } else {
      manage_controllers['items'][v.oid] = v;
      var unit = $('<div />', {
        id: v.oid,
        class: 'mng_item_holder'
      });
      var unit_info = $('<div />', {
        class: 'descr_block'
      }).appendTo(unit);
      $('<div />', {
        class: 'item_name',
        html: v.id
      }).appendTo(unit_info);
      $('<div />', {
        class: 'item_descr',
        html: v.description
      }).appendTo(unit_info);

      // $('<input />', {
      //   type: 'checkbox',
      //   class: 'custom_chbox custom_chbox_round',
      //   id: 'btn_' + v.oid,
      //   onclick: 'unit_on_off(event, "' + 
      //     manage_controllers["current_controller"] + 
      //     '", "' + v.oid + '", ' + (1 - v.status) + ')',
      // }).prop((v.status === 1 ? 'checked' : ''), 'checked')
      // .prop((v.action_enabled? '': 'disabled'), 'disabled')
      // .appendTo(unit);
      // $('<label />', {for: 'btn_' + v.oid}).appendTo(unit);    
      var unit_btns = $('<div />', {
        class: 'buttons_block'
      }).appendTo(unit);
      if(v.action_enabled) {
        $('<button />', {
          class: 'item_btn btn_enable active',
          id: 'btn_enable_' + v.oid,
          onclick: 'enable_disable_unit("' +
            manage_controllers["current_controller"] +
            '", "' + v.oid + '", "disable")',
          html: 'ENABLED'
        }).appendTo(unit_btns);
      } else {
        $('<button />', {
          class: 'item_btn btn_disable',
          id: 'btn_enable_' + v.oid,
          onclick: 'enable_disable_unit("' +
            manage_controllers["current_controller"] +
            '", "' + v.oid + '", "enable")',
          html: 'DISABLED'
        }).appendTo(unit_btns);
      }
      $('<button />', {
        class: 'item_btn btn_set',
        onclick: 'unit_state_dialog("' + 
          manage_controllers["current_controller"] + 
          '", "' + v.oid + '")',
        html: 'SET'
      }).appendTo(unit_btns);
      $('<button />', {
        class: 'item_btn btn_kill',
        onclick: 'ask_kill_unit("' + 
          manage_controllers["current_controller"] + 
          '", "' + v.oid + '")',
        html: 'KILL'
      }).appendTo(unit_btns);
      $('<button />', {
        class: 'item_btn btn_remove',
        onclick: 'ask_remove_unit("' + 
          manage_controllers["current_controller"] + 
          '", "' + v.oid + '")',
        html: 'DELETE'
      }).appendTo(unit_btns);
      if($('#'+$.escapeSelector(v.oid))[0]) {
        $('#'+$.escapeSelector(v.oid)).html(unit.html());
      } else {
        ig[manage_controllers['current_item'] + '_' + v.group].append(unit);
      }
    }
    eva_sfa_register_update_state(v.oid, redraw_unit);
  });
  $.each(Object.keys(manage_controllers["items"]), function(k, v) {
    if(manage_controllers["items"][v] && 
        manage_controllers["items"][v].type == "unit" && 
        !units_oid_list.includes(v)) {
      $('#'+$.escapeSelector(v)).remove();
      delete manage_controllers["items"][v];
    }
  });
  hideManageGroupHolders(ih);
  var curId = $('#mng_' + manage_controllers['current_item'] + '_group').val();
  showCurrentGroupHolder(curId);
  manage_controllers['reload_units'] = true;
}
function insertSensorsList(result) {
  var ih = $('#mng_' + manage_controllers['current_item']);
  var ig = [];
  var sensors_oid_list = [];
  $.each(result.data, function(k, v) {
    sensors_oid_list.push(v.oid);
    if(!$('#' + manage_controllers['current_item'] + '_' + v.group)[0]) {
      ig[manage_controllers['current_item'] + '_' + v.group] = 
        $('<div />', {
        class: 'group_holder',
        id: manage_controllers['current_item'] + '_' + v.group
      }).appendTo(ih);
    } else {
      ig[manage_controllers['current_item'] + '_' + v.group] = 
        $('#' + manage_controllers['current_item'] + '_' + v.group);
    }
    if(manage_controllers['reload_sensors'] && manage_controllers['items'][v.oid] && 
      JSON.stringify(v) == JSON.stringify(manage_controllers['items'][v.oid])) {
      return true;
    } else {
      manage_controllers['items'][v.oid] = v;
      var sensor = $('<div />', {
        id: v.oid,
        class: 'mng_item_holder'
      });
      var sensor_info = $('<div />', {
        class: 'descr_block'
      }).appendTo(sensor);
      $('<div />', {
        class: 'item_name',
        html: v.id
      }).appendTo(sensor_info);
      $('<div />', {
        class: 'item_descr',
        html: v.description
      }).appendTo(sensor_info);
      $('<div />', {
        class: 'item_val',
        html: v.value
      }).appendTo(sensor_info);
      var sensor_btns = $('<div />', {
        class: 'buttons_block'
      }).appendTo(sensor);
      if(v.status === 1) {
        $('<button />', {
          class: 'item_btn btn_enable',
          id: 'btn_' + v.oid,
          onclick: 'enable_disable_sensor("'+ 
            manage_controllers["current_controller"] + 
            '", "' + v.oid + '", 0)',
          html: 'ENABLED'
        }).appendTo(sensor_btns);
      } else {
        $('<button />', {
          class: 'item_btn btn_disable',
          id: 'btn_' + v.oid,
          onclick: 'enable_disable_sensor("'+ 
            manage_controllers["current_controller"] + 
            '", "' + v.oid + '", 1)',
          html: 'DISABLED'
        }).appendTo(sensor_btns);
      }
      $('<button />', {
          class: 'item_btn btn_remove',
          id: 'remove_btn_' + v.oid,
          onclick: 'ask_remove_sensor("'+ 
            manage_controllers["current_controller"] + 
            '", "' + v.oid + '")',
          html: 'DELETE'
        }).appendTo(sensor_btns);
      if($('#'+$.escapeSelector(v.oid))[0]) {
        $('#'+$.escapeSelector(v.oid)).html(sensor.html());
      } else {
        ig[manage_controllers['current_item'] + '_' + v.group].append(sensor);
      }
    }
    eva_sfa_register_update_state(v.oid, redraw_enable_sensor_btn);
  });
  $.each(Object.keys(manage_controllers["items"]), function(k, v) {
    if(manage_controllers["items"][v] && 
        manage_controllers["items"][v].type == "sensor" && 
        !sensors_oid_list.includes(v)) {
      $('#'+$.escapeSelector(v)).remove();
      delete manage_controllers["items"][v];
    }
  });
  hideManageGroupHolders(ih);
  var curId = $('#mng_' + manage_controllers['current_item'] + '_group').val();
  showCurrentGroupHolder(curId);
  manage_controllers['reload_sensors'] = true;
}
function insertLvarsList(result) {
  var ih = $('#mng_' + manage_controllers['current_item']);
  var ig = [];
  var lvars_oid_list = [];
  $.each(result.data, function(k, v) {
    lvars_oid_list.push(v.oid);
    if(!$('#' + manage_controllers['current_item'] + '_' + v.group)[0]) {
      ig[manage_controllers['current_item'] + '_' + v.group] = 
        $('<div />', {
        class: 'group_holder',
        id: manage_controllers['current_item'] + '_' + v.group
      }).appendTo(ih);
    } else {
      ig[manage_controllers['current_item'] + '_' + v.group] = 
        $('#' + manage_controllers['current_item'] + '_' + v.group);
    }
    if(manage_controllers['reload_lvars'] && manage_controllers['items'][v.oid] && 
      JSON.stringify(v) == JSON.stringify(manage_controllers['items'][v.oid])) {
      return true;
    } else {
      manage_controllers['items'][v.oid] = v;
      var lvar = $('<div />', {
        id: v.oid,
        class: 'mng_item_holder'
      });
      var lvar_info = $('<div />', {
        class: 'descr_block'
      }).appendTo(lvar);
      $('<div />', {
        id: 'lname_' + v.oid,
        class: 'item_name lvar_s' + v.status,
        html: v.id
      }).appendTo(lvar_info);
      $('<div />', {
        class: 'item_descr',
        html: v.description
      }).appendTo(lvar_info);
      var lvar_vals = $('<div />', {
        class: 'descr_block'
      }).appendTo(lvar);
      $('<div />', {
        id: 'lvar_expires_' + v.oid,
        class: 'lvar_expires',
        html: format_expire_time(v)
      }).appendTo(lvar_vals);
      $('<div />', {
        id: 'lval_' + v.oid,
        class: 'item_val',
        html: 'Val = ' + v.value
      }).appendTo(lvar_vals);
      var lvar_btns = $('<div />', {
        class: 'buttons_block'
      }).appendTo(lvar);
      $('<button />', {
        class: 'item_btn btn_set',
        onclick: 'select_lvar_state("' +
          manage_controllers["current_controller"] +
          '", "' + v.oid + '")',
        html: 'SET'
      }).appendTo(lvar_btns);
      $('<button />', {
        class: 'item_btn btn_remove',
        onclick: 'ask_remove_lvar("' +
          manage_controllers["current_controller"] +
          '", "' + v.oid + '")',
        html: 'DELETE'
      }).appendTo(lvar_btns);
      if($('#'+$.escapeSelector(v.oid))[0]) {
        $('#'+$.escapeSelector(v.oid)).html(lvar.html());
      } else {
        ig[manage_controllers['current_item'] + '_' + v.group].append(lvar);
      }
    }
    eva_sfa_register_update_state(v.oid, redraw_lvar_state);
  });
  $.each(Object.keys(manage_controllers["items"]), function(k, v) {
    if(manage_controllers["items"][v] && 
        manage_controllers["items"][v].type == "lvar" && 
        !lvars_oid_list.includes(v)) {
      $('#'+$.escapeSelector(v)).remove();
      delete manage_controllers["items"][v];
    }
  });
  hideManageGroupHolders(ih);
  var curId = $('#mng_' + manage_controllers['current_item'] + '_group').val();
  showCurrentGroupHolder(curId);
  manage_controllers['reload_lvars'] = true;
}
function insertMacrosList(result) {
  var ih = $('#mng_macros');
  var ig = [];
  var macros_oid_list = [];
  $.each(result.data, function(k, v) {
    macros_oid_list.push(v.oid);
    if(!$('#macros_' + v.group)[0]) {
      ig['macros_' + v.group] = 
        $('<div />', {
        class: 'group_holder',
        id: 'macros_' + v.group
      }).appendTo(ih);
    } else {
      ig['macros_' + v.group] = $('#macros_' + v.group);
    }
    if(manage_controllers['reload_macros'] && manage_controllers['items'][v.oid] && 
      JSON.stringify(v) == JSON.stringify(manage_controllers['items'][v.oid])) {
      return true;
    } else {
      manage_controllers['items'][v.oid] = v;
      var macro = $('<div />', {
        id: v.oid,
        class: 'mng_item_holder'
      });
      var macro_info = $('<div />', {
        class: 'descr_block'
      }).appendTo(macro);
      $('<div />', {
        class: 'item_name',
        html: v.id
      }).appendTo(macro_info);
      $('<div />', {
        class: 'item_descr',
        html: v.description
      }).appendTo(macro_info);
      var macro_btns = $('<div />', {
        class: 'buttons_block'
      }).appendTo(macro);
      if(v.action_enabled) {
        $('<button />', {
          class: 'item_btn btn_enable',
          id: 'macro_enable_' + v.oid,
          onclick: 'enable_disable_macro("' +
            manage_controllers["current_controller"] +
            '", "' + v.oid + '", 0)',
          html: 'ENABLED'
        }).appendTo(macro_btns);
      } else {
        $('<button />', {
          class: 'item_btn btn_disable',
          id: 'macro_enable_' + v.oid,
          onclick: 'enable_disable_macro("' +
            manage_controllers["current_controller"] +
            '", "' + v.oid + '", 1)',
          html: 'DISABLED'
        }).appendTo(macro_btns);
      }
      $('<button />', {
        class: 'item_btn btn_run',
        id: 'btn_macro_run_' + v.oid,
        onclick: 'prepare_macro_run("' +
          manage_controllers["current_controller"] +
          '", "' + v.oid + '", 1)',
        html: 'RUN'
      }).prop((v.action_enabled? '': 'disabled'), 'disabled')
      .appendTo(macro_btns);
      $('<button />', {
        class: 'item_btn btn_edit',
        id: 'btn_macro_edit_' + v.oid,
        onclick: 'get_macro_props_for_edit("' +
          manage_controllers["current_controller"] +
          '", "' + v.oid + '")',
        html: 'PROPS'
      }).appendTo(macro_btns);
      get_macro_props_for_edit
      if($('#' + $.escapeSelector(v.oid))[0]) {
        $('#' + $.escapeSelector(v.oid)).html(macro.html());
      } else {
        ig['macros_' + v.group].append(macro);
      }
    }
  });
  $.each(Object.keys(manage_controllers["items"]), function(k, v) {
    if(manage_controllers["items"][v] && 
        manage_controllers["items"][v].type == "lmacro" && 
        !macros_oid_list.includes(v)) {
      $('#'+$.escapeSelector(v)).remove();
      delete manage_controllers["items"][v];
    }
  });
  hideManageGroupHolders(ih);
  var curId = $('#mng_macros_group').val();
  showCurrentGroupHolder(curId);
  manage_controllers['reload_macros'] = true;
}
function insertCyclesList(result) {
  var ih = $('#mng_' + manage_controllers['current_item']);
  var ig = [];
  var cycles_oid_list = [];
  $.each(result.data, function(k, v) {
    cycles_oid_list.push(v.oid);
    if(!$('#' + manage_controllers['current_item'] + '_' + v.group)[0]) {
      ig[manage_controllers['current_item'] + '_' + v.group] = 
        $('<div />', {
        class: 'group_holder',
        id: manage_controllers['current_item'] + '_' + v.group
      }).appendTo(ih);
    } else {
      ig[manage_controllers['current_item'] + '_' + v.group] = 
        $('#' + manage_controllers['current_item'] + '_' + v.group);
    }
    if(manage_controllers['reload_cycles'] && manage_controllers['items'][v.oid] && 
      JSON.stringify(v) == JSON.stringify(manage_controllers['items'][v.oid])) {
      return true;
    } else {
      if(!manage_controllers['items'][v.oid]) {
        eva_sfa_register_update_state(v.oid, redraw_cycle_state);
      }
      manage_controllers['items'][v.oid] = v;
      var cycle = $('<div />', {
        id: v.oid,
        class: 'mng_item_holder'
      });
      var cycle_info = $('<div />', {
        class: 'descr_block'
      }).appendTo(cycle);
      $('<div />', {
        class: 'item_name cycle_s' + v.status,
        id: 'cname_' + v.oid,
        html: v.id
      }).appendTo(cycle_info);
      $('<div />', {
        class: 'item_descr',
        html: v.description
      }).appendTo(cycle_info);
      var cycle_vals = $('<div />', {
        class: 'descr_block'
      }).appendTo(cycle);
      $('<div />', {
        class: 'item_val',
        id: 'cint_' + v.oid,
        html: 'Val = ' + v.interval.toFixed(4) + ' - ' +
          parseFloat(v.avg).toFixed(4) + ' - ' + v.iterations
      }).appendTo(cycle_vals);
      var cycle_btns = $('<div />', {
        class: 'buttons_block'
      }).appendTo(cycle);
      $('<button />', {
        class: 'item_btn btn_start',
        id: 'btn_cycle_start_' + v.oid,
        onclick: 'start_cycle("' +
          manage_controllers['current_controller'] +
          '", "' + v.oid + '")',
        html: 'START'
      }).prop((v.status == 1 ? 'disabled' : ''), 'disabled')
      .appendTo(cycle_btns);
      $('<button />', {
        class: 'item_btn btn_stop',
        id: 'btn_cycle_stop_' + v.oid,
        onclick: 'stop_cycle("' +
          manage_controllers['current_controller'] +
          '", "' + v.oid + '")',
        html: 'STOP'
      }).prop((v.status == 0 ? 'disabled' : ''), 'disabled')
      .appendTo(cycle_btns);
      $('<button />', {
        class: 'item_btn btn_reset',
        onclick: 'reset_cycle_stats("' +
          manage_controllers['current_controller'] +
          '", "' + v.oid + '")',
        html: 'RESET'
      }).appendTo(cycle_btns);
      $('<button />', {
        class: 'item_btn btn_edit',
        id: 'btn_cycle_edit_' + v.oid,
        onclick: 'get_cycle_for_edit("' +
          manage_controllers['current_controller'] +
          '", "' + v.oid + '")',
        html: 'PROPS'
      }).prop((v.status == 1 ? 'disabled' : ''), 'disabled')
      .appendTo(cycle_btns);
      if($('#' + $.escapeSelector(v.oid))[0]) {
        $('#' + $.escapeSelector(v.oid)).html(cycle.html());
      } else {
        ig[manage_controllers['current_item'] + '_' + v.group].append(cycle);
      }
    }
  });
  $.each(Object.keys(manage_controllers["items"]), function(k, v) {
    if(manage_controllers["items"][v] && 
        manage_controllers["items"][v].type == "lcycle" && 
        !cycles_oid_list.includes(v)) {
      $('#'+$.escapeSelector(v)).remove();
      delete manage_controllers["items"][v];
    }
  });
  hideManageGroupHolders(ih);
  var curId = $('#mng_' + manage_controllers['current_item'] + '_group').val();
  showCurrentGroupHolder(curId);
  manage_controllers['reload_cycles'] = true;
}
function insertRuleList(result) {
  if(result.code === 0) {
    var ih = $('#mng_' + manage_controllers['current_item']);
    var ig;
    if($('#mng_' + manage_controllers['current_item'] + '_group')[0]) {
      ig = $('#mng_' + manage_controllers['current_item'] + '_group');
      var options = [];
      for(var i = 0; i < ig[0].options.length; i++) {
        options.push(ig[0].options[i].value)
      }
      $.each(result.data, function(k, v) {
        var id = v.for_item_type + ':' + v.for_item_group;
        if(!options.includes(id)) {
          manage_controllers['items']['rule_groups'][id] = $('<div />', {
            class: 'group_holder',
            id: 'rules_' + id
          }).appendTo(ih);
          $('<option />', {value: id}).html(id)
          .prop((id == manage_controllers['current_group'] ? 
            'selected' : ''), 'selected')
          .appendTo(ig);
        }
      });
    } else {
      var ch = $('<div />', {
        class: 'group_ctrl_holder'
      }).appendTo(ih);
      var ig = $('<select />', {
        id: 'mng_' + manage_controllers['current_item'] + '_group'
      }).change(function() {
        if(this.value == '#:#') {
          ih.find('.group_holder').show();
          manage_controllers['current_group'] = '#:#';
        } else {
          hideManageGroupHolders(ih);
          showCurrentGroupHolder(this.value);
        }
      }).appendTo(ch);
      $('<button />', {
        id: 'mng_' + manage_controllers['current_item'] + '_reload',
        class: 'ctrl_reload_btn'
      }).click(function() {
        manage_controllers['items']['rule_groups'] = [];
        var curType = $(this.closest('.ctrl_holder')).find('.mng_btn_active');
        ih.html('');
        manage_controllers['reload_' + manage_controllers['current_item']] = false;
        curType.click();
      }).html('Reload').appendTo(ch);
      $('<button />', {
        id: 'mng_' + manage_controllers['current_item'] + '_add',
        class: 'add_rule_btn'
      }).click(function() {
        get_macro_for_rule_edit(manage_controllers['current_controller']);
      }).html('Create rule').appendTo(ch);
      $('<option />', {value: '#:#'}).html('#:#').appendTo(ig);
      manage_controllers['items']['rule_groups']['#:#'] = $('<div />', {
          class: 'group_holder',
          id: 'rules_#:#'
      }).appendTo(ih);
      if(!manage_controllers['current_group']) {
        $('#mng_' + manage_controllers['current_item'] + '_group').val('#:#');
      }
    }
    var changed = false;
    var rules_id_list = [];
    $.each(result.data, function(k, v) {
      rules_id_list.push(v.id);
      var id = v.for_item_type + ':' + v.for_item_group;
      if(!$('#rules_' + $.escapeSelector(id))[0]) {
        manage_controllers['items']['rule_groups'][id] = $('<div />', {
          class: 'group_holder',
          id: 'rules_' + id
        }).appendTo(ih);
        $('<option />', {value: id}).html(id)
        .prop((v.for_item_type + ':' + v.for_item_group == 
          manage_controllers['current_group'] ? 'selected' : ''), 'selected')
        .appendTo(ig);
      } else {
        manage_controllers['items']['rule_groups'][id] = 
          $('#rules_' + $.escapeSelector(id));
      }
      if(manage_controllers['reload_rules'] && manage_controllers['items'][v.id] && 
        JSON.stringify(v) == JSON.stringify(manage_controllers['items'][v.id])) {
        return true;
      } else {
        changed = true;
        manage_controllers['items'][v.id] = v;
        var rule = $('<div />', {
          id: 'rule_' + v.id,
          class: 'mng_item_holder'
        });
        var rule_info = $('<div />', {
          class: 'descr_block'
        }).appendTo(rule);
        $('<div />', {
          id: 'rule_priority_' + v.id,
          class: 'item_priority',
          html: v.priority
        }).appendTo(rule_info);
        $('<div />', {
          id: 'rule_id_' + v.id,
          class: 'item_id',
          html: v.id
        }).appendTo(rule_info);
        $('<div />', {
          class: 'item_desc',
          html: v.description
        }).appendTo(rule_info);
        $('<div />', {
          class: 'device_descr',
          html: v.for_oid
        }).appendTo(rule_info);
        var rule_vals = $('<div />', {
          class: 'descr_block'
        }).appendTo(rule);
        var rem = '';
        if (dm_rule_for_expire(v)) {
          rem = ' (expire)';
        } else if (dm_rule_for_set(v)) {
          rem = ' (set)';
        }
        $('<div />', {
          class: 'rule_condition',
          html: v.condition + rem
        }).appendTo(rule_vals);
        $('<div />', {
          class: 'rule_info',
          html:
            'Initial: <b>' + rs_for_init(v.for_initial) +
            '</b>. Break: <b>' + manage_controllers['status_labels']
              ['rule']['break'][v.break_after_exec ? 1 : 0] + '</b>'
        }).appendTo(rule_vals);
        $('<div />', {
          class: 'rule_info',
          html: 'Chillout: <b>' + v.chillout_time + '</b> sec'
        }).appendTo(rule_vals);
        if (v.macro != null) {
          var m = '<b>' + v.macro + '</b>(';
          if (v.macro_args != null) {
            var args = '';
            $.each(v.macro_args, function(k, v) {
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
          if(v.macro_args && Object.keys(v.macro_kwargs).length > 0)
            m += ',';
          if (Object.keys(v.macro_kwargs).length > 0) {
            var kwargs = '';
            $.each(v.macro_kwargs, function(k, v) {
              if (kwargs != '') {
                kwargs += ',';
              }
              var _v = String(v);
              if (_v.indexOf(' ') > -1) {
                _v = '"' + v + '"';
              }
              kwargs += ' ' + String(k) + '=' + _v;
            });
            m += kwargs;
          }
          m += ')';
          $('<div />', {
            class: 'rule_info',
            html: 'Macro: ' + m + ''
          }).appendTo(rule_vals);
        }
        var rule_buttons = $('<div />', {
          class: 'buttons_block'
        }).appendTo(rule);
        $('<button />', {
          id: 'btn_rule_enable_' + v.id,
          class: 'item_btn' + 
            (v.enabled == 0 ? ' btn_disable' : ' active btn_enable'),
          onclick: 'enable_disable_rule("' +
            manage_controllers['current_controller'] + 
            '", "' + v.id + '", ' +
            (v.enabled == 0 ? 1 : 0) + ')',
          html: v.enabled == 0 ? 'DISABLED' : 'ENABLED'
        }).appendTo(rule_buttons);
        $('<button />', {
          id: 'btn_rule_edit_' + v.id,
          class: 'item_btn',
          onclick: 'get_macro_for_rule_edit("' +
            manage_controllers['current_controller'] +
            '", "' + v.id + '")',
          html: 'EDIT'
        }).appendTo(rule_buttons);
        $('<button />', {
          id: 'btn_rule_delete_' + v.id,
          class: 'item_btn',
          onclick: 'ask_del_rule("' +
            manage_controllers['current_controller'] +
            '", "' + v.id + '")',
          html: 'DELETE'
        }).appendTo(rule_buttons);
      }
      if($('#rule_' + v.id)[0]) {
        $('#rule_' + v.id).html(rule.html());
      } else {
        manage_controllers['items']['rule_groups'][id].append(rule);
      }
    });
    $.each(Object.keys(manage_controllers["items"]), function(k, v) {
      if(manage_controllers["items"][v] && 
          manage_controllers["items"][v].type == "dmatrix_rule" && 
          !rules_id_list.includes(v)) {
        redraw_deleted_rule(v);
      }
    });
    if(changed) {
      var current_rule_group = ig.val();
      ig.html(ig.find('option').sort(function(x, y) {
        return $(x).text() > $(y).text() ? 1 : -1;
      }));
      ig.val(current_rule_group);
    }
    hideManageGroupHolders(ih);
    var curId = $('#mng_' + manage_controllers['current_item'] + '_group').val();
    if(curId == '#:#') {
      ih.find('.group_holder').show();
    } else {
      showCurrentGroupHolder(curId);
    }
    manage_controllers['reload_rules'] = true;
  } else {
    $popup('error', 'ERROR', 'Unable to show rules. Result: ' + result.error)
  }
}

function enable_disable_unit(id, oid, s) {
  $call(id, s+'_actions', {i: oid}, function(res) {
    var data = res.data;
    if(data && data.ok) {
      manage_controllers['items'][oid].action_enabled = 
        s == 'enable' ? true : false;
      manage_controllers["current_controller"] = id;
    } else {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'ERROR changing unit state. </br>Result: ' + data.error + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. State not changed</div>');
  });
}
function enable_disable_sensor(id, oid, s) {
  $call(id, 'update', {
      i:oid,
      s: s
    }, function(res) {
      var data = res.data;
      if(data && data.ok) {
        manage_controllers['items'][oid].status = s === 1 ? 1 : 0;
      } else {
        $popup('error', 'ERROR', '<div class="content_msg">' +
          'ERROR changing sensor state. </br>Result: ' + data.error + '</div>');
      }
    }, function(res) {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. State not changed</div>');
    }
  );
}
function enable_disable_macro(id, oid, s) {
  $call(id, 'set_macro_prop', {
      i: oid, 
      p: 'action_enabled', 
      v: s
    }, function(res) {
      var data = res.data;
      if(data && data.ok) {
        manage_controllers['items'][oid].action_enabled = 
          s === 1 ? true : false;
        redraw_enable_macro_btn(id, oid);
      } else {
        $popup('error', 'ERROR', '<div class="content_msg">' +
          'ERROR changing macro state.</br>Result: ' + data.error + '</div>');
      }
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. State not changed</div>');
    }
  );
}
function enable_disable_rule(id, i, e) {
  $call(id, 'set_rule_prop', {
      i: i,
      p: 'enabled',
      v: e
    }, function(res) {
      var data = res.data;
      if(data && data.ok) {
        manage_controllers['items'][i].enabled = (e == 1 ? true : false);
        var btn = $('#btn_rule_enable_' + i);
        if (e == 1) {
          btn.removeClass('btn_disable');
          btn.addClass('active btn_enable');
        } else {
          btn.removeClass('active btn_enable');
          btn.addClass('btn_disable');
        }
        btn.attr( 'onclick', 'enable_disable_rule("' + 
          id + '", "' + i + '", ' + (e == 0 ? 1 : 0) + ')'
        );
        btn.html(e == 0 ? 'DISABLED' : 'ENABLED');
      } else {
        $popup('error', 'ERROR', '<div class="content_msg">' +
          'Parameter not changed. </br>Result: ' + data.error + '</div>');
      }
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. Parameter not changed</div>');
    }
  );
}

function create_unit() {
  var group = $('#unit_group').val();
  var name = $('#unit_name').val();
  var id = manage_controllers['current_controller'];
  $call(id, 'create_unit', {
      i: name,
      g: group
    }, function(res) {
      var data = res.data;
      var msg = '<div class="content_msg">';
      if (data && data.id) {
        if ('pt' in data && data.pt == 'denied') {
          msg += 'Current action can not be terminated</div>';
          var title = 'ERROR';
          var popt = 'error';
          $popup(popt, title, msg);
        } else {
          reload_controller(manage_controllers['current_controller']);
          update_unit_state(manage_controllers['current_controller'], 
            data.oid, true);
        }
      } else {
        msg += 'Create command failed. Result: ' + data.result + '</div>';
        $popup('error', 'ERROR', msg);
      }
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' + 
        'Server error. Create command failed</div>');
    }
  );
}
function update_unit_state(id, oid, isCreate) {
  var s = $('#set_unit_state')[0].unit_status.value;
  var v = $('#unit_value').val();
  $call(id, 'update', {
      i: oid,
      s: s,
      v: v
    }, function(res) {
      var data = res.data;
      var msg = '<div class="content_msg">';
      if (res.data && res.data.ok) {
        if(isCreate) {
          msg += 'Unit successfully created</div>';
          $popup('info', 'SUCCESS', msg);
        } else {
          manage_controllers['items'][oid].status = s;
          manage_controllers['items'][oid].value = v;
          manage_controllers["current_controller"] = id;
        }
      } else {
        msg += 'Unit state not changed. Result: ' + res.result + '</div>';
        $popup('error', 'ERROR', msg);
      }
    }, 
    function() {
      $popup('error', 'ERROR', '<div class="content_msg">Server error</div>');
    }
  );
}
function unit_on_off(e, id, oid, s) {
  e.preventDefault();
  var btn = $('#btn_' + $.escapeSelector(oid));
  btn.attr('disabled', 'disabled');
  $call(id, 'action', {
      i:oid,
      s: s,
      w: "120"
    }, function(res) {
      var data = res.data;
      if (data.status == 'completed') {
        btn.attr('onclick', 'unit_on_off(event, "' + 
            manage_controllers["current_controller"] + 
            '", "' + oid + '", ' + (1 - s) + ')');
        btn.prop('checked', s == 1);
        btn.removeAttr('disabled');
      } else {
        var r = 'error';
        if (data.status == 'running') {
          r = 'confirm';
        }
        $popup(r, 'ACTION RESULT', '<div class="content_msg">' +
          'Action result: ' + data.status + '</div>');
        btn.removeAttr('disabled');
      }
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. Parameter not changed</div>');
    }
  );
}
function kill_unit(id, oid) {
  $call(id, 'kill', {i: oid}, function(res) {
    var data = res.data;
    var msg = '<div class="content_msg">';
    if (data && data.ok) {
      msg += 'All actions of ' + oid + ' killed';
      var title = 'KILLED ' + oid;
      var popt = 'info';
      if ('pt' in data && data.pt == 'denied') {
        msg = '<div class="content_msg">' +
          'Current action can not be terminated ' +
          'because action_allow_termination is false';
        title = 'WARNING';
        popt = 'warning';
      }
      $popup(popt, title, msg + '.<br /><br /> Action queue cleared.</div>');
    } else {
      $popup('error', 'ERROR', msg + 'Kill command failed for ' + oid +
        '. Result: ' + data.result + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Kill command failed</div>');
  });
}
function remove_unit(id, oid) {
  $call(id, 'destroy', {i: oid}, function(res) {
    var data = res.data;
    if (data && data.ok) {
      $('#' + $.escapeSelector(oid)).remove();
      var cur_group = $('#mng_units_group').val();
      if($('#units_' + $.escapeSelector(cur_group)).html() == "") {
        $('#mng_units_group option[value=' +
          $.escapeSelector(cur_group) + ']').remove();
        $('#units_' + $.escapeSelector(cur_group)).remove();
        $('#mng_units_group').val($('#mng_units_group option')[0].value).
          trigger('change');
      }
    } else {
      var msg = '<div class="content_msg">'+ 'Remove command failed for ' + 
        oid + '. Result: ' + data.result + '</div>';
      $popup('error', 'ERROR', msg );
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Remove command failed</div>');
  });
}

function create_sensor() {
  var group = $('#sensor_group').val();
  var name = $('#sensor_name').val();
  var id = manage_controllers['current_controller'];
  $call(id, 'create_sensor', {i: name, g: group}, function(res) {
    var data = res.data;
    var msg = '<div class="content_msg">';
    if (data && data.id) {
      msg += 'Sensor created';
      var title = 'SUCCESS';
      var popt = 'info';
      if ('pt' in data && data.pt == 'denied') {
        msg = '<div class="content_msg">' +
          'Current action can not be terminated<br />';
        title = 'ERROR';
        popt = 'error';
      }
      msg += '</div>';
      reload_controller(manage_controllers['current_controller']);
      $popup(popt, title, msg);
    } else {
      $popup('error', 'ERROR', msg +
        'Create command failed. Result: ' + data.result + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Create command failed</div>');
  });
}
function remove_sensor(id, oid) {
  $call(id, 'destroy', {i: oid}, function(res) {
    var data = res.data;
    if (data && data.ok) {
      $('#' + $.escapeSelector(oid)).remove();
      var cur_group = $('#mng_sensors_group').val();
      if($('#sensors_' + $.escapeSelector(cur_group)).html() == "") {
        $('#mng_sensors_group option[value=' +
          $.escapeSelector(cur_group) + ']').remove();
        $('#sensors_' + $.escapeSelector(cur_group)).remove();
        $('#mng_sensors_group').val($('#mng_sensors_group option')[0].value).
          trigger('change');
      }
    } else {
      var msg = '<div class="content_msg">'+ 'Remove command failed for ' + 
        oid + '. Result: ' + data.result + '</div>';
      $popup('error', 'ERROR', msg );
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Remove command failed</div>');
  });
}

function create_lvar() {
  var group = $('#lvar_group').val();
  var name = $('#lvar_name').val();
  // var s = $('#set_lvar_state')[0].lvar_status.value;
  // var v = $('#lvar_value').val();
  var id = manage_controllers['current_controller'];
  $call(id, 'create_lvar', {
      i: name, 
      g: group, 
      // s: s, 
      // v: v
    }, function(res) {
      var data = res.data;
      var msg = '<div class="content_msg">';
      if (data && data.id) {
        var title = 'SUCCESS';
        var popt = 'info';
        msg += 'Lvar successfully created</div>';
        if ('pt' in data && data.pt == 'denied') {
          msg = '<div class="content_msg">' +
            'Current action can not be terminated</div>';
          title = 'ERROR';
          popt = 'error';
          $popup(popt, title, msg);
        } else {
          reload_controller(manage_controllers['current_controller']);
          set_lvar_state(manage_controllers['current_controller'], 
            data.oid, true);
        }
        // $popup(popt, title, msg);
      } else {
        msg += 'Create command failed. Result: ' + data.result + '</div>';
        $popup('error', 'ERROR', msg);
      }
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. Create command failed</div>');
    }
  );
}
function set_lvar_state(id, oid, isCreate) {
  var s = $('#set_lvar_state')[0].lvar_status.value;
  var v = $('#lvar_value').val();
  $call(id, 'set', {i: oid, s: s, v: v}, 
    function(res) {
      var data = res.data;
      var msg = '<div class="content_msg">';
      if (data && data.ok) {
        if(isCreate) {
          msg += 'Lvar successfully created</div>';
          $popup('info', 'SUCCESS', msg);
        } else {
          manage_controllers['items'][oid].status = s;
          if(s == 1) {
            manage_controllers['items'][oid].value = v;
          }
          redraw_lvar_state(manage_controllers['items'][oid]);
        }
      } else {
        msg += 'LVar not changed. </br>Result: ' + data.error + '</div>';
        $popup('error', 'ERROR', msg);
      }
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. LVar not changed</div>');
    }
  );
}
function remove_lvar(id, oid) {
  $call(id, 'destroy_lvar', {i: oid}, function(res) {
    var data = res.data;
    if (data && data.ok) {
      $('#' + $.escapeSelector(oid)).remove();
      var cur_group = $('#mng_lvars_group').val();
      if($('#lvars_' + $.escapeSelector(cur_group)).html() == "") {
        $('#mng_lvars_group option[value=' +
          $.escapeSelector(cur_group) + ']').remove();
        $('#lvars_' + $.escapeSelector(cur_group)).remove();
        $('#mng_lvars_group').val($('#mng_lvars_group option')[0].value).
          trigger('change');
      }
    } else {
      var msg = '<div class="content_msg">'+ 'Remove command failed for ' + 
        oid + '. Result: ' + data.result + '</div>';
      $popup('error', 'ERROR', msg );
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Remove command failed</div>');
  });
}

function create_macro() {
  var group = $('#macro_group').val();
  var name = $('#macro_name').val();
  var id = manage_controllers['current_controller'];
  $call(id, 'create_macro', {i: name, g: group}, function(res) {
    var data = res.data;
    var msg = '<div class="content_msg">';
    if (data && data.id) {
      if ('pt' in data && data.pt == 'denied') {
        msg = '<div class="content_msg">' +
          'Current action can not be terminated<br />';
        var title = 'ERROR';
        var popt = 'error';
        msg += '</div>';
        $popup(popt, title, msg);
      } else {
        edit_macro(manage_controllers['current_controller'], data.oid, true);
      }
    } else {
      $popup('error', 'ERROR', msg +
        'Create command failed. Result: ' + data.result + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Create command failed</div>');
  });
}
function run_macro(id, oid) {
  var btn = $('#btn_macro_run_' + $.escapeSelector(oid));
  var args = $('#macro_run_args').val();
  btn.attr('disabled', 'disabled');
  btn.addClass('disabled');
  $call(id, 'run', {
    i: manage_controllers['items'][oid].id, 
    a: args, 
    w: "120"
  }, function(res) {
      var data = res.data;
      if (data.status != 'completed') {
        var r = 'error';
        if (data.status == 'running') {
          r = 'confirm';
        }
        $popup(r, 'ACTION RESULT', '<div class="content_msg">' +
          'Action result: ' + data.status + '</div>');
      }
      btn.removeAttr('disabled');
      btn.removeClass('disabled');
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. Macro not runned</div>');
      btn.removeAttr('disabled');
      btn.removeClass('disabled');
    }
  );
}
function edit_macro(id, oid, isCreate) {
  var action_enabled = $('#action_enabled').is(':checked');
  var action_exec = $('#action_exec').val();
  var pass_errors = $('#pass_errors').is(':checked');
  var send_critical = $('#send_critical').is(':checked');
  $call(id, 'set_macro_prop', { i: oid, p: '', v: {
      'action_enabled': action_enabled,
      'action_exec': (action_exec != '' ? action_exec : null),
      'pass_errors': pass_errors,
      'send_critical': send_critical
    } }, function(res) {
    var data = res.data;
    var msg = '<div class="content_msg">';
    if(data && data.ok) {
      $call(id, 'groups_macro', null , insertGroups, $log);
      if(isCreate) {
        msg += 'Macro created successfully</div>';
        $popup('info', 'SUCCESS', msg);
      } else {
        msg += 'Result: props set successfully</div>';
        $popup('info', 'SUCCESS', msg);
      }
    } else {
      msg += 'Unable set props. Result: ' + data.result + '</div>';
      $popup('error', 'ERROR', msg);
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Unable to set macro props</div>');
  });
}

function create_cycle() {
  var id = manage_controllers['current_controller'];
  var group = $('#cycle_group').val();
  var name = $('#cycle_name').val();
  var autostart = $('#cycle_autostart').is(':checked');
  var ict = $('#cycle_ict').val();
  var interval = $('#cycle_interval').val();
  var macro = $('#cycle_macro').val();
  var v = {
    'autostart': autostart,
    'interval': interval,
    'macro': macro
  }
  if(ict)
    v.ict = ict;
  $call(id, 'create_cycle', {i: name, g: group, v: v}, function(res) {
    var data = res.data;
    var msg = '<div class="content_msg">';
    if (data && data.id) {
      var title = 'SUCCESS';
      var popt = 'info';
      msg += 'Cycle successfully created</div>';
      if ('pt' in data && data.pt == 'denied') {
        msg = '<div class="content_msg">' +
          'Current action can not be terminated<br />';
        title = 'ERROR';
        popt = 'error';
        msg += '</div>';
      }
      $popup(popt, title, msg);
      reload_controller(manage_controllers['current_controller']);
    } else {
      $popup('error', 'ERROR', msg +
        'Create command failed. Result: ' + data.result + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Create command failed</div>');
  });
}
function start_cycle(id, oid) {
  $call(id, 'start_cycle', {i: oid}, function(res) {
    var data = res.data;
    if (data && data.ok) {
      manage_controllers['items'][oid].status = 1
      redraw_cycle_state(manage_controllers['items'][oid])
    } else {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Start command failed for<br />' + oid + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Start command failed for<br />' + oid + '</div>');
  });
}
function stop_cycle(id, oid) {
  $call(id, 'stop_cycle', {i: oid}, function(res) {
    var data = res.data;
    if (data && data.ok) {
      manage_controllers['items'][oid].status = 0
      redraw_cycle_state(manage_controllers['items'][oid])
    } else {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Stop command failed for<br />' + oid + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Stop command failed for<br />' + oid + '<div>');
  });
}
function reset_cycle_stats(id, oid) {
  $call(id, 'reset_cycle_stats', {i: oid}, function(res) {
    var data = res.data;
    if (data && data.ok) {
      manage_controllers['items'][oid].iterations = 0;
      redraw_cycle_state(manage_controllers['items'][oid]);
    } else {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Reset stats command failed for<br />' + oid + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR','<div class="content_msg">' +
      'Server error. Reset stats command failed for<br />' + oid + '</div>');
  });
}
function edit_cycle(id, oid) {
  var autostart = $('#cycle_autostart').is(':checked');
  var ict = $('#cycle_ict').val();
  var interval = $('#cycle_interval').val();
  var macro = $('#cycle_macro').val();
  if (macro == '') {
    macro = null;
  }
  var v = {
    'autostart': autostart,
    'interval': interval,
    'macro': macro
  }
  if(ict)
    v.ict = ict;
  $call(id, 'set_cycle_prop', {
      i: oid, 
      p: '', 
      v: v
    }, function(res) {
      var data = res.data;
      var popt = 'info';
      var title = 'SUCCESS';
      var msg = '<div class="content_msg">';
      if(data && data.ok) {
        msg += 'Result: props set successfully</div>';
      } else {
        popt = 'error';
        title = 'ERROR';
        msg += 'Unable set props. Result: ' + data.result + '</div>';
      }
      $popup(popt, title, msg);
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
          'Server error. Unable to set cycle props</div>');
    }
  );
}

function set_rule_props_ae(id, i) {
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
  var f = 'create_rule';
  if (i !== undefined && i != 'undefined') {
    f = 'set_rule_prop';
    d.i = i;
  }
  $call(id, f, {i: i, v: rule}, function(res) {
      if(res && res.code === 0) {
        var data = res.data;
        if (data && data.ok) {
          // rule props changed successfully
        }
      } else {
        $popup('error', 'ERROR', '<div class="content_msg">' +
          'Unable to process rule</div>');
      }
      $call(id, 'list_rules', null ,insertRuleList, function() {
        load_error('remote rules');
      });
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. Unable to process rule</div>');
      $call(id, 'list_rules', null ,insertRuleList, function() {
        load_error('remote rules');
      });
    }
  );
}
function del_rule(id, i) {
  $call(id, 'destroy_rule', {i: i}, function(res) {
    var data = res.data;
    if(data && data.ok) {
      redraw_deleted_rule(i);
    } else {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Unable to delete rule. Result: ' + data.result + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Unable to delete rule</div>');
  });
}


function redraw_unit(v) {
  eoid = $.escapeSelector(v.oid);
  // var btn = $('#btn_' + eoid);
  // btn.attr('onclick', 'unit_on_off(event, "' + 
  //     manage_controllers["current_controller"] + 
  //     '", "' + v.oid + '", ' + (1 - eva_sfa_states[v.oid].status) + ')');
  // btn.prop('checked', eva_sfa_states[v.oid].status == 1);
  if (eva_sfa_states[v.oid].status != -1) {
    $('[id="uname_' + eoid + '"]').removeClass('device-error');
  } else {
    $('[id="uname_' + eoid + '"]').addClass('device-error');
  }
  var eb = $('[id="btn_enable_' + eoid + '"]');
  if (eva_sfa_states[v.oid].action_enabled) {
    eb.html('ENABLED');
    eb.removeClass('btn_disable').addClass('btn_enable active');
    eb.attr('onclick', 'enable_disable_unit("' + 
      v.controller_id + '", "' + v.oid + '", "disable")');
    // btn.removeAttr('disabled');
  } else {
    eb.html('DISABLED');
    eb.removeClass('active btn_enable').addClass('btn_disable');
    eb.attr('onclick', 'enable_disable_unit("' + 
      v.controller_id + '", "' + v.oid + '", "enable")');
    // btn.attr('disabled', 'disabled');
  }
}
function redraw_enable_sensor_btn(v) {
  // manage_controllers['items'][v.oid] = eva_sfa_states[v.oid];
  var btn = $('#btn_' + $.escapeSelector(v.oid));
  if(eva_sfa_states[v.oid].status === 1) {
    btn.removeClass('btn_disable');
    btn.addClass('btn_enable');
    btn.attr('onclick' , 'enable_disable_sensor("' + v.controller_id +
      '", "' + v.oid + '", 0)');
    btn.html('ENABLED');
  } else {
    btn.addClass('btn_disable');
    btn.removeClass('btn_enable');
    btn.attr('onclick' , 'enable_disable_sensor("' + v.controller_id +
      '", "' + v.oid + '", 1)');
    btn.html('DISABLED');
  }
}
function redraw_lvar_state(v) {
  var eoid = $.escapeSelector(v.oid);
  for (a = -1; a <= 1; a++) {
    if (eva_sfa_states[v.oid].status != a) {
      $('#lname_' + eoid).removeClass('lvar_s' + a);
    } else {
      $('#lname_' + eoid).addClass('lvar_s' + a);
    }
  }
  $('#lval_' + eoid).html('Val = ' + eva_sfa_states[v.oid].value);
  var rb = $('#lvar_expires_' + eoid);
  if (eva_sfa_states[v.oid].expires > 0) {
    rb.show();
  } else {
    rb.hide();
  }
  $('#lval_expires_' + eoid).html(
    format_expire_time(eva_sfa_states[v.oid])
  );
}
function redraw_enable_macro_btn(id, oid) {
  var btn = $('#macro_enable_' + $.escapeSelector(oid));
    btn.toggleClass('btn_enable');
    btn.toggleClass('btn_disable');
  if(manage_controllers['items'][oid].action_enabled) {
    btn.attr('onclick' , 
      'enable_disable_macro("' + id + '", "' + oid + '", 0)');
    btn.html('ENABLED');
    $('#btn_macro_run_' + $.escapeSelector(oid)).removeAttr('disabled');
  } else {
    btn.attr('onclick' , 
      'enable_disable_macro("' + id + '", "' + oid + '", 1)');
    btn.html('DISABLED');
    $('#btn_macro_run_' + $.escapeSelector(oid)).attr('disabled', 'disabled');
  } 
}
function redraw_cycle_state(v) {
  var eoid = $.escapeSelector(v.oid);
  for (a = 0; a <= 2; a++) {
    if (eva_sfa_states[v.oid].status != a) {
      $('#cname_' + eoid).removeClass('cycle_s' + a);
    } else {
      $('#cname_' + eoid).addClass('cycle_s' + a);
    }
  }
  $('#cint_' + eoid).html('Val = ' + 
    eva_sfa_states[v.oid].interval.toFixed(4) + ' - ' +
    parseFloat(eva_sfa_states[v.oid].avg).toFixed(4) + ' - ' + 
    eva_sfa_states[v.oid].iterations
  );
  if (eva_sfa_states[v.oid].status != 0) {
    $('#btn_cycle_stop_' + eoid).removeAttr('disabled');
    $('#btn_cycle_start_' + eoid).attr('disabled', 'disabled');
    $('#btn_cycle_edit_' + eoid).attr('disabled', 'disabled');
  } else {
    $('#btn_cycle_start_' + eoid).removeAttr('disabled');
    $('#btn_cycle_edit_' + eoid).removeAttr('disabled');
    $('#btn_cycle_stop_' + eoid).attr('disabled', 'disabled');
  }
}
function redraw_deleted_rule(i) {
  var cur_group = $('#mng_rules_group').val();
  var rule_group = $('#rule_' + i).parent()[0].id;
  $('#rule_' + i).remove();
  delete manage_controllers["items"][i];
  if(cur_group != '#:#') {
    if($('#rules_' + $.escapeSelector(cur_group)).html() == "") {
      $('#mng_rules_group option[value=' +
        $.escapeSelector(cur_group) + ']').remove();
      $('#mng_rules_group').val('#:#').trigger('change');
    }
  } else if($('#' + $.escapeSelector(rule_group)).html() == "") {
    $('#mng_rules_group option[value=' +
      $.escapeSelector(rule_group).substr(6) + ']').remove();
  }
}


function ask_kill_unit(id, oid) {
  $popup('confirm', 'KILL ' + oid, '<div class="content_msg">' +
    'Terminate ALL running and queued actions?</div>', {
      btn1: 'YES',
      btn1a: function() {
        var val = '$masterkey';
        if (!$('#controller_masterkey_local').is(':checked')) {
          val = $('#controller_masterkey').val();
        }
        kill_unit(id, oid);
      },
      btn2: 'NO'
    }
  );
}
function ask_remove_unit(id, oid) {
  $popup('confirm', 'Remove ' + oid, '<div class="content_msg">' +
    'Do you realy want to remove ' + oid + '?</div>', {
      btn1: 'OK',
      btn1a: function() {
        remove_unit(id, oid);
      },
      btn2: 'CANCEL'
    }
  );
}
function unit_state_dialog(id, oid) {
  var html = '<form class="form-horizontal" id="set_unit_state">';
  if(!id) {
    html +=
      // line 1
      '<div class="form-group">' +
      '<label class="control-label"' +
      ' for="unit_group">Group:</label>' +
      '<input class="form-control" type="text" size="5"' +
      'id="unit_group" value="" /></div>' +
      // line 2
      '<div class="form-group">' +
      '<label class="control-label"' +
      ' for="unit_name">Name:</label>' +
      '<input class="form-control" type="text" size="5"' +
      'id="unit_name" value="" /></div>';
  }
  html +=
    '<div class="form-group">' +
    '<label for="unit_status">Status</label>' +
    '<div class="form_radio_holder" id="unit_status"><div>';

  $.each(manage_controllers['status_labels']['units'], function(_k, v) {
    html += '<input type="radio" name="unit_status" class="form_radio" ' +
      'id="radio_' + _k + '" value="' + _k + '"';
    if (oid && _k == manage_controllers['items'][oid].status ||
        !oid && _k ==0)
      html += ' checked';
    html += '><label for="radio_' + _k + '">' + v + '</label>' +
      '<label class="bg_col"></label>';
  });
  var val = ""
  if(oid)
    val = manage_controllers['items'][oid].value;
  html += '</div></div></div>' + 
    '<div class="form-group">' +
    '<label for="unit_value">Value</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="unit_value" value="' + val + '" /></div></form>';
  $popup('confirm', (id ? 'Set state of ' + oid : 'Create unit'), 
    html, {
      btn1:'OK',
      btn2: 'CANCEL',
      btn1a: function() {
        if(id) {
          update_unit_state(id, oid);
        } else {
          create_unit();
        }
      }
    }
  );
  if(!id)
    $('#unit_group').focus();
}

function create_sensor_dialog() {
  var html =
    '<form class="form-horizontal">' +
    // line 1
    '<div class="form-group">' +
    '<label class="control-label"' +
    ' for="sensor_group">Group:</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="sensor_group" value="" /></div>' +
    // line 2
    '<div class="form-group">' +
    '<label class="control-label"' +
    ' for="sensor_name">Name:</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="sensor_name" value="" /></div></form>';
  $popup('confirm', 'Create sensor',
    html, {
      btn1: 'CREATE',
      btn2: 'CANCEL',
      btn1a: function() {
        create_sensor();
      }
    }
  );
  $('#sensor_group').focus();
}
function ask_remove_sensor(id, oid) {
  $popup('confirm', 'Remove ' + oid, '<div class="content_msg">' +
    'Do you realy want to remove ' + oid + '?</div>', {
      btn1: 'OK',
      btn1a: function() {
        remove_sensor(id, oid);
      },
      btn2: 'CANCEL'
    }
  );
}

function select_lvar_state(id, oid) {
  var html = '<form class="form-horizontal" id="set_lvar_state">';
  if(!id) {
    html += '<div class="form-group">' +
      '<label class="control-label"' +
      ' for="lvar_group">Group:</label>' +
      '<input class="form-control" type="text" size="5"' +
      'id="lvar_group" value="" /></div>' +
      // line 2
      '<div class="form-group">' +
      '<label class="control-label"' +
      ' for="lvar_name">Name:</label>' +
      '<input class="form-control" type="text" size="5"' +
      'id="lvar_name" value="" /></div>';
  }
  html +=
    // line 3
    '<div class="form-group">' +
    '<label>Status</label>' +
    '<div class="form_radio_holder"><div>';
  $.each(manage_controllers['status_labels']['lvars'], function(_k, v) {
    html += '<input type="radio" name="lvar_status" class="form_radio" ' +
      'id="radio_' + _k + '" value="' + _k + '"';
    if (oid && _k == manage_controllers['items'][oid].status || 
        !oid && _k == 1) 
      html += ' checked';
    html += '><label for="radio_' + _k + '">' + v + '</label>' +
      '<label class="bg_col"></label>';
  });
  var value = "";
  if(oid)
    value = manage_controllers['items'][oid].value;
  html +=
    '</div></div></div>' +
    // line 4
    '<div class="form-group">' +
    '<label for="lvar_value">Value</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="lvar_value" value="' + value + '" /></div></form>';
  $popup('confirm', (id ? 'Set state of ' + oid : 'Create lvar'), 
    html, {
      btn1: 'OK',
      btn2: 'CANCEL',
      btn1a: function() {
        if(id) {
          set_lvar_state(id, oid);
        } else {
          create_lvar();
        }
      }
    }
  );
  if(!id)
    $('#lvar_group').focus();
}
function ask_remove_lvar(id, oid) {
  $popup('confirm', 'Remove ' + oid, '<div class="content_msg">' +
    'Do you realy want to remove ' + oid + '?</div>', {
      btn1: 'OK',
      btn1a: function() {
        remove_lvar(id, oid);
      },
      btn2: 'CANCEL'
    }
  );
}

function prepare_macro_run(id, oid) {
  var html =
    '<form class="form-horizontal">' +
    '<div class="form-group">' +
    '<label for="lvar_value">Run args:</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="macro_run_args" value="" /></div></form>';
  $popup('confirm', 'Run macro "' + 
    manage_controllers['items'][oid].id + '"',
    html, {
      btn1: 'RUN',
      btn2: 'CANCEL',
      btn1a: function() {
        run_macro(id, oid);
      }
    }
  );
  $('#macro_run_args').focus();
}
function get_macro_props_for_edit(id, oid) {
  $call(id, 'list_macro_props', { i: oid }, function(res) {
    var data = res.data;
    if(data && res.code === 0) {
      edit_macro_dialog(id, oid, data);
    } else {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Unable get props. Result: ' + data.result + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">' +
      'Server error. Unable to get macro props</div>');
  });
}
function edit_macro_dialog(id, oid, props) {
  var html = '<form class="form-horizontal">';
  if(!id) {
    html +=
    // line 1
    '<div class="form-group">' +
    '<label class="control-label"' +
    ' for="macro_group">Group:</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="macro_group" value="" /></div>' +
    // line 2
    '<div class="form-group">' +
    '<label class="control-label"' +
    ' for="macro_name">Name:</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="macro_name" value="" /></div>';
  }
  html +=
    // line 3
    '<div class="form-group">' +
    '<label class="control-label">Action enabled:</label>' +
    '<div class="custom_chbox_holder">' +
    '<input class="custom_chbox" type="checkbox" ' +
    'id="action_enabled" ';
  if(props) {
    html += props.action_enabled?'checked':'';
  } else {
    html += 'checked';
  }
  html += '/>' +
    '<label for="action_enabled"></label></div></div>' +
    // line 4
    '<div class="form-group">' +
    '<label class="control-label"' +
    'for="action_exec">Action exec:</label>' +
    '<input class="form-control" type="text"' +
    'id="action_exec" value="'; 
  if(props)
    html += props.action_exec != null ? props.action_exec : "";
  html += '"/></div>' +
    // line 5
    '<div class="form-group row">' +
    '<div class="col-6"' +
    '<label class="control-label">Pass errors:</label>' +
    '<div class="custom_chbox_holder">' +
    '<input class="custom_chbox" type="checkbox" ' +
    'id="pass_errors" ';
  if(props)
    html += props.pass_errors?'checked':'';
  html += '/>' +
    '<label for="pass_errors"></label></div></div>' +
    // line 5.5
    '<div class="col-6"' +
    '<label class="control-label">Send critical:</label>' +
    '<div class="custom_chbox_holder">' +
    '<input class="custom_chbox" type="checkbox" ' +
    'id="send_critical" ';
  if(props)
    html += props.send_critical?'checked':'';
  html += '/>' +
    '<label for="send_critical"></label></div></div></div></form>';
  $popup('confirm', (id ? 'Edit': 'Create') + ' macro',
    html, {
      btn1: 'OK',
      btn2: 'CANCEL',
      btn1a: function() {
        if(id) {
          edit_macro(id, oid);
        } else {
          create_macro();
        }
      }
    }
  );
  if(!id) {
    $('#macro_group').focus();
  }
}

function get_cycle_for_edit(id, oid) {
  if(!manage_controllers['reload_macros']) {
    $call(manage_controllers['current_controller'], 'list_macros', 
      null, function(res) {
        insertMacrosList(res);
        get_cycle_props_for_edit(id, oid);
      }, function() {
        load_error('macros');
    });
  } else {
    get_cycle_props_for_edit(id, oid);
  }
}
function get_cycle_props_for_edit(id, oid) {
  if(id) {
    $call(id, 'list_cycle_props', { i: oid }, function(res) {
      var data = res.data;
      if(data && res.code === 0) {
        edit_cycle_dialog(id, oid, data);
      } else {
        $popup('error', 'ERROR', '<div class="content_msg">' +
          'Unable get props. Result: ' + data.result + '</div>');
      }
    }, function() {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Server error. Unable to get cycle props</div>');
    });
  } else {
    edit_cycle_dialog();
  }
}
function edit_cycle_dialog(id, oid, props) {
  var html = '<form class="form-horizontal">';
  if(!id) {
    html +=
      // line 1
      '<div class="form-group">' +
      '<label class="control-label" for="cycle_group">Group:</label>' +
      '<input class="form-control" type="text" size="5"' +
      'id="cycle_group" value="" /></div>' +
      // line 2
      '<div class="form-group">' +
      '<label class="control-label" for="cycle_name">Name:</label>' +
      '<input class="form-control" type="text" size="5"' +
      'id="cycle_name" value="" /></div>';
  }
  html +=
    // line 3
    '<div class="form-group">' +
    '<label class="control-label">Autostart:</label>' +
    '<div class="custom_chbox_holder">' +
    '<input class="custom_chbox" type="checkbox" ' +
    'id="cycle_autostart" ';
  if(props)
    html += props.autostart?'checked':'';
  html += '/>' +
    '<label for="cycle_autostart"></label></div></div>' +
    // line 4
    '<div class="form-group row">' +
    '<div class="col-6">' +
    '<label class="control-label"' +
    'id="l_cycle_ict" for="cycle_ict">ICT:</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="cycle_ict" value="';
  if(props)
    html += props.ict;
  html += '"/></div>' +
    // line 4.5
    '<div class="col-6">' +
    '<label class="control-label" id="l_cycle_interval" ' +
    'for="cycle_interval">Interval:</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="cycle_interval" value="';
  if(props)
    html += props.interval;
  html += '"/></div></div>' +
    // line 5
    '<div class="form-group">' +
    '<label class="control-label" for="cycle_macro">Macro:</label>' +
    '<select class="form-control" id="cycle_macro" ' +
    'onchange="type_macro(this)">' +
    '<option value="">select</option>';
    for(var i in manage_controllers["items"]) {
      if(i.startsWith('lmacro')) {
        html += '<option value="' + i + '"';
        if(props && 'lmacro:' + props.macro === i) {
          html += ' selected ';
        }
        html += '>' + i.substr(7) + '</option>';
      }
    }
  html += '</select></div>';
  // line 6
  html += '<div class="form-group">' +
    '<input id="macro_custom" class="form-control" type="text"';

  if(!props || props && (props.macro == null || 
      Object.keys(manage_controllers["items"])
        .includes('lmacro:' + props.macro)))
    html += ' style="display:none"';

  html += '/></div></form>';
  $popup('confirm', (id ? 'Edit' : 'Create') + ' cycle',
    html, {
      btn1: 'OK',
      btn2: 'CANCEL',
      btn1a: function() {
        if(id) {
          edit_cycle(id, oid);
        } else {
          create_cycle();
        }
      },
      va: validate_cycle_dialog
    }
  );
  if(!id)
    $('#cycle_group').focus();
}

function get_macro_for_rule_edit(id, oid) {
  if(!manage_controllers['reload_macros']) {
    $call(manage_controllers['current_controller'], 'list_macros', 
      null, function(res) {
        insertMacrosList(res);
        edit_rule_dialog(id, oid);
      }, function() {
        load_error('macros');
    });
  } else {
    edit_rule_dialog(id, oid);
  }
}
function edit_rule_dialog(id, i) {
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
    _title = 'CREATE RULE';
  } else {
    _priority = manage_controllers['items'][i].priority;
    _chillout = manage_controllers['items'][i].chillout_time;
    _description = manage_controllers['items'][i].description;
    if (manage_controllers['items'][i].macro != null) _macro = 
      manage_controllers['items'][i].macro;
    if (manage_controllers['items'][i].macro_args != null) {
      var args = '';
      $.each(manage_controllers['items'][i].macro_args, function(k, v) {
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
    if (manage_controllers['items'][i].macro_kwargs) {
      var kwargs = '';
      $.each(manage_controllers['items'][i].macro_kwargs, function(k, v) {
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
    _prop = manage_controllers['items'][i].for_prop;
    _item_type = manage_controllers['items'][i].for_item_type;
    if (_item_type == null) _item_type = '#';
    _for_group = manage_controllers['items'][i].for_item_group;
    if (_for_group == null) _for_group = '#';
    _for_item_id = manage_controllers['items'][i].for_item_id;
    if (_for_item_id == null) _for_item_id = '#';
    _for_initial = rs_for_init(manage_controllers['items'][i].for_initial);
    _break = manage_controllers['items'][i].break_after_exec ? '1' : '0';
    if (manage_controllers['items'][i].in_range_min != null || 
        manage_controllers['items'][i].in_range_max != null) {
      if (dm_rule_for_expire(manage_controllers['items'][i])) {
        _condition = 'expire';
      } else if (dm_rule_for_set(manage_controllers['items'][i])) {
        _condition = 'set';
      } else if (manage_controllers['items'][i].condition.indexOf(' == ') > -1) {
        _condition = 'equals';
      } else {
        _condition = 'range';
      }
    }
    if (manage_controllers['items'][i].in_range_min != null)
      _in_range_min = manage_controllers['items'][i].in_range_min;
    if (manage_controllers['items'][i].in_range_max != null)
      _in_range_max = manage_controllers['items'][i].in_range_max;
    _in_range_min_eq = manage_controllers['items'][i].in_range_min_eq;
    _in_range_max_eq = manage_controllers['items'][i].in_range_max_eq;
  }
  // row 1
  var html = '<form class="form-horizontal rule_dialog row" id="edit_rule">';
  html +=
    '<div class="form-group col-12 col-sm-4">' +
    '<label id="l_rule_priority" for="rule_priority">Priority</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_priority" value="' + _priority + '">';
  html +=
    '<label id="l_rule_chillout" class="row-schf" for="rule_chillout">' +
    'Chillout</label><input class="form-control" type="text" size="5"' +
    'id="rule_chillout" value="' + _chillout + '" /></div>';
  // row 2
  html +=
    '<div class="col-12 col-sm-8">' +
    '<label for="rule_description">Description</label>' +
    '<textarea class="form-control" type="text" size="15" rows="3" ' +
    'id="rule_description">' + _description + '</textarea></div>';
  html += '<div class="form_delimiter"></div>';
  // row 3
  html +=
    '<div class="form-group">' +
    '<div class="col-12 col-sm-4 row-schf">' +
    '<label for="rule_for_prop">Property</label>' +
    '<select class="form-control" id="rule_for_prop">';
  $.each(manage_controllers['status_labels']['rule']['for_props'], 
    function(_k, v) {
      html += '<option value="' + v + '"';
      if (v == _prop) html += ' selected';
      html += '>' + v + '</option>';
  });
  html += '</select></div>';
  html +=
    '<div class="col-12 col-sm-4 row-schf">' +
    '<label for="rule_item_type">For&nbsp;item</label>' +
    '<select class="form-control" id="rule_item_type">';
  $.each(manage_controllers['status_labels']['rule']['item_types'], 
    function(_k, v) {
      html += '<option value="' + v + '"';
      if (v == _item_type) html += ' selected';
      html += '>' + v + '</option>';
  });
  html += '</select></div></div>';
  // row 4
  html +=
    '<div class="form-group">' +
    '<div class="col-12 col-sm-4">' +
    '<label for="rule_for_group">Group</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_for_group" value="' + _for_group + '" /></div>';
  html +=
    '<div class="col-12 col-sm-4 row-schf">' +
    '<label for="rule_for_item_id">ID</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_for_item_id" value="' + _for_item_id + '" /></div></div>';
  // row 5
  html +=
    '<div class="form-group">' +
    '<div class="col-12 col-sm-4">' +
    '<label for="rule_condition">Condition</label>' +
    '<select class="form-control" id="rule_condition"' +
    ' onchange="rule_form_condition_switch()">';
  $.each(manage_controllers['status_labels']['rule']['conditions'], 
    function(_k, v) {
      html += '<option value="' + v + '"';
      if (v == _condition) html += ' selected';
      html += '>' + v + '</option>';
  });
  html += '</select></div>';
  // condition forms
  // equals
  html +=
    '<div class="col-12 col-sm-4 input-group row-schf" ' +
    'id="d_rule_cond_eq"><div class="input-group-prepend">' +
    '<span class="input-group-text" id="l_rule_cond_eq">' +
    'x&nbsp;==</span></div>' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_in_range_min" value="' + _in_range_min + '"></div>';
  // row 5.5
  // range
  html += 
    '<div class="col-12 col-sm-8 input-group row-schf" ' +
    'id="d_rule_cond_range">' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_in_range_min_r" value="' + _in_range_min + '">' +
    '<select class="form-control custom-select" id="rule_in_range_min_eq">' +
    '<option value="0">&lt;</option>'+
    '<option value="1"' + (_in_range_min_eq ? ' selected' : '') +
    '>&lt;=</option></select>' +
    '<span class="input-group-text" id="l_rule_cond_eq">x</span>' +
    '<select class="form-control custom-select" id="rule_in_range_max_eq">' +
    '<option value="0">&lt;</option>' +
    '<option value="1"' +(_in_range_max_eq ? ' selected' : '') +
    '>&lt;=</option></select>' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_in_range_max_r" value="' + _in_range_max + '"></div>';
  html += '</div></div>';
  // row 6
  html +=
    '<div class="form-group">' +
    '<div class="col-6 col-sm-4">' +
    '<label for="rule_for_initial">Initial</label>' +
    '<select class="form-control" id="rule_for_initial">';
  $.each(manage_controllers['status_labels']['rule']['for_iniial'], 
    function(_k, v) {
      html += '<option value="' + v + '"';
      if (v == _for_initial) html += ' selected';
      html += '>' + v + '</option>';
  });
  html += '</select></div>';
  html +=
    '<div class="col-6 col-sm-4">' +
    '<label for="rule_break">Break action exec</label>' +
    '<div class="form_radio_holder" id="rule_break"><div>';
  $.each(manage_controllers['status_labels']['rule']['break'], 
    function(_k, v) {
      html += '<input type="radio" name="rule_break" class="form_radio" ' +
        'id="radio_' + _k + '" value="' + _k + '"';
      if (_k == _break) html += ' checked';
      html += '><label for="radio_' + _k + '">' + v + '</label>' +
        '<label class="bg_col"></label>';
  });
  html += '</div></div></div></div>';
  // row 7
  html +=
    '<div class="form-group">' +
    '<div class="col-12 col-sm-6">' +
    '<label for="rule_macro">Macro</label>' +
    '<select class="form-control" id="rule_macro" ' +
    'onchange="type_macro(this)">' +
    '<option value="">select</option>' +
    '<option value="-1"';
  var custom_macro = false;
  if(_macro && _macro != null && 
      !Object.keys(manage_controllers["items"]).includes(_macro)) {
    html += ' selected';
    custom_macro = true;
  }
  html += '>custom macro</option>';
  for(var m in manage_controllers["items"]) {
    if(m.startsWith('lmacro')) {
      html += '<option value="' + m + '"';
      if(_macro === m) 
        html += ' selected ';
      html += '>' + m.substr(7) + '</option>';
    }
  }
  html += '</select></div>';
  html += '<div class="col-12 col-sm-6 row-schf" id="macro_custom"';
  if(!custom_macro)
    html += ' style="display:none"';
  html += '>' +
    '<label for="rule_macro_kwargs">Own macro</label>' +
    '<input class="form-control" type="text"';
  if(custom_macro)
    html += ' value="' + _macro + '"';
  html += '/></div></div>';
  // row 8
  html += '<div class="form-group">' +
    '<div class="col-12 col-sm-8">' +
    '<label for="rule_macro_args">Args</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_macro_args" value="' + _macro_args + '" /></div></div>';
  // row 9
  html +=
    '<div class="form-group">' +
    '<div class="col-12 col-sm-8">' +
    '<label for="rule_macro_kwargs">Kwargs</label>' +
    '<input class="form-control" type="text" size="5"' +
    'id="rule_macro_kwargs" value="' + _macro_kwargs + '" /></div></div>';
  // end form
  html += '</form>';
  $popup('!confirm', _title, html, {
      btn1: 'OK',
      btn2: 'CANCEL',
      btn1a: function() {
        set_rule_props_ae(id, i);
      },
      va: validate_rule_dialog
    }
  );
  rule_form_condition_switch();
  $('#rule_priority').focus();
}
function ask_del_rule(id, i) {
  $popup('warning', 'DELETE RULE', '<div class="content_msg">' +
    'Rule ' + i + ' will be deleted.<br />Please confirm</div>', {
      btn1: 'DELETE',
      btn2: 'CANCEL',
      btn1a: function() {
        del_rule(id, i);
      }
    }
  );
}

manage_controllers['create_units'] = unit_state_dialog;
manage_controllers['create_sensors'] = create_sensor_dialog;
manage_controllers['create_lvars'] = select_lvar_state;
manage_controllers['create_macros'] = edit_macro_dialog;
manage_controllers['create_cycles'] = get_cycle_for_edit;


function validate_cycle_dialog() {
  var _v = true;
  // $('#l_cycle_ict').removeClass('device-error');
  $('#l_cycle_interval').removeClass('device-error');
  $('#cycle_ict').removeClass('device-error');
  $('#cycle_interval').removeClass('device-error');

  // var ict = $('#cycle_ict').val();
  var interval = $('#cycle_interval').val();

  // if (!isInt(ict) || ict < 1) {
  //   $('#l_cycle_ict').addClass('device-error');
  //   $('#cycle_ict').addClass('device-error');
  //   $('#cycle_ict').focus();
  //   _v = false;
  // }
  if (!isNumeric(interval) || interval <= 0) {
    $('#l_cycle_interval').addClass('device-error');
    $('#cycle_interval').addClass('device-error');
    $('#cycle_interval').focus();
    _v = false;
  }
  return _v;
}
function type_macro(e) {
  if(e.value == -1) {
    $('#macro_custom').show();
  } else {
    $('#macro_custom').hide();
  }
}
function format_expire_time(i) {
  if (i.expires == 0) return '';
  if (i.status == 0) return 'Exp = 0.0';
  var t = i.expires - new Date().getTime() / 1000 + tsdiff + i.set_time;
  if (t < 0) return 'Exp = 0.0';
  return 'Exp = ' + Number(Math.round(t * 10) / 10).toFixed(1);
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
  $('#d_rule_cond_range').addClass('hidden');
  $('#d_rule_cond_eq').addClass('hidden');
  $('#rule_for_prop').attr('disabled', 'disabled');
  var c = $('#rule_condition').val();
  if (c == 'equals') {
    $('#d_rule_cond_eq').removeClass('hidden');
    $('#rule_for_prop').removeAttr('disabled');
  } else if (c == 'range') {
    $('#d_rule_cond_range').removeClass('hidden');
    $('#rule_for_prop').removeAttr('disabled');
  } else if (c == 'none') {
    $('#rule_for_prop').removeAttr('disabled');
  }
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
  if ($('#edit_rule')[0].rule_break.value == '1') {
    rule.break_after_exec = true;
  } else {
    rule.break_after_exec = false;
  }
  rule.macro = $('#rule_macro').val();
  if(rule.macro == -1) {
    rule.macro = $('#macro_custom input').val();
  }
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
          Number(rule.in_range_min) > Number(rule.in_range_max)))) {
      $('#rule_in_range_min_r').addClass('device-error');
      if (_v) $('#rule_in_range_min_r').focus();
      _v = false;
    }
    if (
      (rule.in_range_max != '' && !isNumeric(rule.in_range_max)) ||
      (isNumeric(rule.in_range_min) && 
        isNumeric(rule.in_range_max) &&
        Number(rule.in_range_min) > Number(rule.in_range_max))) {
      $('#rule_in_range_max_r').addClass('device-error');
      if (_v) $('#rule_in_range_max_r').focus();
      _v = false;
    }
  }
  return _v;
}
function isInt(n) {
  if (n == '' || n == null) return false;
  return Number(n) == n && n % 1 == 0;
}
function isNumeric(n) {
  if (n == '' || n == null) return false;
  return Number(n) == n;
}

debug_mode = [];
function show_debug_info(res) {
  if(res && res.data) {
    if(manage_controllers['current_controller'] == 
        res.data.product_code + "\/" + res.data.system)
      debug_mode[manage_controllers['current_controller']] = res.data.debug;
  }
  if (debug_mode[manage_controllers['current_controller']]) {
    $('#i_debug_' + 
        $.escapeSelector(manage_controllers['current_controller']))
      .css('color', 'orange')
      .css('font-weight', 'bold')
      .html('Debug mode: ON');
    if (eva_sfa_server_info.acl.master) {
      $('#i_debug_' + 
          $.escapeSelector(manage_controllers['current_controller']))
        .css('cursor', 'pointer')
        .attr('onclick', 'set_debug_mode("' + 
          manage_controllers['current_controller'] + '", false)');
    }
  } else {
    $('#i_debug_' + 
        $.escapeSelector(manage_controllers['current_controller']))
      .css('color', '#4D4D4D')
      .css('font-weight', 'normal')
      .html('Debug mode: OFF');
    if (eva_sfa_server_info.acl.master) {
      $('#i_debug_' + 
          $.escapeSelector(manage_controllers['current_controller']))
        .css('cursor', 'pointer')
        .attr('onclick', 'set_debug_mode("' + 
          manage_controllers['current_controller'] + '", true)');
    }
  }
}

function set_debug_mode(id, mode) {
  $call(id, 'set_debug', {debug: (mode ? '1' : '0')}, function(res) {
    var data = res.data;
    if (data && data.ok) {
      debug_mode[id] = !debug_mode[id];
      manage_controllers['current_controller'] = id;
      show_debug_info();
      $popup('info', 'DEBUG', '<div class="content_msg">' +
        'Debug mode is now ' + (debug_mode ? 'enabled' : 'disabled')
        + '</div>');
    } else {
      $popup('error', 'ERROR', '<div class="content_msg">' +
        'Debug mode not changed<br />Result: ' + data.result + '</div>');
    }
  }, function() {
    $popup('error', 'ERROR', '<div class="content_msg">Server error</div>');
  });
}

function save(id) {
  $call(id, 'save', null, function(res) {
    var data = res.data;
    if(data && data.ok) {
      var msg = '<div class="content_msg">' +
        'System data updated successfully</div>';
      $popup('info', 'UPDATED', msg);
    } else {
      var msg = '<div class="content_msg">Unable to update system data' +
        '<br />Result: ' + data.result + '</div>';
      $popup('error', 'ERROR', msg);
    }
  }, function(res) {
    var data = res.data;
    var msg = '<div class="content_msg">';
    if (data.status == 403) {
      $popup('error', 'ACCESS DENIED', msg + 'INVALID API KEY</div>', {
        btn1: 'OK',
        btn2: '',
        btn1a: function() {
          stop();
        }
      });
      return;
    }
    msg += 'Unable to update system data<br />UNKNOWN ERROR</div>';
    $popup('error', 'ERROR', msg);
  });
}
var controller_list = [];
function update_controllers(data) {
  var update = false;
  if(Object.keys(controller_list).length != data.length) {
    update = true;
  } else {
    $.each(data, function(k, v) {
      if(JSON.stringify(v) != JSON.stringify(controller_list[v.oid])) {
        update = true;
        return;
      }
    });
  }
  if(update) {
    controller_list = [];
    var ucs = $('#ucs');
    var lms = $('#lms');
    ucs.html('');
    lms.html('');
    $.each(data, function(k, v) {
      controller_list[v.oid] = v;
      var ct = null;
      if (v.group == 'uc') {
        ct = ucs;
      } else if (v.group == 'lm') {
        ct = lms;
      }
      if (ct) append_controller(v, ct);
    });
  }
}

function load_error(msg) {
  var msg = 'Unable to load ' + msg;
  $log_error(msg);
}

function set_error(msg) {
  var msg = '<div class="content_msg">Unable to set ' + msg + '</div>';
  $log_error(msg);
  $popup('error', 'Set error', msg);
}

function remove_error(msg) {
  var msg = '<div class="content_msg">Unable to remove ' + msg + '</div>';
  $log_error(msg);
  $popup('error', 'Remove error', msg);
}

function reload_error(msg) {
  var msg = '<div class="content_msg">Unable to reload ' + msg + '</div>';
  $log_error(msg);
  $popup('error', 'Reload error', msg);
}

function do_login(enter_type, login, password) {
  if (!enter_type || !login) {
    enter_type = $('#enter_type').val();
    if(enter_type == "masterkey") {
      eva_sfa_apikey = $('#f_masterkey').val();
    } else {
      eva_sfa_login = $('#f_login').val();
      eva_sfa_password = $('#f_password').val();
    }
  } else if(enter_type =="masterkey") {
    eva_sfa_apikey = login;
  } else {
    eva_sfa_login = login;
    eva_sfa_password = password;
  }
  if ($('#f_remember').is(':checked')) {
    if(enter_type == "masterkey") {
      create_cookie('enter_type', enter_type, 365 * 10, '/cloudmanager/');
      create_cookie('masterkey', eva_sfa_apikey, 365 * 10, '/cloudmanager/');
    } else {
      create_cookie('enter_type', enter_type, 365 * 10, '/cloudmanager/');
      create_cookie('login', eva_sfa_login, 365 * 10, '/cloudmanager/');
      create_cookie('password', eva_sfa_password, 365 * 10, '/cloudmanager/');
    }
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
  eva_sfa_apikey = "";
  eva_sfa_login = "";
  eva_sfa_password = "";
  erase_cookie('password', '/cloudmanager/');
  erase_cookie('masterkey', '/cloudmanager/');
  show_login_form();
}

var tbars = [
  {
    name: 'Units',
    id: 'remote-units',
    cols: ['Controller', 'Unit ID', 'A', 'S', 'V'],
    reload: reload_remote_units
  },
  {
    name: 'Sensors',
    id: 'remote-sensors',
    cols: ['Controller', 'Sensor ID', 'S', 'V'],
    reload: reload_remote_sensors
  },
  {
    name: 'LVars',
    id: 'remote-lvars',
    cols: ['Controller', 'LVar ID', 'S', 'V'],
    reload: reload_remote_lvars
  },
  {
    name: 'Macros',
    id: 'remote-macros',
    cols: ['Controller', 'Macro ID', 'A'],
    reload: reload_remote_macros
  },
  {
    name: 'Cycles',
    id: 'remote-cycles',
    cols: ['Controller', 'Cycle ID', 'Status', 'Interval', 'Average'],
    reload: reload_remote_cycles
  }
];

$(document).ready(function() {
  var d_tbars = $('#d_tbars');
  $.each(tbars, function(k, v) {
    tbar_reload_func[v.id] = v.reload;
    var btn = $('<a />', {
      href: '#tbar-' + v.id,
      'data-toggle': 'list',
      'aria-selected': (k==0?'true':'false'),
      role: 'tab',
      class:'list-group-item list-group-item-action show'
    }).on('click', function() {
      tbar_show(v.id);
    }).html(v.name);
    if (k == 0) {
      btn.addClass('active');
    }
    d_tbars.append(btn);
  });
  d_tbars = $('#d_tbars + .tab-content');
  $.each(tbars, function(k, v) {
    var c = $('<div />', {
      id: 'tbar-' + v.id, 
      class: 'tab-pane show', 
      role: 'tab-panel'
    });
    if (k == 0) {
      c.addClass('active');
    }
    var tbl = $('<table />', {
      id: 'tbl-' + v.id, 
      class: 'table table-hover'
    });
    var tr = $('<tr />');
    $.each(v.cols, function(i, x) {
      tr.append($('<th />').html(x));
    });
    $('<thead />')
      .append(tr)
      .appendTo(tbl);
    c.append(tbl);
    d_tbars.append(c);
  });
  $('#d_tbars + .tab-content table.table').DataTable({
    scrollY: '300px',
    scrollCollapse: true,
    paging: false,
    info: false,
    preDrawCallback: function(settings) {
      pageScrollPos = $(settings.nScrollBody).scrollTop();
    },
    drawCallback: function(settings) {
      $('div.dataTables_scroll').addClass('nano');
      $('div.dataTables_scrollBody').addClass('nano-content').scrollTop(pageScrollPos);
    }
  });
  tbar_show('remote-units');
  eva_sfa_state_updates = true;
  eva_sfa_init();
  eva_sfa_cb_login_success = function(data) {
    $('#eva_ui_login_error').hide();
    $('#loginform').hide();
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
  eva_sfa_cb_login_error = function(code, msg, data) {
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
      $('#eva_ui_login_error').html(msg).show();
      setTimeout(eva_sfa_start, 1000);
    }
    show_login_form()
  };
  setInterval(reload_data, 1000);
  show_login_form();
});
