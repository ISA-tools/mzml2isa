#!/bin/bash

echo "             _        _           _ _       _     _       ";
echo "  /\/\   ___| |_ __ _| |__   ___ | (_) __ _| |__ | |_ ___ ";
echo " /    \ / _ \ __/ _\` | '_ \ / _ \| | |/ _\` | '_ \| __/ __|";
echo "/ /\/\ \  __/ || (_| | |_) | (_) | | | (_| | | | | |_\__ \\";
echo "\/    \/\___|\__\__,_|_.__/ \___/|_|_|\__, |_| |_|\__|___/";
echo "                  ftp.ebi.ac.uk       |___/       EBI     ";
echo "                                                          ";


/usr/bin/python3 -c "
import json
import urllib.request as rq
study_url = 'http://ftp.ebi.ac.uk/pub/databases/metabolights/study_file_extensions/ml_file_extension.json'
req = rq.Request(study_url)
con = rq.urlopen(req)
e = json.JSONDecoder()
study = e.decode(con.read().decode('utf-8'))
mzml_studies = [k['id'] for k in study if '.mzML' in k['extensions']]
for study in mzml_studies:
    print(study)
" > scripts/mzml_studies.txt


[ -d example_files/metabolights ] || mkdir example_files/metabolights
[ -n "$(ls -A example_files/metabolights)" ] || curlftpfs ftp.ebi.ac.uk/pub/databases/metabolights/studies/public example_files/metabolights

[ -d out_folder/metabolights ] || mkdir out_folder/metabolights
while read study; do
	mzml2isa -i example_files/metabolights/$study -o out_folder/metabolights -s ${study#*/*/*}
	[ -d out_folder/metabolights/$study ] || echo $study >> fails.txt
done < scripts/mzml_studies.txt

echo "Completed parsing... Press ENTER to unmount fuse MetaboLights"
read
fusermount -u example_files/metabolights
