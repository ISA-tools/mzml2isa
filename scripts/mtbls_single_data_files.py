#!/usr/bin/env python
# coding: utf-8

from __future__ import unicode_literals
from __future__ import print_function

import io
import ftplib
import posixpath


ftp = ftplib.FTP("ftp.ebi.ac.uk")
ftp.connect()
ftp.login()

base = "/pub/databases/metabolights/studies/public/"


ftp.cwd(base)
studies = [x for x in ftp.nlst() if x.startswith('MTBLS')]


for i, study in enumerate(sorted(studies)):
    print("Study:", "{}".format(study).rjust(8), "[{}/{}]".format(i+1, len(studies)), end=" ")
    ftp.cwd(posixpath.join(base, study))
    mzml_files = [x for x in ftp.nlst() if x.lower().endswith('.mzml')]
    print(len(mzml_files), "mzML files")

    if mzml_files:
        with open(mzml_files[0], 'wb') as dst:
            ftp.retrbinary("RETR {}".format(mzml_files[0]), dst.write)
