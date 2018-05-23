/*
 * Author: Altertech Group, http://www.altertech.com/
 * Copyright: (C) 2012-2017 Altertech Group
 * License: See http://www.eva-ics.com/
 * Version: 3.0.2
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
 * Contains functions called after either successful or failed login
 */
eva_sfa_cb_login_success = null;
eva_sfa_cb_login_error = null;

/** Contains function which's called as f(data) when ws event is received
 *  function should return true, if it return false, WS data processing
 *  is stopped
 */
eva_sfa_ws_event_handler = null;

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
 * Reload interval for rule monitor (in seconds)
 */
eva_sfa_rule_monitor_interval = 60;

/**
 * "Heartbeat" interval (requests to system info, in seconds)
 */
eva_sfa_heartbeat_interval = 5;

/**
 * After successfull login contains server info (API test function output)
 * data is refreshed every eva_sfa_heartbeat_interval seconds
 */
eva_sfa_server_info = null;

/**
 * WebSocket mode if true, is set by eva_sfa_init()
 * Setting this to false (after calling eva_sfa_init()) will force
 * AJAX mode
 */
eva_sfa_ws_mode = true;

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
  var q = '';
  if (eva_sfa_apikey !== null) {
    if (eva_sfa_apikey != '') {
      q += 'k=' + eva_sfa_apikey;
    }
  } else {
    q += 'u=' + eva_sfa_login + '&p=' + eva_sfa_password;
  }
  $.post('/sfa-api/login', q, function(data) {
    eva_sfa_after_login(data);
  }).error(function(data) {
    eva_sfa_logged_in = false;
    eva_sfa_stop_engine();
    if (eva_sfa_cb_login_error !== null) eva_sfa_cb_login_error(data);
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
 * Start rule monitor. Rule monitor should be started manually after every
 * login because in many typical cases rules are registered after the sucessful
 * auth
 */
function eva_sfa_start_rule_monitor() {
  if (eva_sfa_rule_reload !== null) {
    clearInterval(eva_sfa_rule_reload);
  } else {
    eva_sfa_rule_monitor();
  }
  eva_sfa_rule_reload = setInterval(
    eva_sfa_rule_monitor,
    eva_sfa_rule_monitor_interval * 1000,
  );
}

/**
 * Stop API
 * After calling the function will close open WebSocket if available,
 * clear all the refresh intervals then try to close server session
 */
function eva_sfa_stop(cb) {
  eva_sfa_stop_engine();
  eva_sfa_logged_in = false;
  $.getJSON('/sfa-api/logout', function(data) {
    if (cb !== undefined && cb !== null) cb(data);
  }).error(function(data) {
    if (cb !== undefined && cb !== null) cb(data);
  });
}

/**
 * Register the function (or javascript code) to be called in case of state
 * change event (or at first state load)
 *
 * @param oid - object id in format obj:full_id, i.e. sensor:env/temp1
 * @param cb - function to be called
 *
 * if state is already loaded, function will be called immediately
 */
function eva_sfa_register_update_state(oid, cb) {
  eva_sfa_update_state_functions[oid] = cb;
  var state = eva_sfa_state(oid);
  if (state !== undefined) cb(state);
}

/**
 * Register rule to be monitored
 *
 * @param rule_id - rule ID
 * @param cb - function called after rule props are reloaded
 */
function eva_sfa_register_rule(rule_id, cb) {
  eva_sfa_rules_to_monitor.push({rule_id: rule_id, cb: cb});
  var props = eva_sfa_rule_props(rule_id);
  if (props !== undefined) cb(props);
}

/**
 * Get obj state
 *
 * @param oid - object id in format obj:full_id, i.e. sensor:env/temp1
 *
 * @returns - object state or undefined if no object found
 */
function eva_sfa_state(oid) {
  if (oid in eva_sfa_states) {
    return eva_sfa_states[oid];
  } else {
    return undefined;
  }
}

/**
 * Get rule props
 *
 * @param rule_id - rule ID
 *
 * @returns - object with rule props or undefined if no rule found
 */
function eva_sfa_rule_props(rule_id) {
  if (rule_id in eva_sfa_rule_props_data) {
    return eva_sfa_rule_props_data[rule_id];
  } else {
    return undefined;
  }
}

/**
 * Get obj status
 *
 * @param oid - object id in format obj:full_id, i.e. sensor:env/temp1
 *
 * @returns object status(int) or undefined if no object found
 */
function eva_sfa_status(oid) {
  var state = eva_sfa_state(oid);
  if (state === undefined || state === null) return undefined;
  return state.status;
}

/**
 * Get obj status
 *
 * @param oid - object id in format obj:full_id, i.e. sensor:env/temp1
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
 * Run macro
 *
 * @param macro_id - full macro ID
 * @param args - macro args (string)
 * @param wait - seconds to wait until complete
 * @param priority - action priority (optional)
 * @param uuid - action uuid (optional)
 */
function eva_sfa_run(
  macro_id,
  args,
  wait,
  priority,
  uuid,
  cb_success,
  cb_error,
) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += 'k=' + eva_sfa_apikey;
  }
  q += '&i=' + macro_id;
  if (args !== undefined && args !== null) {
    q += '&a=' + encodeURIComponent(args);
  }
  if (priority !== undefined && priority !== null) {
    q += '&p=' + priority;
  }
  if (uuid !== undefined && uuid !== null) {
    q += '&u=' + uuid;
  }
  if (wait !== undefined && wait !== null) {
    q += '&w=' + wait;
  }
  $.getJSON('/sfa-api/run?' + q, function(data) {
    if (cb_success !== undefined && cb_success !== null) cb_success(data);
  }).error(function(data) {
    if (cb_error !== undefined && cb_error !== null) cb_error(data);
  });
}

