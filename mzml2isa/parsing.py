# coding: utf-8
"""Higher-level interface to parser/converter functionalities.

This module exposes basic API of mzml2isa, either being called from command
line interface with arguments parsing via **main** function, or from another
Python program via the **fparse** function which works the same.

Example:
    >>> from mzml2isa.parsing import convert
    >>> convert('examples/hupo-psi-1', 'output_directory', 'PSI1')

About:
    The mzml2isa parser was created by Tom Lawson (University of Birmingham, UK)
    as part of a NERC funded placement at EBI Cambridge in June 2015. Python 3
    port and enhancements were carried out by Martin Larralde (ENS Cachan, FR)
    in June 2016 during an internship at the EBI Cambridge.

License:
    GNU General Public License version 3.0 (GPLv3)
"""
from __future__ import absolute_import

import io
import os
import sys
import six
import glob
import argparse
import contextlib
import textwrap
import warnings
import json
import tarfile
import zipfile
import multiprocessing
import multiprocessing.pool
import pronto
import functools
import fs
import fs.path


from . import __author__, __version__, __name__, __license__
from .isa import ISA_Tab
from .mzml import MzMLFile
from .imzml import ImzMLFile
from .usermeta import UserMetaLoader
from .utils import longest_substring, merge_spectra, star_args
from ._impl import tqdm


@star_args
def _parse_file(filesystem, path, parser):
    """Parse a single file using a cache ontology and a metadata extractor

    Arguments:
        filesystem (FS URL or FS): the filesystem the file is located on
        path (str): filesystem path to the (i)mzML file
        ontology (pronto.Ontology): the cached ontology to use
            (either IMS or MS)
        parser (mzml.mzMLmeta): the parser to use on the file
            (either mzml2isa.mzml.mzMLmeta or mzml2isa.mzml.imzMLmeta)

    Returns:
        dict: a dictionary containing the extracted metadata
    """
    meta = parser(filesystem, path).metadata
    # if pbar is not None:
    #     pbar.update(pbar.value + 1)
    # else:
    #     print("Finished parsing: {}".format(path))
    return meta


def convert(
    in_path,
    out_path,
    study_identifier,
    usermeta=None,
    split=True,
    merge=False,
    jobs=1,
    template_directory=None,
    verbose=True,
):
    """ Parses a study from given *in_path* and then creates an ISA file.

    A new folder is created in the out directory bearing the name of
    the study identifier.

    Arguments:
        in_path (str): path to the directory or archive containing mzml files
        out_path (str): path to the output directory
        study_identifier (str): study identifier (e.g. MTBLSxxx)

    Keyword Arguments:
        usermeta (str, optional): the path to a json file, a xlsx file or
            directly a json formatted string containing user-defined
            metadata [default: None]
        split (bool): split assay files based on the polarity of the scans
            [default: True]
        merge (bool): for imzML studies, try to merge centroid and profile
            scans in a single sample row [default: False]
        jobs (int): the number of jobs to use for parsing mzML or imzML files
            [default: 1]
        template_directory (str, optional): the path to a directory
            containing custom templates to use when importing ISA tab
            [default: None]
        verbose (bool): display more output [default: True]
    """

    PARSERS = {"mzML": MzMLFile, "imzML": ImzMLFile}

    # open user metadata file if any
    meta_loader = UserMetaLoader(usermeta)

    # open the filesystem containing the files
    with fs.open_fs(in_path) as filesystem:

        # get all mzML files
        mzml_files = list(
            filesystem.filterdir("/", files=["*mzML"], exclude_dirs=["*"])
        )

        if mzml_files:
            # store the first mzml_files extension
            extension = mzml_files[0].name.rsplit(os.path.extsep)[-1]
            parser = PARSERS[extension]

            # prepare the parser arguments
            files_iter = [
                (filesystem, mzml_file.name, parser)
                for mzml_file in sorted(mzml_files, key=lambda f: f.name)
            ]

            # wrap in a progress bar if needed
            if not verbose and tqdm is not None:
                files_iter = tqdm.tqdm(files_iter)

            # parse using threads if needed
            if jobs > 1:
                with contextlib.closing(multiprocessing.pool.ThreadPool(jobs)) as pool:
                    metalist = pool.map(_parse_file, files_iter)
            else:
                metalist = list(map(_parse_file, files_iter))

            # merge spectra if needed
            if merge and extension == "imzML":
                if verbose:
                    print("Attempting to merge profile and centroid scans")
                metalist = merge_spectra(metalist)

            # write isa-tab file
            if metalist:
                if verbose:
                    print("Parsing mzML meta information into ISA-Tab structure")
                    print(out_path, template_directory)
                isa_tab = ISA_Tab(
                    out_path,
                    study_identifier,
                    usermeta=meta_loader.usermeta,
                    template_directory=template_directory,
                )
                isa_tab.write(metalist, extension, split=split)

        else:
            warnings.warn("No files were found in {}.".format(in_path), UserWarning)


