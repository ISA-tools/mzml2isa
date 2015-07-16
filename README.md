# mzml 2 isa

## About
Parser to get meta information from mzML file and create an ISA-Tab file structure with the relevant meta information.

Still a few things to do but basic functionality to do the following is available

* Extract meta information from mzML files and store as either python dictionary or JSON format
* Create an ISA-Tab file structure with relevant meta information
* Can be used as standalone script or python package, see scripts folder

## mzML to ISA-tab parsing

Can use standalone script found in the scripts folder:

```
mzml_2_isa_parser.py -i /path/to/mzml_files/ -o /path/to/out_folder/ -s [study identifier name]
```

Or you can import the package

```
from mzml_2_isa import parsing
in_dir = '/path/to/mzml_files/
out_dir = '/path/to/out_folder/
study_identifier_name = "new_metabolomics_thing"

parsing.full_parse(in_dir, out_dir, study_identifier_name)
```

## Meta extraction

If you just want to extract meta information if that is all you want.

```
from mzml_2_isa import mzml
onefile = os.path.join(in_dir,"samp1.mzML")
mm = mzml.mzMLmeta(onefile)

# python dictionary format
print mm.meta

# JSON format
print mm.meta_json
```
See scipts/example.py for all examples 

## Todo 

* Check to see how comptable with MetaboLights upload


## Ref
For ontology extraction i used a modified version from this blog [1], and modified slightly the class from pymzml [2]

[1] http://blog.nextgenetics.net/?e=6
[2] http://pymzml.github.io/

