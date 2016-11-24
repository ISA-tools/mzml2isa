#!/usr/bin/env python
# released under the GNU General Public License version 3.0 (GPLv3)

import setuptools
import sys
import mzml2isa

setuptools.setup(
    name='mzml2isa',
    version=mzml2isa.__version__,

    packages=setuptools.find_packages(),

    py_modules=['mzml2isa'],

    author= mzml2isa.__author__,
    author_email= 'tnl495@bham.ac.uk',

    description="mzml2isa - mzML to ISA-tab parsing tool",
    long_description=open('README.rst').read(),

    install_requires=open('requirements.txt').read().splitlines(),

    extras_require={ 'pb': ['progressbar2'], 'lxml': ['lxml'] },

    include_package_data=True,

    url='https://github.com/ISA-tools/mzml2isa',

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
            'mzml2isa = mzml2isa.parsing:main',
        ],
    },
    license="GPLv3",

    keywords = ['Metabolomics', 'Mass spectrometry', 'metabolites', 'ISA Tab', 'mzML', 'parsing'],

)

