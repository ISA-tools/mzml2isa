#!/usr/bin/env python

import zipfile
import ftplib
import io
import os
import sys
import argparse
import glob

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", default=os.curdir, action="store")
parser.add_argument("-f", "--force", default=False, action="store_true")


args = parser.parse_args()

if not glob.glob(os.path.join(args.output, "*.xml")) or args.force:

    if not os.path.exists(args.output):
        os.mkdir(args.output)
    
    ebi_ftp = ftplib.FTP("ftp.ebi.ac.uk")
    ebi_ftp.login()

    ebi_ftp.cwd("/pub/databases/metabolights/submissionTool/")

    zip_in_memory = io.BytesIO()
    ebi_ftp.retrbinary("RETR ISAcreatorMetaboLights.zip", zip_in_memory.write)

    zip_in_memory = zipfile.ZipFile(zip_in_memory)

    configuration_files = [ n for n in zip_in_memory.namelist() 
                              if n.startswith("Configurations/MetaboLights")]

    for configuration_file in configuration_files[1:]:
        with open(os.path.join(args.output, os.path.basename(configuration_file)), 'wb') as out_file:
            with zip_in_memory.open(configuration_file, 'rU') as in_file:
                out_file.write(in_file.read())

