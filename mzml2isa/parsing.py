import os
import glob
import argparse
import textwrap

import mzml2isa.isa as isa
import mzml2isa.mzml as mzml




def run():
	p = argparse.ArgumentParser(prog='PROG',
	                                 formatter_class=argparse.RawDescriptionHelpFormatter,
	                                 description='''Extract meta information from mzML files and create ISA-tab structure''',
	                                 epilog=textwrap.dedent('''\
	                                 -------------------------------------------------------------------------

	                                 Example Usage:
	                                 python mzml_2_isa.py -i [in dir] -o [out dir] -s [study identifier name]
	                                 '''))

	p.add_argument('-i', dest='in_dir', help='in folder containing mzML files', required=True)
	p.add_argument('-o', dest='out_dir', help='out folder, new directory will be created here', required=True)
	p.add_argument('-s', dest='study_name', help='study identifier name', required=True)

	args = p.parse_args()
	print("{} in directory: {}".format(os.linesep, args.in_dir))
	print("out directory: {}".format(os.path.join(args.out_dir, args.study_name)))
	print("Sample identifier name:{}{}".format(args.study_name, os.linesep))

	full_parse(args.in_dir, args.out_dir, args.study_name)


def full_parse(in_dir, out_dir, study_identifer):

    # get mzML file in the example_files folder
    mzml_path = os.path.join(in_dir, "*.mzML")
    print(mzml_path)
    mzml_files = [mzML for mzML in glob.glob(mzml_path)]
    mzml_files.sort()
    print(mzml_files)
    # get meta information for all files
    metalist = [ mzml.mzMLmeta(i).meta_isa for i in mzml_files ]

    # update isa-tab file
    isa_tab_create = isa.ISA_Tab(metalist,out_dir, study_identifer)

