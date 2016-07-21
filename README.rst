mzml2isa
========

Parser to get meta information from mzML file and parse relevant information to a ISA-Tab structure

|Version| |Py versions| |Git| |Build Status| |License| |RTD doc|

Overview
--------

mzml2isa is a Python3 program that can be used to generate an ISA-Tab
structure out of mzML files, providing the backbone of a study which can
then be edited with an ISA editing tool (see `MetaboLights pre-packaged
ISA Creator <http://www.ebi.ac.uk/metabolights/>`__)

Currently the program does the following:
  * Extract meta information from mzML files and store as either python dictionary or JSON format
  * Create an ISA-Tab file structure with relevant meta information
  * Add additional metadata that cannot be parsed from mzML files to the ISA-Tab files through a JSON formatted dictionnary.

Install
-------

See the `Installation page <http://2isa.readthedocs.io/en/latest/mzml2isa/install.html>`__ of
the `online documentation <http://2isa.readthedocs.io/en/latest/mzml2isa/index.html>`__.

Usage
-----

CLI
'''

.. code:: bash

    mzml2isa -i /path/to/mzml_files/ -o /path/to/out_folder/ -s name_of_study

Python Module
'''''''''''''

See the `Usage page <http://2isa.readthedocs.io/en/latest/mzml2isa/usage.html>`__ and
the `Examples page <http://2isa.readthedocs.io/en/latest/mzml2isa/examples.html>`__ for more
information.



Metabolights
------------

To download some real data from
`MetaboLights <http://www.ebi.ac.uk/metabolights/>`__ studies to test
the converter with, run

.. code:: bash

    python scripts/metabolights-dl.py <size>

from inside the repository, where *size* is the maximum size in GiB you
can allocate to download files. The script will download the files to
the ``example_files/metabolight``\ s folder and then run mzml2isa on
those files..

If you use a \*NIX machine with **curlftpfs** and **bash** available,
you can also run

.. code:: bash

    scripts/metabolights.sh

to mount the database to the example directory and start converting mzML
studies.

Workflow
--------

.. figure:: https://raw.githubusercontent.com/Tomnl/mzml2isa/master/isa_config/mzml2isa.png
   :alt: workflow


.. |Build Status| image:: https://img.shields.io/travis/althonos/mzml2isa.svg?style=flat&maxAge=2592000
   :target: https://travis-ci.org/althonos/mzml2isa

.. |Py versions| image:: https://img.shields.io/pypi/pyversions/mzml2isa.svg?style=flat&maxAge=2592000
   :target: https://pypi.python.org/pypi/mzml2isa/

.. |Version| image:: https://img.shields.io/pypi/v/mzml2isa.svg?style=flat&maxAge=2592000
   :target: https://pypi.python.org/pypi/mzml2isa/

.. |Git| image:: https://img.shields.io/badge/repository-GitHub-blue.svg?style=flat&maxAge=2592000
   :target: https://github.com/althonos/mzml2isa

.. |License| image:: https://img.shields.io/pypi/l/mzml2isa.svg?style=flat&maxAge=2592000
   :target: https://www.gnu.org/licenses/gpl-3.0.html

.. |RTD doc| image:: https://img.shields.io/badge/documentation-RTD-71B360.svg?style=flat&maxAge=2592000
   :target: http://2isa.readthedocs.io/en/latest/mzml2isa/index.html
