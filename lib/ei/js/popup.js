/*
 * Author: Altertech Group, https://www.altertech.com/
 * Copyright: (C) 2012-2021 Altertech Group
 * License: Apache License 2.0
 * Version: 3.4.1
 */

function popup(pclass, title, msg, btn1, btn2, btn1a, btn2a, va) {
  var _pclass = pclass;
  $('#popup_window').removeClass();
  if (pclass[0] == '!') {
    _pclass = pclass.substr(1);
    $('#popup_window').addClass('popup_window_big');
  } else {
    $('#popup_window').addClass('popup_window');
  }
  $('#popup_header').removeClass();
  $('#popup_header').addClass('popup_header');
  $('#popup_header').addClass('popup_header_' + _pclass);
  $('#popup_header').html(title);
  $('#popup_content').html(msg);
  $('#popup_btn_1').html('');
  $('#popup_btn_2').html('');
  if (va === undefined) {
    _popup_validated = function() {
      return true;
    };
  } else {
    _popup_validated = va;
  }
  var btn1text = 'OK';
  if (btn1) {
    btn1text = btn1;
  }
  var btn1 = $('<div />', {
    class: 'popup_btn popup_btn_' + _pclass,
    html: btn1text
  });
  if (btn1a) {
    btn1.attr(
      'onclick',
      'if (_popup_validated()) {' + 'close_popup();' + btn1a + ';}'
    );
  } else {
    btn1.attr('onclick', 'close_popup()');
  }
  btn1.appendTo($('#popup_btn_1'));
  if (btn2) {
    var btn2 = $('<div />', {
      class: 'popup_btn popup_btn_' + _pclass,
      html: btn2
    });
    if (btn2a) {
      btn2.attr('onclick', btn2a);
    } else {
      btn2.attr('onclick', 'close_popup()');
    }
    btn2.appendTo($('#popup_btn_2'));
    $('#popup_btn_1').removeClass();
    $('#popup_btn_2').removeClass();
    $('#popup_btn_1').addClass('col-5 col-sm-4');
    $('#popup_btn_2').addClass('col-5 col-sm-4');
    $('#popup_btn_2').show();
  } else {
    $('#popup_btn_1').removeClass();
    $('#popup_btn_1').addClass('col-10 col-sm-8');
    $('#popup_btn_2').hide();
  }
  safe_close_tool_menu();
  $('#popup').show();
  $(document).on('keydown', function(e) {
    if (e.which == 27) {
      close_popup();
      e.preventDefault();
    }
    if (e.which == 13) {
      if (_popup_validated()) {
        close_popup();
        if (btn1a !== undefined) eval(btn1a);
        e.preventDefault();
      }
    }
  });
}

function close_popup() {
  $(document).off('keydown');
  $('#popup').hide();
}
