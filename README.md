# YAML Processor

## Installation

To install from PyPI, run:

```sh
python3 -m pip install yamlprocessor
```

## YAML Modularisation / Include

Allow modularisation of YAML files using a controlled include file mechanism,
backed by dividing the original JSON schema file into a set of subschema files.

Consider a YAML file `hello.yaml`:

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
# And so on
```

And its associated JSON schema file:

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

We want to modularise the YAML file in this way.
Let's call this `hello-root.yaml`:

```yaml
hello:
  - INCLUDE: earth.yaml
  - INCLUDE: mars.yaml
```

Where `earth.yaml` contains:

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

At runtime, we can run the `yp-data INFILE OUTFILE`
command to process and recombine the YAML files.

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
subschemas. In the example above, we can give use the setting:

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

## YAML Modularisation / Include with Query

Consider an example where we want to include only a subset of the data structure
from the include file. We can use a [JMESPath](https://jmespath.org/)
query to achieve this.

For example, we may have something like this in `hello-root.yaml`:

```yaml
hello:
  INCLUDE: planets.yaml
  QUERY: "[?type=='rocky'].{location: location, targets: targets}"
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

Running `yp-data hello-root.yaml` will return:

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

## YAML Validation with JSON Schema

You can tell `yp-data` to look for a JSON schema file and validate
the current YAML file by adding a `#!<SCHEMA-URI>` to the beginning
of the YAML file. The `SCHEMA-URI` is a string pointing to the location
of a JSON schema file. Some simple assumptions apply:

* If `SCHMEA-URI` is a normal URI with a leading scheme,
  e.g. `https://`, it is used as-is.
* If `SCHEMA-URI` does not have a leading scheme and exists in the local
  file system, then it is also used as-is.
* Otherwise, if the `YP_SCHEMA_PREFIX` environment variable is defined
  or if `--schema-prefix=PREFIX` is specified, then the prefix will be
  added to the value of the `SCHEMA-URI`.

## YAML String Value Variable Substitution

Process variable substitution syntax for string values in YAML files.
Consider:

```yaml
key: ${SWEET_HOME}/sugar.txt
```

(Note: You can write `$SWEET_HOME` or `${SWEET_HOME}` in here.)

If `SWEET_HOME` is defined in the environment and has a value `/home/sweet`,
then running `yp-data` on the above will give:

```yaml
key: /home/sweet/sugar.txt
```

You can also use the `--define=NAME=VALUE` (`-D NAME=VALUE`) option
of `yp-data` to define and/or override environment variables.
E.g., `yp-data -D SWEET_HOME=/home/sweet` provides another way to
specify the value of a variable to use for substitution.

## YAML String Value Date-Time Substitution

The `yp-data` application also supports date-time substitution using a
similar syntax, for variables names starting with `YP_TIME_NOW` (time
when `yp-data` starts running) `YP_TIME_REF` (reference time,
specified using the `YP_TIME_REF_VALUE` environment variable
or the `--time-ref=VALUE` command line option). If no value is set
for the reference time, any reference to the reference time will
simply use the current time.

You can use one or more of these trialing suffixes to apply deltas for the date-time:

* `_ADD_XXX`: adds the duration to the date-time.
* `_MINUS_XXX`: substracts the duration to the date-time.
* `_AT_xxx`: sets individual fields of the date-time. E.g. `_AT_T0H` will set
  the hour of the day part the date-time to 00 hour.

where `xxx` is date-time duration-like syntax in the form `nYnMnDTnHnMnS`, e.g.:
* 12Y is 12 years.
* 1M2D is 1 month and 2 days.
* 1DT12H is 1 day and 12 hours.
* T12H30M is 12 hours and 30 minutes.

Examples, (for argument sake, let's assume the
current time is `2022-02-01T10:11:18Z` and
we have set the reference time to `2024-12-25T00:00:00Z`.)

```sh
${YP_TIME_NOW}                      # 2022-02-01T10:11:18+0000
${YP_TIME_NOW_AT_0H0M0S}            # 2022-02-01T00:00:00+0000
${YP_TIME_NOW_AT_0H0M0S_PLUS_T12H}  # 2022-02-01T12:00:00+0000
${YP_TIME_REF}                      # 2024-12-25T00:00:00+0000
${YP_TIME_REF_AT_1DT18H}            # 2024-12-01T18:00:00+0000
${YP_TIME_REF_PLUS_T6H30M}          # 2024-12-25T06:30:00+0000
${YP_TIME_REF_MINUS_1D}             # 2024-12-24T00:00:00+0000
```

You can control date-time output formats using the
`--time-format=[NAME=]FORMAT` option or `YP_TIME_FORMAT[_<NAME>]`
environment variables.

For example, if you set:
* `--time-format='%FT%T%z'` (default)
* `--time-format=CTIME='%a %e %b %T %Z %Y'`
  or `export YP_TIME_FORMAT_CTIME='%a %e %b %T %Z %Y'`
* `--time-format=ABBR='%Y%m%dT%H%M%S%z'`
  or `export YP_TIME_FORMAT_ABBR='%Y%m%dT%H%M%S%z'`

Then:

```sh
${YP_TIME_REF}                        # 2024-12-25T00:00:00+0000
${YP_TIME_REF_FORMAT_CTIME}           # Wed 25 Dec 00:00:00 GMT 2024
${YP_TIME_REF_PLUS_T12H_FORMAT_ABBR}  # 20241225T120000+0000
```

Finally, if a variable name is already defined in the environment
or in a `--define=...` option, then the defined value takes precedence,
so if you have already `export YP_TIME_REF=whatever`, then you will get
the value `whatever` instead of the reference time.