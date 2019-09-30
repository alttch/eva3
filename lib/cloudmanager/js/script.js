function setBodyHeight() {
  if ($('.page_content').height() > (window.innerHeight||screen.height) - $('.header').height() - 60) {
    $('body').css({height: 'auto'});
  } else {
    $('body').css({height: window.innerHeight||screen.height});
  }
}
function enableScroll(e) {
  var time = 1;
  if (e) {
    time = e;
  }
  setTimeout(function() {
    $(".nano").nanoScroller();
  },time);
}