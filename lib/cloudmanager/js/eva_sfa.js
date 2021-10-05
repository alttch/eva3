/*
 * Author: Altertech Group, https://www.altertech.com/
 * Copyright: (C) 2012-2021 Altertech Group
 * License: Apache License 2.0
 * Version: 3.4.2
 */

/**
 * Next 2 vars should always contain login and password or API will be unable
 * to reconnect in case of i.e. server reboot
 */
eva_sfa_login = '';
eva_sfa_password = '';

/**
 * Use API key instead of login. Insecure but fine for testing
 */
eva_sfa_apikey = null;

/**
 * Set/clear auth cookies for /ui, /pvt and /rpvt
 */
eva_sfa_set_auth_cookies = true;

/**
 * Contains current API token after log in. Filled by framework automatically
 */
eva_sfa_api_token = null;

/**
 * True if framework engine is started and user is logged in, false if not.
 * Should not be changed outside framework functions
 */
eva_sfa_logged_in = false;

/**
 * Contains functions called after either successful or failed login
 */
eva_sfa_cb_login_success = null;
eva_sfa_cb_login_error = null;

/**
 * Contains function called after framework loads initial item states
 */
eva_sfa_cb_states_loaded = null;

/** Contains function which's called as f(data) when ws event is received
 *  function should return true, if it return false, WS data processing
 *  is stopped
 */
eva_sfa_ws_event_handler = null;

/** Contains function which's called as f() when reload event is received
 *  (server ask the clients to reload the interface)
 */
eva_sfa_reload_handler = null;

/** Contains function which's called as f() when server restart event is
 * received (server warns the clients about it's restart)
 */
eva_sfa_server_restart_handler = null;

/**
 * Contains function called if heartbeat got an error (usually user is forcibly
 * logged out). The function is called f(data) if there's HTTP error data or
 * f() if there's no HTTP error data (i.e. unable to send WebSocket message)
 */
eva_sfa_heartbeat_error = eva_sfa_restart;

/**
 * Reload interval for AJAX mode (in seconds)
 */
eva_sfa_ajax_reload_interval = 2;

/**
 * Reload interval for WS mode (in seconds), just in case something wrong
 */
eva_sfa_force_reload_interval = 5;

/**
 * Log refresh interval for AJAX mode (in seconds)
 */
eva_sfa_log_reload_interval = 2;

/**
 * Max log records to get/keep
 */
eva_sfa_log_records_max = 200;

/**
 * Append log entry
 */
eva_sfa_process_log_record = null;

/**
 * Log post processing function i.e. to autoscroll the log viewer
 */
eva_sfa_log_postprocess = null;

/**
 * "Heartbeat" interval (requests to system info, in seconds)
 */
eva_sfa_heartbeat_interval = 5;

/**
 * After successfull login contains server info (API test function output)
 * data is refreshed every eva_sfa_heartbeat_interval seconds
 */
eva_sfa_server_info = null;

/*
 * Contains difference (in seconds) between server and client time
 */
eva_sfa_tsdiff = null;

/**
 * WebSocket mode if true, is set by eva_sfa_init()
 * Setting this to false (after calling eva_sfa_init()) will force
 * AJAX mode
 */
eva_sfa_ws_mode = true;

/**
 * Update item states via AJAX and subscribe to state updates via websocket
 *
 * Possible values:
 *  true - get states of all items API key has access to
 *  {'p': [types], 'g': [groups]} - subscribe to specified types and groups
 *  false - disable state updates
 */
eva_sfa_state_updates = true;

/**
 * Initializes eva_sfa javascript API
 * automatically sets WebSocket or AJAX mode depending on the browser features
 *
 * Always call this function at your program start
 */
function eva_sfa_init() {
  if (window.WebSocket) {
    eva_sfa_ws_mode = true;
  } else {
    eva_sfa_ws_mode = false;
  }
}

/**
 * Start API
 * After calling the function will authorize user, open WebSocket
 * (in case of WS mode) or schedule AJAX refresh interval
 */
function eva_sfa_start() {
  if (eva_sfa_logged_in) return;
  eva_sfa_last_ping = null;
  eva_sfa_last_pong = null;
  var q = {};
  if (eva_sfa_apikey) {
    q = {k: eva_sfa_apikey};
  } else if (eva_sfa_login) {
    q = {u: eva_sfa_login, p: eva_sfa_password};
  }
  eva_sfa_api_call('login', q, eva_sfa_after_login, function(code, msg, data) {
    eva_sfa_logged_in = false;
    eva_sfa_stop_engine();
    if (eva_sfa_cb_login_error !== null)
      eva_sfa_cb_login_error(code, msg, data);
  });
}

/**
 * Restart API
 * i.e. used on heartbeat error
 */
function eva_sfa_restart() {
  eva_sfa_stop();
  eva_sfa_start();
}
/**
 * Stop API
 * After calling the function will close open WebSocket if available,
 * clear all the refresh intervals then try to close server session
 */
