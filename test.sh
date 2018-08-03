#!/bin/sh
curlftpfs -o ftp_port=- -d ftp.ebi.ac.uk/pub/databases/metabolights/studies/public example_files/metabolights &

sleep 5

ls example_files/metabolights

