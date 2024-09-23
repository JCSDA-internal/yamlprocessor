Data Pre-Processor
==================

The preprocessor looks for the DIRECT_INCLUDE= keyword in the input yaml and
concatenates the associated file at this point in the input file. The result
is written to the output file or standard out if - is specified.

It is expected that the keyword in the input yaml file will take the following
format:

.. code-block:: yaml

   DIRECT_INCLUDE=/path/to/file/to/be/included

Command line
------------

.. code-block:: bash

   yp-preprocessor [options] -o output-file-name input-file-name

Type ``yp-preprocessor --help`` for a list of options. See :doc:`cli` for
detail.

Python
------

.. code-block:: python

   from yamlprocessor.datapreprocessor import DataPreProcessor
   preprocessor = DataPreProcessor()
   preprocessor.add_replacements_map(keymap) # optional line
   preprocessor.process_yaml(input_file, output_file)

Examples
------------------------

Consider an input YAML file containing the following data:

.. code-block:: yaml

   DIRECT_INCLUDE=a.yaml

   hello:
     - location: *planet
       targets:
         - human
         - cat
         - dog

If ``a.yaml`` contains:

.. code-block:: yaml

   _:
   - &planet earth

Running the preprocessor on the input YAML file will yield the following
output:

.. code-block:: yaml

   _:
   - &planet earth

   hello:
     - location: *planet
       targets:
         - human
         - cat
         - dog

The preprocessor simply concatenates the contents of `a.yaml` at the correct
place in the input yaml file.  This file can then be passed to `yp-data` for
parsing.