/**
 * Execute unit action
 *
 * @param unit_id - full unit ID
 * @param nstatus - new unit status (int)
 * @param nvalue - new unit value (optional)
 * @param wait - seconds to wait until complete
 * @param priority - action priority (optional)
 * @param uuid - action uuid (optional)
 */
function eva_sfa_action(
  unit_id,
  nstatus,
  nvalue,
  wait,
  priority,
  uuid,
  cb_success,
  cb_error,
) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += 'k=' + eva_sfa_apikey;
  }
  q += '&i=' + unit_id;
  q += '&s=' + nstatus;
  if (nvalue !== undefined && nvalue !== null) {
    q += '&v=' + nvalue;
  }
  if (priority !== undefined && priority !== null) {
    q += '&p=' + priority;
  }
  if (uuid !== undefined && uuid !== null) {
    q += '&u=' + uuid;
  }
  if (wait !== undefined && wait !== null) {
    q += '&w=' + wait;
  }
  $.getJSON('/sfa-api/action?' + q, function(data) {
    if (cb_success !== undefined && cb_success !== null) cb_success(data);
  }).error(function(data) {
    if (cb_error !== undefined && cb_error !== null) cb_error(data);
  });
}

/**
 * Execute unit action, toggle current status (if status is 0 or 1)
 *
 * @param unit_id - full unit ID
 * @param wait - seconds to wait until complete
 * @param priority - action priority (optional)
 * @param uuid - action uuid (optional)
 *
 * @returns true - if action started
 *          false - if no status loaded
 */
function eva_sfa_action_toggle(
  unit_id,
  wait,
  priority,
  uuid,
  cb_success,
  cb_error,
) {
  var cstatus = eva_sfa_status('unit:' + unit_id);
  if (cstatus === undefined) return false;
  var nstatus = cstatus ? 0 : 1;
  eva_sfa_action(
    unit_id,
    nstatus,
    null,
    wait,
    priority,
    uuid,
    cb_success,
    cb_error,
  );
  return true;
}

/**
 * Kill running unit action and clean queue
 *
 * @param unit_id - full unit ID
 */
function eva_sfa_kill(unit_id, cb_success, cb_error) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += 'k=' + eva_sfa_apikey;
  }
  q += '&i=' + unit_id;
  $.getJSON('/sfa-api/kill?' + q, function(data) {
    if (cb_success !== undefined && cb_success !== null) cb_success(data);
  }).error(function(data) {
    if (cb_error !== undefined && cb_error !== null) cb_error(data);
  });
}