function eva_sfa_stop(cb) {
  eva_sfa_stop_engine();
  eva_sfa_logged_in = false;
  eva_sfa_api_call('logout', eva_sfa_prepare(), cb, cb);
  eva_sfa_api_token = null;
  _eva_sfa_set_token_cookie();
}

/**
 * Register the function (or javascript code) to be called in case of state
 * change event (or at first state load)
 *
 * @param oid - item id in format type:full_id, i.e. sensor:env/temp1
 * @param cb - function to be called
 *
 * if state is already loaded, function will be called immediately
 */
function eva_sfa_register_update_state(oid, cb) {
  if (!oid.includes('*')) {
    eva_sfa_update_state_functions[oid] = cb;
    var state = eva_sfa_state(oid);
    if (state !== undefined) cb(state);
  } else {
    eva_sfa_update_state_mask_functions[oid] = cb;
    var i = eva_sfa_state(oid);
    $.each(i, function(k, v) {
      cb(v);
    });
  }
}

/**
 * Calls any available API function
 *
 * @param func - API function
 * @param params - function params
 * @param cb_success - function called on success
 * @param cb_error - function called if error occured
 */
function eva_sfa_call(func, params, cb_success, cb_error) {
  var p = eva_sfa_prepare(params);
  eva_sfa_api_call(func, p, cb_success, cb_error);
}

/**
 * Get item state
 *
 * @param oid - item id in format type:full_id, i.e. sensor:env/temp1
 *
 * @returns - object state or undefined if no object found
 */
function eva_sfa_state(oid) {
  if (!oid.includes('*')) {
    if (oid in eva_sfa_states) {
      return eva_sfa_states[oid];
    } else {
      return undefined;
    }
  }
  var result = new Array();
  $.each(Object.keys(eva_sfa_states), function(i, v) {
    if (eva_sfa_oid_match(v, oid)) {
      result.push(eva_sfa_states[v]);
    }
  });
  return result;
}

/**
 * Get expiration time left (in seconds)
 *
 * @param lvar_id - item id in format type:full_id, e.g. lvar:timers/timer1
 *
 * @returns - seconds to expiration, -1 if expired, -2 if stopped
 */

function eva_sfa_expires_in(lvar_id) {
  // get item
  var i = eva_sfa_state(lvar_id.startsWith('lvar:') ? '' : 'lvar:' + lvar_id);
  // if no such item
  if (i === undefined) return undefined;
  // if item has no expiration or expiration is set to zero
  if (i.expires === undefined || i.expires == 0) return null;
  // if no timestamp diff
  if (eva_sfa_tsdiff == null) return undefined;
  // if timer is disabled (stopped), return -2
  if (i.status == 0) return -2;
  // if timer is expired, return -1
  if (i.status == -1) return -1;
  var t = i.expires - new Date().getTime() / 1000 + eva_sfa_tsdiff + i.set_time;
  if (t < 0) t = 0;
  return t;
}

/**
 * Get item status
 *
 * @param oid - item id in format type:full_id, i.e. sensor:env/temp1
 *
 * @returns object status(int) or undefined if no object found
 */
function eva_sfa_status(oid) {
  var state = eva_sfa_state(oid);
  if (state === undefined || state === null) return undefined;
  return state.status;
}

/**
 * Get item status
 *
 * @param oid - item id in format type:full_id, i.e. sensor:env/temp1
 *
 * @returns object value (null, string or numeric if possible)
 * or undefined if no object found
 */
function eva_sfa_value(oid) {
  var state = eva_sfa_state(oid);
  if (state === undefined || state === null) return undefined;
  if (Number(state.value) == state.value) {
    return Number(state.value);
  } else {
    return state.value;
  }
}

/**
 * Get groups list
 *
 * @param params - object with props
 *              p = item type (U for unit, S for sensor, LV for lvar)
 *              g - group filter (mqtt style)
 * @param cb_success - function called on success
 * @param cb_error - function called if error occured
 */
function eva_sfa_groups(params, cb_success, cb_error) {
  eva_sfa_api_call('groups', eva_sfa_prepare(params), cb_success, cb_error);
}

/**
 * Get item state history
 *
 * @param params - state history params
 * @param cb_success - function called on success
 * @param cb_error - function called if error occured
 */
function eva_sfa_state_history(oid, params, cb_success, cb_error) {
  var q = eva_sfa_prepare(params);
  q['i'] = oid;
  eva_sfa_api_call('state_history', q, cb_success, cb_error);
}

/**
 * Run macro
 *
 * @param macro_id - full macro ID
 * @param params - object with props
 *              a - macro args
 *              kw - macro kwargs
 *              w - seconds to wait until complete
 *              p - action priority
 *              u - action uuid
 * @param cb_success - function called on success
 * @param cb_error - function called if error occured
 */
function eva_sfa_run(macro_id, params, cb_success, cb_error) {
  var q = eva_sfa_prepare(params);
  q['i'] = macro_id;
  eva_sfa_api_call('run', q, cb_success, cb_error);
}

