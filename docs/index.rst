YAML Processor
==============

This project provides two utilities.

The data processor utility allows automation of the following in a single
command:

 - Modularisation of YAML files via include files.

   - Can use a query to select a sub data structure from an include file.
   - Can search for include files from a list of folders/directories.

 - Variable substitutions in string values.

   - Environment and pre-defined variables.
   - Date-time variables, based on the current time and/or a reference time.

 - Validation using JSON schema.

The schema processor utility is a compliment to the YAML modularisation /
include functionality provided by the data processor. It allows users to break
up a monolithic JSON schema file into a set of subschema files.

User Guide And Reference
------------------------

.. toctree::
   :maxdepth: 2

   install
   basic-usage
   data-preprocessor
   data-process
   schema-process
   cli
   api

* :ref:`genindex`
