from ISA_tab import ISA_tab
from mzML import mzMLmeta
import os
import glob

# get mzML file in the testing folder
dirname = os.path.dirname(os.path.realpath(__file__))
testing_path = os.path.join(dirname, "testing", "*.mzML")
mzml_files = [mzML for mzML in glob.glob(testing_path)]

# get meta information for all files
metalist = [ mzMLmeta(i).meta_isa for i in mzml_files ]

# update isa-tab file
isa = ISA_tab(metalist,os.path.join(dirname,"out_folder"), "new_study")
