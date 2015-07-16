import argparse
import textwrap
import os
from mzml_2_isa import parsing

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
print os.linesep, "in directory:", args.in_dir
print "out directory:", os.path.join(args.out_dir, args.study_name)
print "Sample identifier name:", args.study_name, os.linesep

parsing.full_parse(args.in_dir, args.out_dir, args.study_name)