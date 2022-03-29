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
       "OUTPUT-ROOT-SCHEMA-FILENAME": "",
       "OUTPUT-SUB-SCHEMA-FILENAME-1": "JMESPATH-1",
       "And so on": "..."
   }

Obviously, we must have a root schema output file name.
The rest of the entries are output file names for the subschemas.
The `JMESPath <https://jmespath.org/>`_ syntax tells the
``yp-schema`` command where to split JSON schema into
subschemas. In the example above, we can use the setting:

.. code-block:: json

   {
       "hello.schema.json": "",
       "hello-location.schema.json": "properties.hello.items"
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
                       {
                           "properties": {
                               "INCLUDE": {
                                   "type": "string"
                               },
                               "QUERY": {
                                   "type": "string"
                               }
                           },
                           "required": ["INCLUDE"],
                           "type": "string"
                       }
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
