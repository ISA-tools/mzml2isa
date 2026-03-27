# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import operator
import os
import re
import tarfile
import unittest
import warnings

import parameterized
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r"pkg_resources is deprecated as an API\.",
        category=UserWarning,
    )
    import fs
    import fs.errors
    import fs.path
    from fs.archive.tarfs import TarFS
    from fs.tempfs import TempFS
    from fs.copy import copy_fs

from mzml2isa.mzml import MzMLFile

from ._utils import HTTPDownloader


def _local_study_ids(data_root):
    with fs.open_fs(data_root) as data_fs:
        with open(data_fs.getsyspath("MTBLS-no-binary.tar.xz"), "rb") as handle:
            with TarFS(handle) as archive:
                return archive.listdir("/")


class TestRemoteMTBLS(unittest.TestCase):

    # --- Setup / Teardown --------------------------------------------------

    @classmethod
    def setUpClass(cls):
        try:
            cls.ebifs = HTTPDownloader(
                fs.open_fs(
                    "ftp://ftp.ebi.ac.uk/pub/databases/metabolights/studies/public/"
                )
            )
            cls.ebifs.listdir("/")
        except (fs.errors.CreateFailed, fs.errors.RemoteConnectionError):
            raise unittest.SkipTest("cannot connect to the EBI FTP")

    def setUp(self):
        self.tmpfs = fs.open_fs("temp://")

    def tearDown(self):
        self.tmpfs.close()

    @classmethod
    def tearDownClass(cls):
        cls.ebifs.close()

    # --- Generic test case  ------------------------------------------------

    def _test_study(self, study_id, instrument=None):

        # open the study directory and find the smallest mzML file
        with self.ebifs.opendir(study_id) as study_fs:
            candidates = []
            for path in study_fs.walk.files(filter=["*.mzML", "*.mzml"]):
                info = study_fs.getinfo(path, namespaces=["details"])
                size = getattr(info, "size", None)
                if size is None:
                    size = info.raw.get("details", {}).get("size")
                candidates.append((size if size is not None else float("inf"), path))

            if not candidates:
                raise unittest.SkipTest(
                    "study {} does not currently expose any mzML files".format(study_id)
                )

            _, path = min(candidates, key=operator.itemgetter(0))

            # open and parse mzML file
            mzml_file = MzMLFile(study_fs, path)
            self.assertIsNotNone(mzml_file.tree)
            self.assertIsNotNone(mzml_file.metadata)

            # check instrument
            if instrument is not None:
                self.assertEqual(mzml_file.metadata["Instrument"]["name"], instrument)

    # --- Metabolights studies -----------------------------------------------

    def test_MTBLS126(self):
        self._test_study("MTBLS126", instrument="LTQ Orbitrap XL")

    def test_MTBLS267(self):
        self._test_study("MTBLS267", instrument="LTQ Orbitrap")

    def test_MTBLS341(self):
        self._test_study("MTBLS341", instrument="micrOTOF-Q")


class TestLocalMTBLS(unittest.TestCase):

    # --- Setup / Teardown --------------------------------------------------

    _DATA_ROOT = os.path.join(__file__, os.pardir, "data")

    @classmethod
    def _get_json_meta_results(cls, data_fs):
        results = {}
        with tarfile.open(data_fs.getsyspath("MTBLS-json-meta.tar.xz"), mode="r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile() or not member.name.endswith(".json"):
                    continue
                match = re.match(r"^(MTBLS\d*)-(.*).json", fs.path.basename(member.name))
                if match is None:
                    continue
                id_, name = match.groups()
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                with extracted as f:
                    results[id_] = json.load(f)
        return results

    @classmethod
    def setUpClass(cls):
        cls._DATA_FS = fs.open_fs(cls._DATA_ROOT)
        cls._MZML_FS = TempFS()
        with open(cls._DATA_FS.getsyspath("MTBLS-no-binary.tar.xz"), "rb") as handle:
            with TarFS(handle) as archive:
                copy_fs(archive, cls._MZML_FS)
        cls.results_original = cls._get_json_meta_results(cls._DATA_FS)

    @classmethod
    def tearDownClass(cls):
        cls._MZML_FS.close()
        cls._DATA_FS.close()

    # --- Parameterised test case  ------------------------------------------

    @parameterized.parameterized.expand(
        _local_study_ids(_DATA_ROOT),
        name_func=lambda f, n, p: str("{}_{}".format(f.__name__, p.args[0])),
    )
    def test(self, id_):
        with self._MZML_FS.opendir(id_) as study_fs:
            path = next(study_fs.walk.files(filter=["*.mzml", "*.mzML"]))
            result = MzMLFile(study_fs, path).metadata
        expected = self.results_original[id_]

        keys = (
            "Data Transformation Name",
            "Data Transformation software",
            "Data Transformation software version",
            "Detector",
            "Inlet Type",
            "Instrument",
            "Instrument manufacturer",
            "Instrument software",
            "Ion source",
            "MS Assay Name",
            "Mass analyzer",
            "Native spectrum identifier format",
            "Number of scans",
            "Sample Name",
            "Scan m/z range",
            "Scan polarity",
            #"Spectrum representation"
        )

        for key in filter(expected.__contains__, keys):
            self.assertEqual(
                result[key],
                expected[key],
                'parsed "{}" differs from the expected value'.format(key),
            )

        if "Derived Spectral Data File" in expected:
            self.assertEqual(
                result["Derived Spectral Data File"]["entry_list"][0]["value"],
                expected["Derived Spectral Data File"]["entry_list"][0]["value"],
            )

        if "Instrument serial number" in expected:
            self.assertEqual(
                result["Instrument serial number"]["value"],
                expected["Instrument serial number"]["value"],
                'parsed "Instrument serial number" differs from the expected valued',
            )


if __name__ == "__main__":
    unittest.main()
