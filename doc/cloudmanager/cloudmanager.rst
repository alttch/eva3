Cloud Manager
*************

If *cloud_manager* option is enabled in :doc:`/sfa/sfa` configuration file, you
may monitor and manage the whole your EVA ICS setup via web interface.

Cloud manager can be accessed at *http://<SFA_IP>:8828/cloudmanager* by users
with master key assigned. You may create such user in :doc:`CLI </cli>` or use
master API key to login.

Dashboard
=========

.. figure:: cloudmanager.png
    :scale: 50%
    :alt: Cloud Manager Dashboard

Cloud Manager dashboard display all resources, available for :doc:`/sfa/sfa`
where Cloud Manager is running on.

Controller management
=====================

Connected controllers can be also managed. :doc:`/sfa/sfa` must know controller
master API key to connect and manage remote controller.

If Cloud Manager was not enabled during the installation, you should specify
master key manually by pressing "edit" button in the controller table. By
default, local master key is used.

.. figure:: cloudmanager_edit_controller.png
    :scale: 50%
    :alt: Cloud Manager Dashboard
