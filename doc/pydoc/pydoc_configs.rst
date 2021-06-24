
.. py


.. py:class:: ConfigFile(fname, init_if_missing=False, backup=True)
   

   A helper to manage .ini files
   
   .. rubric:: Example
   
   with ConfigFile('file.ini') as cf:
       cf.set('section', 'field1', 'value1')
   
   
   .. py:method:: ConfigFile.add_section(section, values)
      
   
      Add section with dict of values
      
   
   .. py:method:: ConfigFile.append(section, name, value)
      
   
      Append value to array field (in .ini configs, arrays are string fields
      with values, separated with commas)
      
   
   .. py:method:: ConfigFile.delete(section, name)
      
   
      Delete field from section
      
   
   .. py:method:: ConfigFile.get_section(section)
      
   
      Get dict of section values
      
   
   .. py:method:: ConfigFile.is_changed()
      
   
      Returns True, if configuration file was changed and will be saved after
      the statement exit
      
   
   .. py:method:: ConfigFile.remove(section, name, value)
      
   
      Remove value from array field
      
   
   .. py:method:: ConfigFile.remove_section(section)
      
   
      Remove section
      
   
   .. py:method:: ConfigFile.replace_section(section, values)
      
   
      Replace section with dict of values
      
   
   .. py:method:: ConfigFile.set(section, name, value)
      
   
      Set section field value
      

.. py:class:: ShellConfigFile(fname, init_if_missing=False, backup=True)
   

   A helper to manage shell scripts configuration files
   
   .. rubric:: Example
   
   with ShellConfigFile('eva_config') as cf:
       cf.set('KEYNAME', 0)
   
   
   .. py:method:: ShellConfigFile.append(name, value)
      
   
      Append value to array field (in shell configs, arrays are string fields
      with values, separated with spaces)
      
   
   .. py:method:: ShellConfigFile.delete(name)
      
   
      Delete field
      
   
   .. py:method:: ShellConfigFile.get(name, default=<class 'KeyError'>)
      
   
      Get field value
      
   
   .. py:method:: ShellConfigFile.is_changed()
      
   
      Returns True, if configuration file was changed and will be saved after
      the statement exit
      
   
   .. py:method:: ShellConfigFile.remove(name, value)
      
   
      Remove value from array field
      
   
   .. py:method:: ShellConfigFile.set(name, value)
      
   
      Set field to value
      
