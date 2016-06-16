#!/usr/bin/env python
# released under the GNU General Public License version 3.0 (GPLv3)

from setuptools import setup, find_packages
import glob
import sys
import os

import mzml2isa

if sys.version_info[0] == 2: deps = ['lxml', 'argparse', 'progressbar2']
else: deps = ['progressbar2']

## SETUPTOOLS VERSION
setup(
    name='mzml2isa',
    version=mzml2isa.__version__,
    
    packages=find_packages(),
    
    py_modules=['mzml2isa'],
    
    author= mzml2isa.__author__,
    author_email= 'tnl495@bham.ac.uk',

    description="mzml2isa - mzML to ISA-tab parsing tool",
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

