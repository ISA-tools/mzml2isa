#==================================================
# Setup in and out directory
#===================================================
import os
# get mzML file in the example_files folder
crnt_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Change to path/2/mzml files
in_dir = os.path.join(crnt_dir, "example_files")
out_dir = os.path.join(crnt_dir, "out_folder")


#==================================================
# Simple parsing
#===================================================
from mzml2isa import parsing
parsing.full_parse(in_dir, out_dir, "metabolomics_study_457")

input() # input is just a standard python function that stops the script until the user presses enter

#====================================================
# Just get meta information from a SINGLE mzML file
#====================================================
# from mzml2isa import mzml
# onefile = os.path.join(in_dir,"1_samp.mzML")
# mm = mzml.mzMLmeta(onefile)
#
# # Dictionary format
# print mm.meta
#
# # JSON format
# print mm.meta_json
#
# # Naming compatible with ISA-Tab
# print mm.meta_isa
#
# raw_input()
#
# #====================================================
# # Get meta information for all mzML files
# #====================================================
# from mzml2isa import mzml
# import glob
#
# # get a list of mzml files
# mzml_path = os.path.join(in_dir, "*.mzML")
# mzml_files = [mzML for mzML in glob.glob(mzml_path)]
#
# # get meta information for all files
# metalist = [ mzml.mzMLmeta(i).meta_json for i in mzml_files ]
#
# # print the meta information
# for m in metalist:
#     print m
