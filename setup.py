#!/usr/bin/env python
# released under the GNU General Public License version 3.0 (GPLv3)

from setuptools import setup, find_packages
import glob
import sys
import os

import mzml2isa

if sys.version_info[0] == 2: deps = ['lxml']
else: deps = []

"""
def main():
    #if sys.version_info[0] != 2 and sys.version_info[1] != 7:
    #    raise Error("Python-2.7.8 is required")
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
    packages=['mzml2isa'],
    package_data={'': ['default/*.txt','*.obo']},

    data_files=[(example_path, example_files)],
    long_description="mzml2isa - mzML to ISA-tab parsing tool",)

if __name__ == "__main__":
    main()
"""

## SETUPTOOLS VERSION
setup(
    name='mzml2isa',
    version=mzml2isa.__version__,
    
    packages=find_packages(),
    
    py_modules=['mzml2isa'],
    

    author= "Thomas Lawson",
    author_email= "tnl495@bham.ac.uk",


    description="mzML to ISA-tab parsing tool",
    long_description=open('README.md').read(),
    
    install_requires= deps,

    include_package_data=True,

    url='http://www.biosciences.bham.ac.uk/labs/viant/',



    classifiers=[
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Topic :: Text Processing :: Markup :: XML",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
    "Topic :: Utilities",
    "Operating System :: OS Independent",
    ],


    entry_points = {
        'console_scripts': [
            'mzml2isa = mzml2isa.parsing:run',
        ],
    },
    license="GPLv3",

    keywords = ['Metabolomics', 'Mass spectrometry', 'metabolites', 'ISA Tab', 'mzML', 'parsing'],




)

