Schema Processor
================

Consider the ``hello.yaml`` example in the :doc:`data-process`.
Its schema may look like:

.. code-block:: json

   {
       "properties": {
           "hello": {
               "items": {
                   "properties": {
                       "location": {
                           "type": "string"
                       },
                       "targets": {
                           "items": {
                               "type": "string"
                           },
                           "minItems": 1,
                           "type": "array",
                           "uniqueItems": true
                       }
                   },
                   "required": ["location", "targets"],
                   "type": "object"
               },
               "type": "array"
           }
       },
       "required": ["hello"],
       "type": "object"
   }

To split the schema to support these YAML files, however, we'll
use the schema processor. On the command line, the schema processor can
be invoke with this syntax:

.. code-block:: bash

   yp-schema SCHEMA-FILE CONFIG-FILE

For this command to work, we need to supply it with some settings
to tell it where to split up the schema in the syntax:

.. code-block:: json

   {
       "": "OUTPUT-ROOT-SCHEMA-FILENAME",
       "JMESPATH-1": "OUTPUT-SUB-SCHEMA-FILENAME-1",
       "And so on": "..."
   }

Obviously, we must have a root schema output file name.
The rest of the entries are output file names for the subschemas.
The `JMESPath <https://jmespath.org/>`_ syntax tells the
``yp-schema`` command where to split JSON schema into
subschemas. In the example above, we can use the setting:

.. code-block:: json

   {
       "": "hello.schema.json",
       "properties.hello.items": "hello-location.schema.json"
   }

The resulting ``hello.schema.json`` will look like this,
which can be used to validate both ``hello.yaml`` and ``hello-root.yaml``.

.. code-block:: json

   {
       "properties": {
           "hello": {
               "items": {
                   "oneOf": [
                       {"$ref": "hello-location.schema.json"},
                       {"$ref": "yp-include.schema.json"},
                   ]
               },
               "type": "array"
           }
       },
       "required": ["hello"],
       "type": "object"
   }

The resulting ``hello-location.schema.json`` will look like this
which can be used to validate ``earth.yaml`` and ``mars.yaml``:

.. code-block:: json

   {
       "properties": {
           "location": {
               "type": "string"
           },
           "targets": {
               "items": {
                   "type": "string"
               },
               "minItems": 1,
               "type": "array",
               "uniqueItems": true
           }
       },
       "required": ["location", "targets"],
       "type": "object"
   }

You may notice a file called ``yp-include.schema.json`` in the current
working directory. This is the sub-schema for the syntax related to the
``INCLUDE`` functionality described in :doc:`data-process`. The file is
referenced by ``hello.schema.json`` in the example above.

The default output location of the file is ``yp-include.schema.json``, but you
can change it by adding an entry for ``$ref.yp-include.schema.json`` in the
configuration file. Using the above example configuration file, you can do:

.. code-block:: json

   {
       "": "hello.schema.json",
       "$ref:yp-include.schema.json": "yp-include.schema.json",
       "properties.hello.items": "hello-location.schema.json"
   }

(Note: ``$ref:yp-include.schema.json`` is a special entry. It is not a valid
JMESPath syntax.)
