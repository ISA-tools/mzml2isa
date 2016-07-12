import string
import os

import csv
import sys

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

import mzml2isa


class ISA_Tab(object):

    def __init__(self, out_dir, name, usermeta=None):

        # Create one or several study files / one or several study section in investigation

        dirname = os.path.dirname(os.path.realpath(__file__))
        self.usermeta = usermeta or {}
        self.isa_env = {
            'out_dir': os.path.join(out_dir, name),
            'Study Identifier':  name,
            'Study file name': 's_{}.txt'.format(name),
            'Assay polar file name': 'a_{}_{{}}_metabolite_profiling_mass_spectrometry.txt'.format(name),
            'Assay file name': 'a_{}_metabolite_profiling_mass_spectrometry.txt'.format(name),
            'default_path': os.path.join(dirname, 'default'),
            'Technology type': [],
            'Measurement type': [],
            'Written assays': [],
            'mzML measurement': {'name': 'metabolite profiling', 'accession':'http://purl.obolibrary.org/obo/OBI_0000366', 'ref':'OBI' },
            'mzML technology': {'name': 'mass spectrometry', 'accession':'http://purl.obolibrary.org/obo/OBI_0000470', 'ref':'OBI' },

        }

        self.isa_env['Converter'] = mzml2isa.__name__
        self.isa_env['Converter version'] = mzml2isa.__version__

    def write(self, metalist, datatype, split=True):

        self.isa_env['Platform'] = [ next((meta['Instrument'] for meta in metalist if 'Instrument' in meta), '') ]

        if not os.path.exists(self.isa_env['out_dir']):
            os.makedirs(self.isa_env['out_dir'])

        h,d = self.make_assay_template(metalist, datatype)

        self.create_assay(metalist, h, d, split)
        self.create_study(metalist,datatype)
        self.create_investigation(metalist, datatype)

    def make_assay_template(self, metalist, ext):

        template_a_path = os.path.join(self.isa_env['default_path'], 'a_{}.txt'.format(ext))

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

    def create_assay(self, metalist, headers, data, split=True):
        fmt = PermissiveFormatter()

        if split:
            polarities = set( meta['Scan polarity']['value'] for meta in metalist ) \
                            if 'Scan polarity' in metalist[0].keys() else ['nopolarity']
        else:
            polarities = ['nosplit']

        new_a_path = os.path.join(self.isa_env['out_dir'], self.isa_env['Assay file name']) \
                        if len(polarities)==1 \
                        else os.path.join(self.isa_env['out_dir'], self.isa_env['Assay polar file name'])

        for polarity in polarities:
            with open(new_a_path.format(polarity[:3].upper()), 'w') as a_out:

                self.isa_env['Written assays'].append(os.path.basename(new_a_path.format(polarity[:3].upper())))
                self.isa_env['Technology type'].append(self.isa_env['mzML technology'])
                self.isa_env['Measurement type'].append(self.isa_env['mzML measurement'])

                writer=csv.writer(a_out, quotechar='"', quoting=csv.QUOTE_ALL, delimiter='\t')
                writer.writerow(headers)

                for meta in ( x for x in metalist if x['Scan polarity']['value']==polarity ):
                    writer.writerow( [ fmt.vformat(x, None, ChainMap(meta, self.usermeta)) for x in data] )

    def create_study(self, metalist, datatype):

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
        investigation_file = os.path.join(self.isa_env['default_path'], 'i_{}.txt'.format(datatype))
        new_i_path = os.path.join(self.isa_env['out_dir'], 'i_Investigation.txt')

        meta = metalist[0]
        fmt = PermissiveFormatter()

        chained = ChainMap(self.isa_env, meta, self.usermeta)

        with open(investigation_file, 'r') as i_in:
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
        return string.replace('Parameter Value[', '').replace(']', '')

class PermissiveFormatter(string.Formatter):
    """A formatter that replace wrong and missing key with a blank."""
    def __init__(self, missing='', bad_fmt=''):
        self.missing, self.bad_fmt=missing, bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val=super(PermissiveFormatter, self).get_field(field_name, args, kwargs)
        except (KeyError, AttributeError, IndexError, TypeError):
            val=None,field_name
        return val

    def format_field(self, value, spec):
        # handle an invalid format
        if value==None: return self.missing
        try:
            return super(PermissiveFormatter, self).format_field(value, spec)
        except ValueError:
            if self.bad_fmt is not None: return self.bad_fmt
            else: raise
