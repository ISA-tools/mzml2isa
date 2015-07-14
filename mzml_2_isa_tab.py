from ISA_tab import ISA_tab
from mzML import mzMLmeta
import os

# get testing folder
dirname = os.path.dirname(os.path.realpath(__file__))
testing_path = os.path.join(dirname, "testing")

# get the example dataset
in_file = os.path.join(testing_path, 'small.pwiz.1.1.mzML')
# in_file = '/mnt/hgfs/DATA/MEGA/metabolomics/example_data/C30_LCMS/Daph_C18_Frac1_run3_neg.mzML'

###################################
# Create ISA-Tab
###################################
# CURRENTLY RESTRUCTURING! Comeback later!
#     Two options:
#       * use existing ISA tab folder and populate an assay file with the mzML files
#       * Create a new ISA-Tab folder with investigation/samples/ etc
#     get 2 examples meta file infor just for testing
metalist = [ mzMLmeta(in_file).meta for i in range(2)]

# update isa-tab file
#  assay_file = os.path.join(testing_path, 'a_ap_amp1_amd_metabolite_profiling_mass_spectrometry.txt')
isa_assay = ISA_tab(metalist)
