/*
 * Author: Altertech Group, http://www.altertech.com/
 * Copyright: (C) 2012-2017 Altertech Group
 * License: See http://www.eva-ics.com/
 * Version: 3.0.1
 */

function open_tool_menu() {
    $('#toolmenu_btn').hide()
    $('#toolmenu').removeClass('hidden-xs hidden-sm')
    $('#toolmenu').show()
    toolmenu_opened = true
}


function close_tool_menu() {
    $('#toolmenu').addClass('hidden-xs hidden-sm')
    $('#toolmenu_btn').show()
    toolmenu_opened = false
}


function safe_close_tool_menu() {
    if (toolmenu_opened) close_tool_menu()
}
