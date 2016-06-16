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



import os
import sys
import glob
import argparse
import textwrap
import warnings
import json

try:
    import progressbar as pb
    PB_AVAILABLE = True
except ImportError:
    PB_AVAILABLE = True

import mzml2isa.isa as isa
import mzml2isa.mzml as mzml




def run():
    """ Runs **mzml2isa** from the command line"""
    p = argparse.ArgumentParser(prog='PROG',
	                        formatter_class=argparse.RawDescriptionHelpFormatter,
	                        description='''Extract meta information from mzML files and create ISA-tab structure''',
	                        epilog=textwrap.dedent('''\
	                        -------------------------------------------------------------------------

                                Example Usage:
                                mzml2isa -i [in dir] -o [out dir] -s [study identifier name] -m [usermeta...]
                                '''))

    p.add_argument('-i', dest='in_dir', help='in folder containing mzML files', required=True)
    p.add_argument('-o', dest='out_dir', help='out folder, new directory will be created here', required=True)
    p.add_argument('-s', dest='study_name', help='study identifier name', required=True)
    p.add_argument('-m', dest='usermeta', help='additional user provided metadata (JSON format)', required=False, type=json.loads)
    p.add_argument('-n', dest='split', help='do NOT split assay files based on polarity', action='store_false', default=True)
	
    if PB_AVAILABLE:	
        p.add_argument('-v', dest='verbose', help='print more output', action='store_true', default=False)

    args = p.parse_args()
    
    if not PB_AVAILABLE:
        setattr(args, 'verbose', True)

    if args.verbose:
	print("{} in directory: {}".format(os.linesep, args.in_dir))
        print("out directory: {}".format(os.path.join(args.out_dir, args.study_name)))
	print("Sample identifier name:{}{}".format(args.study_name, os.linesep))

    full_parse(args.in_dir, args.out_dir, args.study_name, 
               args.usermeta if args.usermeta else {}, 
               args.split, args.verbose)


def full_parse(in_dir, out_dir, study_identifer, usermeta={}, split=True, verbose=False):
    """ Parses every study from *in_dir* and then creates ISA files.

	A new folder is created in the out directory bearing the name of
	the study identifier. 

    :param str in_dir: 			 path to directory containing studies
    :param str out_dir:          path to out directory
    :param str study_identifier: name of the study (directory to create)
    """

    # get mzML file in the example_files folder
    mzml_path = os.path.join(in_dir, "*.mzML")
    
    if verbose:
    	print(mzml_path)

    
    mzml_files = [mzML for mzML in glob.glob(mzml_path)]
    #mzml_files.sort()

    metalist = []
    if mzml_files:

        # get meta information for all files
        if not verbose:
	        pbar = pb.ProgressBar(widgets=['Parsing: ',
                                           pb.Counter(), '/', str(len(mzml_files)), 
                                           pb.Bar(marker="█", left=" |", right="| "),  
                                           pb.Timer(), ' | ',
                                           pb.AdaptiveETA()])
	        for i in pbar(mzml_files):
	        	metalist.append(mzml.mzMLmeta(i).meta_isa)

        else:
            for i in mzml_files:
                print("Parsing mzml file: {}".format(i))
                metalist.append(mzml.mzMLmeta(i).meta_isa)

        # update isa-tab file
        if verbose:
            print("Parse mzML meta information into ISA-Tab structure")
        isa_tab_create = isa.ISA_Tab(metalist,out_dir, study_identifer, usermeta, split)
    
    else:
    	warnings.warn("No files were found in directory."), UserWarning
    	#print("No files were found.")	