/**
 * Execute unit action
 *
 * @param unit_id - full unit ID
 * @param params - object with props
 *              s - new unit status (int)
 *              v - new unit value (optional)
 *              w - seconds to wait until complete
 *              p - action priority (optional)
 *              u - action uuid (optional)
 * @param cb_success - function called on success
 * @param cb_error - function called if error occured
 */
function eva_sfa_action(unit_id, params, cb_success, cb_error) {
  var q = eva_sfa_prepare(params);
  q['i'] = unit_id;
  eva_sfa_api_call('action', q, cb_success, cb_error);
}

/**
 * Execute unit action, toggle status beteween 0 and 1
 *
 * @param unit_id - full unit ID
 * @param params - object with props
 *              s - new unit status (int)
 *              v - new unit value (optional)
 *              w - seconds to wait until complete
 *              p - action priority (optional)
 *              u - action uuid (optional)
 * @param cb_success - function called on success
 * @param cb_error - function called if error occured
 */
function eva_sfa_action_toggle(unit_id, params, cb_success, cb_error) {
  var q = eva_sfa_prepare(params);
  q['i'] = unit_id;
  eva_sfa_api_call('action_toggle', q, cb_success, cb_error);
}

/**
 * Get action results by unit ID
 *
 * @param params - object with props
 *              i - object oid (type:group/id), unit or lmacro
 *              u - action uuid (either i or u must be specified)
 *              g - filter by group
 *              s - filter by status (Q, R, F - queued, running, finished)
 * @param cb_success - function called on success
 * @param cb_error - function called if error occured
 */
function eva_sfa_result(params, cb_success, cb_error) {
  eva_sfa_api_call('result', eva_sfa_prepare(params), cb_success, cb_error);
}

/**
 * Kill running unit action and clean queue
 *
 * @param unit_id - full unit ID
 */
function eva_sfa_kill(unit_id, cb_success, cb_error) {
  var q = eva_sfa_prepare();
  q['i'] = unit_id;
  eva_sfa_api_call('kill', q, cb_success, cb_error);
}

/**
 * Clean queue for unit
 *
 * @param unit_id - full unit ID
 */
function eva_sfa_q_clean(unit_id, cb_success, cb_error) {
  var q = eva_sfa_prepare();
  q['i'] = unit_id;
  eva_sfa_api_call('q_clean', q, cb_success, cb_error);
}

/**
 * Terminate current unit action if possible
 *
 * @param unit_id - full unit ID
 */
function eva_sfa_terminate(unit_id, cb_success, cb_error) {
  var q = eva_sfa_prepare();
  q['i'] = unit_id;
  eva_sfa_api_call('terminate', q, cb_success, cb_error);
}

/**
 * Terminate current unit action by uuid if possible
 *
 * @param uuid - action uuid
 */
function eva_sfa_terminate_by_uuid(uuid, cb_success, cb_error) {
  var q = eva_sfa_prepare();
  q['u'] = uuid;
  eva_sfa_api_call('terminate', q, cb_success, cb_error);
}

/**
 * Set lvar value
 *
 * @param lvar_id - full lvar ID
 * @param value - new lvar value, optional
 */
function eva_sfa_set(lvar_id, value, cb_success, cb_error) {
  var q = eva_sfa_prepare();
  q['i'] = lvar_id;
  q['v'] = value;
  eva_sfa_api_call('set', q, cb_success, cb_error);
}

/**
 * Set lvar value, toggle current value (if value is 0 or 1)
 * useful when lvar is being used as flag
 *
 * @param lvar_id - full lvar ID
 */
function eva_sfa_toggle(lvar_id, cb_success, cb_error) {
  var q = eva_sfa_prepare();
  q['i'] = lvar_id;
  eva_sfa_api_call('toggle', q, cb_success, cb_error);
}

/* deprecated - use eva_sfa_toggle instead */
function eva_sfa_set_toggle(lvar_id, cb_success, cb_error) {
  _eva_sfa_deprecated('eva_sfa_set_toggle', 'eva_sfa_toggle');
  return eva_sfa_toggle(lvar_id, cb_success, cb_error);
}

/**
 * Reset lvar (set status/value to 1)
 *
 * @param lvar_id - full lvar ID
 */
function eva_sfa_reset(lvar_id, cb_success, cb_error) {
  var q = eva_sfa_prepare();
  q['i'] = lvar_id;
  eva_sfa_api_call('reset', q, cb_success, cb_error);
}

/**
 * Clear lvar (for timer - set status to 0, otherwise value to 0)
 *
 * @param lvar_id - full lvar ID
 */
function eva_sfa_clear(lvar_id, cb_success, cb_error) {
  var q = eva_sfa_prepare();
  q['i'] = lvar_id;
  eva_sfa_api_call('clear', q, cb_success, cb_error);
}

/**
 * Start log processing
 *
 * @param log_level - log processing level (optional)
 */
