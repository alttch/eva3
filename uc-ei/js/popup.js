/*
 * Author: Altertech Group, http://www.altertech.com/
 * Copyright: (C) 2012-2017 Altertech Group
 * License: See http://www.eva-ics.com/
 * Version: 3.0.1
 */

function popup(pclass, title, msg, btn1, btn2, btn1a, btn2a) {
  $('#popup_header').removeClass();
  $('#popup_header').addClass('popup_header');
  $('#popup_header').addClass('popup_header_' + pclass);
  $('#popup_header').html(title);
  $('#popup_content').html(msg);
  $('#popup_btn_1').html('');
  $('#popup_btn_2').html('');
  var btn1text = 'OK';
  if (btn1) {
    btn1text = btn1;
  }
  var btn1 = $('<div />', {
    class: 'popup_btn popup_btn_' + pclass,
    html: btn1text,
  });
  if (btn1a) {
    btn1.attr('onclick', 'close_popup();' + btn1a);
  } else {
    btn1.attr('onclick', 'close_popup()');
  }
  btn1.appendTo($('#popup_btn_1'));
  if (btn2) {
    var btn2 = $('<div />', {
      class: 'popup_btn popup_btn_' + pclass,
      html: btn2,
    });
    if (btn2a) {
      btn2.attr('onclick', btn2a);
    } else {
      btn2.attr('onclick', 'close_popup()');
    }
    btn2.appendTo($('#popup_btn_2'));
    $('#popup_btn_1').removeClass();
    $('#popup_btn_2').removeClass();
    $('#popup_btn_1').addClass('col-xs-5 col-sm-4');
    $('#popup_btn_2').addClass('col-xs-5 col-sm-4');
    $('#popup_btn_2').show();
  } else {
    $('#popup_btn_1').removeClass();
    $('#popup_btn_1').addClass('col-xs-10 col-sm-8');
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
      close_popup();
      if (btn1a !== undefined) eval(btn1a);
      e.preventDefault();
    }
  });
}

function close_popup() {
  $(document).off('keydown');
  $('#popup').hide();
}
