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
port and small enhancements were carried out by Martin Larralde (ENS Cachan,
France) in June 2016 during an internship at the EBI Cambridge.

License
-----------------------------------------------------------------------------
GNU General Public License version 3.0 (GPLv3)
"""


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

from multiprocessing.pool import Pool
from pronto import Ontology

try:
    import progressbar as pb
    PB_AVAILABLE = True
except ImportError:
    PB_AVAILABLE = False

MARKER = "#" if sys.version_info[0]==2 else "█"

import mzml2isa
import mzml2isa.isa as isa
import mzml2isa.mzml as mzml
from mzml2isa.versionutils import longest_substring


_PARSERS = {'mzML': mzml.mzMLmeta,
           'imzML': mzml.imzMLmeta}

# change the ontology and start extracting imaging specific metadata
warnings.simplefilter('ignore')
dirname = os.path.dirname(os.path.realpath(__file__))

if not any(x in sys.argv for x in ('-h', '--help', '--version')):
    _ms = Ontology(os.path.join(dirname, "psi-ms.obo"), False)
    _ims = Ontology(os.path.join(dirname, "imagingMS.obo"), False)
    _ims.terms.update(_ms.terms)
else:
    _ms, _ims = None, None
#_ims.merge(_ms)


_ONTOLOGIES = {'mzML': _ms,
               'imzML': _ims }
del dirname


def _multiparse(filepath):
    print('Parsing file: {}'.format(filepath))
    parser = _PARSERS[filepath.split(os.path.extsep)[-1]]
    ont = _ONTOLOGIES[filepath.split(os.path.extsep)[-1]]
    return parser(filepath, ont).meta_isa

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





def run():
    """ Runs **mzml2isa** from the command line"""
    p = argparse.ArgumentParser(prog='PROG',
                            formatter_class=argparse.RawDescriptionHelpFormatter,
                            description='''Extract meta information from (i)mzML files and create ISA-tab structure''',
                            epilog=textwrap.dedent('''\
                            -------------------------------------------------------------------------

                                Example Usage:
                                mzml2isa -i [in dir] -o [out dir] -s [study identifier name] -m [usermeta...]
                                '''))

    p.add_argument('-i', dest='in_dir', help='in folder containing mzML files', required=True)
    p.add_argument('-o', dest='out_dir', help='out folder, new directory will be created here', required=True)
    p.add_argument('-s', dest='study_name', help='study identifier name', required=True)
    p.add_argument('-m', dest='usermeta', help='additional user provided metadata (JSON format)', required=False)#, type=json.loads)
    p.add_argument('-j', dest='jobs', help='launch different processes for parsing', required=False, default=0, type=int)
    p.add_argument('-n', dest='split', help='do NOT split assay files based on polarity', action='store_false', default=True)
    p.add_argument('-c', dest='merge', help='do NOT group centroid & profile samples', action='store_false', default=True)
    p.add_argument('-W', dest='wrng_ctrl', help='warning control (with python default behaviour)', action='store', default='ignore',
                         required=False, choices=['ignore', 'always', 'error', 'default', 'module', 'once'])
    p.add_argument('--version', action='version', version='mzml2isa {}'.format(mzml2isa.__version__))



    if PB_AVAILABLE:
        p.add_argument('-v', dest='verbose', help='print more output', action='store_true', default=False)

    args = p.parse_args()

    try:
        if not args.usermeta:
            usermeta = None
        elif os.path.isfile(args.usermeta):
            with open(args.usermeta) as f:
                usermeta = json.load(f)
        else:
            usermeta = json.loads(args.usermeta)
    except json.decoder.JSONDecodeError:
        warnings.warn("Usermeta could not be parsed.", UserWarning)
        usermeta = None



    if not PB_AVAILABLE:
        setattr(args, 'verbose', True)

    if args.verbose:
        print("{} in directory: {}".format(os.linesep, args.in_dir))
        print("out directory: {}".format(os.path.join(args.out_dir, args.study_name)))
        print("Sample identifier name:{}{}".format(args.study_name, os.linesep))

    with warnings.catch_warnings():
        warnings.filterwarnings(args.wrng_ctrl)

        full_parse(args.in_dir, args.out_dir, args.study_name,
                   usermeta if usermeta else None,
                   args.split, args.merge, args.verbose, args.jobs)

def full_parse(in_dir, out_dir, study_identifier, usermeta=None, split=True, merge=False, verbose=False, multip=False):
    """ Parses every study from *in_dir* and then creates ISA files.

    A new folder is created in the out directory bearing the name of
    the study identifier.

    :param str in_dir:           path to directory containing studies
    :param str out_dir:          path to out directory
    :param str study_identifier: name of the study (directory to create)
    """

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

        if verbose:
            print(mzml_path)

        mzml_files = [mzML for mzML in glob.glob(mzml_path)]
        #mzml_files.sort()

    if multip:
        pool = Pool(multip)

    metalist = []
    if mzml_files:

        if multip:
            metalist = pool.map(_multiparse, mzml_files)
            pool.close()
            pool.join()


        # get meta information for all files
        elif not verbose:
            pbar = pb.ProgressBar(widgets=['Parsing {:8}: '.format(study_identifier),
                                           pb.FormatLabel('%(value)4d'), '/',
                                           '%4d' % len(mzml_files),
                                           pb.Bar(marker=MARKER, left=" |", right="| "),
                                           pb.ETA()])

            for i in pbar(mzml_files):

                if compr:
                   ext = i.name.split(os.path.extsep)[-1]
                else:
                   ext = i.split(os.path.extsep)[-1]
                parser = _PARSERS[ext]
                ont = _ONTOLOGIES[ext]

                metalist.append(parser(i, ont).meta)

        else:
            for i in mzml_files:
                print("Parsing file: {}".format(i))

                if compr:
                    ext = i.name.split(os.path.extsep)[-1]
                else:
                    ext = i.split(os.path.extsep)[-1]

                parser = _PARSERS[ext]
                ont = _ONTOLOGIES[ext]

                metalist.append(parser(i, ont).meta)

        # update isa-tab file

        if merge and ext=='imzML':
            if verbose:
                print('Attempting to merge profile and centroid scans')
            metalist = merge_spectra(metalist)


        if metalist:
            if verbose:
                print("Parsing mzML meta information into ISA-Tab structure")
            isa_tab_create = isa.ISA_Tab(out_dir, study_identifier, usermeta or {}).write(metalist, ext, split)

    else:
        warnings.warn("No files were found in directory.", UserWarning)


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
        #cfiles = [comp.extractfile(m) for m in comp.getmembers() if m.name.lower().endswith(filend)]

        cfiles = [_TarFile(m.name, comp.extractfile(m)) for m in comp.getmembers() if m.name.lower().endswith(filend)]
        filelist = [f for f in comp.getnames()]

    # And add these file names as additional attribute the compression tar or zip objects
    for cf in cfiles:
        cf.filelist = filelist

    return cfiles







if __name__ == '__main__':
    run()