function eva_sfa_log_start(log_level) {
  eva_sfa_log_started = true;
  if (log_level !== undefined) {
    eva_sfa_log_level = log_level;
  }
  if (!eva_sfa_ws_mode || eva_sfa_log_first_load) {
    eva_sfa_log_loaded = false;
    eva_sfa_load_log_entries(false, true);
  }
}

/**
 * Change log processing level
 *
 * @param log_level - log processing level
 */
function eva_sfa_change_log_level(log_level) {
  eva_sfa_log_level = log_level;
  eva_sfa_set_ws_log_level(log_level);
  eva_sfa_load_log_entries(false, true);
}

/**
 * Get log level name
 *
 * @param lid - log level id
 */

function eva_sfa_log_level_name(log_level) {
  return eva_sfa_log_level_names[log_level];
}

/*
 * Displays a chart
 *
 * @param ctx - html container element id to draw in (must have fixed
 *              width/height)
 * @param cfg - Chart.js configuration
 * @param oid - item oid or oids, array or comma separated (type:full_id)
 * @param params - object with props
 *              timeframe - timeframe to display (5T - 5 min, 2H - 2 hr, 2D - 2
 *                          days etc.), default: 1D
 *              fill - precision[:np] (10T - 60T recommended, more accurate -
   *              more data), np - number precision, optional. default: 30T:2
 *              update - update interval in seconds
 *              prop - item property to use (default is value)
 *
 * note: if the conteiner is no longer visible, chart ends updating forever
 */
function eva_sfa_chart(ctx, cfg, oid, params, _do_update) {
  var params = params;
  if (!params) params = {};
  var timeframe = params['timeframe'];
  if (!timeframe) {
    timeframe = '1D';
  }
  var fill = params['fill'];
  if (!fill) {
    fill = '30T:2';
  }
  var update = params['update'];
  var prop = params['prop'];
  var cc = $('#' + ctx);
  var chart = null;
  if (_do_update) {
    chart = _do_update;
  }
  if (_do_update !== undefined && !cc.is(':visible')) {
    if (chart) chart.destroy();
    return;
  }
  var d = new Date();
  if (timeframe[timeframe.length - 1] == 'T') {
    d.setMinutes(d.getMinutes() - timeframe.substring(0, timeframe.length - 1));
  } else if (timeframe[timeframe.length - 1] == 'H') {
    d.setHours(d.getHours() - timeframe.substring(0, timeframe.length - 1));
  } else if (timeframe[timeframe.length - 1] == 'D') {
    d.setHours(
      d.getHours() - timeframe.substring(0, timeframe.length - 1) * 24
    );
  }
  if (!_do_update) eva_sfa_load_animation(ctx);
  var x = 'value';
  if (prop !== undefined && prop != null) {
    x = prop;
  }
  eva_sfa_state_history(
    oid,
    {t: 'iso', s: d.toISOString(), x: x, w: fill},
    function(data) {
      if (chart) {
        chart.data.labels = data.t;
        if (oid.indexOf(',') == -1) {
          chart.data.datasets[0].data = data[x];
        } else {
          $.each(oid.split(','), function(a, v) {
            chart.data.datasets[a].data = data[v + '/' + x];
          });
        }
        chart.update();
      } else {
        var canvas = $('<canvas />', {
          width: '100%',
          height: '100%',
          class: 'eva_sfa_chart'
        });
        var work_cfg = $.extend({}, cfg);
        work_cfg.data.labels = data.t;
        if (oid.indexOf(',') == -1) {
          work_cfg.data.datasets[0].data = data[x];
        } else {
          $.each(oid.split(','), function(a, v) {
            work_cfg.data.datasets[a].data = data[v + '/' + x];
          });
        }
        cc.html(canvas);
        chart = new Chart(canvas, work_cfg);
      }
    },
    function(code, msg, data) {
      var d_error = $('<div />', {
        class: 'eva_sfa_chart',
        style:
          'width: 100%; height: 100%; ' +
          'color: red; font-weight: bold; font-size: 14px'
      }).html('Error loading chart data: ' + msg);
      cc.html(d_error);
      if (chart) chart.destroy();
      chart = null;
    }
  );

  if (update) {
    setTimeout(function() {
      eva_sfa_chart(ctx, cfg, oid, params, chart);
    }, update * 1000);
  }
}

/*
 * Animate html element block (simple loading animation)
 *
 * @param el_id - html element id
 */
function eva_sfa_load_animation(el_id) {
  $('#' + el_id).html(
    '<div class="eva-sfa-cssload-square"><div ' +
      'class="eva-sfa-cssload-square-part eva-sfa-cssload-square-green">' +
      '</div><div class="eva-sfa-cssload-square-part ' +
      'eva-sfa-cssload-square-pink">' +
      '</div><div class="eva-sfa-cssload-square-blend"></div></div>'
  );
}

