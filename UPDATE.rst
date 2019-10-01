EVA ICS 3.2.5
*************

What's new
==========

- Cloud Manager web ui
- various bug fixes

Complete change log: https://get.eva-ics.com/3.2.5/stable/CHANGELOG.html

Update instructions
===================

Install and enjoy

Notes
=====

LM PLC chill-out logic changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Old way:

 - rule during chill-out period is completely ignored, rule match isn't checked
   after chill-out time

New way:

 - rule during chill-out period is ignored, however if rule event is triggered
   during chill-out time, action is executed after chill-out period if rule
   still matches the condition.
