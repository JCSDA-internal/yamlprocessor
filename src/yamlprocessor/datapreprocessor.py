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
import sys


class DataPreProcessor:

    def __init__(self):
        self.replacements = {}

    def add_replacements_map(self, replacements):
        self.replacements = replacements

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
                for key, value in self.replacements.items():
                    yaml_header_File = \
                        yaml_header_File.replace(f'${key}', value)
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

    # Optional --define arguments
    parser.add_argument(
        '--define', '-d',
        action='append',
        help='Key-value pairs in the format key=value', default=[]
    )

    # Parse arguments and print for sanity checking
    args = parser.parse_args()
    print(f"Input file: {args.input_file}", file=sys.stderr)
    print(f"Output file: {args.output_file}", file=sys.stderr)
    print(f"Defines: {args.define}", file=sys.stderr)

    # Process define arguments into a dictionary for passing to the class
    key_value_pairs = {}
    if args.define:
        for item in args.define:
            key, value = item.split('=')
            key_value_pairs[key] = value

    # Run preprocessor
    preprocessor = DataPreProcessor()
    preprocessor.add_replacements_map(key_value_pairs)
    preprocessor.process_yaml(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
