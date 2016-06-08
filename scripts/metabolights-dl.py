#!/usr/bin/env python

import os
import sys
import json
import ftplib 

try :
    import urllib.request as rq
except ImportError:
    import urllib2 as rq

try: # fastest way to emulate a cli
    MAX_SIZE = int(sys.argv[1])
except IndexError:
    MAX_SIZE = 5



def human_readable(size,precision=2):
    """
    turns an int into a human reable byte size without the need of an external module
    found there : http://code.activestate.com/recipes/577081-humanized-representation-of-a-number-of-bytes/
    """
    suffixes=['B','KB','MB','GB','TB']
    suffixIndex = 0
    while size > 1024:
        suffixIndex += 1 #increment the index of the suffix
        size = size/1024.0 #apply the division
    return '{0:.{1}f} {2}'.format(size, precision, suffixes[suffixIndex])



print('Connecting to ebi public FTP server...')
## get ml_file_extensions via http
study_url = 'http://ftp.ebi.ac.uk/pub/databases/metabolights/study_file_extensions/ml_file_extension.json'
req = rq.Request(study_url)
con = rq.urlopen(req)

## get studies containing mzML
e = json.JSONDecoder()
study = e.decode(con.read().decode('utf-8'))
mzml_studies = [k['id'] for k in study if '.mzML' in k['extensions']]

## create output folder
if not os.path.isdir('example_files/metabolights'): os.mkdir('example_files/metabolights')
os.chdir('example_files/metabolights')

## start ftp session
ftp = ftplib.FTP('ftp.ebi.ac.uk')
ftp.login()
ftp.cwd('pub/databases/metabolights/studies/public')

## get the size of every folder in the study folder
print("", end='')
size_dict = {}
for study in mzml_studies:
    print("\rCalculating size of directories: {}  ".format(study), end='')
    ftp.cwd(study)
    listdir = []
    ftp.dir(listdir.append)    # v~~~ this gives the size of each file from ftp output 
    size_dict[study] = sum([int([x for x in line.split(' ') if x][4]) for line in listdir])
    ftp.cwd('..')
print("\rCalculating size of directories: Done !   ")

## Download studies
print('Downloading study files (max {} GiB):'.format(MAX_SIZE))
total_dl_size, total_dl_studies, total_files = 0, 0, 0
for study in sorted(size_dict, key=size_dict.__getitem__):
    
    ## check if next study is too large for max size
    if total_dl_size + size_dict[study] > MAX_SIZE * (2**30):
        break
    total_dl_size += size_dict[study]
    total_dl_studies += 1

    print('  - {} ({})'.format(study, human_readable(size_dict[study])), end=' ')

    ftp.cwd(study)  # chdir on remote 
    if not os.path.isdir(study): os.mkdir(study)
    os.chdir(study) # chdir on local

    filecount = 0 #dl files for this study
    study_files = len([x for x in ftp.nlst() if x[-4:] == 'mzML']) #total number of mzML files for this study

    for filename in ftp.nlst():
        if filename.split('.')[-1].upper() == 'MZML':
            filecount += 1
            print('{}/{} files downloaded'.format(filecount, study_files), end = '\r')
        try:
            ftp.retrbinary('RETR '+filename, open(filename, 'wb').write) #dl file
        except ftplib.all_errors:
            pass
        print('\r  - {} ({})'.format(study, human_readable(size_dict[study])), end=' ')
    
    print()
    total_files += filecount

    os.chdir('..')
    ftp.cwd('..')

ftp.close()
print('Downloaded {} of data in total ({} studies, {} files).'.format(human_readable(total_dl_size), total_dl_studies, total_files))
