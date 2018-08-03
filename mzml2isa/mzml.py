# coding: utf-8
"""
mzml2isa.mzml
==============================================================================

Content
------------------------------------------------------------------------------
This module contains two classes, mzMLmeta and imzMLmeta, which are used
to parse and serialize the metadata of a mzML or imzML file into a Python
dictionary.

About
------------------------------------------------------------------------------
The mzml2isa parser was created by Tom Lawson (University of Birmingham, UK)
as part of a NERC funded placement at EBI Cambridge in June 2015. Python 3
port and enhancements were carried out by Martin Larralde (ENS Cachan, FR)
in June 2016 during an internship at the EBI Cambridge.

License
------------------------------------------------------------------------------
GNU General Public License version 3.0 (GPLv3)
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import os
import posixpath
import re
import warnings

import fs
import fs.path
import pronto
import pkg_resources
import six
from cached_property import cached_property

from .utils import etree, get_parent


class _CVParameter(
    collections.namedtuple(
        "_CVParameter", ["accession", "cv", "name", "plus1", "value", "software", "merge"]
    )
):
    """A named tuple with controlled vocabulary parameter information.

    Attributes:
        accession (str): The controlled vocabulary accession of the parameter.
        name (str): The name of the parameter.
        plus1 (bool): `True` if there can be more than of this parameter.
        cv (bool): `True` if a *controlled vocabulary term* should be checked
            for the parameter.
        value (bool): `True` if a *value* should be checked for the parameter.
        software (bool): `True` if *software information* should be checked for
            the parameter.
    """


class MzMLFile(object):

    _XPATHS = {
        "file_content": "{root}/s:fileDescription/s:fileContent/s:cvParam",
        "source_file": "{root}/s:fileDescription/s:sourceFileList/s:sourceFile/s:cvParam",
        "ionization": "{root}/{instrument}List/{instrument}/s:componentList/s:source/s:cvParam",
        "analyzer": "{root}/{instrument}List/{instrument}/s:componentList/s:analyzer/s:cvParam",
        "detector": "{root}/{instrument}List/{instrument}/s:componentList/s:detector/s:cvParam",
        "data_processing": "{root}/s:dataProcessingList/s:dataProcessing/s:processingMethod/s:cvParam",
        "contact": "{root}/s:fileDescription/s:contact/s:cvParam",
        "ic_ref": "{root}/{instrument}List/{instrument}/s:referenceableParamGroupRef",
        "ic_elements": "{root}/s:referenceableParamGroupList/s:referenceableParamGroup",
        "ic_nest": "{root}/{instrument}List/{instrument}",
        "ic_soft_ref": "{root}/{instrument}List/{instrument}/{software}",
        "software_elements": "{root}/s:softwareList/s:software",
        "sp": "{root}/s:run/{spectrum}List/{spectrum}",
        "sp_cv": "{root}/s:run/{spectrum}List/{spectrum}/s:cvParam",
        "scan_window_cv": "{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/{scanWindow}List/{scanWindow}/s:cvParam",
        "scan_cv": "{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:cvParam",
        "scan_num": "{root}/s:run/{spectrum}List",
        "cv": "{root}/s:cvList/s:cv",
        "raw_file": "{root}/s:fileDescription/s:sourceFileList/s:sourceFile",
        "scan_sp": "s:cvParam",
        "scan_combination": "{scanList}/s:cvParam",
        "scan_configuration": "{scanList}/s:scan/s:cvParam",
        "scan_binary": "s:binaryDataArrayList/s:binaryDataArray/s:cvParam",
        "scan_activation": "s:precursorList/s:precursor/s:activation/s:cvParam",
        "scan_isolation_window": "s:precursorList/s:precursor/s:isolationWindow/s:cvParam",
        "scan_selected_ion": "s:precursorList/s:precursor/s:selectedIonList/s:selectedIon/s:cvParam",
        "ref_sp": "s:referenceableParamGroupRef",
        "ref_combination": "{scanList}/s:scan/s:referenceableParamGroupRef",
        "ref_binary": "{scanList}/s:scan/s:referenceableParamGroupRef",
    }

    _VOCABULARY = pronto.Ontology(
        pkg_resources.resource_stream("mzml2isa", "ontologies/psi-ms.obo"), imports=False
    )

    def __init__(self, filesystem, path, vocabulary=None):
        self.fs = fs.open_fs(filesystem)
        self.path = path
        self.vocabulary = vocabulary or self._VOCABULARY

    ### COMPATIBILITY LAYER WITH IMZML #######################################

    # NB: OVERRIDE ME IN SUBCLASSES
    @classmethod
    def _environment_paths(cls):
        return collections.OrderedDict(
            [
                ("root", ["./s:mzML", "."]),
                (
                    "spectrum",
                    [
                        "{root}/s:run/s:spectrumList/s:spectrum",
                        "{root}/s:run/s:chromatogramList/s:chromatogram",
                    ],
                ),
                (
                    "scanList",
                    [
                        "{root}/s:run/{spectrum}List/{spectrum}/s:scanList",
                        "{root}/s:run/{spectrum}List/{spectrum}/s:spectrumDescription",
                    ],
                ),
                (
                    "scanWindow",
                    [
                        "{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:scanWindowList/s:scanWindow",
                        "{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:selectionWindowList/s:selectionWindow",
                    ],
                ),
                (
                    "instrument",
                    [
                        "{root}/s:instrumentConfigurationList/s:instrumentConfiguration",
                        "{root}/s:instrumentList/s:instrument",
                    ],
                ),
                (
                    "software",
                    [
                        "{root}/{instrument}List/{instrument}/s:softwareRef",
                        "{root}/{instrument}List/{instrument}/s:instrumentSoftwareRef",
                    ],
                ),
            ]
        )

    # NB: OVERRIDE ME IN SUBCLASSES
    @classmethod
    def _environment_attributes(cls):
        return collections.OrderedDict(
            [
                (
                    "filename",
                    [
                        "{root}/s:fileDescription/s:sourceFileList/s:sourceFile[@name]",
                        "{root}/s:fileDescription/s:sourceFileList/s:sourceFile[@filename]",
                        "{root}/s:fileDescription/s:sourceFileList/s:sourceFile[@sourceFileName]",
                    ],
                ),
                (
                    "cvRef",
                    [
                        "{root}/s:referenceableParamGroupList/s:referenceableParamGroup/s:cvParam[@cvLabel]",
                        "{root}/s:referenceableParamGroupList/s:referenceableParamGroup/s:cvParam[@cvRef]",
                        "{root}/s:run/{spectrum}List/{spectrum}/s:cvParam[@cvRef]",
                    ],
                ),
                ("cvLabel", ["{root}/s:cvList/s:cv[@id]", "{root}/s:cvList/s:cv[@cvLabel]"]),
                ("softwareRef", ["{root}/{instrument}List/{instrument}/{software}[@ref]"]),
            ]
        )

    # NB:
    @classmethod
    def _assay_parameters(cls):
        terms = collections.OrderedDict()

        terms["file_content"] = [
            _CVParameter(
                accession="MS:1000524",
                cv=True,
                name="Data file content",
                plus1=True,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000525",
                cv=True,
                name="Spectrum representation",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
        ]

        terms["source_file"] = [
            _CVParameter(
                accession="MS:1000767",
                cv=True,
                name="Native spectrum identifier format",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000561",
                cv=True,
                name="Data file checksum type",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000560",
                cv=True,
                name="Raw data file format",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
        ]

        terms["contact"] = [
            _CVParameter(
                accession="MS:1000586",
                cv=True,
                name="Contact name",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000587",
                cv=True,
                name="Contact adress",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000588",
                cv=True,
                name="Contact url",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000589",
                cv=True,
                name="Contact email",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000590",
                cv=True,
                name="Contact affiliation",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
        ]

        terms["ionization"] = [
            _CVParameter(
                accession="MS:1000482",
                cv=False,
                name="source_attribute",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000008",
                cv=True,
                name="Ion source",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000007",
                cv=True,
                name="Inlet type",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
        ]

        terms["analyzer"] = [
            _CVParameter(
                accession="MS:1000480",
                cv=False,
                name="analyzer_attribute",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000443",
                cv=True,
                name="Mass analyzer",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
        ]

        terms["detector"] = [
            _CVParameter(
                accession="MS:1000481",
                cv=False,
                name="detector_attribute",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000026",
                cv=True,
                name="Detector",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000027",
                cv=True,
                name="Detector mode",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
        ]

        terms["data_processing"] = [
            _CVParameter(
                accession="MS:1000630",
                cv=False,
                name="data_processing_parameter",
                plus1=True,
                value=True,
                software=True,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000452",
                cv=True,
                name="Data Transformation Name",
                plus1=True,
                value=False,
                software=True,
                merge=False,
            ),
        ]

        return terms

    @classmethod
    def _scan_parameters(cls):
        terms = collections.OrderedDict()

        terms["scan_sp"] = terms["ref_sp"] = {
            _CVParameter(
                accession="MS:1000524",
                cv=True,
                name="Data file content",
                plus1=True,
                value=False,
                software=False,
                merge=True,
            ),
            _CVParameter(
                accession="MS:1000796",
                cv=False,
                name="Spectrum title",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000465",
                cv=True,
                name="Polarity",
                plus1=True,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000511",
                cv=False,
                name="MS Level",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000525",
                cv=True,
                name="Spectrum representation",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000504",
                cv=False,
                name="Base Peak m/z",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000505",
                cv=False,
                name="Base Peak intensity",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000285",
                cv=False,
                name="Total ion current",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000927",
                cv=False,
                name="Ion injection time",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000512",
                cv=False,
                name="Filter string",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000528",
                cv=False,
                name="Lowest observed m/z",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000527",
                cv=False,
                name="Highest observed m/z",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
        }

        terms["scan_combination"] = terms["ref_combination"] = {
            _CVParameter(
                accession="MS:1000570",
                cv=True,
                name="Spectrum combination",
                plus1=True,
                value=False,
                software=False,
                merge=False,
            )
        }

        terms["scan_configuration"] = {
            _CVParameter(
                accession="MS:1000016",
                cv=False,
                name="Scan start time",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000512",
                cv=False,
                name="Filter string",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000616",
                cv=False,
                name="Preset scan configuration",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000927",
                cv=False,
                name="Ion injection time",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000018",
                cv=True,
                name="Scan direction",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000019",
                cv=True,
                name="Scan law",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
        }

        terms["scan_isolation_window"] = {
            _CVParameter(
                accession="MS:1000827",
                cv=False,
                name="Isolation window target m/z",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000828",
                cv=False,
                name="Isolation window lower offset",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000829",
                cv=False,
                name="Isolation window higher offset",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
        }

        terms["scan_selected_ion"] = {
            _CVParameter(
                accession="MS:1000744",
                cv=False,
                name="Selected ion m/z",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000041",
                cv=False,
                name="Charge state",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000042",
                cv=False,
                name="Peak intensity",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
        }

        terms["scan_activation"] = {
            _CVParameter(
                accession="MS:1000044",
                cv=True,
                name="Dissociation method",
                plus1=True,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000045",
                cv=False,
                name="Collision Energy",
                plus1=True,
                value=True,
                software=False,
                merge=False,
            ),
        }

        terms["scan_binary"] = terms["ref_binary"] = {
            _CVParameter(
                accession="MS:1000518",
                cv=True,
                name="Binary data type",
                plus1=True,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000572",
                cv=True,
                name="Binary data compression type",
                plus1=True,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000513",
                cv=True,
                name="Binary data array",
                plus1=True,
                value=False,
                software=False,
                merge=False,
            ),
        }

        return terms

    ### UTILS ################################################################

    @classmethod
    def _urlize_meta(cls, meta):
        for key, nested in six.iteritems(meta):
            if "accession" in nested:
                nested["accession"] = cls._urlize_accession(nested["accession"])
            if "accession" in nested.get("unit", {}):
                nested["unit"]["accession"] = cls._urlize_accession(nested["unit"]["accession"])
            for entry in nested.get("entry_list", []):
                if "accession" not in entry and "unit" not in entry:
                    break
                if "accession" in entry:
                    entry["accession"] = cls._urlize_accession(entry["accession"])
                if "accession" in entry.get("unit", {}):
                    entry["unit"]["accession"] = cls._urlize_accession(entry["unit"]["accession"])

    @classmethod
    def _urlize_accession(cls, accession):
        try:
            namespace, id_ = accession.split(":", 1)
            if namespace in {"MS", "UO"}:
                url = "http://purl.obolibrary.org/obo/{}_{}"
            elif namespace == "IMS":
                url = "http://www.maldi-msi.org/download/imzml/imagingMS.obo#{}:{}"
            else:
                url = "{}:{}"
            return url.format(namespace, id_)
        except ValueError:
            return accession

    ### ENVIRONMENT ##########################################################

    @cached_property
    def tree(self):
        """An XML element tree representation of the ``mzML`` file.
        """
        if self.fs.hassyspath(self.path):
            return etree.parse(self.fs.getsyspath(self.path))
        with self.fs.openbin(self.path) as handle:
            return etree.parse(handle)

    @cached_property
    def namespace(self):
        """The XML namespace of the ``mzML`` file.
        """
        root = self.tree.getroot()
        try:
            ns = root.nsmap
            ns["s"] = ns.pop(None)
        except AttributeError:
            ns = {"s": re.search(r"^{(.*)}", root.tag).group(1)}
        return ns

    @cached_property
    def environment(self):
        ns = self.namespace
        env = collections.OrderedDict()

        # setup XPaths variables
        for key, paths in six.iteritems(self._environment_paths()):
            for path in paths:
                if self.tree.find(path.format(**env), ns) is not None:
                    env[key] = posixpath.basename(path)
                    break
            else:
                env[key] = None

        # setup XPaths attributes variables
        for key, paths in six.iteritems(self._environment_attributes()):
            for path in paths:
                if self.tree.find(path.format(**env), ns) is not None:
                    env[key] = re.search(r"\[@(.*)\]", path).group(1)
                    break
            else:
                env[key] = None

        return env

        # check which method to use when extracting instrument
        # path = '{root}/s:referenceableParamGroupList/s:referenceableParamGroup/s:cvParam[@accession="MS:1000529"]'
        # if self.tree.find(path.format(**env))

    def _find_xpath(self, query):
        return self.tree.iterfind(query.format(**self.environment), self.namespace)

    @cached_property
    def _referenceable_parameters(self):
        return {x.attrib["id"]: x for x in self._find_xpath(self._XPATHS["ic_elements"])}

    ### METADATA #############################################################

    def _extract_software(self, software_ref, name, meta):

        if name.endswith("Name"):
            name = name.replace(" Name", "")

        for element in self._find_xpath(self._XPATHS["software_elements"]):
            if element.attrib["id"] == software_ref:

                version = None
                software = None

                try:  # <Softwarelist <Software <cvParam>>>
                    if element.attrib["version"]:
                        version = {"value": element.attrib["version"]}
                    for ie in element.iterfind("s:cvParam", self.namespace):
                        software = {
                            "accession": ie.attrib["accession"],
                            "name": ie.attrib["name"],
                            "ref": ie.attrib[self.environment["cvRef"]],
                        }
                except KeyError:  # <SoftwareList <software <softwareParam>>>
                    params = element.find("s:softwareParam", namespaces=self.namespace)
                    if params.attrib["version"]:
                        version = {"value": params.attrib["version"]}
                    software = {
                        "accession": params.attrib["accession"],
                        "name": params.attrib["name"],
                        "ref": params.attrib[self.environment["cvRef"]],
                    }

                if software is not None:
                    meta["{} software".format(name)] = software
                if version is not None:
                    meta["{} software version".format(name)] = version

    def _extract_cv_params(self, element, parameters, meta):

        descendents = {
            k: self.vocabulary[k].rchildren().id + [k]
            for k in (param_info.accession for param_info in parameters)
        }

        for param_info in parameters:
            if element.attrib["accession"] in descendents[param_info.accession]:
                param = {}

                if param_info.cv:
                    param["accession"] = element.attrib["accession"]
                    param["name"] = element.attrib["name"]
                    param["ref"] = element.attrib[self.environment["cvRef"]]

                if param_info.value:
                    param["value"] = element.attrib["value"]  # TODO transtype

                # try getting a unit
                try:
                    param["unit"] = {
                        "name": element.attrib["unitName"],
                        "ref": element.attrib["unitCvRef"],
                        "accession": element.attrib["unitAccession"],
                    }
                except KeyError:
                    pass

                if param_info.plus1:
                    # setup the dictionary for multiple entries
                    entries = meta.setdefault(param_info.name, dict(entry_list=[]))["entry_list"]
                    if not param_info.merge or param not in entries:
                        entries.append(param)
                else:
                    meta[param_info.name] = param

                if param_info.software:
                    try:  # softwareRef in <Processing Method>
                        soft_ref = get_parent(element, self.tree).attrib["softwareRef"]
                    except KeyError:  # softwareRef in <DataProcessing>
                        soft_ref = get_parent(get_parent(element, self.tree), self.tree).attrib[
                            "softwareRef"
                        ]
                    self._extract_software(soft_ref, param_info.name, meta)

    def _extract_assay_parameters(self, meta):
        terms = self._assay_parameters()
        for location, term in six.iteritems(terms):
            for element in self._find_xpath(self._XPATHS[location]):
                self._extract_cv_params(element, terms[location], meta)

    def _extract_derived_file(self, meta):
        spectral_file = fs.path.basename(self.path)
        ms_assay_name, _ = fs.path.splitext(spectral_file)
        meta["Derived Spectral Data File"] = {"entry_list": [{"value": spectral_file}]}
        meta["MS Assay Name"] = meta["Sample Name"] = {"value": ms_assay_name}

    def _extract_raw_file(self, meta):
        try:
            raw_file = next(self._find_xpath(self._XPATHS["raw_file"])).attrib[
                self.environment["filename"]
            ]
            meta["Raw Spectral Data File"] = {"entry_list": [{"value": os.path.basename(raw_file)}]}
        except StopIteration:
            warnings.warn("Could not find any metadata about Raw Spectral Data File.")

    def _extract_polarity(self, meta):

        sp_cv = self._find_xpath(self._XPATHS["sp_cv"])
        pos = neg = False

        for i in sp_cv:
            pos |= i.attrib["accession"] == "MS:1000130"
            neg |= i.attrib["accession"] == "MS:1000129"

        meta["Scan polarity"] = (
            {"name": "alternating scan", "ref": "", "accession": ""}
            if pos and neg
            else {"name": "positive scan", "ref": "MS", "accession": "MS:1000130"}
            if pos
            else {"name": "negative scan", "ref": "MS", "accession": "MS:1000129"}
            if neg
            else {"name": "n/a", "ref": "", "accession": ""}
        )

    def _extract_spectrum_representation(self, meta):
        representations = self.vocabulary["MS:1000525"].rchildren()
        for element in self._find_xpath(self._XPATHS["sp_cv"]):
            if element.attrib["accession"] in representations:
                meta["Spectrum representation"] = {
                    "accession": element.attrib["accession"],
                    "name": element.attrib["name"],
                    "ref": element.attrib[self.environment["cvRef"]],
                }
                return

    def _extract_timerange(self, meta):

        try:
            scan_cv = self._find_xpath(self._XPATHS["scan_cv"])
            times = [
                float(i.attrib["value"]) for i in scan_cv if i.attrib["accession"] == "MS:1000016"
            ]
            meta["Time range"] = {"value": "{:.3f}-{:.3f}".format(min(times), max(times))}

            unit = next(
                (
                    i
                    for i in self._find_xpath(self._XPATHS["scan_cv"])
                    if i.attrib["accession"] == "MS:1000016" and "unitName" in i.attrib
                ),
                None,
            )

            if unit is not None:
                meta["Time range"]["unit"] = {
                    "name": unit.attrib["unitName"],
                    "accession": unit.attrib["unitAccession"],
                    "ref": unit.attrib.get("unitCvRef", unit.attrib[self.environment["cvRef"]]),
                }

        except ValueError:
            pass

    def _extract_mzrange(self, meta):

        try:
            minmz = []
            maxmz = []
            unit = None

            for element in self._find_xpath(self._XPATHS["scan_window_cv"]):
                if element.attrib["accession"] == "MS:1000501":
                    minmz.append(float(element.attrib["value"]))
                    if unit is None and "unitName" in element.attrib:
                        unit = {
                            "name": element.attrib["unitName"],
                            "ref": element.attrib["unitCvRef"],
                            "accession": element.attrib["unitAccession"],
                        }
                elif element.attrib["accession"] == "MS:1000500":
                    maxmz.append(float(element.attrib["value"]))

            meta["Scan m/z range"] = {"value": "{}-{}".format(int(min(minmz)), int(max(maxmz)))}

            if unit is not None:
                meta["Scan m/z range"]["unit"] = unit

        except ValueError:
            if type(self) is MzMLFile:
                warnings.warn("Could not find any m/z range")

    def _extract_data_file_content(self, meta):

        file_contents = self.vocabulary["MS:1000524"].rchildren().id

        def unique_everseen(it, key):
            memo = set()
            for element in it:
                signature = key(element)
                if signature not in seen:
                    seen.add(signature)
                    yield element

        meta["Data file content"] = {
            "entry_list": [
                {
                    "name": cv.attrib["name"],
                    "ref": cv.attrib[self.environment["cvRef"]],
                    "accession": cv.attrib["accession"],
                }
                for cv in unique_everseen(
                    self._find_xpath(self._XPATHS["sp_cv"]), key=lambda cv: cv.attrib["accession"]
                )
                if cv.attrib["accession"] in file_contents
            ]
        }

    def _extract_instrument(self, meta):

        # Find the instrument config: either directly the instrument element
        # with its attached parameters or a referenceableParamGroup referenced
        # in the instrument
        instrument = self._find_instrument_config()
        manufacturers = self.vocabulary["MS:1000031"].children.id

        # The parameters we want to extract (Instrument Manufacturer will be
        # handled differently later)
        parameters = [
            _CVParameter(
                accession="MS:1000031",
                cv=True,
                name="Instrument",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="MS:1000529",
                cv=True,
                name="Instrument serial number",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
        ]

        # Extract the parameters
        for param in instrument.iterfind("s:cvParam", self.namespace):
            self._extract_cv_params(param, parameters, meta)

        if "Instrument" in meta:
            # Check the instrument name and accession are the same
            term = self.vocabulary[meta["Instrument"]["accession"]]
            if meta["Instrument"]["name"] != term.name:
                msg = "The instrument name in the mzML file ({}) does not correspond to the instrument accession ({})"
                warnings.warn(msg.format(meta["Instrument"]["name"], term.name))
                meta["Instrument"]["name"] = term.name

            # Get the instrument manufacturer
            man = next((p for p in term.rparents() if p.id in manufacturers), term)
            meta["Instrument manufacturer"] = {
                "accession": man.id,
                "name": man.name,
                "ref": man.id.split(":")[0],
            }

        try:  # Get associated software
            param = next(self._find_xpath(self._XPATHS["ic_soft_ref"]))
            soft_ref = param.attrib[self.environment["softwareRef"]]
            self._extract_software(soft_ref, "Instrument", meta)
        except (
            IndexError,
            KeyError,
            StopIteration,
        ):  # Sometimes <Instrument> contains no Software tag
            if "Instrument" in meta:
                instrument = meta["Instrument"]["name"]
            elif "Instrument serial number" in meta:
                instrument = "<{}>".format(meta["Instrument serial number"])
            else:
                instrument = "?"
            warnings.warn("Instrument {} does not have a software tag.".format(instrument))

    def _extract_scan_number(self, meta):
        scan_num = next(self._find_xpath(self._XPATHS["scan_num"]))
        meta["Number of scans"] = {"value": int(scan_num.attrib["count"])}

    def _extract_scan_parameters(self, meta):
        terms = self._scan_parameters()

        for spectrum in self._find_xpath(self._XPATHS["sp"]):
            for location, parameters in six.iteritems(terms):
                xpath = self._XPATHS[location].format(**self.environment)
                # we are extracting from a referenced parameter group
                # so we must retrieve them before being able to extract
                # the CV parameters
                if location.startswith("ref"):
                    params = (
                        self._referenceable_parameters[ref.attrib["ref"]]
                        for ref in spectrum.iterfind(xpath, self.namespace)
                    )
                    elements = (
                        element
                        for param in params
                        for element in param.iterfind("s:cvParam", self.namespace)
                    )
                # we can extract the CV parameters directly
                else:
                    elements = spectrum.iterfind(xpath, self.namespace)

                for element in elements:
                    self._extract_cv_params(element, parameters, meta)

    def _find_instrument_config(self):
        # Get the instrument configuration reference if it exists or None
        ic_ref = next(self._find_xpath(self._XPATHS["ic_ref"]), None)
        # if the configuration exist, find it in the referenceable parameters
        if ic_ref is not None:
            return self._referenceable_parameters[ic_ref.attrib["ref"]]
        # otherwise return the instrument in the instrument list
        else:
            return next(self._find_xpath(self._XPATHS["ic_nest"]))

    @cached_property
    def metadata(self):
        meta = {}

        self._extract_assay_parameters(meta)
        self._extract_instrument(meta)
        self._extract_derived_file(meta)
        self._extract_raw_file(meta)
        self._extract_polarity(meta)
        self._extract_timerange(meta)
        self._extract_mzrange(meta)
        self._extract_scan_number(meta)
        self._extract_scan_parameters(meta)

        if "Spectrum representation" not in meta:
            self._extract_spectrum_representation(meta)
        if "Data file content" not in meta:
            self._extract_data_file_content(meta)

        self._urlize_meta(meta)

        return meta
