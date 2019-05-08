Mobile clients
**************

Android
=======

EVA ICS Control Center client
-----------------------------

You can use official `EVA ICS Control Center client
<https://play.google.com/store/apps/details?id=com.altertech.evacc`_ to access
:doc:`SFA</sfa/sfa>` UI from Android-based mobile phones.

.. figure:: sfa.png
    :scale: 100%
    :align: right

The client is evaHI-based application, so it can be `configured the same way
<https://github.com/alttch/evaHI#create-configuration-file-on-your-web-server>`_

:doc:`SFA</sfa/sfa>` automatically maps *ui/.evahi* directory to */.evahi* URI.
If front-end server is used, URI should be accessible without user
authentication to let all application features work properly.

SFA framework function :ref:`eva_sfa_hi_qr<sfw_eva_sfa_hi_qr>` can be used to
generate configuration QR code for the current authenticated user.

Building own client
-------------------

You can easily build custom Android client for your EVA ICS UI, customizing
application class, name, menu, icons. Please refer to
`evaHI<https://github.com/alttch/evaHI>`_ building instructions.

Apple iOS and other mobile platforms
====================================

Currently we have no plans to release native iOS client, iPhone users may
access :doc:`SFA</sfa/sfa>` UI via 3rd-party apps or built-in mobile browser.

