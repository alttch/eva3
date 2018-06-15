SCADA Final Aggregator
----------------------

SCADA Final Aggregator (SFA) is a subsystem usually installed directly in the
host wherein the user interface or third-party applications are installed.

Aggregates all the :doc:`control and monitoring items</items>`, :doc:`logic
macros</lm/macros>` and :doc:`decision rules</lm/decision_matrix` from all
connected :doc:`UC</uc/uc>` and :doc:`LM PLC</lm/lm>` controllers into a single
space. As the result, the final interface or application doesn't need to know
on which controller the :doc:`item</items>` is present, it does all the
function calls directly to SFA. Ids of the items should always be specified in
full form (*group/id*) and be unique in the whole installation.

.. figure:: sfa.png
    :scale: 50%
    :alt: SCADA Final Aggregator

    Example of the controller aggregation with the use of two SFA servers

SFA is set up and controlled with **sfa-cmd** :doc:`console application</cli>`
and :doc:`sfa_api`. The API doesn't have an user interface by default, it's
developed specifically for the certain installation using specifically for the
certain installation using :doc:`sfa_framework`.
