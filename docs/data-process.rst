Data Processor
==============


Modularisation / Include
------------------------

Consider an input YAML file containing the following data:

.. code-block:: yaml

   hello:
     - INCLUDE: earth.yaml
     - INCLUDE: mars.yaml

If ``earth.yaml`` contains:

.. code-block:: yaml

   location: earth
   targets:
     - human
     - cat
     - dog

And ``mars.yaml`` contains:

.. code-block:: yaml

   location: mars
   targets:
     - martian

Running the processor on the input YAML file will yield the following output:

.. code-block:: yaml

   hello:
     - location: earth
       targets:
         - human
         - cat
         - dog
     - location: mars
       targets:
         - martian

If an include file is specified as a relative location, the processor searches
for it from these locations in order:

 - The folder/directory containing the parent file.
 - The current working folder/directory.
 - The list of include folders/directories. This list can be specified:

   - Using the environment variable ``YP_INCLUDE_PATH``. Use the same syntax as
     the ``PATH`` environment variable on your platform to specify multiple
     folders/directories.
   - Using the command line option :option:`--include=DIR <yp-data --include>`.
     This option can be used multiple times.
     The utility will append each ``DIR`` to the list.
   - In the :py:attr:`.include_paths` (list) attribute of the relevant
     :py:class:`yamlprocessor.dataprocess.DataProcessor` instance.

(In Python only.) The :py:attr:`.include_dict` (dict) attribute of the relevant
:py:class:`yamlprocessor.dataprocess.DataProcessor` instance can be populated
with keys to match ``INCLUDE`` names. On a matching key, the value will be
inserted as if it were the content loaded from an include file. The processor
will always attempt to find a match from this attribute before looking for
matching include files from the file system. Suppose we use the following
Python logic with the above files:

.. code-block:: python

   from yamlprocessor.dataprocess import DataProcessor
   # ...
   processor = DataProcessor()
   processor.include_dict.update({
       'earth.yaml': {'location': 'earth', 'targets': ['dinosaur']},
   })
   processor.process_data('hello.yaml')

We'll get:

.. code-block:: yaml

   hello:
     - location: earth
       targets:
         - dinosaur
     - location: mars
       targets:
         - martian

LIMITATIONS

 - YAML anchors/references will only work within files, so an include file will
   not see anchors in the parent file, and vice versa.
 - Since INCLUDE is part of a map/dict, keys in the same map/dict that are not
   recognised will not be processed.


Modularisation / Include with Query
-----------------------------------

Consider an example where we want to include only a subset of the data
structure from the include file.
We can use a `JMESPath <https://jmespath.org/>`_ query to achieve this.

For example, we may have something like this in ``hello-root.yaml``:

.. code-block:: yaml

   hello:
     INCLUDE: planets.yaml
     QUERY: "[?type=='rocky']"

Where ``planets.yaml`` contains:

.. code-block:: yaml

   - location: earth
     type: rocky
     targets:
       - human
       - cat
       - dog
   - location: mars
     type: rocky
     targets:
       - martian
   - location: jupiter
     type: gaseous
     targets:
       - ...

The processor will select the planets of rocky type,
and the output will look like:

.. code-block:: yaml

   hello:
   - location: earth
     type: rocky
     targets:
       - human
       - cat
       - dog
   - location: mars
     type: rocky
     targets:
       - martian


String Value Variable Substitution
----------------------------------

Consider:

.. code-block:: yaml

   key: ${SWEET_HOME}/sugar.txt

If ``SWEET_HOME`` is defined in the environment and has a value
``/home/sweet``, then passing the above input to the processor will give the
following output:

.. code-block:: yaml

   key: /home/sweet/sugar.txt

Note:

 - The processor recognises both ``$SWEET_HOME`` or ``${SWEET_HOME}``.
 - The processor is not implemented using a shell,
   so shell variable syntax won't work.

You can configure what variables are available for substitution.

On the command line:

 - Use the :option:`--define=KEY=VALUE <yp-data --define>`
   (``-D KEY=VALUE``) option
   to define new variables or override the value of an existing one.
 - Use the :option:`--undefine=KEY <yp-data --undefine>` (``-U KEY``)
   option to remove a variable.
 - Use the :option:`--no-environment <yp-data --no-environment>` (``-i``)
   option if you do not want to use any variables defined in the environment
   for substitution. (So only those specified with
   :option:`--define=KEY=VALUE <yp-data --define>` will work.)

In Python, simply manipulate the :py:attr:`.variable_map` (dict) attribute of
the relevant :py:class:`yamlprocessor.dataprocess.DataProcessor` instance. The
dict is a copy of :py:data:`os.environ` at initialisation.

Finally, if you reference a variable in YAML that is not defined, you will
normally get an unbound variable error. You can modify this behaviour by
setting a place holder. On the command line, use the
:option:`--unbound-placeholder=VALUE <yp-data --unbound-placeholder>`
option. In Python, set the :py:attr:`.unbound_placeholder` attribute of the
relevant :py:class:`yamlprocessor.dataprocess.DataProcessor` instance to a
string value.


