#!/usr/bin/env python3
"""Read a YAML application configuration, process any includes.

Read a YAML application configuration, process any includes, and dump out the
result.
"""

from argparse import ArgumentParser
import os
import sys

import yaml


INCLUDE_DIRECTIVE = 'yaml::'


def get_filename(filename: str, orig_filename: str = None) -> str:
    """Return absolute path of filename.

    If `orig_filename` is specified and `filename` is a relative path,
    `filename` is assumed to be relative to `orig_filename`.

    :param filename: File name to expand or return.
    :param orig_filename: File name in the original scope.
    """
    if os.path.isabs(filename):
        return filename
    if orig_filename is None:
        root_dir: str = os.path.abspath('.')
    else:
        root_dir: str = os.path.abspath(os.path.dirname(orig_filename))
    return os.path.join(root_dir, filename)


def app_conf_process(in_filename: str, out_filename: str) -> None:
    """Process includes in input file and dump results in output file.

    :param in_filename: input file name.
    :param out_filename: output file name.
    """
    in_filename = get_filename(in_filename)
    root = yaml.safe_load(open(in_filename))
    stack = [(root, in_filename)]
    while stack:
        data, current_filename = stack.pop()
        if isinstance(data, str) and data.startswith(INCLUDE_DIRECTIVE):
            filename = get_filename(
                data[len(INCLUDE_DIRECTIVE):],
                current_filename)
            data = yaml.safe_load(open(filename))
        items_iter = None
        if isinstance(data, list):
            items_iter = enumerate(data)
        elif isinstance(data, dict):
            items_iter = data.items()
        if items_iter is None:
            continue
        for key, item in items_iter:
            filename = current_filename
            if isinstance(item, str) and item.startswith(INCLUDE_DIRECTIVE):
                filename = get_filename(
                    item[len(INCLUDE_DIRECTIVE):],
                    current_filename)
                item = data[key] = yaml.safe_load(open(filename))
            if isinstance(item, dict) or isinstance(item, list):
                stack.append((data[key], filename))
    yaml.dump(root, open(out_filename, 'w'), default_flow_style=False)


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
    app_conf_process(args.in_filename, args.out_filename)


if __name__ == '__main__':
    main(sys.argv)
