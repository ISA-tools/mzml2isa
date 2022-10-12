# coding: utf-8
"""``imzML`` file metadata parser.

About:
    The mzml2isa parser was created by Tom Lawson (University of Birmingham, UK)
    as part of a NERC funded placement at EBI Cambridge in June 2015. Python 3
    port and enhancements were carried out by Martin Larralde (ENS Cachan, FR)
    in June 2016 during an internship at the EBI Cambridge.

License:
    GNU General Public License version 3.0 (GPLv3)
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import copy

import pronto
import pkg_resources

from .mzml import _CVParameter, MzMLFile


class ImzMLFile(MzMLFile):

    _XPATHS = copy.copy(MzMLFile._XPATHS)
    _XPATHS.update(
        {
            "scan_settings": "{root}/s:scanSettingsList/s:scanSettings/s:cvParam",
            "source": "{root}/{instrument}List/{instrument}/s:componentList/s:source/s:cvParam",
            "scan_dimensions": "{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:cvParam",
            "scan_ref": "{root}/s:run/{spectrum}List/{spectrum}/s:referenceableParamGroupRef",
            "ref_param_list": "{root}/s:referenceableParamGroupList/s:referenceableParamGroup",
        }
    )

    _VOCABULARY = pronto.Ontology(
        pkg_resources.resource_stream("mzml2isa", "ontologies/imagingMS.obo"),
        # import_depth=1,
    )

    @classmethod
    def _assay_parameters(cls):
        terms = super(ImzMLFile, cls)._assay_parameters()

        terms["file_content"] = [
            _CVParameter(
                accession="MS:1000525",
                cv=True,
                name="Spectrum representation",
                plus1=True,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000008",
                cv=True,
                name="Universally unique identifier",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000009",
                cv=True,
                name="Binary file checksum type",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000003",
                cv=True,
                name="Ibd binary type",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
        ]

        terms["scan_settings"] = [
            _CVParameter(
                accession="IMS:1000040",
                cv=True,
                name="Linescan sequence",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000041",
                cv=True,
                name="Scan pattern",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000042",
                cv=True,
                name="Max count of pixel x",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000043",
                cv=True,
                name="Max count of pixel y",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000044",
                cv=True,
                name="Max dimension x",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000045",
                cv=True,
                name="Max dimension y",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000046",
                cv=True,
                name="Pixel size x",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000047",
                cv=True,
                name="Pixel size y",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000048",
                cv=True,
                name="Scan type",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000049",
                cv=True,
                name="Line scan direction",
                plus1=False,
                value=False,
                software=False,
                merge=False,
            ),
        ]

        terms["source"] = [
            _CVParameter(
                accession="IMS:1001213",
                cv=True,
                name="Solvent flowrate",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1001211",
                cv=True,
                name="Solvent",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1000202",
                cv=True,
                name="Target material",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
            _CVParameter(
                accession="IMS:1001212",
                cv=True,
                name="Spray voltage",
                plus1=False,
                value=True,
                software=False,
                merge=False,
            ),
        ]

        return terms
