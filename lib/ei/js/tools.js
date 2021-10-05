/*
 * Author: Altertech Group, https://www.altertech.com/
 * Copyright: (C) 2012-2021 Altertech Group
 * License: Apache License 2.0
 * Version: 3.4.2
 */

function load_animation(o) {
  $('#' + o).html(
    '<div class="cssload-square"><div ' +
      'class="cssload-square-part cssload-square-green">' +
      '</div><div class="cssload-square-part cssload-square-pink">' +
      '</div><div class="cssload-square-blend"></div></div>'
  );
}

function get_arg(name) {
  url = window.location.href;
  name = name.replace(/[\[\]]/g, '\\$&');
  var regex = new RegExp('[?&]' + name + '(=([^&#]*)|&|#|$)'),
    results = regex.exec(url);
  if (!results) return null;
  if (!results[2]) return '';
  return decodeURIComponent(results[2].replace(/\+/g, ' '));
}

function pad(num, size) {
  var s = num + '';
  while (s.length < size) s = '0' + s;
  return s;
}

function escape_oid(oid) {
  return oid.replace(/[:\/]/g, '___')
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

function isInt(n) {
  if (n == '' || n == null) return false;
  return Number(n) == n && n % 1 == 0;
}

function isNumeric(n) {
  if (n == '' || n == null) return false;
  return Number(n) == n;
}

function dynamic_sort(property) {
  var sortOrder = 1;
  if (property[0] === '-') {
    sortOrder = -1;
    property = property.substr(1);
  }
  return function(a, b) {
    var result =
      a[property] < b[property] ? -1 : a[property] > b[property] ? 1 : 0;
    return result * sortOrder;
  };
}
