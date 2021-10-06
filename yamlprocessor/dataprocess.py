#!/usr/bin/env python3
"""Read a YAML application configuration, process any includes.

Read a YAML application configuration, process any includes, and dump out the
result.
"""

from argparse import ArgumentParser
import os
import re
import sys

import yaml


INCLUDE_DIRECTIVE = 'yaml::'


RE_SUBSTITUTE = re.compile(
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


class UnboundVariableError(ValueError):

    """An error raised on attempt to substitute an unbound variable."""

    def __repr__(self):
        return f"[UNBOUND VARIABLE] {self.args[0]}"

    __str__ = __repr__


def get_filename(filename: str, orig_filename: str = None) -> str:
    """Return absolute path of filename.

    If `orig_filename` is specified and `filename` is a relative path,
    `filename` is assumed to be relative to `orig_filename`.

    :param filename: File name to expand or return.
    :param orig_filename: File name in the original scope.
    """
    filename = os.path.expanduser(filename)
    if os.path.isabs(filename):
        return filename
    if orig_filename is None:
        root_dir: str = os.path.abspath('.')
    else:
        root_dir: str = os.path.abspath(os.path.dirname(orig_filename))
    return os.path.join(root_dir, filename)


def get_include(value: str) -> str:
    """Returns include file str if value matches include file syntax.

    :return: include file string where relevant, an empty string otherwise.
    :param value: an input value.
    """
    if isinstance(value, str) and value.startswith(INCLUDE_DIRECTIVE):
        return value[len(INCLUDE_DIRECTIVE):]
    else:
        return ""


def load_include(value: object, orig_filename: str = None) -> object:
    """Load include file if filename contains an include file name to load.

    :param value: Value that may contain file name to load.
    :param orig_filename: File name in the original scope.
    """
    include_filename = get_include(value)
    if include_filename:
        filename = get_filename(include_filename, orig_filename)
        return yaml.safe_load(open(filename)), filename
    else:
        return value, orig_filename


def process_data(in_filename: str, out_filename: str) -> None:
    """Process includes in input file and dump results in output file.

    :param in_filename: input file name.
    :param out_filename: output file name.
    """
    in_filename = get_filename(in_filename)
    root = yaml.safe_load(open(in_filename))
    stack = [(root, in_filename)]
    while stack:
        data, current_filename = stack.pop()
        if isinstance(data, str):
            data = process_variable(data)
        data = load_include(data)[0]
        items_iter = None
        if isinstance(data, list):
            items_iter = enumerate(data)
        elif isinstance(data, dict):
            items_iter = data.items()
        if items_iter is None:
            continue
        for key, item in items_iter:
            if isinstance(item, str):
                item = data[key] = process_variable(item)
            include_data, filename = load_include(item, current_filename)
            if include_data != item:
                item = data[key] = include_data
            if isinstance(item, dict) or isinstance(item, list):
                stack.append((data[key], filename))
    yaml.dump(root, open(out_filename, 'w'), default_flow_style=False)


def process_variable(
    text: str,
    environ: dict = os.environ,
    unbound: str = None,
) -> str:
    """Substitute environment variables into a string.

    For each `$NAME` and `${NAME}` in `text`, substitute with the value
    of the environment variable `NAME`.

    If `NAME` is not defined in the `environ` and `unbound` is None, raise an
    `UnboundVariableError`.

    If `NAME` is not defined in the `environ` and `unbound` is not None,
    substitute `NAME` with the value of `unbound`.

    :param text: text to process.
    :param unbound: text to substitute in unbound variables.
    :param environ: mapping of variables that can be used in substitution.
    :return: processed text.

    """
    ret = ""
    try:
        tail = text.decode()
    except AttributeError:
        tail = text
    while tail:
        match = RE_SUBSTITUTE.match(tail)
        if match:
            groups = match.groupdict()
            substitute = groups["symbol"]
            if len(groups["escape"]) % 2 == 0:
                if groups["name"] in environ:
                    substitute = environ[groups["name"]]
                elif unbound is not None:
                    substitute = str(unbound)
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


def main(argv=None):
    parser = ArgumentParser(description=__file__)
    parser.add_argument(
        'in_filename',
        metavar='IN-FILE',
        help='Name of input file')
    parser.add_argument(
        'out_filename',
        metavar='OUT-FILE',
        help='Name of output file')
    args = parser.parse_args(argv)
    process_data(args.in_filename, args.out_filename)


if __name__ == '__main__':
    main(sys.argv)
