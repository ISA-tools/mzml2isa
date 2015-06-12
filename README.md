# mzML_2_ISA-Tab

## About

Parser to get meta information from mzML file and parse relevant information to a ISA-Tab assay file

Input: Takes in as input a (MetaboLights formatted) ISA-Tab assay file and 1 or more mzML files:

Outputs: Updated ISA-Tab assay file with relevant meta information for mass spectrometry

In very early stages at the moment (A few bits are hardcoded)! Come back later for a proper working version :) 

isa_mzML.py contains the classes mzML meta extraction and ISA-tab file creation
obo_parse.py and  pymzml_obo_parse.py are parsers I have modified from a blog[1] and the python package pymzml
psi-ms.obo contains all the onotology terms used

## Todo 

* Get derived meta data from mzML (e.g. scan start time)
* Create new columns in ISA-Tab assay file
* Get JSON in correct format

## Notes

The way in which the ISA-Tab file will be created may change depending on developments elsewhere of other parsing tools.

## Ref

[1] http://blog.nextgenetics.net/?e=6