/**
 * Clean queue for unit
 *
 * @param unit_id - full unit ID
 */
function eva_sfa_q_clean(unit_id, cb_success, cb_error) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += 'k=' + eva_sfa_apikey;
  }
  q += '&i=' + unit_id;
  $.getJSON('/sfa-api/q_clean?' + q, function(data) {
    if (cb_success !== undefined && cb_success !== null) cb_success(data);
  }).error(function(data) {
    if (cb_error !== undefined && cb_error !== null) cb_error(data);
  });
}

/**
 * Terminate current unit action if possible
 *
 * @param unit_id - full unit ID
 */
function eva_sfa_terminate(unit_id, cb_success, cb_error) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += 'k=' + eva_sfa_apikey;
  }
  q += '&i=' + unit_id;
  $.getJSON('/sfa-api/terminate?' + q, function(data) {
    if (cb_success !== undefined && cb_success !== null) cb_success(data);
  }).error(function(data) {
    if (cb_error !== undefined && cb_error !== null) cb_error(data);
  });
}

/**
 * Set lvar value
 *
 * @param lvar_id - full lvar ID
 * @param value - new lvar value, optional
 */
function eva_sfa_set(lvar_id, value, cb_success, cb_error) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += 'k=' + eva_sfa_apikey;
  }
  q += '&i=' + lvar_id;
  q += '&v=' + value;
  $.getJSON('/sfa-api/set?' + q, function(data) {
    if (cb_success !== undefined && cb_success !== null) cb_success(data);
  }).error(function(data) {
    if (cb_error !== undefined && cb_error !== null) cb_error(data);
  });
}

/**
 * Set lvar value, toggle current value (if value is 0 or 1)
 * useful when lvar is being used as flag
 *
 * @param lvar_id - full lvar ID
 * @returns true - if set started
 *          false - if no value loaded
 */
function eva_sfa_set_toggle(lvar_id, cb_success, cb_error) {
  var cvalue = eva_sfa_value('lvar:' + lvar_id);
  if (cvalue === undefined) return false;
  var nvalue = cvalue ? 0 : 1;
  eva_sfa_set(lvar_id, nvalue, cb_success, cb_error);
  return true;
}

/**
 * Reset lvar (set status/value to 1)
 *
 * @param lvar_id - full lvar ID
 */
function eva_sfa_reset(lvar_id, cb_success, cb_error) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += 'k=' + eva_sfa_apikey;
  }
  q += '&i=' + lvar_id;
  $.getJSON('/sfa-api/reset?' + q, function(data) {
    if (cb_success !== undefined && cb_success !== null) cb_success(data);
  }).error(function(data) {
    if (cb_error !== undefined && cb_error !== null) cb_error(data);
  });
}

/**
 * Set rule prop
 *
 * @param rule_id - rule ID
 * @param prop - rule property
 * @param value - new prop value, optional
 * @param save - true if rule should be immediately saved
 */
function eva_sfa_set_rule_prop(
  rule_id,
  prop,
  value,
  save,
  cb_success,
  cb_error,
) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += 'k=' + eva_sfa_apikey;
  }
  q += '&i=' + rule_id;
  q += '&p=' + prop;
  if (value !== undefined && value !== null) {
    q += '&v=' + value;
  }
  if (save !== undefined && save !== null && save) {
    q += '&save=1';
  }
  $.post('/sfa-api/set_rule_prop', q, function(data) {
    if (cb_success !== undefined && cb_success !== null) cb_success(data);
  }).error(function(data) {
    if (cb_error !== undefined && cb_error !== null) cb_error(data);
  });
}
/* ----------------------------------------------------------------------------
 * INTERNAL FUNCTIONS AND VARIABLES
 */

eva_sfa_update_state_functions = Array();
eva_sfa_rules_to_monitor = Array();
eva_sfa_logged_in = false;
eva_sfa_ws = null;
eva_sfa_ajax_reload = null;
eva_sfa_heartbeat_reload = null;
eva_sfa_rule_reload = null;
eva_sfa_states = Array();
eva_sfa_rule_props_data = Array();

eva_sfa_last_ping = null;
eva_sfa_last_pong = null;