String Value Variable Substitution Include Scope
------------------------------------------------

It is possible to define or override the values of the variables for
substitution in include files. The scope of the change will be local to the
include file (and files that it includes). The following is an example of how
to specify include scope variables.

Suppose we have a file called ``hello.yaml`` with:

.. code-block:: yaml

   hello:
     - INCLUDE: world.yaml
       VARIABLES:
         WORLD_NAME: venus
     - INCLUDE: world.yaml
       VARIABLES:
         WORLD_NAME: mars
     - INCLUDE: world.yaml

And a file called ``world.yaml`` with:

.. code-block:: yaml

   name: ${WORLD_NAME}
   is_rocky: true

Running :program:`yp-data --define=WORLD_NAME=earth hello.yaml <yp-data>` will
give:

.. code-block:: yaml

   hello:
     - name: venus
       is_rocky: true
     - name: mars
       is_rocky: true
     - name: earth
       is_rocky: true

This can even be nested. For example, suppose we have ``main.yaml``:

.. code-block:: yaml

   hello:
   - INCLUDE: building.yaml
     VARIABLES:
       building: Castle
       car: Porsche

And a file called ``building.yaml`` with:

.. code-block:: yaml

   property: ${building}
   car:
     INCLUDE: cars.yaml

And a file called ``cars.yaml`` with:

.. code-block:: yaml

   type: ${car}

Running :program:`yp-data main.yaml <yp-data>` will give:

.. code-block:: yaml

   hello:
   - property: Castle
     car:
       type: Porsche


String Value Date-Time Substitution
-----------------------------------

The YAML processor utility also supports date-time substitution using a
similar syntax, for variables names starting with:

 - ``YP_TIME_NOW`` (current time, time when :program:`yp-data` starts running
   or set on initialisation of a
   :py:class:`yamlprocessor.dataprocess.DataProcessor` instance).
 - ``YP_TIME_REF`` (reference time, specified using
   the :envvar:`YP_TIME_REF_VALUE` environment variable,
   the :option:`--time-ref=VALUE <yp-data --time-ref>`
   command line option, or the :py:attr:`.time_ref` attribute of the relevant
   :py:class:`yamlprocessor.dataprocess.DataProcessor` instance in Python). If
   no value is set for the reference time, any reference to the reference time
   will simply use the current time.

You can use one or more of these trailing suffixes to apply deltas for the
date-time:

 - ``_PLUS_XXX``: adds the duration to the date-time.
 - ``_MINUS_XXX``: substracts the duration to the date-time.
 - ``_AT_xxx``: sets individual fields of the date-time.
   E.g., ``_AT_T0H`` will set the hour of the day part of the date-time to
   ``00`` hour.

where ``xxx`` is date-time duration-like syntax in the form ``nYnMnDTnHnMnS``,
e.g.:

 - ``12Y`` is 12 years.
 - ``1M2D`` is 1 month and 2 days.
 - ``1DT12H`` is 1 day and 12 hours.
 - ``T12H30M`` is 12 hours and 30 minutes.

Examples, (for argument sake, let's assume the
current time is ``2022-02-01T10:11:18Z`` and
we have set the reference time to ``2024-12-25T11:11:11Z``.)

.. list-table::
   :header-rows: 1

   * - Variable
     - Output
   * - ${YP_TIME_NOW}
     - 2022-02-01T10:11:18Z
   * - ${YP_TIME_NOW_AT_T0H0M0S}
     - 2022-02-01T00:00:00Z
   * - ${YP_TIME_NOW_AT_T0H0M0S_PLUS_T12H}
     - 2022-02-01T12:00:00Z
   * - ${YP_TIME_REF}
     - 2024-12-25T11:11:11Z
   * - ${YP_TIME_REF_AT_1DT18H}
     - 2024-12-01T18:11:11Z
   * - ${YP_TIME_REF_PLUS_T6H30M}
     - 2024-12-25T17:41:11Z
   * - ${YP_TIME_REF_MINUS_1D}
     - 2024-12-24T11:11:11Z

You can specify different date-time output formats using:

 - Environment variables :envvar:`YP_TIME_FORMAT[_<NAME>]`.
 - The command line option
   :option:`--time-format=[NAME=]FORMAT <yp-data --time-format>`.
 - The :py:attr:`.time_formats` (dict) attribute of the relevant
   :py:class:`yamlprocessor.dataprocess.DataProcessor`
   instance in Python. The default format is ``%FT%T%:z``.

For example, if you set:

 - ``--time-format='%FT%T%:z'`` (default)
 - ``--time-format=CTIME='%a %e %b %T %Z %Y'``
   or ``export YP_TIME_FORMAT_CTIME='%a %e %b %T %Z %Y'``
 - ``--time-format=ABBR='%Y%m%dT%H%M%S%z'``
   or ``export YP_TIME_FORMAT_ABBR='%Y%m%dT%H%M%S%z'``

Then:

