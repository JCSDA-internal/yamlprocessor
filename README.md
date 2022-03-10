# YAML Processor

## Installation

To install from PyPI, run:

```sh
python3 -m pip install yamlprocessor
```

## Introduction

This project provides two command line utilities `yp-data` and `yp-schema`,
which are based on the Python modules `yamlprocessor.dataprocess`
and `yamlprocessor.schemaprocess` respectively.

The `yp-data` utility allows automation of the following in a single command:

* Modularisation of YAML files via include files.
  * Can use a query to select a sub data structure from an include file.
  * Can search for include files from a list of folders/directories.
* Variable substitutions in string values.
  * Environment and pre-defined variables.
  * Date-time variables, based on the current time and/or a reference time.
* Validation using JSON schema.

The `yp-schema` utility is a compliment to the YAML modularisation / include
functionality provided by `yp-data`. It allows users to break up a monolithic
JSON schema file into a set of subschema files.

## Basic Usages

Command line:

```sh
yp-data [options] input-file-name output-file-name
```

Type `yp-data --help` for a list of options, and see below for usage detail.

Python:

```python
from yamlprocessor.dataprocess import DataProcessor
processor = DataProcessor()
# ... Customise the `DataProcessor` instance as necessary ..., then:
processor.process_data(in_file_name, out_file_name)
```

## YAML Modularisation / Include

Consider an input YAML file containing the following data:

```yaml
hello:
  - INCLUDE: earth.yaml
  - INCLUDE: mars.yaml
```

If `earth.yaml` contains:

```yaml
location: earth
targets:
  - human
  - cat
  - dog
```

And `mars.yaml` contains:

```yaml
location: mars
targets:
  - martian
```

Running the processor on the input YAML file will yield the following output:

```yaml
hello:
  - location: earth
    targets:
      - human
      - cat
      - dog
  - location: mars
    targets:
      - martian
```

If an include file is specified as a relative location, the processor searches
for it from these locations in order:

* The folder/directory containing the parent file.
* The current working folder/directory.
* The list of include folders/directories. This list can be specified:
  * Using the environment variable `YP_INCLUDE_PATH`. Use the same syntax as
    the `PATH` environment variable on your platform to specify multiple
    folders/directories.
  * Using the command line option `--include=DIR`. This option can be used
    multiple times. The utility will append each `DIR` to the list.
  * In the `.include_paths` (list) attribute of the relevant `DataProcessor`
    instance.

LIMITATION. It is worth noting that YAML anchors/references will only work
within files, so an include file will not see anchors in the parent file,
and vice versa.

## YAML Modularisation / Include with Query