function eva_sfa_after_login(data) {
  eva_sfa_logged_in = true;
  eva_sfa_load_initial_states();
  eva_sfa_heartbeat(true, data);
  if (!eva_sfa_ws_mode) {
    if (eva_sfa_ajax_reload !== null) {
      clearInterval(eva_sfa_ajax_reload);
    }
    eva_sfa_ajax_reload = setInterval(
      eva_sfa_load_initial_states,
      eva_sfa_ajax_reload_interval * 1000,
    );
  } else {
    if (eva_sfa_ajax_reload !== null) {
      clearInterval(eva_sfa_ajax_reload);
    }
    if (eva_sfa_force_reload_interval) {
      eva_sfa_ajax_reload = setInterval(function() {
        eva_sfa_load_initial_states(true);
      }, eva_sfa_force_reload_interval * 1000);
    }
  }
  if (eva_sfa_heartbeat_reload !== null) {
    clearInterval(eva_sfa_heartbeat_reload);
  }
  eva_sfa_heartbeat_reload = setInterval(
    eva_sfa_heartbeat,
    eva_sfa_heartbeat_interval * 1000,
  );
}

function eva_sfa_process_ws(evt) {
  var data = JSON.parse(evt.data);
  if (data.s == 'pong') {
    eva_sfa_last_pong = Date.now() / 1000;
    return;
  }
  if (eva_sfa_ws_event_handler !== null) {
    if (!eva_sfa_ws_event_handler(data)) return;
  }
  if (data.s == 'state') {
    $.each(data.d, function(i, s) {
      eva_sfa_process_state(s);
    });
  }
}

function eva_sfa_process_state(state) {
  var oid = state.type + ':' + state.group + '/' + state.id;
  eva_sfa_states[oid] = state;
  if (oid in eva_sfa_update_state_functions) {
    var f = eva_sfa_update_state_functions[oid];
    if (typeof f === 'string' || f instanceof String) {
      eval(f);
    } else {
      f(state);
    }
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
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += '?k=' + eva_sfa_apikey;
  }
  eva_sfa_ws = new WebSocket(uri + '/ws' + q);
  eva_sfa_ws.onmessage = function(evt) {
    eva_sfa_process_ws(evt);
  };
  eva_sfa_ws.addEventListener('open', function(event) {
    eva_sfa_ws.send(JSON.stringify({s: 'state'}));
  });
}

function eva_sfa_stop_engine() {
  eva_sfa_states = Array();
  eva_sfa_rule_props_data = Array();
  eva_sfa_server_info = null;
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
  if (eva_sfa_rule_reload !== null) {
    clearInterval(eva_sfa_rule_reload);
    eva_sfa_rule_reload = null;
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
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '')
    q += '?k=' + eva_sfa_apikey;
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
  $.getJSON('/sfa-api/test' + q, function(data) {
    eva_sfa_server_info = data;
    if (on_login !== undefined && on_login) {
      if (eva_sfa_cb_login_success !== null) eva_sfa_cb_login_success(data);
    }
  }).error(function(data) {
    if (eva_sfa_heartbeat_error !== null) {
      eva_sfa_heartbeat_error(data);
    }
  });
}

function eva_sfa_rule_monitor() {
  $.each(eva_sfa_rules_to_monitor, function(i, r) {
    eva_sfa_load_rule_props(r.rule_id, r.cb);
  });
}

function eva_sfa_load_rule_props(rule_id, cb) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '')
    q += 'k=' + eva_sfa_apikey;
  q += '&i=' + rule_id;
  $.post('/sfa-api/list_rule_props', q, function(data) {
    eva_sfa_rule_props_data[rule_id] = data;
    if (cb !== undefined && cb !== null) cb(data);
  });
}

function eva_sfa_load_initial_states(reload) {
  var q = '';
  if (eva_sfa_apikey !== null && eva_sfa_apikey != '') {
    q += '?k=' + eva_sfa_apikey;
  }
  $.getJSON('/sfa-api/state_all' + q, function(data) {
    $.each(data, function(i, s) {
      eva_sfa_process_state(s);
    });
    if (eva_sfa_ws_mode && reload !== true) {
      eva_sfa_start_ws();
    }
  });
}
