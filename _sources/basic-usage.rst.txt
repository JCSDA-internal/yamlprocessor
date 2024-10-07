Basic Usages
============

Command line
------------

.. code-block:: bash

   yp-data [options] input-file-name ... output-file-name
   yp-data [options] -o output-file-name input-file-name ...


Type ``yp-data --help`` for a list of options. See :doc:`cli` for detail.

Python
------

.. code-block:: python

   from yamlprocessor.dataprocess import DataProcessor
   processor = DataProcessor()
   # ... Customise the `DataProcessor` instance as necessary ..., then:
   processor.process_data([in_file_name], out_file_name)

See :doc:`api` for detail.