/*
 * Opens popup window. Requires bootstrap css included
 * There may be only 1 popup opened. If the page want to open another popup, the
 * current one will be overwritten unless it's class is higher than a new one.
 *
 * @param ctx - html element id to use as popup (any empty <div /> is fine)
 * @param pclass - popup class: info, warning or error. opens big popup window
 *                 if '!' is put before the class (i.e. !info)
 * @param title - popup window title
 * @param msg - popup window message
 * @param params - object with handlers and additional parameters:
 *              ct - popup auto close time (sec), equal to pressing escape
 *              btn1 - button 1 name ('OK' if not specified)
 *              btn2 - button 2 name
 *              btn1a - function to run if button 1 (or enter) is pressed
 *              btn2a - function(arg) to run if button 2 (or escape) is
 *                      pressed. arg is true if the button was pressed, false
 *                      if escape key or auto close.
 *              va - validate function which runs before btn1a.
 *                   if the function return true, the popup is closed and btn1a
 *                   function is executed. otherwise the popup is kept and the
 *                   function btn1a is not executed. va function is used to
 *                   validate an input, if popup contains any input fields.
 *
 */
function eva_sfa_popup(ctx, pclass, title, msg, params) {
  var params = params;
  if (!params) params = {};
  var ct = params['ct'];
  var btn1 = params['btn1'];
  var btn2 = params['btn2'];
  var btn1a = params['btn1a'];
  var btn2a = params['btn2a'];
  var wclass = params['wclass'];
  var va = params['va'];
  var _pclass = pclass;
  if (pclass[0] == '!') {
    _pclass = pclass.substr(1);
  }
  if (
    eva_sfa_popup_priority(eva_sfa_popup_active) >
    eva_sfa_popup_priority(_pclass)
  ) {
    return false;
  }
  eva_sfa_popup_active = _pclass;
  var popup = $('#' + ctx);
  popup.removeClass();
  popup.html('');
  popup.addClass('eva_sfa_popup');
  var popup_window = $('<div />', {class: 'eva_sfa_popup_window'});
  popup.append(popup_window);
  if(wclass)
    popup_window.addClass(wclass);
  if (pclass[0] == '!') {
    popup_window.addClass('eva_sfa_popup_window_big');
  } else {
    popup_window.addClass('eva_sfa_popup_window');
  }
  var popup_header = $('<div />', {
    class: 'eva_sfa_popup_header eva_sfa_popup_header_' + _pclass
  });
  if (title !== undefined && title != null) {
    popup_header.html(title);
  } else {
    popup_header.html(_pclass.charAt(0).toUpperCase() + _pclass.slice(1));
  }
  popup_window.append(popup_header);
  var popup_content = $('<div />', {class: 'eva_sfa_popup_content'});
  popup_content.html(msg);
  popup_window.append(popup_content);
  var popup_footer = $('<div />', {class: 'eva_sfa_popup_footer'});
  popup_window.append(popup_footer);
  var popup_buttons = $('<div />', {class: 'eva_sfa_popup_btn_holder'});
  popup_window.append(popup_buttons);
  var btn1text = 'OK';
  if (btn1) {
    btn1text = btn1;
  }
  var btn1_o = $('<div />', {
    class: 'eva_sfa_popup_btn eva_sfa_popup_btn_' + _pclass,
    html: btn1text
  });
  var f_validate_run_and_close = function() {
    if (va === undefined || va == null || va()) {
      eva_sfa_close_popup(ctx);
      if (btn1a) btn1a();
    }
  };
  if (btn1a) {
    btn1_o.on('click', f_validate_run_and_close);
  } else {
    btn1_o.on('click', function() {
      eva_sfa_close_popup(ctx);
    });
  }
  var btn2_o = null;
  if (btn2) {
    btn2_o = $('<div />', {
      class: 'eva_sfa_popup_btn eva_sfa_popup_btn_cancell',
      html: btn2
    });
    btn2_o.on('click', function() {
      if (btn2a) btn2a(true);
      eva_sfa_close_popup(ctx);
    });
    popup_buttons.append(btn2_o);
  }
  popup_buttons.append(btn1_o);
  popup.show();
  $('body').css({overflow: 'hidden'});
  $(document).on('keydown', function(e) {
    if (e.which == 27) {
      eva_sfa_close_popup(ctx);
      if (btn2a) btn2a(false);
      e.preventDefault();
    }
    if (e.which == 13) {
      f_validate_run_and_close();
      e.preventDefault();
    }
  });
  if (ct && ct > 0) {
    eva_sfa_popup_tick(ctx, btn1_o, btn1text, btn2_o, btn2, btn2a, ct);
  }
  return true;
}

/* ----------------------------------------------------------------------------
 * INTERNAL FUNCTIONS AND VARIABLES
 */

eva_sfa_update_state_functions = Array();
eva_sfa_update_state_mask_functions = Array();
eva_sfa_ws = null;
eva_sfa_ajax_reload = null;
eva_sfa_heartbeat_reload = null;
eva_sfa_states = Array();

eva_sfa_log_level = 20;
eva_sfa_log_subscribed = false;
eva_sfa_log_first_load = true;
eva_sfa_log_loaded = false;
eva_sfa_log_started = false;

