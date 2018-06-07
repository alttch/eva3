Virtual items
=============

:doc:`/uc/uc` items may be either virtual or real. You may toggle the item by
changing the configuration while the server is running.

What are virtual items?
-----------------------

Virtual items were originally developed for testing EVA, but we decided to
include them in the final product. Virtual items allow you to:

* Test EVA without connecting a real equipment
* Debug various configurations before embedding
* Check how the system responses to the emergencies

:any:`Units<unit>`, :any:`sensors<sensor>` and :any:`multiupdates<multiupdate>`
can be virtual and have the following features:

* The virtual unit runs the action commands just like the real one
* You can manually assign any value to the virtual sensor
* The virtual multiupdate updates states of the  several virtual items at once
  in passive mode

The :doc:`/cli` console application *./xc/evirtual* is used to control the
virtual items. API and the interface for the remote control of the items will
be added to the future EVA versions.

Before switching the item to the virtual state, you should create its
configuration:

    ./xc/evirtual sensor temp1 init
    ./xc/evirtual sensor temp2 init
    ./xc/evirtual mu mutemp init temp1,temp2
    ./xc/evirtual sensor temp1 set 1 29.44
    ./xc/evirtual sensor temp2 set 1 29.556
    ./xc/evirtual sensor temp1 update
    29.445
    ./xc/evirtual mu mutemp update
    29.44
    29.556

The behavior of evirtual application is similar to the behavior of :doc:`item
scripts</item_scripts>`; if item is in the virtual state, the system
automatically runs "evirtual" instead of the real control/update script. If
there is no virtual item configuration, :doc:`UC</uc/uc>` will return an error
once you try to start the action or the passive update.

After the item is made real, its virtual configuration is preserved and can be
used later if the item is made virtual again.

Basic operations with virtual items
-----------------------------------

To display all virtual configurations, you should run a command

    ./xc/evirtual list

To create a new configuration, you should run a command

    ./xc/evirtual unit unit1 init 0
    ./xc/evirtual sensor sensor1 init 1 29.445

You can specify the initial value of the item state (status and value) after
init. If the virtual configuration already exists, it will be rewritten.

To create a new configuration of :any:`multiupdate<multiupdate>`, you should
run a command

    ./xc/evirtual mu multiupdate1 init unit1,sensor1

To add/delete the item to/from the multiupdate, you should re-create its
configuration.

To display the virtual item parameters, you should run the following command:

    ./xc/evirtual unit unit1

To set the status or value or the unit or sensor, you should run the following
command:

    ./xc/evirtual unit unit1 set 1
    ./xc/evirtual sensor sensor1 set 1 29.4445

You should always set the status, but the value is an optional parameter.

To simulate the execution of the unit action script, you should run the
following command:

    ./xc/evirtual unit unit1 1

To delete the virtual item configuration, you should run the following command:

    ./xc/evirtual unit unit1 rm
    ./xc/evirtual sensor sensor1 rm
    ./xc/evirtual mu multiupdate1 rm

Active virtual items
--------------------

Active virtual items automatically send their state to the :doc:`/uc/uc` after
being changed via :doc:`/uc/uc_api`.

In order to make the item active, you should run the following command:

    ./xc/evirtual unit unit1 x
    ./xc/evirtual sensor sensor1 x

After running the command

    ./xc/evirtual unit unit1 nx

the item is no longer active and automatically stops sending its status.

Errors and delays simulation
----------------------------

For the unit, simulation of action failures may be set up as follows:

* ./xc/evirtual unit unit1 as - after the the action is called, the virtual
  unit changes its status normally
* ./xc/evirtual unit unit1 is - does not change its status and does not report
  an error
* ./xc/evirtual unit unit1 av - changes its value normally
* ./xc/evirtual unit unit1 iv - does not change its value and does not report
  an error
* ./xc/evirtual unit unit1 a - changes both status and value
* ./xc/evirtual unit unit1 i - does not change neither status nor value without
  reporting an error

For the unit, simulation of action delay is set up as follows:

    ./xc/evirtual unit unit1 d 2.5

after the action is received, the unit simulates a delay, e. g. 2.5 sec (in this
example)

For the unit, simulation of the action runtime failure is set up as follows:

    ./xc/evirtual unit unit1 e 1

after the action is received, the program exits with the error code 1. To
disable the error code, set it to 0

For all the items: to simulate, let's say, a 3.5-second delay when the UC
starts a passive status update

    ./xc/evirtual unit unit1 ud 3.5
    ./xc/evirtual sensor temp1 ud 3.5
    ./xc/evirtual mu multiupdate1 ud 3.5

For all the items: to complete the passive state update with the error code 1

    ./xc/evirtual sensor temp1 ue 1

To disable the error code, set it to 0.
