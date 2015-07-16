import isa
import mzml
import os
import glob

def full_parse(in_dir, out_dir, study_identifer):

    # get mzML file in the example_files folder
    mzml_path = os.path.join(in_dir, "*.mzML")
    print mzml_path
    mzml_files = [mzML for mzML in glob.glob(mzml_path)]
    print mzml_files
    # get meta information for all files
    metalist = [ mzml.mzMLmeta(i).meta_isa for i in mzml_files ]

    # update isa-tab file
    isa_tab_create = isa.ISA_Tab(metalist,out_dir, study_identifer)