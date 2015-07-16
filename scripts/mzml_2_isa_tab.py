import os
from mzml_2_isa import parsing


# get mzML file in the example_files folder
# Change to path/2/mzml files
crnt_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

in_dir = os.path.join(crnt_dir, "example_files")
out_dir = os.path.join(crnt_dir,"out_folder")

parsing.full_parse(in_dir, out_dir, "testing")