eva_sfa_lr2p = new Array();

eva_sfa_last_ping = null;
eva_sfa_last_pong = null;

eva_sfa_popup_active = null;

eva_sfa_log_level_names = {
  10: 'DEBUG',
  20: 'INFO',
  30: 'WARNING',
  40: 'ERROR',
  50: 'CRITICAL'
};

function eva_sfa_api_call(func, params, cb_success, cb_error, use_sysapi) {
  var id = eva_sfa_uuidv4();
  var payload = {
    jsonrpc: '2.0',
    method: func,
    params: params,
    id: id
  };
  return $.ajax({
    type: 'POST',
    //url: '/' + api + '/' + func,
    url: '/jrpc',
    contentType: 'application/json',
    data: JSON.stringify(payload),
    dataType: 'json',
    success: function(data) {
      if (
        !'id' in data ||
        data.id != id ||
        (!'result' in data && !'error' in data)
      ) {
        cb_error(9, 'Invalid server response', data);
      } else if ('error' in data) {
        if (cb_error) {
          cb_error(data.error.code, data.error.message, data);
        }
      } else {
        if (cb_success) {
          cb_success(data.result);
        }
      }
    },
    error: function(data) {
      if (cb_error) {
        cb_error(7, 'Server error', data);
      }
    }
  });
}

function eva_sfa_after_login(data) {
  var enter_type = 'masterkey';
  if(data.user) {
    enter_type = 'username';
  }
  var cookie_time = 0;
  if ($('#f_remember').is(':checked')) {
    cookie_time = 365;
  }
  if(enter_type == "masterkey") {
    create_cookie('enter_type', enter_type, cookie_time, '/cloudmanager/');
    create_cookie('masterkey', eva_sfa_apikey, cookie_time, '/cloudmanager/');
  } else {
    create_cookie('enter_type', enter_type, cookie_time, '/cloudmanager/');
    create_cookie('login', eva_sfa_login, cookie_time, '/cloudmanager/');
    create_cookie('password', eva_sfa_password, cookie_time, '/cloudmanager/');
  }
  eva_sfa_logged_in = true;
  eva_sfa_api_token = data.token;
  _eva_sfa_set_token_cookie();
  eva_sfa_load_initial_states(true, false);
  eva_sfa_heartbeat(true, data);
  if (!eva_sfa_ws_mode) {
    if (eva_sfa_ajax_reload !== null) {
      clearInterval(eva_sfa_ajax_reload);
    }
    eva_sfa_ajax_reload = setInterval(
      eva_sfa_load_initial_states,
      eva_sfa_ajax_reload_interval * 1000
    );
  } else {
    if (eva_sfa_ajax_reload !== null) {
      clearInterval(eva_sfa_ajax_reload);
    }
    if (eva_sfa_force_reload_interval) {
      eva_sfa_ajax_reload = setInterval(function() {
        eva_sfa_load_initial_states(false, true);
      }, eva_sfa_force_reload_interval * 1000);
    }
  }
  if (eva_sfa_heartbeat_reload !== null) {
    clearInterval(eva_sfa_heartbeat_reload);
  }
  eva_sfa_heartbeat_reload = setInterval(
    eva_sfa_heartbeat,
    eva_sfa_heartbeat_interval * 1000
  );
}

function eva_sfa_process_ws(evt) {
  var data = JSON.parse(evt.data);
  if (data.s == 'pong') {
    eva_sfa_last_pong = Date.now() / 1000;
    return;
  }
  if (data.s == 'reload') {
    if (eva_sfa_reload_handler != null) {
      return eva_sfa_reload_handler();
    }
  }
  if (data.s == 'server' && data.d == 'restart') {
    if (eva_sfa_server_restart_handler != null) {
      eva_sfa_server_restart_handler();
    }
    return;
  }
  if (eva_sfa_ws_event_handler !== null) {
    if (!eva_sfa_ws_event_handler(data)) return;
  }
  if (data.s == 'state') {
    $.each(data.d, function(i, s) {
      eva_sfa_process_state(s);
    });
    return;
  }
  if (data.s == 'log' && eva_sfa_log_started) {
    $.each(data.d, function(i, l) {
      eva_sfa_preprocess_log_record(l);
    });
    if (eva_sfa_log_postprocess != null) {
      eva_sfa_log_postprocess();
    }
    return;
  }
}

function eva_sfa_process_state(state) {
  var oid = state.type + ':' + state.group + '/' + state.id;
  // copy missing fields from old state
  if (oid in eva_sfa_states) {
    var old_state = eva_sfa_states[oid];
    $.each(Object.getOwnPropertyNames(old_state), function(k, v) {
      if (!(v in state)) {
        state[v] = old_state[v];
      }
    });
  }
  eva_sfa_states[oid] = state;

  if (!eva_sfa_cmp(state, old_state)) {
    if (oid in eva_sfa_update_state_functions) {
      var f = eva_sfa_update_state_functions[oid];
      if (typeof f === 'string' || f instanceof String) {
        eval(f);
      } else {
        f(state);
      }
    }
    $.each(Object.keys(eva_sfa_update_state_mask_functions), function(i, v) {
      if (eva_sfa_oid_match(oid, v)) {
        var f = eva_sfa_update_state_mask_functions[v];
        if (typeof f === 'string' || f instanceof String) {
          eval(f);
        } else {
          f(state);
        }
      }
    });
  }
}

