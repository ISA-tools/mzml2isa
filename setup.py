#!/usr/bin/env python
# released under the GNU General Public License version 3.0 (GPLv3)

from distutils.core import setup
import glob
import sys
import os

def main():
    if sys.version_info[0] != 2 and sys.version_info[1] != 7:
        raise Error("Python-2.7.8 is required")
    example_files = glob.glob(os.path.join('scripts', '*.*'))
    example_path = os.path.join('scripts')

    setup( name="mzml_2_isa",
    version= "0.1",
    description= "mzML to ISA-tab parsing tool",
    author= "Thomas Lawson",
    author_email= "tnl495@bham.ac.uk",
    url= "http://www.biosciences.bham.ac.uk/labs/viant/",
    platforms = ['Linux (ubuntu), Windows'],
    keywords = ['Metabolomics', 'Mass spectrometry', 'metabolites', 'ISA Tab', 'mzML', 'parsing'],
    packages=['mzml_2_isa'],

    package_dir={'mzml_2_isa': 'mzml_2_isa'},
    #package_data={'MI_Pack': ['*.pyd', '*.so']},

    data_files=[(example_path, example_files)],
    long_description="mzml_2_isa - mzML to ISA-tab parsing tool",)

if __name__ == "__main__":
    main()

