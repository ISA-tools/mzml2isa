# mzML 2 ISA-Tab

## About
Parser to get meta information from mzML file and create an ISA-Tab file structure with the relevant meta information.

Still a few things to complete and the code needs tidying up but the basic functionality is there. Does the following:

* Extract meta information from mzML files and store as either python dictionary or JSON format
* Create an ISA-Tab file structure with relevant meta information
* Can be used as standalone script or python package, see scripts/ for examples

## Workflow

![alt tag](https://github.com/Tomnl/mzml_2_isa/blob/master/isa_config/mzml2isa.png)


## Install the python package

```bash
git clone https://github.com/Tomnl/mzml2isa.git

cd mzml2isa

# if in Linux
sudo python setup.py install

# if in windows need admin rights
python setup.py install

```

## mzML to ISA-tab parsing

You can use the system command that ships with the library:

```bash
mzml2isa -i /path/to/mzml_files/ -o /path/to/out_folder/ -s name_of_study
```

Or you can import the package

```python
from mzml2isa import parsing

in_dir = "/path/to/mzml_files/"
out_dir = "/path/to/out_folder/"
study_identifier_name = "name_of_study"

parsing.full_parse(in_dir, out_dir, study_identifier_name)
```

## Meta extraction

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
To download some real data from MetaboLights studies to test the converter with, run
```bash
python scripts/metabolights-dl.py <size>
```
where size is the maximum size in GiB you can allocate to download files.
The script will download the files to the example_files/metabolights folder and the run mzml2isa.

If you use a *NIX machine with **curlftpfs** installed, you can also run
```bash
scripts/metabolights.sh
```
to mount the database to the example directory and start converting mzML studies.


## Todo 

* Check to see how compatible with MetaboLights upload


## Ref
For ontology extraction i used a modified version from this blog [1], and modified slightly the class from pymzml [2]

[1] http://blog.nextgenetics.net/?e=6

[2] http://pymzml.github.io/

