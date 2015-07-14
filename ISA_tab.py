import csv
import os

class ISA_tab(object):
    """ Class to hold the ISA_tab components

    Bit clumsy at the moment. But just did it this way to show how it could be done.

    """
    def __init__(self, metalist, isa_tab_assay_file = False,):
        '''
        # Class to update and ISA-Tab assay file
        '''
        self.get_file_structure(isa_tab_assay_file, metalist)
        #self.existing_assay(isa_tab_assay_file, metalist)

    def get_file_structure(self,isa_tab_assay_file, metalist):

        # Either take in 'ideal' file format or get user provided assay file
        if isa_tab_assay_file:
            print "use user assay file"

        else:
            print "use the default ideal file"
            dirname = os.path.dirname(os.path.realpath(__file__))
            testing_path = os.path.join(dirname, "testing")
            assay_file = os.path.join(testing_path, 'a_ideal.txt')

        # Get location of the mass spectrometry section

        with open(assay_file, 'rb') as isa_orig:

            for index, line in enumerate(isa_orig):
                line = line.replace('"', '')
                if index == 0:

                    headers_l = line.split('\t')

                elif index == 1:

                    standard_row = line.split('\t')
                    mass_protocol_idx = standard_row.index('Mass spectrometry')
                    adj = mass_protocol_idx+1
                    break

            c = 1
            for i in headers_l[mass_protocol_idx+1:]:
                if i == "Protocol REF":
                    mass_end_idx = c+mass_protocol_idx
                    break
                c += 1

            pre_headers = headers_l[:mass_protocol_idx+1]
            mass_headers = headers_l[mass_protocol_idx+1:mass_end_idx]
            post_headers = headers_l[mass_end_idx:]

            pre_row = standard_row[:mass_protocol_idx+1]
            mass_row = standard_row[mass_protocol_idx+1:mass_end_idx]
            post_row = standard_row[mass_end_idx:]

        print "pre headers", pre_headers
        print "mass headers", mass_headers
        print "post headers", post_headers

        #self.new_mass_row = [""]*len(mass_headers)
        self.new_mass_row = [""]*len(mass_headers)

        full_row = []

        indices = [i for i, val in enumerate(mass_headers) if val == "Parameter Value[Ion source]"]
        # Get columns that are going to be added
        for file_meta in metalist:

            for key, value in file_meta.items():
                # if key is an entry list it means this means there can be more than one of this meta type
                # This will check all meta data where there might be multiple columns of the same data e.g.
                # data file content
                if "entry_list" in value.keys():
                    for list_item in value.values():
                        indices = [i for i, val in enumerate(mass_headers) if val == key]
                        for meta_id, meta_val in list_item.items():
                            try:
                                main = indices.pop()
                                self.write_row(main, meta_val)
                            except IndexError as e:
                                print e
                else:
                    try:
                        main = mass_headers.index(key)
                        self.write_row(main, value)
                    except ValueError as e:
                        print e

            print mass_headers
            print self.new_mass_row
            full_row.append(pre_row+self.new_mass_row+post_row)

        headers_l, full_row = self.remove_blank_columns(mass_protocol_idx,mass_end_idx,full_row,headers_l)

        with open("isa_new.txt", 'wb') as new_file:
            writer = csv.writer(new_file)
            writer.writerow(headers_l)

            for row in full_row:
                print row
                writer.writerow(row)

    def remove_blank_columns(self,start,end,full_row,headers_l):
        delete_cols = []
        update_row = []
        for i in range(start,end-2):
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
            self.new_mass_row[main] = name
            main = main+1
        except KeyError as e:
            print e

        try:
            accession = meta_val['accession']
            self.new_mass_row[main] = "MS"
            main = main+1
            self.new_mass_row[main] = accession
            main = main+1
        except KeyError as e:
            print e

        try:
            value = meta_val['value']
            self.new_mass_row[main] = value
        except KeyError as e:
            print e