def main(argv=None):
    """Run **mzml2isa** from the command line

    Arguments
        argv (list, optional): the list of arguments to run mzml2isa
            with (if None, then sys.argv is used) [default: None]
    """
    p = argparse.ArgumentParser(
        prog=__name__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Extract meta information from (i)mzML files and create ISA-tab structure""",
        usage="mzml2isa -i IN_PATH -o OUT_PATH -s STUDY_ID [options]",
    )

    p.add_argument(
        "-i",
        dest="in_path",
        help="input folder or archive containing mzML files",
        required=True,
    )

    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-o", dest="out_path", help="out folder (new files will be created here)"
    )
    p.add_argument(
        "-s", dest="study_id", help="study identifier (e.g. MTBLSxxx)", required=True
    )
    p.add_argument(
        "-m",
        dest="usermeta",
        help="additional user provided metadata (JSON format)",
        default=None,
        required=False,
    )
    p.add_argument(
        "-j",
        dest="jobs",
        help="launch different processes for parsing",
        action="store",
        required=False,
        default=1,
        type=int,
    )
    p.add_argument(
        "-n",
        dest="split",
        help="do NOT split assay files based on polarity",
        action="store_false",
        default=True,
    )
    p.add_argument(
        "-c",
        dest="merge",
        help="do NOT group centroid & profile samples",
        action="store_false",
        default=True,
    )
    p.add_argument(
        "-W",
        dest="wrng_ctrl",
        help="warning control (with python default behaviour)",
        action="store",
        default="once",
        required=False,
        choices=["ignore", "always", "error", "default", "module", "once"],
    )
    p.add_argument(
        "-t",
        dest="template_dir",
        help="directory containing default template files",
        action="store",
        default=None,
    )
    p.add_argument(
        "--version", action="version", version="mzml2isa {}".format(__version__)
    )
    p.add_argument(
        "-v",
        dest="verbose",
        help="show more output (default if tqdm is not installed)",
        action="store_true",
        default=False,
    )

    args = p.parse_args(argv or sys.argv[1:])

    if not tqdm:
        setattr(args, "verbose", True)

    if args.verbose:
        print("{} input path: {}".format(os.linesep, args.in_path))
        print("output path: {}".format(args.out_path))
        print("Sample identifier:{}{}".format(args.study_id, os.linesep))

    with warnings.catch_warnings():
        warnings.filterwarnings(args.wrng_ctrl)
        convert(
            args.in_path,
            args.out_path,
            args.study_id,
            usermeta=args.usermeta,
            split=args.split,
            merge=args.merge,
            verbose=args.verbose,
            jobs=args.jobs,
            template_directory=args.template_dir,
        )


#### DEPRECATED


@functools.wraps(main)
def run(*args, **kwargs):
    warnings.warn(
        "mzml2isa.parsing.run is deprecated, use " "mzml2isa.parsing.main instead",
        DeprecationWarning,
    )
    return main(*args, **kwargs)


@functools.wraps(convert)
def full_parse(*args, **kwargs):
    warnings.warn(
        "mzml2isa.parsing.full_parse is deprecated, use "
        "mzml2isa.parsing.convert instead",
        DeprecationWarning,
    )
    return convert(*args, **kwargs)


if __name__ == "__main__":
    main()
