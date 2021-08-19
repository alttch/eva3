/*
 * Author: Altertech Group, https://www.altertech.com/
 * Copyright: (C) 2012-2021 Altertech Group
 * License: Apache License 2.0
 * Version: 3.4.1
 */

function open_tool_menu() {
  $('#toolmenu_btn').hide();
  $('#toolmenu').removeClass('hidden-xs hidden-sm');
  $('#toolmenu').show();
  toolmenu_opened = true;
}

function close_tool_menu() {
  $('#toolmenu').addClass('hidden-xs hidden-sm');
  $('#toolmenu_btn').show();
  toolmenu_opened = false;
}

function safe_close_tool_menu() {
  if (toolmenu_opened) close_tool_menu();
}