function eva_sfa_preprocess_log_record(l) {
  if (!eva_sfa_log_loaded) {
    eva_sfa_lr2p.push(l);
  } else if (eva_sfa_process_log_record != null) {
    eva_sfa_process_log_record(l);
  }
}

function eva_sfa_start_ws() {
  var loc = window.location,
    uri;
  if (loc.protocol === 'https:') {
    uri = 'wss:';
  } else {
    uri = 'ws:';
  }
  uri += '//' + loc.host;
  eva_sfa_ws = new WebSocket(uri + '/ws?k=' + eva_sfa_api_token);
  eva_sfa_ws.onmessage = function(evt) {
    eva_sfa_process_ws(evt);
  };
  eva_sfa_ws.addEventListener('open', function(event) {
    var st = null;
    if (eva_sfa_state_updates) {
      st = {s: 'state'};
      if (eva_sfa_state_updates !== true) {
        var groups = eva_sfa_state_updates['g'];
        if (!groups) {
          groups = '#';
        }
        var tp = eva_sfa_state_updates['p'];
        if (!tp) {
          tp = '#';
        }
        st['g'] = groups;
        st['tp'] = tp;
        st['i'] = [];
      }
    }
    if (st) {
      eva_sfa_ws.send(JSON.stringify(st));
    }
    if (eva_sfa_log_subscribed) {
      eva_sfa_set_ws_log_level(eva_sfa_log_level);
    }
  });
}

function eva_sfa_set_ws_log_level(l) {
  eva_sfa_log_subscribed = true;
  try {
    if (eva_sfa_ws != null) eva_sfa_ws.send(JSON.stringify({s: 'log', l: l}));
  } catch (err) {}
}

function eva_sfa_stop_engine() {
  eva_sfa_states = Array();
  eva_sfa_server_info = null;
  eva_sfa_tsdiff = null;
  eva_sfa_last_ping = null;
  eva_sfa_last_pong = null;
  if (eva_sfa_heartbeat_reload !== null) {
    clearInterval(eva_sfa_heartbeat_reload);
    eva_sfa_heartbeat_reload = null;
  }
  if (eva_sfa_ajax_reload !== null) {
    clearInterval(eva_sfa_ajax_reload);
    eva_sfa_ajax_reload = null;
  }
  if (eva_sfa_ws !== null) {
    try {
      eva_sfa_ws.onclose = null;
      eva_sfa_ws.send(JSON.stringify({s: 'bye'}));
      eva_sfa_ws.close();
    } catch (err) {}
  }
}

function eva_sfa_heartbeat(on_login, data) {
  if (on_login) eva_sfa_last_ping = null;
  var q = eva_sfa_prepare();
  if (on_login) {
    q['icvars'] = 1;
  }
  if (eva_sfa_ws_mode) {
    if (eva_sfa_last_ping !== null) {
      if (
        eva_sfa_last_pong === null ||
        eva_sfa_last_ping - eva_sfa_last_pong > eva_sfa_heartbeat_interval
      ) {
        if (eva_sfa_heartbeat_error !== null) {
          eva_sfa_heartbeat_error();
        }
      }
    }
    if (!on_login && eva_sfa_ws !== null) {
      eva_sfa_last_ping = Date.now() / 1000;
      try {
        eva_sfa_ws.send(JSON.stringify({s: 'ping'}));
      } catch (err) {
        if (eva_sfa_heartbeat_error !== null) {
          eva_sfa_heartbeat_error();
        }
      }
    }
  }
  eva_sfa_api_call(
    'test',
    q,
    function(data) {
      eva_sfa_server_info = data;
      eva_sfa_tsdiff = new Date().getTime() / 1000 - data.time;
      if (on_login !== undefined && on_login) {
        eva_sfa_set_cvars(data['cvars']);
        if (eva_sfa_cb_login_success !== null) eva_sfa_cb_login_success(data);
      }
    },
    function(code, msg, data) {
      if (eva_sfa_heartbeat_error !== null) {
        eva_sfa_heartbeat_error(code, msg, data);
      }
    }
  );
}

function eva_sfa_set_cvars(cvars) {
  $.each(cvars, function(k, v) {
    eval(k + ' = "' + v + '"');
  });
}

function eva_sfa_do_load_states(cb) {
  if (!eva_sfa_state_updates) {
    cb([]);
  } else {
    var params = {};
    if (eva_sfa_state_updates !== true) {
      var groups = eva_sfa_state_updates['g'];
      var tp = eva_sfa_state_updates['p'];
      if (groups) {
        params['g'] = groups;
      }
      if (tp) {
        params['p'] = tp;
      }
    }
    eva_sfa_api_call('state_all', eva_sfa_prepare(params), cb);
  }
}

