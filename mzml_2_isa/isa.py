import csv
import os
import shutil

class ISA_Tab(object):
    """ Class to hold the ISA_tab components

    Bit clumsy at the moment. But just did it this way to show how it could be done.

    """
    def __init__(self, metalist, out_dir, name, assay_file = False,investigation_file = False):
        '''
        # Class to update and ISA-Tab assay file
        '''
        self.out_dir = os.path.join(out_dir, name)
        self.name = name
        self.platform = {}
        self.assay_file_name = 'a_'+self.name+'_metabolite_profiling_mass_spectrometry.txt'
        self.study_file_name = 's_'+self.name+'.txt'
        self.investigation_file_name = 'i_'+self.name+'.txt'

        dirname = os.path.dirname(os.path.realpath(__file__))
        self.default_path = os.path.join(dirname, "default")

        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

        self.check_assay_name(metalist)

        self.create_assay(assay_file, metalist)
        self.create_investigation(investigation_file, metalist)
        self.create_study()
        #self.existing_assay(isa_tab_assay_file, metalist)

    def check_assay_name(self, metalist):
        instruments = []
        accession = []
        for meta in metalist:
            instruments.append(meta['Parameter Value[Instrument]']['name'])
            accession.append(meta['Parameter Value[Instrument]']['accession'])

        if len(set(instruments)) > 1:
            print "Warning: More than one instrument platform used. Metabolights by default divides assays based on" \
                  " platform. For convenience here though only one assay file will be created including all files, " \
                  " the investigation file though will detail the most common platform used" \

        # get most common item in list
        c_name = max(set(instruments), key=instruments.count)
        c_accession = max(set(accession), key=accession.count)

        self.platform = {
            'name':c_name,
            'accession':c_accession
        }

    def create_investigation(self, investigation_file, metalist):
        #
        #
        if not investigation_file:
            print "use the default ideal file"
            dirname = os.path.dirname(os.path.realpath(__file__))
            path = os.path.join(dirname, "default")
            investigation_file = os.path.join(path, 'i_investigation.txt')

        new_i_path = os.path.join(self.out_dir,"i_investigation.txt")

        with open(investigation_file, "rb") as i_in:
            with open(new_i_path, "w") as i_out:
                for l in i_in:

                    l = l.replace('STUDY_IDENTIFIER', self.name)
                    l = l.replace('STUDY_FILE_NAME', self.study_file_name)
                    l = l.replace('ASSAY_FILE_NAME', self.assay_file_name)
                    l = l.replace('NAME_OF_MS_PLATFORM', self.platform['name'])
                    l = l.replace('MS_ACCESSION_NUMBER', self.platform['name'])

                    i_out.write(l)


    def create_study(self):

        src_file = os.path.join(self.default_path, "s_mzML_parse.txt")
        shutil.copy(src_file, self.out_dir)
        dst_file = os.path.join(self.out_dir, "s_mzML_parse.txt")
        out_file = os.path.join(self.out_dir, self.study_file_name)
        os.rename(dst_file, out_file)

    def create_assay(self,isa_tab_assay_file, metalist):

        # Either take in 'ideal' file format or get user provided assay file
        if isa_tab_assay_file:
            print "use user assay file"

        else:
            print "use the default ideal file"
            assay_file = os.path.join(self.default_path, 'a_mzML_parse.txt')

        # Get location of the mass spectrometry section
        with open(assay_file, 'rb') as isa_orig:

            for index, line in enumerate(isa_orig):
                line = line.rstrip()
                line = line.replace('"', '')

                if index == 0:

                    headers_l = line.split('\t')

                elif index == 1:

                    standard_row = line.split('\t')
                    mass_protocol_idx = standard_row.index("Mass spectrometry")
                    mass_end_idx = standard_row.index("Metabolite identification")
                    data_tran_idx = standard_row.index("Data transformation")
                    break

        pre_headers = headers_l[:mass_protocol_idx+1]
        mass_headers = headers_l[mass_protocol_idx+1:mass_end_idx]
        post_headers = headers_l[mass_end_idx:]

        pre_row = standard_row[:mass_protocol_idx+1]
        mass_row = standard_row[mass_protocol_idx+1:mass_end_idx]
        post_row = standard_row[mass_end_idx:]

        self.new_mass_row = [""]*len(mass_headers)

        full_row = []

        #indices = [i for i, val in enumerate(mass_headers) if val == '"Parameter Value[Ion source]"']
        # Get columns that are going to be added
        for file_meta in metalist:

            for key, value in file_meta.items():
                # if key is an entry list it means this means there can be more than one of this meta type
                # This will check all meta data where there might be multiple columns of the same data e.g.
                # data file content
                if "entry_list" in value.keys():
                    for list_item in value.values():
                        indices = [i for i, val in enumerate(mass_headers) if val == key]
                        # needs to be in reverse order
                        indices = indices[::-1]
                        for meta_id, meta_val in list_item.items():
                            try:
                                main = indices.pop()
                            except IndexError as e:
                                pass
                            else:
                                self.write_row(main, meta_val)
                else:
                    try:
                        main = mass_headers.index(key)
                    except ValueError as e:
                        pass
                    else:
                        self.write_row(main, value)


            full_row.append(pre_row+self.new_mass_row+post_row)

        headers_l, full_row = self.remove_blank_columns(mass_protocol_idx, mass_end_idx, full_row,headers_l)

        with open(os.path.join(self.out_dir,self.assay_file_name), 'wb') as new_file:
            writer = csv.writer(new_file, quotechar='"', quoting=csv.QUOTE_ALL, delimiter='\t')
            writer.writerow(headers_l)

            data_tran_idx = headers_l.index("Derived Spectral Data File")-2 # need to add in data-transformation info

            for row in full_row:
                row[data_tran_idx] = "Data transformation"
                writer.writerow(row)

    def remove_blank_columns(self,start,end,full_row,headers_l):
        delete_cols = []
        update_row = []
        for i in range(start,end-3):
            # check if a column is empty
            column = [col[i] for col in full_row]
            if column.count('') == len(full_row):
                delete_cols.append(i)

        for row in full_row:
            # pythons way of deleting multiple entries of a list. So much more hassle than numpy/pandas....
            row[:] = [ item for i, item in enumerate(row) if i not in delete_cols ]
            update_row.append(row)

        update_headers = []
        update_headers[:] = [ item for i, item in enumerate(headers_l) if i not in delete_cols ]

        return update_headers, update_row

    def write_row(self,main, meta_val):

        try:
            name = meta_val['name']
        except KeyError as e:
            pass
        else:
            self.new_mass_row[main] = name
            main = main+1

        try:
            accession = meta_val['accession']
        except KeyError as e:
            pass
        else:
            self.new_mass_row[main] = "MS"
            main = main+1
            self.new_mass_row[main] = accession
            main = main+1

        try:
            value = meta_val['value']
        except KeyError as e:
            pass
        else:
            self.new_mass_row[main] = value





