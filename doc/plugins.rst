Core plug-ins
*************

Developing core plug-ins is the most advanced way to extend EVA ICS
functionality. You can create own API methods, functions for :doc:`/lm/macros`
and :doc:`/sfa/sfa_templates` plus much and much more.

Guide by example
================

.. note::

    All plugin objects and custom API functions are always registered as
    x_{plugin}_{name}

.. literalinclude:: examples/plugins/my.py
    :language: python

Resources
=========

.. include:: pydoc/pydoc_plugins.rst
