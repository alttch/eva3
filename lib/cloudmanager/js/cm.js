function $log(data) {
  console.log(data);
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

function start() {
  $('#main').show();
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
  eva_sfa_log_start(20);
  reload_controllers();
}

function logout() {
  eva_sfa_stop();
  $('#main').hide();
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
        $popup(
          'error',
          controller_id + ' access error',
          'API CODE ' + data.code
        );
      } else {
        cb_success(data);
      }
    },
    cb_error
  );
}

function reload_controllers() {
  eva_sfa_call('list_controllers', null, update_controllers, function() {
    load_error('controllers');
  });
}

function set_controller_masterkey(controller_id, masterkey) {
  eva_sfa_call(
    'set_controller_prop',
    {i: controller_id, p: 'masterkey', v: masterkey, save: 1},
    reload_controllers,
    function() {
      set_error(controller_id + ' masterkey');
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
  if (c.managed) {
    cel.click(function() {
      manage_controller(c.type, c.oid);
    });
    cel.addClass('controller-link');
  } else {
    cel.addClass('controller-unmanaged');
  }
  cel.html(c.full_id).appendTo(cdiv);
  $('<button />')
    .addClass('btn-manage-controller')
    .html('edit')
    .click(function() {
      edit_controller_props(c.full_id);
    })
    .appendTo(cdiv);
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
  $popup('error', 'Load error', 'Unable to load ' + msg);
}

function set_error(msg) {
  $popup('error', 'Load error', 'Unable to set ' + msg);
}
