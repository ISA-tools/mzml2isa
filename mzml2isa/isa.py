"""
The mzml2isa parse was created by Tom Lawson (University of Birmingham). As part of a NERC funded placement at EBI
Cambridge in June 2015.

Birmingham supervisor: Prof Mark Viant
Help provided from  Reza Salek ‎[reza.salek@ebi.ac.uk]‎‎, Ken Haug ‎[kenneth@ebi.ac.uk]‎ and Christoph Steinbeck
‎[christoph.steinbeck@gmail.com]‎ at the EBI Cambridge.
-------------------------------------------------------
"""

import csv
import os
import sys
import shutil

from mzml2isa.versionutils import RMODE, WMODE

class ISA_Tab(object):
    """ Class to create an ISA-Tab structure based on a python meta dictionary generated from the mzMLmeta class.

    Uses a default ISA-Tab found in folder ./default created using the ISA-Tab configeration tool.

    Creates a new investigation, study and assay file based on the meta information.

    """
    def __init__(self, metalist, out_dir, name):
        """ **Constructor**: Setup the xpaths and terms. Then run the various extraction methods

        :param list metalist: list of dictionaries containing mzML meta information
        :param str out_dir: Pth to out directory
        :param str name: Study identifier name
        """
        print("Parse mzML meta information into ISA-Tab structure")

        # Setup the instance variables
        self.out_dir = os.path.join(out_dir, name)
        self.name = name
        self.platform = {}
        self.assay_file_name = 'a_'+self.name+'_metabolite_profiling_mass_spectrometry.txt'
        self.study_file_name = 's_'+self.name+'.txt'
        self.investigation_file_name = 'i_'+self.name+'.txt'

        dirname = os.path.dirname(os.path.realpath(__file__))
        self.default_path = os.path.join(dirname, "default")

        # create the new out dir
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

        # Check what instrument to use for the platform used to desribe the assay
        self.check_assay_name(metalist)

        # Create a new assay file based on the relevant meta information
        self.create_assay(metalist)

        # Create a new investigation file
        self.create_investigation()

        # Create a new study file (will just be copy of the default)
        self.create_study()


    def check_assay_name(self, metalist):
        """ Check what instrument to use for the platform used to desribe the assay

        :param list metalist: list of dictionaries containing mzML meta information
        """
        instruments = []
        accession = []
        for meta in metalist:
            instruments.append(meta['Parameter Value[Instrument]']['name'])
            accession.append(meta['Parameter Value[Instrument]']['accession'])

        if len(set(instruments)) > 1:
            print("Warning: More than one instrument platform used. Metabolights by default divides assays based on" \
                  " platform. For convenience here though only one assay file will be created including all files, " \
                  " the investigation file though will detail the most common platform used" \
                  )

        # get most common item in list
        c_name = max(set(instruments), key=instruments.count)
        c_accession = max(set(accession), key=accession.count)

        self.platform = {
            'name':c_name,
            'accession':c_accession
        }

    def create_investigation(self):
        """ Create the investigation file   """
        dirname = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(dirname, "default")
        investigation_file = os.path.join(path, 'i_Investigation.txt')

        new_i_path = os.path.join(self.out_dir,"i_Investigation.txt")

        with open(investigation_file, RMODE) as i_in:
            with open(new_i_path, "w") as i_out:
                for l in i_in:
                    l = l.replace('STUDY_IDENTIFIER', self.name)
                    l = l.replace('STUDY_FILE_NAME', self.study_file_name)
                    l = l.replace('ASSAY_FILE_NAME', self.assay_file_name)
                    l = l.replace('NAME_OF_MS_PLATFORM', self.platform['name'])
                    l = l.replace('MS_ACCESSION_NUMBER', self.platform['name'])
                    i_out.write(l)

    def create_study(self):
        """ Create the study file   """
        # src_file = os.path.join(self.default_path, "s_mzML_parse.txt")
        # shutil.copy(src_file, self.out_dir)
        # dst_file = os.path.join(self.out_dir, "s_mzML_parse.txt")
        # out_file = os.path.join(self.out_dir, self.study_file_name)
        # os.rename(dst_file, out_file)

        dirname = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(dirname, "default")
        study_file = os.path.join(path, 's_mzML_parse.txt')

        new_s_path = os.path.join(self.out_dir, self.study_file_name)

        with open(study_file, RMODE) as isa_orig:
            with open(new_s_path, 'w') as isa_new:
                writer = csv.writer(isa_new, quotechar='"', quoting=csv.QUOTE_ALL, delimiter='\t')
                for index, line in enumerate(isa_orig):
                    line = line.rstrip()
                    line = line.replace('"', '')
                    row = line.split('\t')
                    if index == 0:
                        sample_name_idx = row.index("Sample Name")
                        writer.writerow(row)
                    else:
                        try:
                            row[sample_name_idx] = self.sample_names.pop(0)
                            writer.writerow(row)
                        except IndexError as e:
                            # no more samples left
                            pass


    def create_assay(self, metalist):
        """ Create the assay file.
        * Loops through a default assay file and locates the columns for the mass spectrometry (MS) section.
        * Get associated meta information for each column of the MS section
        * Deletes any unused MS columns
        * Creates the the new assay file
        :param list metalist: list of dictionaries containing mzML meta information
        """

        assay_file = os.path.join(self.default_path, 'a_mzML_parse.txt')

        #=================================================
        # Get location of the mass spectrometry section
        #=================================================
        with open(assay_file, RMODE) as isa_orig:

            for index, line in enumerate(isa_orig):
                line = line.rstrip()
                line = line.replace('"', '')

                if index == 0:

                    headers_l = line.split('\t')
                    sample_name_idx = headers_l.index("Sample Name")

                elif index == 1:

                    standard_row = line.split('\t')
                    mass_protocol_idx = standard_row.index("Mass spectrometry")
                    mass_end_idx = standard_row.index("Metabolite identification")
                    break

        mass_headers = headers_l[mass_protocol_idx+1:mass_end_idx]

        pre_row = standard_row[:mass_protocol_idx+1]
        mass_row = standard_row[mass_protocol_idx+1:mass_end_idx]
        post_row = standard_row[mass_end_idx:]

        self.new_mass_row = [""]*len(mass_headers)
        self.sample_names = []

        full_row = []

        #=================================================
        # Get associated meta information for each column
        #=================================================
        # The columns need to correspond to the names of the dictionary
        # Loop through list of the meta dictionaries
        for file_meta in metalist:
            # get the names and associated dictionaries for each meta term
            for key, value in file_meta.items():
                # special case for sample name as it is not amongst the mass columns
                if key == "Sample Name":
                    pre_row[sample_name_idx] = value['value']
                    self.sample_names.append(value['value'])

                # if key is an entry list it means this means there can be more than one of this meta type
                # This will check all meta data where there might be multiple columns of the same data e.g.
                # data file content
                if "entry_list" in value.keys():
                    # loop through the multiple entries on the entry list
                    for list_item in value.values():
                        # Locate the available columns
                        indices = [i for i, val in enumerate(mass_headers) if val == key]
                        # needs to be in reverse order
                        indices = indices[::-1]
                        # Add the items to the available columns untill they are all full up
                        for meta_id, meta_val in list_item.items():
                            try:
                                main = indices.pop()
                            except IndexError as e:
                                pass
                            else:
                                # update row with meta information
                                self.update_row(main, meta_val)
                else:
                    try:
                        # get matching column for meta information
                        main = mass_headers.index(key)
                    except ValueError as e:
                        pass
                    else:
                        # update row with meta information
                        self.update_row(main, value)

            # Add a list a fully updated row
            full_row.append(pre_row+self.new_mass_row+post_row)

        #=================================================
        # Delete unused mass spectrometry columns
        #=================================================
        headers_l, full_row = self.remove_blank_columns(mass_protocol_idx, mass_end_idx, full_row,headers_l)

        #=================================================
        # Create the the new assay file
        #=================================================
        with open(os.path.join(self.out_dir,self.assay_file_name), WMODE) as new_file:
            writer = csv.writer(new_file, quotechar='"', quoting=csv.QUOTE_ALL, delimiter='\t')
            writer.writerow(headers_l)

            # need to add in data-transformation info that is lost in the above processing
            data_tran_idx = headers_l.index("Derived Spectral Data File")-2

            for row in full_row:
                row[data_tran_idx] = "Data transformation"
                writer.writerow(row)

    def update_row(self, main, meta_val):
        """ Updates the MS section of a row based on the meta information.

        i.e. updates self.new_mass_row with the meta info to the location provided
        :param int main: index of the matched column:
        :param dict meta_val: Dictionary of the associated meta values
        """
        # First add the "name" of the meta, for instrument this would something like "Q Exactive"
        try:
            name = meta_val['name']
        except KeyError as e:
            pass
        else:
            self.new_mass_row[main] = name
            main = main+1

        # Add associated accession
        try:
            accession = meta_val['accession']
        except KeyError as e:
            pass
        else:
            self.new_mass_row[main] = "MS"
            main = main+1
            self.new_mass_row[main] = accession
            main = main+1

        # Add associated value e.g. for number of scans this would be 58
        try:
            value = meta_val['value']
        except KeyError as e:
            pass
        else:
            self.new_mass_row[main] = value

    def remove_blank_columns(self, start, end, full_row, headers_l):
        """ Delete unused mass spectrometry columns between two columns (start, end)

        :param int start: Which column to start at
        :param int end: Which column to end at
        :param list full_row: Row to remove columns from
        :param list headers_l: Headers to remove columns from
        :returns list update_headers, list updated_row
        """
        delete_cols = []
        updated_row = []
        for i in range(start,end-3):
            # check if a column is empty
            column = [col[i] for col in full_row]
            if column.count('') == len(full_row):
                delete_cols.append(i)

        for row in full_row:
            # pythons way of deleting multiple entries of a list. So much more hassle than numpy/pandas....
            row[:] = [ item for i, item in enumerate(row) if i not in delete_cols ]
            updated_row.append(row)

        updated_headers = []
        updated_headers[:] = [ item for i, item in enumerate(headers_l) if i not in delete_cols ]

        return updated_headers, updated_row
