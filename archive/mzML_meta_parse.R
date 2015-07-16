install.packages("jsonlite")
library("jsonlite")
# Simple script to use the mzML python script in R to get meta information

# Update as appropiate
mzML_meta_pth <- "/home/tomnl/Dropbox/code/mzML_2_ISA-Tab/mzML.py"  
in_file <- "/home/tomnl/Dropbox/code/mzML_2_ISA-Tab/testing/small.pwiz.1.1.mzML"    
out_file <- "/home/tomnl/Desktop/mzml_meta.json"

# Run the script
py_call <- paste('python', mzML_meta_pth, "-i", in_file, "-o", out_file, sep=" ")
out <- system(py_call)

# Read in the created JSON file
json_data <- fromJSON(out_file)

# Some of meta information available
json_data$`Parameter Value[Scan polarity]`
json_data$`Parameter Value[Number of scans]`
json_data$`Parameter Value[Instrument]`