function eva_sfa_load_initial_states(on_login, reload) {
  eva_sfa_do_load_states(function(data) {
    $.each(data, function(i, s) {
      eva_sfa_process_state(s);
    });
    if (eva_sfa_ws_mode && reload !== true) {
      eva_sfa_start_ws();
    }
    if (on_login !== undefined && on_login) {
      if (eva_sfa_cb_states_loaded !== null) eva_sfa_cb_states_loaded(data);
    }
  });
}

function eva_sfa_load_log_entries(r, postprocess) {
  if (eva_sfa_ws_mode) eva_sfa_lr2p = new Array();
  var q = eva_sfa_prepare();
  q['l'] = eva_sfa_log_level;
  q['n'] = eva_sfa_log_records_max;
  eva_sfa_call(
    'log_get',
    q,
    function(data) {
      $('#logr').html('');
      if (eva_sfa_ws_mode && eva_sfa_log_first_load) {
        eva_sfa_set_ws_log_level(eva_sfa_log_level);
      }
      $.each(data, function(t, l) {
        if (eva_sfa_process_log_record != null) {
          eva_sfa_process_log_record(l);
        }
      });
      eva_sfa_log_loaded = true;
      $.each(eva_sfa_lr2p, function(i, l) {
        if (eva_sfa_process_log_record != null) {
          eva_sfa_process_log_record(l);
        }
      });
      if (postprocess && eva_sfa_log_postprocess != null) {
        eva_sfa_log_postprocess();
      }
      if ((!eva_sfa_ws_mode && eva_sfa_log_first_load) || r) {
        setTimeout(function() {
          eva_sfa_load_log_entries(true, false);
        }, eva_sfa_log_reload_interval * 1000);
      }
      eva_sfa_log_first_load = false;
    },
    function(data) {
      if ((!eva_sfa_ws_mode && eva_sfa_log_first_load) || r) {
        setTimeout(function() {
          eva_sfa_load_log_entries(true, false);
        }, eva_sfa_log_reload_interval * 1000);
      }
    }
  );
}

function eva_sfa_oid_match(oid, mask) {
  return new RegExp('^' + mask.split('*').join('.*') + '$').test(oid);
}

function _eva_sfa_deprecated(f1, f2) {
  console.log('!!! function ' + f1 + ' is deprecated. Use ' + f2 + ' instead');
}

function eva_sfa_close_popup(ctx) {
  $('body').css({overflow: 'auto'});
  $(document).off('keydown');
  $('#' + ctx).hide();
  eva_sfa_popup_active = null;
}

function eva_sfa_popup_priority(pclass) {
  if (pclass == 'info') return 20;
  if (pclass == 'warning') return 30;
  if (pclass == 'error') return 40;
  return 0;
}

function eva_sfa_popup_tick(ctx, btn1_o, btn1text, btn2_o, btn2, btn2a, ct) {
  if (ct <= 0) {
    eva_sfa_close_popup(ctx);
    if (btn2a) btn2a(false);
    return;
  }
  var obj = null;
  var txt = '';
  if (btn2_o) {
    obj = btn2_o;
    txt = btn2;
  } else {
    obj = btn1_o;
    txt = btn1text;
  }
  obj.html(txt + ' (' + ct + ')');
  setTimeout(function() {
    eva_sfa_popup_tick(ctx, btn1_o, btn1text, btn2_o, btn2, btn2a, ct - 1);
  }, 1000);
}

function eva_sfa_cmp(a, b) {
  if (a === undefined || b === undefined) {
    return false;
  }
  var a_props = Object.getOwnPropertyNames(a);
  var b_props = Object.getOwnPropertyNames(b);
  if (a_props.length != b_props.length) {
    return false;
  }
  for (var i = 0; i < a_props.length; i++) {
    var prop_name = a_props[i];
    if (!Array.isArray(a[prop_name]) && a[prop_name] !== b[prop_name]) {
      return false;
    }
  }
  return true;
}

function eva_sfa_prepare(params) {
  if (params === null || params === undefined) {
    var params = {};
  } else {
    var params = params;
  }
  if (eva_sfa_api_token != null) {
    params['k'] = eva_sfa_api_token;
  }
  return params;
}

function _eva_sfa_set_token_cookie() {
  if (eva_sfa_set_auth_cookies) {
    var uris = Array('/ui', '/pvt', '/rpvt');
    $.each(uris, function(k, v) {
      document.cookie = 'auth=' + eva_sfa_api_token + '; path=' + v;
    });
  }
}

function eva_sfa_uuidv4() {
  var dt = new Date().getTime();
  var uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(
    c
  ) {
    var r = (dt + Math.random() * 16) % 16 | 0;
    dt = Math.floor(dt / 16);
    return (c == 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
  return uuid;
}
