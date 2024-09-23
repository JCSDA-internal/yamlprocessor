Command Line Reference
======================


yp-data
-------

Usage:

.. code-block:: bash

   yp-data [options] input-file-name ... output-file-name
   yp-data [options] -o output-file-name input-file-name ...

See :doc:`data-process` for detail.

.. program:: yp-data

.. option:: file-names

   Names of input or input+output files. Use ``-`` for STDIN/STDOUT.

.. option:: --out-filename=FILENAME, -o FILENAME

   Name of output file. Use ``-`` for STDOUT.

.. option:: --include=DIR, -I DIR

   Add search locations for item specified as relative paths.
   See also :envvar:`YP_INCLUDE_PATHS`.

.. option:: --define=KEY=VALUE, -D KEY=VALUE

   Map KEY to VALUE for variable substitutions.

.. option:: --undefine=KEY, -U KEY

   Unmap KEY for variable substitutions.

.. option:: --no-environment, -i

   Do not use environment variables in variable substitutions.

.. option:: --unbound-placeholder=VALUE

   Substitute an unbound variable with VALUE instead of failing. Use
   ``YP_ORIGINAL`` as VALUE to leave the original syntax unchanged on
   unbound variables.

.. option:: --no-process-include

   Do not process include file instructions.

.. option:: --no-process-variable

   Do not process variable substitutions.

.. option:: --schema-prefix=PREFIX

   Prefix for relative path schemas. See also :envvar:`YP_SCHEMA_PREFIX`.

.. option:: --time-format=NAME=FORMAT, --time-format=FORMAT

   Format for date-time string substitutions.
   See also :envvar:`YP_TIME_FORMAT` and :envvar:`YP_TIME_FORMAT_<NAME>`.

.. option:: --time-ref=TIME

   Reference value for date-time substitutions.
   See also :envvar:`YP_TIME_REF_VALUE`.

yp-preprocesor
--------------

Usage:

.. code-block:: bash

   yp-preprocesor [options] -o output-file-name input-file-name

See :doc:`data-process` for detail.

.. program:: yp-data

.. option:: file-names

   Names of input or input files. Use ``-`` for STDIN/STDOUT.

.. option:: --out-filename=FILENAME, -o FILENAME

   Name of output file. Use ``-`` for STDOUT.

.. option:: --define=KEY=VALUE, -D KEY=VALUE

   Map KEY to VALUE for variable substitutions.

yp-schema
---------

Usage:

.. code-block:: bash

   yp-schema SCHEMA-FILE CONFIG-FILE

See :doc:`schema-process` for detail.

.. program:: yp-schema

.. option:: SCHEMA-FILE

   Name of the JSON schema file to modularise.

.. option:: CONFIG-FILE

   Name of the configuration file.

Common Options
--------------

The following options apply to both :program:`yp-data`, :program:`yp-preprocessor`
and :program:`yp-schema` commands.

.. program:: yp-*

.. option:: --help, -h

   Show help message and exit.

.. option:: --version, -V

   Print version and exit.


Environment Variables
---------------------

.. envvar:: YP_INCLUDE_PATHS

   Set the search path for include files (that are specified as relative
   locations). Expect a list of folders/directories in the same syntax as
   a ``PATH`` like variable on the relevant platform. (E.g., a colon separated
   list on Linux/Unix and a semi-colon separated list on Windows.)
   See :ref:`Modularisation / Include` for more info.

.. envvar:: YP_SCHEMA_PREFIX

   Set a prefix for relative locations to JSON schema files.
   See :ref:`Validation with JSON Schema` for more info.

.. envvar:: YP_TIME_FORMAT

   Set the default time format.
   See :ref:`String Value Date-Time Substitution` for more info.

.. envvar:: YP_TIME_FORMAT_<NAME>

   Set a named time format.
   See :ref:`String Value Date-Time Substitution` for more info.

.. envvar:: YP_TIME_REF_VALUE

   Set the reference time. Expect an ISO-8601 compliant date-time string.
   See :ref:`String Value Date-Time Substitution` for more info.
