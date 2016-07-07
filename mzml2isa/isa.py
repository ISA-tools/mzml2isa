import string
import os
import collections
import csv



class ISA_Tab(object):

    def __init__(self, out_dir, name):

        # Create one or several study files / one or several study section in investigation

        dirname = os.path.dirname(os.path.realpath(__file__))
        self.isa_env = {
            'out_dir': os.path.join(out_dir, name),
            'study_identifier':  name,
            'study_file_name': 's_{}.txt'.format(name),
            'assay_file_name': 'a_{}_metabolite_profiling_mass_spectrometry.txt'.format(name),
            'default_path': os.path.join(dirname, 'default'),
            'platform': {},
        }


    def write(self, metalist, datatype):

        if not os.path.exists(self.isa_env['out_dir']):
            os.makedirs(self.isa_env['out_dir'])

        h,d = self.make_assay_template(metalist, datatype)

        #self.create_investigation(metalist, datatype)
        self.create_study(metalist,datatype)
        self.create_assay(metalist, h, d)

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

        print(data)

        """
        if '{{' in data[i] and "Term" not in header:                            # Handle headers & data sections where
                                                                                # several values are accepted: sections are
            entry_list = metalist[0][self.unparameter(header)]['entry_list']    # duplicated and properly formatted
            hsec, dsec = (headers[i:i+3], data[i:i+3]) \
                            if headers[i+1] == "Term Source REF" \
                            else (headers[i:i+1], data[i:i+1])

            if len(entry_list)==1:
                data [i:i+len(dsec)] = [d.format(0) for d in dsec]

            else:
                for k in range(len(entry_list)):
                    if k==0:
                        headers = headers[:i+len(hsec)] + hsec                        + headers[i+len(hsec):]
                        data    = data[:i+len(hsec)]    + [d.format(k) for d in dsec] + data[i+len(dsec):]
                    else:
                        headers = headers[:i+k*len(hsec)] + hsec                        + headers[i+(k+1)*len(hsec):]
                        data    = data[:i+k*len(hsec)]    + [d.format(k) for d in dsec] + data[i+(k+1)*len(dsec):]
        """


        return headers, data

    def create_assay(self, metalist, headers, data):
        #template_a_path = os.path.join(self.isa_env['default_path'], 'a_imzML_parse.txt')
        new_a_path = os.path.join(self.isa_env['out_dir'], self.isa_env['assay_file_name'])

        fmt = PermissiveFormatter()

        with open(new_a_path, 'w') as a_out:

            writer=csv.writer(a_out, quotechar='"', quoting=csv.QUOTE_ALL, delimiter='\t')
            writer.writerow(headers)

            for meta in metalist:
                writer.writerow( [ fmt.vformat(x, None, meta) for x in data] )

    def create_study(self, metalist, datatype):

        print(self.isa_env['out_dir'])

        template_s_path = os.path.join(self.isa_env['default_path'], 's_{}.txt'.format(datatype))
        new_s_path = os.path.join(self.isa_env['out_dir'], self.isa_env['study_file_name'])

        fmt = PermissiveFormatter()

        with open(template_s_path, 'r') as s_in:
            headers, data = s_in.readlines()

        with open(new_s_path, 'w') as s_out:
            s_out.write(headers)
            for meta in metalist:
                s_out.write(fmt.vformat(data, None, meta))

    def create_investigation(self, metalist):
        investigation_file = os.path.join(self.isa_env['default_path'], '')
        new_i_path = os.path.join(self.isa_env['out_dir'], 'i_Investigation.txt')

        meta = metalist[0]
        fmt = PermissiveFormatter()

        with open(investigation_file, 'r') as i_in:
            with open(new_i_path, "w") as i_out:
                for l in i_in:

                    ## FORMAT SECTIONS WHERE MORE THAN ONE VALUE IS ACCEPTED
                    if l.startswith('Study Person'):
                        person_row = l.strip().split('\t')
                        l = person_row[0]
                        for person in meta['contacts']:
                            l +=  '\t' + fmt.format(person_row[1], study_contact=person)
                        l += '\n'

                    l = l.format(**self.isa_env, **meta).format()
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
        except (KeyError, AttributeError, IndexError):
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
