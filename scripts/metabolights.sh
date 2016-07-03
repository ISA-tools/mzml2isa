#!/bin/bash

echo "             _        _           _ _       _     _       ";
echo "  /\/\   ___| |_ __ _| |__   ___ | (_) __ _| |__ | |_ ___ ";
echo " /    \ / _ \ __/ _\` | '_ \ / _ \| | |/ _\` | '_ \| __/ __|";
echo "/ /\/\ \  __/ || (_| | |_) | (_) | | | (_| | | | | |_\__ \\";
echo "\/    \/\___|\__\__,_|_.__/ \___/|_|_|\__, |_| |_|\__|___/";
echo "                  ftp.ebi.ac.uk       |___/       EBI     ";
echo "                                                          ";


## Get a list of MetaboLights Studies containing .mzML files
/usr/bin/python -c "
import json
import urllib.request as rq
study_url = 'http://ftp.ebi.ac.uk/pub/databases/metabolights/study_file_extensions/ml_file_extension.json'
req = rq.Request(study_url)
con = rq.urlopen(req)
e = json.JSONDecoder()
study = e.decode(con.read().decode('utf-8'))
mzml_studies = [k['id'] for k in study if '.imzML' in k['extensions'] or '.imzML' in k['extensions']]
for study in mzml_studies:
    print(study)
" > scripts/mzml_studies.txt

## Mount ftp remote study folder with curlftpfs
[ -d example_files/metabolights ] || mkdir example_files/metabolights
[ -n "$(ls -A example_files/metabolights)" ] || curlftpfs ftp.ebi.ac.uk/pub/databases/metabolights/studies/public example_files/metabolights

## Create out folder if it does not exist
[ -d out_folder/metabolights ] || mkdir out_folder/metabolights

## Study loop
while read study; do

	## Check if study was not already generated
	if [ -d out_folder/metabolights/$study ]; then
		echo "Study ${study} was already generated."
	else
		## Run mzml2isa parser
		mzml2isa -i example_files/metabolights/$study -o out_folder/metabolights -s $study
		
		[ ! $? -eq 0 ] && exit 1 
		
		## Check if parser worked (look for generated files)
		#[ -f out_folder/metabolights/${study}/s_$study.txt ] \
		#&& [ -f out_folder/metabolights/${study}/i_$study.txt ] \
		#&& [ -f out_folder/metabolights/${study}/a_$study_*.txt ] \
		#|| echo $study >> fails.txt
	fi

done < scripts/mzml_studies.txt

fusermount -u example_files/metabolights
