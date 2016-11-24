# coding: utf-8
"""
Content
-----------------------------------------------------------------------------
This module exposes basic API of mzml2isa, either being called from command
line interface with arguments parsing via **main** function, or from another
Python program via the **fparse** function which works the same.

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
import six
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

from . import (
    __author__,
    __version__,
    __name__,
    __license__,
)
from .isa   import ISA_Tab
from .mzml  import mzMLmeta, imzMLmeta
from .utils import (
    longest_substring,
    merge_spectra,
    compr_extract,
    star_args,
    get_ontology,
)


@star_args
def _parse_file(filepath, ontology, parser, pbar=None):
    """Parse a single file using a cache ontology and a metadata extractor

    Arguments:
        filepath (str): path to the mzml/imzml file to parse
        ontology (pronto.Ontology): the cached ontology to use
            (either IMS or MS)
        parser (mzml.mzMLmeta): the parser to use on the file
            (either mzml2isa.mzml.mzMLmeta or mzml2isa.mzml.imzMLmeta)
        pbar (progressbar.ProgressBar, optional): a progressbar
            to display progresses onto [default: None]

    Returns:
        dict: a dictionary containing the extracted metadata
    """
    meta = parser(filepath, ontology).meta
    if pbar is not None:
        pbar.update(pbar.value + 1)
    else:
        print("Finished parsing: {}".format(filepath))
    return meta

def convert(in_path, out_path, study_identifier, **kwargs):
    """ Parses a study from given *in_path* and then creates an ISA file.

    A new folder is created in the out directory bearing the name of
    the study identifier.

    Arguments:
        in_path (str): path to the directory or archive containing mzml files
        out_path (str): path to the output directory (new directories will be
            created here)
        study_identifier (str): study identifier (e.g. MTBLSxxx)

    Keyword Arguments:
        usermeta (dict, optional):  dictionary containing user-defined
            metadata to include in the final ISA files [default: None]
        split (bool, optional): split assay files based on the polarity
            of the scans [default: True]
        merge (bool, optional): for imzML studies, try to merge centroid
            and profile scans in a single sample row [default: False]
        jobs (int, optional): the number of jobs to use for parsing
            mzML or imzML files [default: 1]
        template_directory (str, optional): the path to a directory
            containing custom templates to use when importing ISA tab
            [default: None]
        verbose (bool): display more output [default: True]
    """
    split = kwargs.get('split', True)
    merge = kwargs.get('merge', False)
    verbose = kwargs.get('verbose', True)
    jobs = kwargs.get('jobs', 1)
    template_directory = kwargs.get('template_directory', None)

    PARSERS = {'mzML': mzMLmeta, 'imzML': imzMLmeta}
    ONTOLOGIES = {'mzML': get_ontology('MS'), 'imzML': get_ontology('IMS')}

    # open
    usermeta = UserMetaLoader(kwargs.get('usermeta', None))

    # get mzML file in the example_files folder
    if os.path.isdir(in_path):
        compr = False
        mzml_files = glob.glob(os.path.join(in_path, "*mzML"))
    elif tarfile.is_tarfile(in_path) or zipfile.is_zipfile(in_path):
        compr = True
        mzml_files = compr_extract(in_path)
    else:
        raise SystemError("Couldn't recognise format of "
                          "{} as a source of mzml files".format(in_dir))

    if mzml_files:
        # store the first mzml_files extension
        extension = getattr(mzml_files[0], 'name', mzml_files[0]).split(os.path.extsep)[-1]
        ontology = ONTOLOGIES[extension]
        parser = PARSERS[extension]

        if not verbose and progressbar is not None:
             pbar = progressbar.ProgressBar(
                min_value = 0, max_value = len(mzml_files),
                widgets=['Parsing {:8}: '.format(study_identifier),
                           progressbar.SimpleProgress(),
                           progressbar.Bar(marker=["#","█"][six.PY3], left=" |", right="| "),
                           progressbar.ETA()]
                )
             pbar.start()
        else:
            pbar = None

        if jobs > 1:
            pool = multiprocessing.pool.ThreadPool(jobs)
            metalist = pool.map(_parse_file, [(mzml_file, ontology, parser, pbar) for mzml_file in sorted(mzml_files)])
        else:
            metalist = [_parse_file([mzml_file, ontology, parser, pbar]) for mzml_file in sorted(mzml_files)]

        # update isa-tab file
        if merge and extension=='imzML':
            if verbose:
                print('Attempting to merge profile and centroid scans')
            metalist = merge_spectra(metalist)

        if metalist:
            if verbose:
                print("Parsing mzML meta information into ISA-Tab structure")
            isa_tab = ISA_Tab(out_path, study_identifier, usermeta=usermeta, template_directory=template_directory)
            isa_tab.write(metalist, extension, split=split)

    else:
        warnings.warn("No files were found in {}.".format(in_path), UserWarning)

def main(argv=None):
    """Run **mzml2isa** from the command line

    Arguments
        argv (list, optional): the list of arguments to run mzml2isa
            with (if None, then sys.argv is used) [default: None]
    """
    p = argparse.ArgumentParser(prog=__name__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='''Extract meta information from (i)mzML files and create ISA-tab structure''',
        usage='mzml2isa -i IN_PATH -o OUT_PATH -s STUDY_ID [options]',
    )

    p.add_argument('-i', dest='in_path', help='input folder or archive containing mzML files', required=True)
    p.add_argument('-o', dest='out_path', help='out folder (a new directory will be created here)', required=True)
    p.add_argument('-s', dest='study_id', help='study identifier (e.g. MTBLSxxx)', required=True)
    p.add_argument('-m', dest='usermeta', help='additional user provided metadata (JSON format)', default=None, required=False)#, type=json.loads)
    p.add_argument('-j', dest='jobs', help='launch different processes for parsing', action='store', required=False, default=1, type=int)
    p.add_argument('-n', dest='split', help='do NOT split assay files based on polarity', action='store_false', default=True)
    p.add_argument('-c', dest='merge', help='do NOT group centroid & profile samples', action='store_false', default=True)
    p.add_argument('-W', dest='wrng_ctrl', help='warning control (with python default behaviour)', action='store', default='once', required=False, choices=['ignore', 'always', 'error', 'default', 'module', 'once'])
    p.add_argument('-t', dest='template_dir', help='directory containing default template files', action='store', default=None)
    p.add_argument('--version', action='version', version='mzml2isa {}'.format(__version__))
    p.add_argument('-v', dest='verbose', help="show more output (default if progressbar2 is not installed)", action='store_true', default=False)

    args = p.parse_args(argv or sys.argv[1:])


    if not progressbar:
        setattr(args, 'verbose', True)

    if args.verbose:
        print("{} input path: {}".format(os.linesep, args.in_path))
        print("output path: {}".format(os.path.join(args.out_path, args.study_id)))
        print("Sample identifier:{}{}".format(args.study_id, os.linesep))

    with warnings.catch_warnings():
        warnings.filterwarnings(args.wrng_ctrl)
        convert(args.in_path, args.out_path, args.study_id,
           usermeta=args.usermeta, split=args.split,
           merge=args.merge, verbose=args.verbose,
           jobs=args.jobs, template_directory=args.template_dir
        )

if __name__ == '__main__':
    main()