.. list-table::
   :header-rows: 1

   * - Variable
     - Output
   * - ${YP_TIME_REF}
     - 2024-12-25T11:11:11Z
   * - ${YP_TIME_REF_FORMAT_CTIME}
     - Wed 25 Dec 11:11:11 GMT 2024
   * - ${YP_TIME_REF_PLUS_T12H_FORMAT_ABBR}
     - 20241225T231111Z

See `strftime <https://man7.org/linux/man-pages/man3/strftime.3.html>`_,
for example, for a list of date-time format code. The processor also
supports the following format codes for numeric time zone:

* ``%:z`` +hh:mm numeric time zone (e.g., -08:00, +05:45).
* ``%::z`` + hh:mm numeric time zone (e.g., -08:00:00, +05:45:00).
* ``%:::z`` numeric time zone with ``:`` to the necessary precision
  (e.g., -08, +05:45).

In addition, for all numeric time zone format code (including ``%z``),
the processor will use ``Z`` to denote UTC time zone (instead of for
example ``+00:00``) to save space.

Finally, if a variable name is already in the variable substitution mapping,
e.g., defined in the environment or in a ``--define=...`` option, then the
defined value takes precedence, so if you have already ``export
YP_TIME_REF=whatever``, then you will get the value ``whatever`` instead of the
reference time.


Cast Value Variable Substitution
--------------------------------

Environment variables are strings by nature, but YAML scalars can be numbers or
booleans. Therefore, for non-string scalar values, i.e. integers, floats and
booleans, the YAML processor utility supports casting the value to the correct
type before using it for substitution:

``${NAME.int}``
    Cast value of ``NAME`` to an integer.

``${NAME.float}``
    Cast value of ``NAME`` to a float.

``${NAME.bool}``
    Cast value of ``NAME`` to a boolean. Value of ``NAME`` must be one of
    the supported case insensitive strings: ``yes``, ``true`` and ``1`` will
    cast to the boolean ``true``, and ``no``, ``false`` and ``0`` will be cast
    to the boolean ``false``.

For example, suppose we have ``main.yaml``:

.. code-block:: yaml

   version: ${ITEM_VERSION.int}
   speed: ${ITEM_SPEED.float}

Running
:program:`yp-data -D ITEM_VERSION=4 -D ITEM_SPEED=3.14 main.yaml <yp-data>`
will give:

.. code-block:: yaml

   version: 4
   speed: 3.14

Note: The processor casts integers and floats using Python's built-in
:py:func:`int` and :py:func:`float` functions. The exact behaviour may change
with the version of Python you are using.

However, a single value can only have a single substitution with a cast:

.. code-block:: yaml

   - ${NUM2.int}             # good
   - xyz${NUM2.int}          # bad
   - ${NUM2.int}${NUM3.int}  # bad


Turn Off Processing
-------------------

If you need to turn off processing of ``INCLUDE`` syntax, you can do:

 - On the command line, use the
   :option:`--no-process-include <yp-data --no-process-include>` option.
 - In Python, set the :py:attr:`.is_process_include` attribute of the relevant
   :py:class:`yamlprocessor.dataprocess.DataProcessor` instance to ``False``.

If you need to turn off processing of variable and date-time substitution,
you can do:

 - On the command line, use the
   :option:`--no-process-variable <yp-data --no-process-variable>` option.
 - In Python, set the :py:attr:`.is_process_variable` attribute of the relevant
   :py:class:`yamlprocessor.dataprocess.DataProcessor` instance to ``False``.


Validation with JSON Schema
---------------------------

You can tell the processor to look for a JSON schema file and validate
the current YAML file by adding a schema association line to the beginning
of the YAML file, which can be one of:

 - ``#!<SCHEMA-URI>``
 - ``# yaml-language-server: $schema=<SCHEMA-URI>``

Where the ``SCHEMA-URI`` is a string pointing to the location of a JSON schema
file.  Some simple assumptions apply:

 - If ``SCHEMA-URI`` is a normal URI with a leading scheme,
   e.g., ``https://``, it is used as-is.
 - If ``SCHEMA-URI`` does not have a leading scheme and exists in the local
   file system, then it is also used as-is.
 - Otherwise, a schema URI prefix can be specified to add to the value of
   ``SCHEMA-URI`` using:

   - The :envvar:`YP_SCHEMA_PREFIX` environment variable.
   - On the command line, the
     :option:`--schema-prefix=PREFIX <yp-data --schema-prefix>` option.
   - In Python, the :py:attr:`.schema_prefix` attribute of the relevant
     :py:class:`yamlprocessor.dataprocess.DataProcessor` instance.

For example, if we have ``export YP_SCHEMA_PREFIX=file:///etc/`` in the
environment, both of the following examples will result in a validation
against the JSON schema in ``file:///etc/world/hello.schema.json``.

.. code-block:: yaml

   #!file:///etc/world/hello.schema.json
   greet: earth
   # ...

.. code-block:: yaml

   #!world/hello.schema.json
   greet: earth
   # ...
