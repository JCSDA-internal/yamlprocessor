# YAML Processor

This project provides a simple utility for working with YAML files, process
include files, substitute string with variable and date-time values, and
validate against JSON schema.

## Quick Start

To install from PyPI, run:

```sh
python3 -m pip install yamlprocessor
```

Command line usage:

```sh
yp-data [options] input-file-name output-file-name
```

Python usage:

```python
from yamlprocessor.dataprocess import DataProcessor
processor = DataProcessor()
# ... Customise the `DataProcessor` instance as necessary ..., then:
processor.process_data(in_file_name, out_file_name)
```

## Documentation

See [User Guide](https://JCSDA-internal.github.io/yamlprocessor) for detail.
