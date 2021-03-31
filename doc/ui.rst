UI basics
*********

HMI applications are served by :doc:`/sfa/sfa` from *EVA_DIR/ui* directory and
available by default at:

    \http://SFA_IP:8828/ui/

Typically, EVA ICS UI applications are completely written in JavaScript. The
file, called "ui/index.html" (or "ui/index.j2") should be the application entry
point.

The applications are usually coded in HTML+JavaScript. The UI applications
should use :doc:`/sfa/sfa_api` methods to authenticate, obtain data and
execute various actions.

Development
===========

EVA ICS provides the following tools to simplify UI development:

* `EVA JS Framework <https://github.com/alttch/eva-js-framework>`_ - provides
  high-level JavaScript API with various typical HMI features, such as
  authentication, data synchronization, events, actions etc.

* :doc:`/sfa/serve_as` in convenient ways.

* :doc:`/sfa/sfa_templates` - server-side templates for HTML, JS and other text
  files.

* :doc:`/sfa/sfa_pvt` - a special API to keep sensitive information securely
  and let it be accessible only to authenticated users.

* :doc:`/sfa/upload` - file upload API.

* :doc:`api_tokens` - use session-bound tokens to authenticate API calls

* Ready-to-use applications for :doc:`evahi`.

Some of ready-to-use HMI applications are available at `EVA ICS download page
<https://www.eva-ics.com/download>`_.

Custom error pages
==================

HTTP error responses (400, 403, 404, 405, 409 and 500) can be customized with
custom error pages. To customize an error response, create file
*EVA_DIR/ui/errors/<code>.html*, e.g. *EVA_DIR/ui/errors/404.html* for HTTP
Error 404 (Not Found).

Custom error pages can have *.j2* extensions as well. In this case, they are
processed as :doc:`/sfa/sfa_templates`.

UI Favicon
==========

If there is no way to define icon path with "link" HTML tag, put a file named
"favicon.ico" in EVA_DIR/ui/ directory to override the default favicon.
