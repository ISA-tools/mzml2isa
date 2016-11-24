"""
Content
-----------------------------------------------------------------------------
This module contains a single class, ISA_Tab, which is used to dump a list
of mzML.meta or imzML.meta dictionaries to ISA files.

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
from __future__ import absolute_import

import os
import csv
import sys
import functools

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from . import (
    __author__,
    __name__,
    __version__,
    __license__
)
from .utils import (
    PermissiveFormatter,
    TEMPLATES_DIR,
)


class ISA_Tab(object):
    """Class to export a list of mzML or imzML metadata dictionnaries to ISA-Tab files

    Attributes:
        usermeta (dict): a dictionary containing metadata defined
            by the user, such as "Study Publication" or "Submission Date". Defaults
            to None.
        isa_env (dict): a dictionary containing various environment
            variables associated with the current ISA_Tab object (such as
            'Study file name', 'Written assays', etc.)
    """

    def __init__(self, out_dir, name, **kwargs):
        """Setup the environments and the directories

        Arguments:
            out_dir (str): the path to the output directory
            name (str): the name of the *omics study to generate

        Keyword Arguments:
            usermeta (dict, optional): a dictionary containing metadata defined
                by the user, such as "Study Publication" or "Submission Date".
                [default: None]
            template_directory (str, optional): the path to a directory containing
                custom ISA-Tab templates. No all templates are required, so if for instance
                only your "a_imzML.txt" is non-standard, then you only have to have a new
                "a_imzML.txt" in your custom template directory. If None, the uses the
                ones shipping with mzml2isa, compatible with MetaboLights [default: None]
        """
        usermeta = kwargs.get('usermeta', None)
        template_directory = kwargs.get('template_directory', None)

        # Create one or several study files / one or several study section in investigation
        self.usermeta = usermeta or {}
        self.isa_env = {
            'out_dir': os.path.join(out_dir, name),
            'Study Identifier':  name,
            'Study file name': 's_{}.txt'.format(name),
            'Assay polar file name': 'a_{}_{{}}_metabolite_profiling_mass_spectrometry.txt'.format(name),
            'Assay file name': 'a_{}_metabolite_profiling_mass_spectrometry.txt'.format(name),
            'default_path': TEMPLATES_DIR,
            'template_path': template_directory or TEMPLATES_DIR,
            'Technology type': [],
            'Measurement type': [],
            'Written assays': [],
            'mzML measurement': {'name': 'metabolite profiling', 'accession':'http://purl.obolibrary.org/obo/OBI_0000366', 'ref':'OBI' },
            'mzML technology': {'name': 'mass spectrometry', 'accession':'http://purl.obolibrary.org/obo/OBI_0000470', 'ref':'OBI' },

        }

        self.isa_env['Converter'] = __name__
        self.isa_env['Converter version'] = __version__

    def write(self, metalist, datatype, **kwargs):
        """Generate and write the ISA files

        Arguments:
            metalist (list): a list of mzml or imzml metadata dictionaries
            datatype (str): the datatype of the study (either 'mzML' or 'imzML')

        Keyword Arguments:
            split (bool, optional): a boolean stating if assay files should be split
                based on their polarities. [default: True]
        """
        split=kwargs.get('split', True)

        self.isa_env['Platform'] = [ next((meta['Instrument'] for meta in metalist if 'Instrument' in meta), '') ]

        if not os.path.exists(self.isa_env['out_dir']):
            os.makedirs(self.isa_env['out_dir'])

        h,d = self.make_assay_template(metalist, datatype)

        self.create_assay(metalist, h, d, split=split)
        self.create_study(metalist,datatype)
        self.create_investigation(metalist, datatype)

    def make_assay_template(self, metalist, datatype):
        """Generate the assay template rows

        Parameters:
            metalist (list): a list of mzml or imzml metadata dictionaries
            datatype (str): the datatype of the study (either 'mzML' or 'imzML')

        Returns
            tuple: a tuple containg the list containing the assay headers row
                and the list containing the assay data row based on the cardinality
                of elements in the metalist
        """

        template_a_path = os.path.join(self.isa_env['template_path'], 'a_{}.txt'.format(datatype))
        if not os.path.exists(template_a_path):
            template_a_path = os.path.join(self.isa_env['template_path'], 'a_{}.txt'.format(datatype))

        with open(template_a_path, 'r') as a_in:
            headers, data = [x.strip().replace('"', '').split('\t') for x in a_in.readlines()]

        i = 0
        while i < len(headers):
            header, datum = headers[i], data[i]

            if '{{' in datum and 'Term' not in header:
                entry_list = metalist[0][self.unparameter(header)]['entry_list']
                hsec, dsec = (headers[i:i+3], data[i:i+3]) \
                                if headers[i+1] == "Term Source REF" \
                                else (headers[i:i+1], data[i:i+1])

                headers[:] = headers[:i] + headers[i+len(hsec):] # Remove the sections we are
                data[:] =    data[:i]    +    data[i+len(dsec):] # going to format and insert

                for n in reversed(range(len(entry_list))):
                    for (h,d) in zip(reversed(hsec),reversed(dsec)):
                        headers.insert(i, h)
                        data.insert(i, d.format(n))

            i+= 1

        return headers, data

    def create_assay(self, metalist, headers, data, **kwargs):
        """Write the assay file

        Arguments:
            metalist (list): a list of mzml or imzml metadata dictionaries
            datatype (str): the datatype of the study (either 'mzML' or 'imzML')
            headers (list): the list containing the assay headers row

        Keyword Arguments:
            split (bool, optional): a boolean stating if assay files should be split
                based on their polarities. [default: True]
        """
        split = kwargs.get('split', True)
        fmt = PermissiveFormatter()

        if split:
            polarities = set( meta['Scan polarity']['name'] for meta in metalist ) \
                            if 'Scan polarity' in metalist[0] else ['nopolarity']
        else:
            polarities = ['nosplit']

        new_a_path = os.path.join(self.isa_env['out_dir'], self.isa_env['Assay file name']) \
                        if len(polarities)==1 \
                        else os.path.join(self.isa_env['out_dir'], self.isa_env['Assay polar file name'])

        for polarity in polarities:

            csv_wopen = functools.partial(open, mode='w', newline='') \
                        if sys.version_info[0]==3 \
                        else functools.partial(open, mode='wb')

            with csv_wopen(new_a_path.format(polarity[:3].upper())) as a_out:

                self.isa_env['Written assays'].append(os.path.basename(new_a_path.format(polarity[:3].upper())))
                self.isa_env['Technology type'].append(self.isa_env['mzML technology'])
                self.isa_env['Measurement type'].append(self.isa_env['mzML measurement'])

                writer=csv.writer(a_out, quotechar='"', quoting=csv.QUOTE_ALL, delimiter='\t')
                writer.writerow(headers)

                for meta in ( x for x in metalist if x['Scan polarity']['name']==polarity ):
                    writer.writerow( [ fmt.vformat(x, None, ChainMap(meta, self.usermeta)) for x in data] )

    def create_study(self, metalist, datatype):
        """Write the study file

        Arguments:
            metalist (:obj:`list`): a list of mzml or imzml metadata dictionaries
            datatype (:obj:`str`): the datatype of the study (either 'mzML' or 'imzML')
        """
        template_s_path = os.path.join(self.isa_env['template_path'], 's_{}.txt'.format(datatype))
        if not os.path.exists(template_s_path):
            template_s_path = os.path.join(self.isa_env['default_path'], 's_{}.txt'.format(datatype))

        new_s_path = os.path.join(self.isa_env['out_dir'], self.isa_env['Study file name'])

        fmt = PermissiveFormatter()

        with open(template_s_path, 'r') as s_in:
            headers, data = s_in.readlines()

        with open(new_s_path, 'w') as s_out:
            s_out.write(headers)
            for meta in metalist:
                s_out.write(fmt.vformat(data, None, ChainMap(meta, self.usermeta)))

    def create_investigation(self, metalist, datatype):
        """Write the investigation file

        Arguments:
            metalist (:obj:`list`): a list of mzml or imzml metadata dictionaries
            datatype (:obj:`str`): the datatype of the study (either 'mzML' or 'imzML')
        """
        template_i_path = os.path.join(self.isa_env['template_path'], 'i_{}.txt'.format(datatype))
        if not os.path.exists(template_i_path):
            template_i_path = os.path.join(self.isa_env['default_path'], 'i_{}.txt'.format(datatype))

        new_i_path = os.path.join(self.isa_env['out_dir'], 'i_Investigation.txt')

        meta = metalist[0]
        fmt = PermissiveFormatter()

        chained = ChainMap(self.isa_env, meta, self.usermeta)

        with open(template_i_path, 'r') as i_in:
            with open(new_i_path, "w") as i_out:
                for l in i_in:

                    if "{{" in l:
                        l, value = l.strip().split('\t')
                        label = value[3:].split('[')[0]

                        if label in chained:

                            for k in range(len(chained[label])):
                                l = '\t'.join([l, value.format(k)])
                            l += '\n'
                        else:
                            l = "\t".join([l, '\"\"', '\n'])

                    l = fmt.vformat(l, None, chained)
                    i_out.write(l)

    @staticmethod
    def unparameter(string):
        """Extract string 's' from 'Parameter Value[s]'

        Arguments:
            string (str): full string

        Return:
            str: the extracted substring
        """
        return string.replace('Parameter Value[', '').replace(']', '')
