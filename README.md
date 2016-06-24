# mzml2isa
#####Parser to get meta information from mzML file and parse relevant information to a ISA-Tab structure

## Overview
mzml2isa is a Python3 program that can be used to generate an ISA-Tab structure out of mzML files, providing the backbone of a study which can then be edited with an ISA editing tool (see [Metabolight pre-packaged ISA Creator](http://www.ebi.ac.uk/metabolights/))

Currently the program does the following
* Extract meta information from mzML files and store as either python dictionary or JSON format
* Create an ISA-Tab file structure with relevant meta information
* Add additional metadatas that cannot be parsed from mzML files to the ISA-Tab files through a JSON formatted dictionnary.

## Install

### With PIP
If `pip` is installed, it can be used to easily install the parser (this may need to be run as administrator depending on the machine's architecture):
```bash
pip3 install mzml2isa
```

### Without PIP
Alternatively, you can also clone the repository and install from the source :
```bash
git clone git://github.com/althonos/mzml2isa && cd mzml2isa 
python3 setup.py install
```

mzml2isa has 2 optional dependencies: `progressbar2` and `lxml`, the latter quickening the parsing process while the other enhances the output of the program. To install them both, use pip:
```bash
pip3 install lxml progressbar2
```

## Use

### CLI
The parser comes with a simple one-liner:
```bash
mzml2isa -i /path/to/mzml_files/ -o /path/to/out_folder/ -s name_of_study
```

### Module
It is also possible to import the package:
```python
from mzml2isa import parsing

in_dir = "/path/to/mzml_files/"
out_dir = "/path/to/out_folder/"
study_identifier_name = "name_of_study"

parsing.full_parse(in_dir, out_dir, study_identifier_name)
```

### Meta extraction
If you just want to extract meta information:

```python
from mzml2isa import mzml

onefile = os.path.join(in_dir,"samp1.mzML")
mm = mzml.mzMLmeta(onefile)

# python dictionary format
print mm.meta

# JSON format
print mm.meta_json
```

## Metabolights
To download some real data from [MetaboLights](http://www.ebi.ac.uk/metabolights/) studies to test the converter with, run 
```bash
python scripts/metabolights-dl.py <size>
```
from inside the repository, where _size_ is the maximum size in GiB you can allocate to download files.
The script will download the files to the `example_files/metabolight`s folder and then run mzml2isa on those files..

If you use a *NIX machine with **curlftpfs** and **bash** available, you can also run
```bash
scripts/metabolights.sh
```
to mount the database to the example directory and start converting mzML studies.

## Workflow

![alt tag](https://github.com/Tomnl/mzml_2_isa/blob/master/isa_config/mzml2isa.png)

## Ref
A modified version of the ontology extraction from this blog[1] was used, and a slightly modified class from pymzml[2]

[1] http://blog.nextgenetics.net/?e=6
[2] http://pymzml.github.io/

