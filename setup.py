#!/usr/bin/env python
# released under the GNU General Public License version 3.0 (GPLv3)

from setuptools import setup, find_packages
import glob
import sys
import os

import mzml2isa

## SETUPTOOLS VERSION
setup(
    name='mzml2isa',
    version=mzml2isa.__version__,
    
    packages=find_packages(),
    
    py_modules=['mzml2isa'],
    
    author= mzml2isa.__author__,
    author_email= 'tnl495@bham.ac.uk',

    description="mzml2isa - mzML to ISA-tab parsing tool",
    long_description=open('README.rst').read(),
    
    install_requires=['pronto'] \
                     if sys.version_info[0]==3 \
                     else ['pronto', 'argparse', 'chainmap'],
    extras_require={ 'extras': ['lxml', 'progressbar2'] },

    include_package_data=True,

    url='http://www.biosciences.bham.ac.uk/labs/viant/',

    classifiers=[
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.5",
    "Topic :: Text Processing :: Markup :: XML",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Topic :: Scientific/Engineering :: Chemistry",
    "Topic :: Utilities",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
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

