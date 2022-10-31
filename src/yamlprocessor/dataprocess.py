#!/usr/bin/env python3
"""Process includes and variable substitutions in a YAML file.

For each value ``{"INCLUDE": "filename.yaml"}``, load content from include file
and substitute the value with the content of the include file.

For each string value with ``$NAME`` or ``${NAME}`` syntax, substitute with
value of corresponding (environment) variable.

For each string value with ``$YP_TIME_*`` or ``${YP_TIME_*}`` syntax,
substitute with value of corresponding date-time string.

Validate against specified JSON schema if root file starts with either
``#!<SCHEMA-URI>`` or ``# yaml-language-server: $schema=<SCHEMA-URI>`` line.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from contextlib import suppress
from datetime import datetime
from errno import ENOENT
import logging
import logging.config
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

from dateutil.parser import parse as datetimeparse
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal
import jmespath
import jsonschema
from ruamel.yaml import YAML
from ruamel.yaml.constructor import ConstructorError

from . import __version__


def configure_basic_logging():
    """Configure basic logging, suitable for most CLI applications.

    Basic no-frill format.
    Stream handler prints message on STDERR.

    Normal usage:

    >>> from yamlprocessor.dataprocess import DataProcessor
    >>> processor = DataProcessor()
    >>> # ... Customise the `DataProcessor` instance as necessary ..., then:
    >>> processor.process_data(in_file_name, out_file_name)
    """
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'basic': {
                'format': '[%(levelname)s] %(message)s',
                # 'format': '%(asctime)s [%(levelname)s] %(message)s',
                # 'datefmt': '%FT%T%z',
            },
        },
        'handlers': {
            'default': {
                'level': 'DEBUG',
                'formatter': 'basic',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['default'],
                'level': 'INFO',
                'propagate': False,
            },
            '__main__': {  # if __name__ == '__main__'
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': False,
            },
        }
    })


def strftime_with_colon_z(dto: datetime, time_format: str):
    """Wrap dto.strftime to support %:z, %::z and %:::z format code.

    Always use Z for UTC - it is short and recognised by any parser.
    """
    utcoffset = dto.utcoffset()
    if utcoffset is None:
        for code in ('%z', '%:z', '%::z', '%:::z'):
            time_format = time_format.replace(code, '')
        return dto.strftime(time_format)
    # Hopefully, we don't need to have sub-seconds in time zones.
    offset_total_seconds = int(utcoffset.total_seconds())
    # Always use Z for UTC
    if offset_total_seconds == 0:
        for code in ('%z', '%:z', '%::z', '%:::z'):
            time_format = time_format.replace(code, 'Z')
        return dto.strftime(time_format)
    # datetime.strftime can handle '%z' but not '%:z' etc
    if not any(code in time_format for code in ('%:z', '%::z', '%:::z')):
        return dto.strftime(time_format)
    if offset_total_seconds >= 0:
        offset_sign = '+'
    else:
        offset_sign = '-'
    offset_total_seconds = abs(offset_total_seconds)
    offset_str = '%s%02d:%02d:%02d' % (
        offset_sign,
        offset_total_seconds / 3600,  # hours
        offset_total_seconds // 60 % 60,  # minutes of hour
        offset_total_seconds % 60)  # seconds of minute
    short_offset_str = offset_str
    while short_offset_str.endswith(':00'):
        short_offset_str = short_offset_str[0:-3]
    time_format = time_format.replace('%:z', offset_str[0:6])
    time_format = time_format.replace('%::z', offset_str)
    time_format = time_format.replace('%:::z', short_offset_str)
    return dto.strftime(time_format)


class UnboundVariableError(ValueError):

    """An error raised on attempt to substitute an unbound variable."""

    def __repr__(self):
        return f"[UNBOUND VARIABLE] {self.args[0]}"

    __str__ = __repr__


def construct_yaml_timestamp(constructor, node):
    """Return a method to add to the YAML constructor to parse datetime."""
    print(1, file=sys.stderr)
    try:
        return datetimeparse(node.value)
    except ValueError:
        raise ConstructorError(
            None,
            None,
            f'failed to construct timestamp from "{node.value}"',
            node.start_mark,
        )


def get_represent_datetime(time_format: str):
    """Return a method to add to the YAML representer to represent datetime."""

    return lambda representer, data: representer.represent_scalar(
        'tag:yaml.org,2002:str',
        strftime_with_colon_z(data, time_format))


class DataProcessor:
    """Process YAML and compatible data structure.

    Import sub-data-structure from include files.
    Process variable substitution in string values.
    Process date-time substitution in string values.
    Validate against JSON schema.

    .. py:attribute:: .is_process_include
       :type: bool

       Turn on/off include file processing.

    .. py:attribute:: .is_process_variable
       :type: bool

       Turn on/off variable substitution.

    .. py:attribute:: .include_dict
       :type: dict

       Dictonary for values that can be substituted for include.

    .. py:attribute:: .include_paths
       :type: list

       Locations for searching include files. Default is the value of the
       :envvar:`YP_INCLUDE_PATH` environment variable split into a list.

    .. py:attribute:: .schema_prefix
       :type: str
       :value: os.getenv("YP_SCHEMA_PREFIX")

       Prefix for JSON schema specified as non-existing relative paths.
       See also :envvar:`YP_SCHEMA_PREFIX`.

    .. py:attribute:: .time_formats
       :type: dict
       :value: {'': '%FT%T%z'}

       Default and named time formats.
       See also :envvar:`YP_TIME_FORMAT` and :envvar:`YP_TIME_FORMAT_<NAME>`.

    .. py:attribute:: .time_now
       :type: datetime.datetime

       Date-time at instance initialisation.

    .. py:attribute:: .time_ref
       :type: datetime.datetime

       Reference date-time. Default is the value of the
       :envvar:`YP_SCHEMA_PREFIX` environment variable as
       :py:class:`datetime.datetime` or :py:attr:`.time_now` if the environment
       variable is not defined.

    .. py:attribute:: .variable_map
       :type: dict
       :value: os.environ

       Mapping for variable substitutions.

    .. py:attribute:: .unbound_placeholder
       :type: str

       Value to substitute for unbound variables.

    .. py:attribute:: .INCLUDE_SCHEMA
       :type: dict

       (Class) The schema of the INCLUDE syntax.
    """

    INCLUDE_KEY = 'INCLUDE'
    MERGE_KEY = 'MERGE'
    QUERY_KEY = 'QUERY'
    VARIABLES_KEY = 'VARIABLES'

    INCLUDE_SCHEMA = {
        'properties': {
            INCLUDE_KEY: {
                'type': 'string',
            },
            MERGE_KEY: {
                'type': 'boolean',
            },
            QUERY_KEY: {
                'type': 'string',
            },
            VARIABLES_KEY: {
                'patternProperties': {
                    r'^[A-z_]\w*$': {'type': 'string'},
                },
                'additionalProperties': False,
                'type': 'object',
            },
        },
        'additionalProperties': False,
        'required': [INCLUDE_KEY],
        'type': 'object',
    }

    REC_SUBSTITUTE = re.compile(
        r"\A"
        r"(?P<head>.*?)"
        r"(?P<escape>\\*)"
        r"(?P<symbol>"
        r"\$"
        r"(?P<brace_open>\{)?"
        r"(?P<name>[A-z_]\w*)"
        r"(?P<cast>\.(?:int|float|bool))?"
        r"(?(brace_open)\})"
        r")"
        r"(?P<tail>.*)"
        r"\Z",
        re.M | re.S)

    REC_DELTA_DATE = re.compile(r'(\d+)([YMD])', re.M | re.S)
    REC_DELTA_TIME = re.compile(r'(\d+)([HMS])', re.M | re.S)
    REC_SUBSTITUTE_TIME_DELTA = re.compile(
        r"_(?P<modifier>(?:AT|PLUS|MINUS))_"
        + r"(?P<date>(?:\d+[YMD])+)*"
        + r"(?P<time>T(?:\d+[HMS])+)*",
        re.M | re.S)
    REC_SUBSTITUTE_TIME_FORMAT = re.compile(
        r"_FORMAT_(?P<name>\w+)",
        re.M | re.S)

    UNBOUND_ORIGINAL = 'YP_ORIGINAL'

    def __init__(self):
        self.is_process_include = True
        self.is_process_variable = True
        self.include_paths = list(
            item
            for item in os.getenv('YP_INCLUDE_PATH', '').split(os.pathsep)
            if item)
        self.include_dict = {}
        self.schema_prefix = os.getenv('YP_SCHEMA_PREFIX')
        self.time_formats = {'': '%FT%T%:z'}
        self.time_now = datetime.now(tzlocal())  # assume application is fast
        time_ref_value = os.getenv('YP_TIME_REF_VALUE')
        if time_ref_value is None:
            self.time_ref = self.time_now
        else:
            self.time_ref = datetimeparse(time_ref_value)
        self.variable_map = os.environ.copy()
        self.unbound_placeholder = None

    def process_data(self, in_filename: str, out_filename: str) -> None:
        """Process includes in input file and dump results in output file.

        :param in_filename: input file name.
        :param out_filename: output file name.
        """
        in_filename = self.get_filename(in_filename, [])
        root = self.load_file(in_filename)
        schema_location = self.load_file_schema(in_filename)
        stack = [[root, [in_filename], self.variable_map]]
        while stack:
            data, parent_filenames, variable_map = stack.pop()
            data = self.process_variable(data, variable_map)
            if data is root:
                # Handle INCLUDE at root level.
                # Ignore the MERGE flag.
                data, parent_filenames, variable_map = self.load_include_file(
                    data, parent_filenames, variable_map)[0:3]
                root = data
            type_of_data = type(data)
            items_iter = None
            skip_keys = set()
            if type_of_data is list:
                items_iter = enumerate(data)
            elif type_of_data is dict:
                items_iter = data.copy().items()
            if items_iter is None:
                continue
            for key, item in items_iter:
                if key in skip_keys:
                    continue
                item = data[key] = self.process_variable(item, variable_map)
                include_data, parent_filenames_x, variable_map_x, is_merge = (
                    self.load_include_file(
                        item, parent_filenames, variable_map))
                if is_merge and type_of_data != type(include_data):
                    raise TypeError()
                if is_merge and type_of_data is list:
                    # For a list, the iterator seems to handle the new items
                    # perfectly fine. We insert the included list at and after
                    # the current position. The current item is logically
                    # replaced by the first item of the inserted list.
                    del data[key]
                    item = None
                    for i, include_item in enumerate(include_data):
                        data.insert(key + i, include_item)
                        if i == 0:
                            item = include_item
                elif is_merge and type_of_data is dict:
                    # For a dict, the iterator cannot handle size changes, so
                    # we can only iterate over a copy of the original dict. We
                    # insert the items in the dict normally, but we'll need to
                    # add elements of the dict to the stack to ensure we visit
                    # any sub-trees for include files, etc.
                    del data[key]
                    item = None
                    for include_key, include_item in include_data.items():
                        data[include_key] = include_item
                        skip_keys.add(include_key)
                        if (
                            isinstance(include_item, dict)
                            or isinstance(include_item, list)
                        ):
                            stack.append([
                                include_item,
                                parent_filenames_x,
                                variable_map_x,
                            ])
                elif include_data != item:
                    item = data[key] = include_data
                if isinstance(item, dict) or isinstance(item, list):
                    stack.append(
                        [data[key], parent_filenames_x, variable_map_x])
        if out_filename == '-':
            out_file = sys.stdout
        else:
            out_file = open(out_filename, 'w')
        yaml = YAML(typ='safe', pure=True)
        yaml.default_flow_style = False
        yaml.sort_base_mapping_type_on_output = False
        yaml.representer.add_representer(
            datetime,
            get_represent_datetime(self.time_formats['']))
        yaml.dump(root, out_file)
        self.validate_data(root, out_filename, schema_location)

    def get_filename(self, filename: str, parent_filenames: list) -> str:
        """Return absolute path of filename.

        If `filename` is a relative path, look for the file but looking in the
        directories containing the parent files, then the current working
        directory, then each path in `.include_paths`.

        :param filename: File name to expand or return.
        :param parent_filenames: Stack of parent file names.
        """
        filename: str = os.path.expanduser(filename)
        if os.path.isabs(filename) or filename == '-':
            return filename
        root_dirs = (
            list(
                os.path.abspath(os.path.dirname(f))
                for f in parent_filenames
                if f != '-'
            )
            + [os.path.abspath('.')]
            + self.include_paths
        )
        for root_dir in root_dirs:
            name = os.path.join(root_dir, filename)
            if os.path.exists(name):
                return name
        raise OSError(ENOENT, filename, os.strerror(ENOENT))

    def load_include_file(
        self,
        value: object,
        parent_filenames: list,
        variable_map: dict,
    ) -> tuple:
        """Load data if value indicates an include file.

        :param value: Value that may contain file name to load.
        :param parent_filenames: Stack of parent file names.
        :param variable_map: :py:attr:`.variable_map` in the local scope,
                             may have additional variables.
        """
        orig_value = value
        parent_filenames = list(parent_filenames)
        variable_map = dict(variable_map)
        is_merge = False
        while self.is_process_include and self._is_include(value):
            is_merge = (self.MERGE_KEY in orig_value)
            include_filename = self.process_variable(
                value[self.INCLUDE_KEY])
            if self.VARIABLES_KEY in value:
                for key, val in value[self.VARIABLES_KEY].copy().items():
                    value[self.VARIABLES_KEY][key] = self.process_variable(val)
            try:
                loaded_value = self.include_dict[include_filename]
                filename = include_filename
            except KeyError:
                filename = self.get_filename(
                    include_filename, parent_filenames)
                loaded_value = self.load_file(filename)
            parent_filenames.append(filename)
            if self.VARIABLES_KEY in value:
                variable_map.update(value[self.VARIABLES_KEY])
            if self.QUERY_KEY in value:
                value = jmespath.search(value[self.QUERY_KEY], loaded_value)
            else:
                value = loaded_value
        return value, parent_filenames, variable_map, is_merge

    @classmethod
    def _is_include(cls, value: object) -> bool:
        """Return True if value is recognised as an INCLUDE syntax.

        :param value: Value that may contain file name to load.
        :return: True if value is recognised as an INCLUDE syntax.
        """
        if not isinstance(value, dict) or cls.INCLUDE_KEY not in value:
            return False
        with suppress(jsonschema.exceptions.ValidationError):
            jsonschema.validate(schema=cls.INCLUDE_SCHEMA, instance=value)
            return True
        return False

    @staticmethod
    def load_file(filename: str) -> object:
        """Load content of (YAML) file into a data structure.

        :param filename: name of file to load content.
        :return: the loaded data structure.
        """
        yaml = YAML(typ='safe', pure=True)
        yaml.constructor.add_constructor(
            'tag:yaml.org,2002:timestamp',
            construct_yaml_timestamp)
        if filename == '-':
            return yaml.load(sys.stdin)
        else:
            with open(filename) as file_:
                return yaml.load(file_)

    @staticmethod
    def load_file_schema(filename: str) -> object:
        """Load schema location from the schema association line of file.

        :param filename: name of file to load schema location.
        :return: a string containing the location of the schema or None.
        """
        if filename == '-':
            line = sys.stdin.readline()
        else:
            with open(filename) as file_:
                line = file_.readline()
        for prefix in ('#!', '# yaml-language-server: $schema='):
            if line.startswith(prefix):
                return line[len(prefix):].strip()
        else:
            return None

    def process_variable(
        self,
        item: object,
        variable_map: dict = None,
    ) -> object:
        """Substitute (environment) variables into a string value.

        Return `item` as-is if not `.is_process_variable` or if `item` is not a
        string.

        For each `$NAME` and `${NAME}` in `item`, substitute with the value
        of the environment variable `NAME`.

        If `NAME` is not defined in the `.variable_map` and
        `.unbound_placeholder` is None, raise an `UnboundVariableError`.

        If `NAME` is not defined in the `.variable_map` and
        `.unbound_placeholder` equals to the value of
        `DataProcessor.UNBOUND_ORIGINAL`, then leave the original syntax
        unchanged.

        If `NAME` is not defined in the `.variable_map` and
        `.unbound_placeholder` is not `None`, substitute `NAME` with the value
        of `.unbound_placeholder`.

        :param item: Item to process. Do nothing if not a str.
        :return: Processed item on success.
        :param variable_map: :py:attr:`.variable_map` in the local scope,
                             may have additional variables.
        """
        if not self.is_process_variable or not isinstance(item, str):
            return item
        if variable_map is None:
            variable_map = self.variable_map
        ret = ''
        try:
            tail = item.decode()
        except AttributeError:
            tail = item
        while tail:
            match = self.REC_SUBSTITUTE.match(tail)
            if match:
                groups = match.groupdict()
                if len(groups['escape']) % 2 == 0:
                    if groups['name'] in variable_map:
                        substitute = variable_map[groups['name']]
                    elif groups['name'].startswith('YP_TIME'):
                        substitute = self._process_time_variable(
                            groups['name'])
                    elif self.unbound_placeholder == self.UNBOUND_ORIGINAL:
                        substitute = groups['symbol']
                    elif self.unbound_placeholder is not None:
                        substitute = str(self.unbound_placeholder)
                    else:
                        raise UnboundVariableError(groups['name'])
                else:
                    substitute = groups['symbol']
                if substitute != groups['symbol'] and groups['cast']:
                    if groups['head'] or tail != item:
                        raise ValueError(
                            f'{item}: bad substitution expression')
                    try:
                        if groups['cast'] == '.int':
                            substitute = int(substitute)
                        elif groups['cast'] == '.float':
                            substitute = float(substitute)
                        elif (
                            groups['cast'] == '.bool'
                            and substitute.lower() in ('0', 'false', 'no')
                        ):
                            substitute = False
                        elif (
                            groups['cast'] == '.bool'
                            and substitute.lower() in ('1', 'true', 'yes')
                        ):
                            substitute = True
                        else:
                            raise ValueError
                    except ValueError:
                        raise ValueError(
                            f'{item}: bad substitution value: {substitute}')
                    ret = substitute
                    tail = ''
                else:
                    ret += (
                        groups['head']
                        + groups['escape'][0:len(groups['escape']) // 2]
                        + substitute)
                    tail = groups['tail']
            else:
                ret += tail
                tail = ''
        return ret

    def _process_time_variable(self, name: str) -> str:
        """Process a string containing the name of a time variable.

        :param name: Time variable name to parse.
        :return: The value to substitute.
        """
        # Can assume name.startswith('YP_TIME') if we are here
        if name.startswith('YP_TIME_NOW'):
            dto = self.time_now
        elif name.startswith('YP_TIME_REF'):
            dto = self.time_ref
        else:
            raise UnboundVariableError(name)
        tail = name[11:]  # remove YP_TIME_NOW/YP_TIME_REF prefix
        try:
            deltas = self._process_time_variable_deltas(tail)
        except UnboundVariableError:
            raise UnboundVariableError(name)
        for delta in deltas:
            dto = dto + delta
        time_fmt_key = ''
        match = self.REC_SUBSTITUTE_TIME_FORMAT.search(tail)
        if match:
            time_fmt_key = match.groups()[0]
        try:
            return strftime_with_colon_z(dto, self.time_formats[time_fmt_key])
        except KeyError:
            raise UnboundVariableError(name)

    def _process_time_variable_deltas(self, tail: str) -> list:
        """Process a string containing delta information of a time variable.

        Expected syntax of `tail`:
        [_AT_NNN][_PLUS_XXX][_MINUS_XXX]

        XXX is a date-time duration string in ISO8601 form without the leading
        P. E.g. 1DT2H is 1 day and 2 hours.

        NNN is in the same format as XXX, but the values are absolute
        information to replace the original date-time value. E.g. If the
        current/reference time is 2022-01-14T12:30Z, applying _AT_1DT2H will
        change the time to 2022-01-01T02:30Z.

        Deltas will be applied in the order they are defined.

        See also: https://dateutil.readthedocs.io/en/stable/relativedelta.html

        :param tail: String to parse into a set of deltas.
        :return: A list of `dateutil.relativedelta.relativedelta` objects.
        """
        modifier_map = {
            'AT': {
                'date': {'Y': 'year', 'M': 'month', 'D': 'day'},
                'time': {'H': 'hour', 'M': 'minute', 'S': 'second'},
                'sign': '',
            },
            'PLUS': {
                'date': {'Y': 'years', 'M': 'months', 'D': 'days'},
                'time': {'H': 'hours', 'M': 'minutes', 'S': 'seconds'},
                'sign': '',
            },
            'MINUS': {
                'date': {'Y': 'years', 'M': 'months', 'D': 'days'},
                'time': {'H': 'hours', 'M': 'minutes', 'S': 'seconds'},
                'sign': '-',
            },
        }
        deltas = []
        for modifier_str, date_str, time_str in (
            self.REC_SUBSTITUTE_TIME_DELTA.findall(tail)
        ):
            delta_args = {}
            modifier = modifier_map[modifier_str]
            sign = modifier['sign']
            delta_args.update(
                (modifier['date'][unit], int(sign + istr))
                for istr, unit in self.REC_DELTA_DATE.findall(date_str)
            )
            delta_args.update(
                (modifier['time'][unit], int(sign + istr))
                for istr, unit in self.REC_DELTA_TIME.findall(time_str)
            )
            deltas.append(relativedelta(**delta_args))
        return deltas

    def validate_data(
        self,
        data: object,
        out_file_name: str,
        schema_location: str,
    ) -> None:
        """Attempt to find the schema and use it to validate data.

        :param data: The data structure to be validated.
        :param schema_location: File name containing a JSON Schema.
        """
        if not schema_location:
            return
        schema = {"$ref": schema_location}
        if not urlparse(schema_location).scheme:
            schema_path = Path(schema_location)
            if schema_path.exists():
                schema = {"$ref": schema_path.absolute().as_uri()}
            elif self.schema_prefix:
                schema = {"$ref": self.schema_prefix + schema_location}
        try:
            jsonschema.validate(schema=schema, instance=data)
        except jsonschema.exceptions.ValidationError as exc:
            logging.error(f'not ok {out_file_name}')
            logging.exception(exc)
            raise
        else:
            logging.info(f'ok {out_file_name}')


def main(argv=None):
    configure_basic_logging()
    parser = ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'in_filename',
        metavar='IN-FILE',
        default='-',
        nargs='?',
        help='Name of input file, "-" for STDIN')
    parser.add_argument(
        'out_filename',
        metavar='OUT-FILE',
        default='-',
        nargs='?',
        help='Name of output file, "-" for STDOUT')
    parser.add_argument(
        '--include', '-I',
        dest='include_paths',
        metavar='DIR',
        action='append',
        default=[],
        help='Add search locations for item specified as relative paths')
    parser.add_argument(
        '--define', '-D',
        dest='defines',
        metavar='KEY=VALUE',
        action='append',
        default=[],
        help='Map KEY to VALUE for variable substitutions')
    parser.add_argument(
        '--undefine', '-U',
        dest='undefines',
        metavar='KEY',
        action='append',
        default=[],
        help='Unmap KEY for variable substitutions')
    parser.add_argument(
        '--no-environment', '-i',
        action='store_true',
        default=False,
        help='Do not use environment variables in variable substitutions')
    parser.add_argument(
        '--unbound-placeholder',
        metavar='VALUE',
        default=None,
        help=(
            'Substitute an unbound variable with VALUE instead of failing.'
            f' Use {DataProcessor.UNBOUND_ORIGINAL} as VALUE to leave the'
            ' original syntax unchanged on unbound variables.'
        ),
    )
    parser.add_argument(
        '--no-process-include',
        dest='is_process_include',
        action='store_false',
        default=True,
        help='Do not process include file instructions')
    parser.add_argument(
        '--no-process-variable',
        dest='is_process_variable',
        action='store_false',
        default=True,
        help='Do not process variable substitutions')
    parser.add_argument(
        '--schema-prefix',
        metavar='PREFIX',
        dest='schema_prefix',
        default=None,
        help='Prefix for relative path schemas. (Override $YP_SCHEMA_PREFIX)')
    parser.add_argument(
        '--time-format',
        metavar='NAME=FORMAT',
        dest='time_formats',
        action='append',
        default=[],
        help=(
            'Format for date-time string substitutions.'
            ' (Override $YP_TIME_FORMAT*)'
        ),
    )
    parser.add_argument(
        '--time-ref',
        metavar='TIME',
        dest='time_ref',
        default=None,
        help=(
            'Reference value for date-time substitutions.'
            ' (Override $YP_TIME_REF_VALUE)'
        ),
    )
    parser.add_argument(
        '--version', '-V',
        dest='is_print_version',
        action='store_true',
        default=False,
        help='Print version and exit')
    args = parser.parse_args(argv)

    if args.is_print_version:
        parser.exit(0, f'{parser.prog} {__version__}\n')

    # Set up processor
    processor = DataProcessor()
    # Include options
    processor.is_process_include = args.is_process_include
    for item in args.include_paths:
        processor.include_paths.extend(item.split(os.path.pathsep))
    # Variable substitution options
    processor.is_process_variable = args.is_process_variable
    if args.no_environment:
        processor.variable_map.clear()
    for key in args.undefines:
        try:
            del processor.variable_map[key]
        except KeyError:
            pass
    for item in args.defines:
        key, value = item.split('=', 1)
        processor.variable_map[key] = value
    processor.unbound_placeholder = args.unbound_placeholder
    # Date-time substitution options
    if args.time_ref is not None:
        processor.time_ref = datetimeparse(args.time_ref)
    for key, value in os.environ.items():
        if key == 'YP_TIME_FORMAT':
            name = ''
        elif key.startswith('YP_TIME_FORMAT_'):
            name = key[15:]  # remove leading 'YP_TIME_FORMAT_'
        else:
            continue
        processor.time_formats[name] = value
    for item in args.time_formats:
        if '=' in item:
            name, time_format = item.split('=', 1)
        else:
            name, time_format = ('', item)
        processor.time_formats[name] = time_format
    # Schema validation options
    if args.schema_prefix is not None:
        processor.schema_prefix = args.schema_prefix

    processor.process_data(args.in_filename, args.out_filename)


if __name__ == '__main__':
    main(sys.argv)
