"""
Content
-----------------------------------------------------------------------------
This module provides classes for collecting metadata from mzML scans.

About
-----------------------------------------------------------------------------
The mzml2isa parser was created by Tom Lawson (University of Birmingham, UK)
as part of a NERC funded placement at EBI Cambridge in June 2015. Python 3
port and enhancements were carried out by Martin Larralde (ENS Cachan, FR)
in June 2016 during an internship at the EBI Cambridge.

License
-----------------------------------------------------------------------------
GNU General Public License version 3.0 (GPLv3)
"""

import six

from . import (
    __author__,
    __name__,
    __version__,
    __license__,
)

SCAN_XPATHS = {
    'cv': './s:cvParam',
    'scan_cv': './{scanList}/s:scan/s:cvParam',
    'scan_window_cv': './{scanList}/s:scan/{scanWindow}List/{scanWindow}/s:cvParam'
}

class AbstractCollector(object):
    def process_scan(self, scan_elem, env, namespace):
        pass

    def populate_meta(self, metadata_dictionary):
        pass

class Polarity(AbstractCollector):
    def __init__(self):
        self.pos = False
        self.neg = False

    def process_scan(self, elem, env, ns):
        for i in elem.iterfind(SCAN_XPATHS['cv'], ns):
            if i.attrib['accession'] == 'MS:1000130':
                self.pos = True
            if i.attrib['accession'] == 'MS:1000129':
                self.neg = True

    def populate_meta(self, meta):
        if self.pos and self.neg:
            polarity = {'name': "alternating scan", 'ref': '', 'accession': ''}
        elif self.pos:
            polarity = {'name': "positive scan", 'ref': 'MS', 'accession': 'MS:1000130'}
        elif self.neg:
            polarity = {'name': "negative scan", 'ref': 'MS', 'accession': 'MS:1000129'}
        else:
            polarity = {'name': "n/a", 'ref': '', 'accession': ''}

        meta['Scan polarity'] = polarity


def _unitInfo(elem):
    return {
        'name': elem.attrib['unitName'],
        'accession': elem.attrib['unitAccession'],
        'ref': elem.attrib['unitCvRef']
    }

class TimeRange(AbstractCollector):
    """Try to extract the Time range of all the scans.

    Time range consists in the smallest and largest time the successive scans
    were started. The unit (most of the time `minute`) will be extracted as well
    if possible.
    """
    def __init__(self):
        self.minrt = float('+inf')
        self.maxrt = float('-inf')
        self.unit = None

    def process_scan(self, elem, env, ns):
        for i in elem.iterfind(SCAN_XPATHS['scan_cv'].format(**env), ns):
            if i.attrib['accession'] == 'MS:1000016':
                time = float(i.attrib['value'])
                self.minrt = min(time, self.minrt)
                self.maxrt = max(time, self.maxrt)
                if 'unitName' in i.attrib and not self.unit:
                    self.unit = _unitInfo(i)

    def populate_meta(self, meta):
        if self.minrt == float('+inf'):
            return

        minrt = str(round(self.minrt, 4))
        maxrt = str(round(self.maxrt, 4))
        timerange = minrt + '-' + maxrt

        meta['Time range'] = {'value': timerange}
        if self.unit is not None:
            meta['Time range']['unit'] = self.unit

class MzRange(AbstractCollector):
    """Try to extract the m/z range of all scans."""
    def __init__(self):
        self.unit = None
        self.minmz = float('+inf')
        self.maxmz = float('-inf')

    def process_scan(self, elem, env, ns):
        for i in elem.iterfind(SCAN_XPATHS['scan_window_cv'].format(**env), ns):
            if i.attrib['accession'] == 'MS:1000501':
                mz = float(i.attrib['value'])
                self.minmz = min(mz, self.maxmz)
                if 'unitName' in i.attrib and not self.unit:
                    self.unit = _unitInfo(i)
            if i.attrib['accession'] == 'MS:1000500':
                mz = float(i.attrib['value'])
                self.maxmz = max(mz, self.maxmz)

    def populate_meta(self, meta):
        if self.minmz == float('+inf'):
            return

        minmz = str(int(self.minmz))
        maxmz = str(int(self.maxmz))
        mzrange = minmz + '-' + maxmz

        meta['Scan m/z range'] = {'value': mzrange}
        if self.unit is not None:
            meta['Scan m/z range']['unit'] = self.unit

class DataFileContent(AbstractCollector):
    """Extract the `Data file content` from all scans.

    This collector is called only in the case the FileContent xml Element
    contained no actual cvParam elements. This was witnessed in at least
    one file from a Waters instrument.
    """

    def __init__(self, file_contents):
        self.entry_list = []
        self.file_contents = file_contents
        self._memo = set()

    def _seen(self, accession):
        if accession in self._memo:
            return True
        self._memo.add(accession)
        return False

    def process_scan(self, elem, ns):
        for cv in elem.iterfind(SCAN_XPATHS['cv'], ns):
            if cv.attrib['accession'] not in self.file_contents:
                continue
            if self._seen(cv.attrib['accession']):
                continue
            self.entry_list.append({
                'name': cv.attrib['name'],
                'ref': cv.attrib['cvRef'],
                'accession': cv.attrib['accession']
            })

    def populate_meta(self, meta):
        meta['Data file content'] = {'entry_list': self.entry_list}