Consider an example where we want to include only a subset of the data structure
from the include file. We can use a [JMESPath](https://jmespath.org/)
query to achieve this.

For example, we may have something like this in `hello-root.yaml`:

```yaml
hello:
  INCLUDE: planets.yaml
  QUERY: "[?type=='rocky']"
```

Where `planets.yaml` contains:

```yaml
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
```

The processor will select the planets of rocky type,
and the output will look like:

```yaml
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
```

## YAML String Value Variable Substitution

Consider:

```yaml
key: ${SWEET_HOME}/sugar.txt
```

If `SWEET_HOME` is defined in the environment and has a value `/home/sweet`,
then passing the above input to the processor will give the following output:

```yaml
key: /home/sweet/sugar.txt
```

Note:

* The processor recognises both `$SWEET_HOME` or `${SWEET_HOME}`.
* The processor is not implemented using a shell,
  so shell variable syntax won't work.

You can configure what variables are available for substitution.

On the command line:

* Use the `--define=NAME=VALUE` (`-D NAME=VALUE`) option
  to define new variables or override the value of an existing one.
* Use the `--undefine=NAME` (`-U NAME`) option to remove a variable.
* Use the `--no-environment` (`-i`) option if you do not want to use any
  variables defined in the environment for substitution. (So only those
  specified with `--define=NAME=VALUE` will work.)

In Python, simply manipulate the `.variable_map` (dict) attribute of the
relevant `DataProcessor` instance. The dict is a copy of `os.environ` at
initialisation.

Finally, if you reference a variable in YAML that is not defined, you will
normally get an unbound variable error. You can modify this behaviour by
setting a place holder. On the command line, use the
`--unbound-placeholder=VALUE` option. In Python, set the
`.unbound_placeholder` attribute of the relevant `DataProcessor` instance to a
string value.

## YAML String Value Date-Time Substitution

The YAML processor utility also supports date-time substitution using a
similar syntax, for variables names starting with:
* `YP_TIME_NOW` (current time, time when `yp-data` starts running or set on
  initialisation of an `DataProcessor` instance).
* `YP_TIME_REF` (reference time, specified using the `YP_TIME_REF_VALUE`
  environment variable, the `--time-ref=VALUE` command line option, or the
  `.time_ref` attribute of the relevant `DataProcessor` instance in Python). If
  no value is set for the reference time, any reference to the reference time
  will simply use the current time.

You can use one or more of these trailing suffixes to apply deltas for the date-time:

* `_PLUS_XXX`: adds the duration to the date-time.
* `_MINUS_XXX`: substracts the duration to the date-time.
* `_AT_xxx`: sets individual fields of the date-time. E.g. `_AT_T0H` will set
  the hour of the day part of the date-time to 00 hour.

where `xxx` is date-time duration-like syntax in the form `nYnMnDTnHnMnS`, e.g.:
* 12Y is 12 years.
* 1M2D is 1 month and 2 days.
* 1DT12H is 1 day and 12 hours.
* T12H30M is 12 hours and 30 minutes.

Examples, (for argument sake, let's assume the
current time is `2022-02-01T10:11:18Z` and
we have set the reference time to `2024-12-25T11:11:11Z`.)

```sh
${YP_TIME_NOW}                       # 2022-02-01T10:11:18Z
${YP_TIME_NOW_AT_T0H0M0S}            # 2022-02-01T00:00:00Z
${YP_TIME_NOW_AT_T0H0M0S_PLUS_T12H}  # 2022-02-01T12:00:00Z
${YP_TIME_REF}                       # 2024-12-25T11:11:11Z
${YP_TIME_REF_AT_1DT18H}             # 2024-12-01T18:11:11Z
${YP_TIME_REF_PLUS_T6H30M}           # 2024-12-25T17:41:11Z
${YP_TIME_REF_MINUS_1D}              # 2024-12-24T11:11:11Z
```

You can specify different date-time output formats using:

* Environment variables `YP_TIME_FORMAT[_<NAME>]`.
* The command line option `--time-format=[NAME=]FORMAT`.
* The `.time_formats` (dict) attribute of the relevant `DataProcessor`
  instance in Python.
  The default format is `.time_formats[''] = '%FT%T%:z'`.

For example, if you set:
* `--time-format='%FT%T%:z'` (default)
* `--time-format=CTIME='%a %e %b %T %Z %Y'`
  or `export YP_TIME_FORMAT_CTIME='%a %e %b %T %Z %Y'`
* `--time-format=ABBR='%Y%m%dT%H%M%S%z'`
  or `export YP_TIME_FORMAT_ABBR='%Y%m%dT%H%M%S%z'`

Then:

```sh
${YP_TIME_REF}                        # 2024-12-25T11:11:11Z
${YP_TIME_REF_FORMAT_CTIME}           # Wed 25 Dec 11:11:11 GMT 2024
${YP_TIME_REF_PLUS_T12H_FORMAT_ABBR}  # 20241225T231111Z
```

See [strftime](https://man7.org/linux/man-pages/man3/strftime.3.html),
for example, for a list of date-time format code. The processor also
supports the following format codes for numeric time zone:

* `%:z` +hh:mm numeric time zone (e.g., -08:00, +05:45).
* `%::z` + hh:mm numeric time zone (e.g., -08:00:00, +05:45:00).
* `%:::z` numeric time zone with `:` to the necessary precision
  (e.g., -08, +05:45).

In addition, for all numeric time zone format code (including `%z`),
the processor will use `Z` to denote UTC time zone (instead of for
example `+00:00`) to save space.

Finally, if a variable name is already in the variable substitution mapping,
e.g., defined in the environment or in a `--define=...` option, then the defined
value takes precedence, so if you have already `export YP_TIME_REF=whatever`,
then you will get the value `whatever` instead of the reference time.

## Turn Off YAML Processing

If you need to turn off processing of `INCLUDE` syntax, you can do:

* On the command line, use the `--no-process-include` option.
* In Python, set the `.is_process_include` attribute of the relevant
  `DataProcessor` instance to `False`.

If you need to turn off processing of variable and date-time substitution,
you can do:

* On the command line, use the `--no-process-variable` option.
* In Python, set the `.is_process_variable` attribute of the relevant
  `DataProcessor` instance to `False`.

## YAML Validation with JSON Schema

You can tell the processor to look for a JSON schema file and validate
the current YAML file by adding a `#!<SCHEMA-URI>` to the beginning
of the YAML file. The `SCHEMA-URI` is a string pointing to the location
of a JSON schema file. Some simple assumptions apply:

* If `SCHEMA-URI` is a normal URI with a leading scheme,
  e.g., `https://`, it is used as-is.
* If `SCHEMA-URI` does not have a leading scheme and exists in the local
  file system, then it is also used as-is.
* Otherwise, a schema URI prefix can be specified to add to the value of
  `SCHEMA-URI` using:
  * The `YP_SCHEMA_PREFIX` environment variable.
  * On the command line, the `--schema-prefix=PREFIX` option.
  * In Python, the `.schema_prefix` attribute of the relevant
    `DataProcessor` instance.

For example, if we have `export YP_SCHEMA_PREFIX=file:///etc/` in the
environment, both of the following examples will result in a validation
against the JSON schema in `file:///etc/world/hello.schema.json`.

```yaml
#!file:///etc/world/hello.schema.json
greet: earth
# ...
```

```yaml
#!world/hello.schema.json
greet: earth
# ...
```

## JSON Schema Modularisation

Consider the `hello.yaml` example we have earlier. Its schema may look like:

```json
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
```

To split the schema to support these YAML files, however, we'll
use the `yp-schema SCHEMA-FILE CONFIG-FILE` command.
For this command to work, we need to supply it with some settings
to tell it where to split up the schema in the syntax:

```json
{
    "OUTPUT-ROOT-SCHEMA-FILENAME": "",
    "OUTPUT-SUB-SCHEMA-FILENAME-1": "JMESPATH-1",
    /* and so on */
}
```

Obviously, we must have a root schema output file name.
The rest of the entries are output file names for the subschemas.
The [https://jmespath.org/](JMESPath) syntax tells the
`yp-schema` command where to split JSON schema into
subschemas. In the example above, we can use the setting:

```json
{
    "hello.schema.json": "",
    "hello-location.schema.json": "properties.hello.items"
}
```

The resulting `hello.schema.json` will look like this,
which can be used to validate both `hello.yaml` and `hello-root.yaml`:

```json
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
```

The resulting `hello-location.schema.json` will look like this
which can be used to validate `earth.yaml` and `mars.yaml`:

```json
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
```
