# coding: utf-8
"""
Content
-----------------------------------------------------------------------------
This module exposes basic API of mzml2isa, either being called from command
line interface with arguments parsing via **run** function, or from another
Python program via the **full_parse** function which works the same.

About
-----------------------------------------------------------------------------
The mzml2isa parser was created by Tom Lawson (University of Birmingham, UK)
as part of a NERC funded placement at EBI Cambridge in June 2015. Python 3
port and enhancements were carried out by Martin Larralde (ENS Cachan, FR)
in June 2016 during an internship at the EBI Cambridge.

License
-----------------------------------------------------------------------------
GNU General Public License version 3.0 (GPLv3)
"""
from __future__ import absolute_import

import io
import os
import sys
import glob
import argparse
import textwrap
import warnings
import json
import tarfile
import zipfile
import multiprocessing
import multiprocessing.pool
import pronto

try:
    import progressbar
except ImportError:
    progressbar = None

MARKER = "#" if sys.version_info[0]==2 else "█"

from . import isa
from . import mzml
from .versionutils import longest_substring



def _parse(args):
    filepath, ontology, parser, pbar = args
    meta = parser(filepath, ontology).meta
    if pbar is not None:
        pbar.update(pbar.value + 1)
    else:
        print("Finished parsing: {}".format(filepath))
    return meta

def merge_spectra(metalist):

    profiles = [m for m in metalist \
        if m['Spectrum representation']['entry_list'][0]['name']=='profile spectrum']
    centroid = [m for m in metalist \
        if m['Spectrum representation']['entry_list'][0]['name']=='centroid spectrum']

    profiles.sort(key=lambda x: x['Sample Name']['value'])
    centroid.sort(key=lambda x: x['Sample Name']['value'])

    if len(profiles)!=len(centroid):
        return metalist

    for p,c in zip(profiles, centroid):
        p['Derived Spectral Data File']['entry_list'].extend(
            c['Derived Spectral Data File']['entry_list']
        )
        p['Raw Spectral Data File']['entry_list'].extend(
            c['Raw Spectral Data File']['entry_list']
        )
        p['Spectrum representation']['entry_list'].extend(
            c['Spectrum representation']['entry_list']
        )
        p['Sample Name']['value'] = longest_substring(
            p['Sample Name']['value'],c['Sample Name']['value']
        ).strip('-_;:() \n\t')
        p['MS Assay Name']['value'] = p['Sample Name']['value']

    return profiles

def full_parse(in_dir, out_dir, study_identifier, **kwargs):
    """ Parses every study from *in_dir* and then creates ISA files.

    A new folder is created in the out directory bearing the name of
    the study identifier.

    Arguments:
        in_dir (:obj:`str`): path to the directory containing the study
        out_dir (:obj:`str`): path to the output directory
        study_identifier (obj:`str`): the id of the study

    Keyword Arguments:
        usermeta (dict, optional):  dictionary containing user-defined
            metadata to include in the final ISA files [default: None]
        split (bool, optional): split assay files based on the polarity
            of the scans [default: True]
        merge (bool, optional): for imzML studies, try to merge centroid
            and profile scans in a single sample row [default: False]
        jobs (int, optional): the number of jobs to use for parsing
            mzML or imzML files [default: CPU count]
        template_directory (str, optional): the path to a directory
            containing custom templates to use when importing ISA tab
            [default: None]
        verbose (bool): display more output [default: True]

    """

    usermeta = kwargs.get('usermeta', None)
    split = kwargs.get('split', True)
    merge = kwargs.get('merge', False)
    verbose = kwargs.get('verbose', True)
    jobs = kwargs.get('jobs', multiprocessing.cpu_count())
    template_directory = kwargs.get('template_directory', None)

    dirname = os.path.dirname(os.path.realpath(__file__))
    if not any(x in sys.argv for x in ('-h', '--help', '--version')):
        ms = pronto.Ontology(os.path.join(dirname, "psi-ms.obo"), False)
        ims = pronto.Ontology(os.path.join(dirname, "imagingMS.obo"), True, 1)
    else:
        ms, ims = None, None

    PARSERS = {'mzML': mzml.mzMLmeta, 'imzML': mzml.imzMLmeta}
    ONTOLOGIES = {'mzML': ms, 'imzML': ims}

    # get mzML file in the example_files folder
    if os.path.isfile(in_dir) and tarfile.is_tarfile(in_dir):
        compr = True
        mzml_files = compr_extract(in_dir, "tar")
    elif os.path.isfile(in_dir) and zipfile.is_zipfile(in_dir):
        compr = True
        mzml_files = compr_extract(in_dir, "zip")
    else:
        compr = False
        mzml_path = os.path.join(in_dir, "*mzML")
        mzml_files = glob.glob(mzml_path)
        mzml_files.sort()

    if mzml_files:
        # store the first mzml_files extension
        extension = getattr(mzml_files[0], 'name', mzml_files[0]).split(os.path.extsep)[-1]
        ontology = ONTOLOGIES[extension]
        parser = PARSERS[extension]

        if not verbose and progressbar is not None:
             pbar = progressbar.ProgressBar(
                min_value = 0,
                max_value = len(mzml_files),
                widgets=['Parsing {:8}: '.format(study_identifier),
                           # pb.FormatLabel('%(value)4d'), '/',
                           # '%4d' % len(mzml_files),
                           progressbar.SimpleProgress(),
                           progressbar.Bar(marker=MARKER, left=" |", right="| "),
                           progressbar.ETA()]
                )
             pbar.start()
        else:
            pbar = None

        if jobs > 1:
            pool = multiprocessing.pool.ThreadPool(jobs)
            metalist = pool.map(_parse, [(mzml_file, ontology, parser, pbar) for mzml_file in mzml_files])
        else:
            metalist = [_parse([mzml_file, ontology, parser, pbar]) for mzml_file in mzml_files]

        # update isa-tab file
        if merge and extension=='imzML':
            if verbose:
                print('Attempting to merge profile and centroid scans')
            metalist = merge_spectra(metalist)

        if metalist:
            if verbose:
                print("Parsing mzML meta information into ISA-Tab structure")
            isa_tab = isa.ISA_Tab(out_dir, study_identifier, usermeta=usermeta, template_directory=template_directory)
            isa_tab.write(metalist, extension, split=split)

    else:
        warnings.warn("No files were found in {}.".format(in_dir), UserWarning)

class _TarFile(object):

    def __init__(self, name, buffered_reader):
        self.name = name
        self.BufferedReader = buffered_reader

    def __getattr__(self, attr):
        if attr=="name":
            return self.name
        return getattr(self.BufferedReader, attr)

def compr_extract(compr_pth, type_):
    # extrac zip or tar(gz) files into python tar or zip objects

    filend = ('.mzml', '.imzml')
    if type_ == "zip":
        comp = zipfile.ZipFile(compr_pth)
        cfiles = [comp.open(f) for f in comp.namelist() if f.lower().endswith(filend)]
        filelist = [f.filename for f in comp.filelist]
    else:
        comp = tarfile.open(compr_pth, 'r:*')
        cfiles = [_TarFile(m.name, comp.extractfile(m)) for m in comp.getmembers() if m.name.lower().endswith(filend)]
        filelist = [f for f in comp.getnames()]

    # And add these file names as additional attribute the compression tar or zip objects
    for cf in cfiles:
        cf.filelist = filelist

    return cfiles







if __name__ == '__main__':
    run()


