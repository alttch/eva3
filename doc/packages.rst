Packages
********

Custom extensions and other data can be packed into packages.

Package format
==============

EVA ICS packages have very simple format:

* The package should be tar or tgz archive, which is extracted to EVA_DIR as-is

* The package MUST contain the file, called *setup.py*

* The package SHOULD have the suffix .evapkg

Setting up packages
===================

Packages can be installed either via :ref:`install_pkg <sysapi_install_pkg>`
API method of any controller or with :ref:`IaC deployment<iac_pkg>` (in this
case, only :doc:`/uc/uc` or :doc:`/lm/lm` packages can be installed, or the
controller should have corresponding writing permissions to install e.g. UI
files).

Setup file format
=================

The Setup file should be called "setup.py" and is launched as EVA ICS
:doc:`corescript </corescript>` (so it has the access to all core script
methods). The script is launched with the event:

.. code-block:: python

  event.type == CS_EVENT_PKG_INSTALL

The variable **event.data** contains package setup params, specified in the API
call option "o".

The script also has the special method *extract_package*. When called, this
method extracts contents of the uploaded package to EVA ICS directory.

.. note::

    Setup script has no access to the package files, except calling extraction
    method. The package is uploaded to controller's memory and there is no
    temporary file written.

Here is a very simple example of the package setup script:

.. code:: python

    if event.type == CS_EVENT_PKG_INSTALL:
        logger.warning(f'installing package with options: {event.data}')
        extract_package()

The package setup script SHOULD check event type, as it can be launched with
other core script events later (functionality is reserved for the further EVA
ICS versions).

Keeping setup core script after install
=======================================

Sometimes it is useful to keep setup core script code after the package
installation is completed. To do that, the function "keep_me()" can be used:

.. code:: python

    # ... perform setup tasks
    keep_me()

When called, the new core script is created from the setup corescript code, for
the controller the package is installed on. This can be useful if the package
requires performing additional tasks, e.g. starts / stops some service at the
controller startup / shutdown.

Installing additional Python modules
====================================

The function "pip_install" allows installing additional Python modules, calling
"pip install" command from EVA ICS venv. The modules are also automatically
added to the node venv configuration.

.. code:: python

    # ... perform setup tasks
    pip_install('flask')

Manipulating with configuration files
=====================================

The setup core script automatically has configuration helpers in globals. These
helpers are already in globals and should not be imported manually.

.. include:: pydoc/pydoc_configs.rst
