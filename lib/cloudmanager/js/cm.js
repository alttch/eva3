function start() {
  $('#main').show();
  eva_sfa_call('list_controllers', null, update_controllers, function() {
    load_error('controllers');
  });
}

function logout() {
  eva_sfa_stop();
  $('#main').hide();
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
}

function manage_lm(controller_id) {
  console.log('LM ' + controller_id);
}

function edit_controller_props(controller_id) {
  eva_sfa_call(
    'list_controller_props',
    {i: controller_id},
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
      edit_controller_props(c.oid);
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
  eva_sfa_popup('popup', 'error', 'Load error', 'Unable to load ' + msg);
}
