# mzML_2_ISA-Tab

## About
Parser to get meta information from mzML file and parse relevant information to a ISA-Tab assay file. To be used as classes or standalone scripts.

In very early stages at the moment. Come back later for a proper working version :) 

mzML.py contains the class  for mzML meta extraction. ISA_tab.py contains the class for ISA-tab file creation
obo_parse.py and  pymzml_obo_parse.py are parsers I have modified from a blog[1] and the python package pymzml
psi-ms.obo contains all the onotology terms used

## Meta extraction

If you just want to extract meta information you can use the mzML.py as a standalone script and it write out a json file of the meta information. Use like so:

mzML.py -i /path/to/mzm_file.mzml -o /path/to/new/file.json 

## mzML to ISA-tab parsing

Full details to come later!

Input: Takes in as input a (MetaboLights formatted) ISA-Tab assay file and 1 or more mzML files:

Outputs: Updated ISA-Tab assay file with relevant meta information for mass spectrometry




## Todo 

* Get derived meta data from mzML (e.g. scan start time) [DONE]
* Create new columns in ISA-Tab assay file
* Get JSON in correct format

## Notes

The way in which the ISA-Tab file will be created may change depending on developments elsewhere of other parsing tools.

## Ref

[1] http://blog.nextgenetics.net/?e=6

