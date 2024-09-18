#!/usr/bin/env python3
"""The pre-process looks for the DIRECT_INCLUDE keyword in the input yaml and concatenates
   the associated file at this point in the input file.  The result is written to the
   output file.

Example usage:
    python datapreprocessor.py <input file> <output file> --define JOPA_AUX=/path/to/my/file
"""

import argparse
import re

class DataPreProcessor:

    def __init__(self, replacements):
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
                # Replace variables in the string
                for key, value in self.replacements.items():
                    yaml_header_File = re.sub(rf'\${key}', value, yaml_header_File)
                # open header file
                with open(yaml_header_File, 'r') as file:
                    auxFileData = file.read()
                # update lies for new file
                new_line.append(auxFileData)
            else:
                new_line.append(iline)
        # same the outcome
        with open(out_yaml, "w") as file:
            file.writelines(new_line)

def main():
    parser = argparse.ArgumentParser(description="Process input and output files with multiple --define options.")

    # Positional arguments for input and output files
    parser.add_argument('input_file', type=str, help='Input file')
    parser.add_argument('output_file', type=str, help='Output file')

    # Optional --define arguments
    parser.add_argument('--define', action='append', help='Key-value pairs in the format key=value', default=[])

    # Parse arguments and print for sanity checking
    args = parser.parse_args()
    print(f"Input file: {args.input_file}")
    print(f"Output file: {args.output_file}")
    print(f"Defines: {args.define}")

    # process define arguments into a dictionary for passing to the class
    key_value_pairs = {}
    if args.define:
        for item in args.define:
            key, value = item.split('=')
            key_value_pairs[key] = value

    # Run preprocessor
    preprocessor = DataPreProcessor(key_value_pairs)
    preprocessor.process_yaml(args.input_file, args.output_file)

if __name__ == "__main__":
    main()
