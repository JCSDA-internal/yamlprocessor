#!/usr/bin/env python3
"""The datapreprocessor looks for the DIRECT_INCLUDE= keyword in the input
   yaml and concatenates the associated file at this point in the input
   file. The result is written to the output file or standard out if - is
   specified.

Example usage:
    python datapreprocessor.py  <input file> -o <output file> \
        --define JOPA_AUX=/path/to/my/file
    python datapreprocessor.py <input file> -o- \
        --define JOPA_AUX=/path/to/my/file
"""

import argparse
import os
import re
import sys


class DataPreProcessor:

    def __init__(self):
        self.replacements = os.environ.copy()

    def __replace_placeholders(self, text):
        # Create a regex pattern that matches $VAR or ${VAR}
        pattern = re.compile(r'\$\{(\w+)\}|\$(\w+)')

        # Function to get the replacement value from env_vars
        def replacer(match):
            var_name = match.group(1) or match.group(2)
            return self.replacements.get(var_name, match.group(0))

        # Substitute the placeholders with actual values
        return pattern.sub(replacer, text)

    def add_replacements_map(self, replacements):
        self.replacements.update(replacements)

    def process_yaml(self, in_yaml, out_yaml):
        # read yaml file
        src_file = open(in_yaml, 'r')
        lines = src_file.readlines()
        src_file.close()

        # process yaml file
        new_line = []
        for iline in lines:
            # look for specific pattern in each line
            if 'DIRECT_INCLUDE=' in iline:
                # retrieve header file
                yaml_header_File = iline.split('=')[1].rstrip()
                # replace variables in the string
                yaml_header_File = self.__replace_placeholders(
                    yaml_header_File)
                # open header file
                with open(yaml_header_File, 'r') as file:
                    auxFileData = file.read()
                # update lines for new file
                new_line.append(auxFileData)
            else:
                new_line.append(iline)
        # save the result
        if out_yaml == '-':
            out_file = sys.stdout
        else:
            out_file = open(out_yaml, 'w')
        out_file.writelines(new_line)


def main():
    parser = argparse.ArgumentParser(
        description="Process input and output "
                    "files with multiple --define options."
    )

    # Positional argument for input
    parser.add_argument('input_file', type=str, help='Input file')

    # Output file specified
    parser.add_argument(
        '--output-file', '-o',
        metavar='FILENAME',
        action="store",
        help='Name of output file, "-" for STDOUT'
    )

    # Optional
    parser.add_argument(
        '--define', '-D',
        action='append',
        help='Key-value pairs in the format key=value', default=[]
    )
    parser.add_argument(
        '--no-environment', '-i',
        action='store_true',
        default=False,
        help='Do not use environment variables in variable substitutions')

    # Parse arguments and print for sanity checking
    args = parser.parse_args()
    print(f"Input file: {args.input_file}", file=sys.stderr)
    print(f"Output file: {args.output_file}", file=sys.stderr)
    print(f"Defines: {args.define}", file=sys.stderr)

    # Process define arguments into a dictionary for adding to the
    # environment variable dictionary
    key_value_pairs = {}
    if args.define:
        for item in args.define:
            key, value = item.split('=')
            key_value_pairs[key] = value

    # Run preprocessor
    preprocessor = DataPreProcessor()
    if args.no_environment:
        preprocessor.replacements.clear()
    preprocessor.add_replacements_map(key_value_pairs)
    preprocessor.process_yaml(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
