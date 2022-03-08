#!/usr/bin/env python3
"""Process includes and variable substitutions in a YAML file.

For each value `{"INCLUDE": "filename.yaml"}`, load content from include file
and substitute the value with the content of the include file.

For each string value with `$NAME` or `${NAME}` syntax, substitute with value
of corresponding (environment) variable.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
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
import yaml
from yaml.dumper import SafeDumper

from . import __version__


def configure_basic_logging():
    """Configure basic logging, suitable for most CLI applications.

    Basic no-frill format.
    Stream handler prints message on STDERR.
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
    offset_str = '%+03d:%02d:%02d' % (
        offset_total_seconds / 3600,  # hours
        abs(offset_total_seconds // 60 % 60),  # minutes of hour
        abs(offset_total_seconds % 60))  # seconds of minute
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


class YpSafeDumper(SafeDumper):
    """Override dumping method for a time stamp to dump out str."""

    @classmethod
    def set_time_format(cls, time_format: str):
        """Set time format."""
        cls.time_format = time_format

    def represent_datetime(self, data: datetime):
        """Dump datetime as string."""
        if hasattr(self, 'time_format'):
            value = strftime_with_colon_z(data, self.time_format)
            return self.represent_scalar('tag:yaml.org,2002:str', value)
        else:
            return super().represent_datetime(data)


YpSafeDumper.add_representer(datetime, YpSafeDumper.represent_datetime)


class DataProcessor:
    """Process YAML and compatible data structure.

    Import sub-data-structure from include files.
    Process variable substitution in string values.

    Attributes:
      `.is_process_include`:
        (bool) Turn on/off include file processing.
      `.is_process_variable`:
        (bool) Turn on/off variable substitution.
      `.include_paths`:
        (list) Locations for searching include files.
      `.schema_prefix`:
        (str) Prefix for JSON schema specified as non-existing relative paths.
      `.time_formats`:
        (dict) Default and named time formats. (Default=`{'': '%FT%T%z'}`)
      `.time_now`:
        (datetime) Date-time at instance initialisation.
      `.time_ref`:
        (datetime) Reference date-time. (Default=`.time_now`)
      `.variable_map`:
        (dict) Mapping for variable substitutions. (Default=`os.environ`)
      `.unbound_placeholder`:
        (str) Value to substitute for unbound variables.
    """

    INCLUDE_KEY = 'INCLUDE'
    QUERY_KEY = 'QUERY'

    REC_SUBSTITUTE = re.compile(
        r"\A"
        r"(?P<head>.*?)"
        r"(?P<escape>\\*)"
        r"(?P<symbol>"
        r"\$"
        r"(?P<brace_open>\{)?"
        r"(?P<name>[A-z_]\w*)"
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

    def __init__(self):
        self.is_process_include = True
        self.is_process_variable = True
        self.include_paths = []
        self.schema_prefix = None
        self.time_formats = {'': '%FT%T%:z'}
        self.time_now = datetime.now(tzlocal())  # assume application is fast
        self.time_ref = self.time_now
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
        stack = [[root, [in_filename]]]
        while stack:
            data, parent_filenames = stack.pop()
            data = self.process_variable(data)
            data = self.load_include_file(data)[0]
            items_iter = None
            if isinstance(data, list):
                items_iter = enumerate(data)
            elif isinstance(data, dict):
                items_iter = data.items()
            if items_iter is None:
                continue
            for key, item in items_iter:
                item = data[key] = self.process_variable(item)
                include_data, parent_filenames = self.load_include_file(
                    item, parent_filenames)
                if include_data != item:
                    item = data[key] = include_data
                if isinstance(item, dict) or isinstance(item, list):
                    stack.append([data[key], parent_filenames])
        if out_filename == '-':
            out_file = sys.stdout
        else:
            out_file = open(out_filename, 'w')
        YpSafeDumper.set_time_format(self.time_formats[''])
        # Set sort_keys=False to preserve dict ordering (with Python 3.7+)
        yaml.dump(
            root,
            out_file,
            Dumper=YpSafeDumper,
            default_flow_style=False,
            sort_keys=False)
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
        parent_filenames: list = None,
    ) -> tuple:
        """Load data if value indicates the root file or an include file.

        :param value: Value that may contain file name to load.
        :param parent_filenames: Stack of parent file names.
        """
        if parent_filenames is None:
            parent_filenames = []
        else:
            parent_filenames = list(parent_filenames)
        while (
            self.is_process_include
            and isinstance(value, dict)
            and self.INCLUDE_KEY in value
        ):
            include_filename = self.process_variable(
                value[self.INCLUDE_KEY])
            filename = self.get_filename(include_filename, parent_filenames)
            parent_filenames.append(filename)
            loaded_value = self.load_file(filename)
            if self.QUERY_KEY in value:
                value = jmespath.search(value[self.QUERY_KEY], loaded_value)
            else:
                value = loaded_value
        return value, parent_filenames

    @staticmethod
    def load_file(filename: str) -> object:
        """Load content of (YAML) file into a data structure.

        :param filename: name of file to load content.
        :return: the loaded data structure.
        """
        if filename == '-':
            return yaml.safe_load(sys.stdin)
        else:
            with open(filename) as file_:
                return yaml.safe_load(file_)

    @staticmethod
    def load_file_schema(filename: str) -> object:
        """Load schema location from #! line of file.

        :param filename: name of file to load schema location.
        :return: a string containing the location of the schema or None.
        """
        if filename == '-':
            line = sys.stdin.readline()
        else:
            with open(filename) as file_:
                line = file_.readline()
        if line.startswith('#!'):
            return line[2:].strip()
        else:
            return None

    def process_variable(self, item: object) -> object:
        """Substitute environment variables into a string value.

        Return `item` as-is if not `.is_process_variable` or if `item` is not a
        string.

        For each `$NAME` and `${NAME}` in `item`, substitute with the value
        of the environment variable `NAME`.

        If `NAME` is not defined in the `.variable_map` and
        `.unbound_placeholder` is None, raise an `UnboundVariableError`.

        If `NAME` is not defined in the `.variable_map` and
        `.unbound_placeholder` is not None, substitute `NAME` with the value
        of `.unbound_placeholder`.

        :param item: Item to process. Do nothing if not a str.
        :return: Processed item on success.

        """
        if not self.is_process_variable or not isinstance(item, str):
            return item
        ret = ""
        try:
            tail = item.decode()
        except AttributeError:
            tail = item
        while tail:
            match = self.REC_SUBSTITUTE.match(tail)
            if match:
                groups = match.groupdict()
                substitute = groups["symbol"]
                if len(groups["escape"]) % 2 == 0:
                    if groups["name"] in self.variable_map:
                        substitute = self.variable_map[groups["name"]]
                    elif groups["name"].startswith('YP_TIME'):
                        substitute = self._process_time_variable(
                            groups["name"])
                    elif self.unbound_placeholder is not None:
                        substitute = str(self.unbound_placeholder)
                    else:
                        raise UnboundVariableError(groups["name"])
                ret += (
                    groups["head"]
                    + groups["escape"][0:len(groups["escape"]) // 2]
                    + substitute)
                tail = groups["tail"]
            else:
                ret += tail
                tail = ""
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
        metavar='PATH',
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
        help='Substitute an unbound variable with VALUE instead of failing')
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
        default=os.getenv('YP_SCHEMA_PREFIX'),
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
        default=os.getenv('YP_TIME_REF_VALUE'),
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
    if args.time_ref:
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
    processor.schema_prefix = args.schema_prefix

    processor.process_data(args.in_filename, args.out_filename)


if __name__ == '__main__':
    main(sys.argv)
