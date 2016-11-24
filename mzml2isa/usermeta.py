import json
import openpyxl
import six
import os
import collections

class UsermetaImporter(object):

    CATEGORIZED_MAP = {

        "Assay Parameters": {

            "Chromatography Instrument Name": [
                ("Chromatography Instrument", "name"), False,
            ],

            "Chromatography Instrument Accession Number": [
                ("Chromatography", "accession"), False,
            ],

            "Chromatography Instrument Term Source REF": [
                ("Chromatography Instrument", "ref"), False,
            ],

            "Column model": [
                ("Column model", "value"), False,
            ],

            "Column type": [
                ("Column type", "value"), False,
            ],

            "Derivatization": [
                ("Derivatization", "value"), False,
            ],

            "Post Extraction": [
                ("Post Extraction", "value"), False,
            ],

        },

        "Characteristics": {

            "Organism Name": [
                ("characteristics", "organism", "name"), False,
            ],

            "Organism Accession Number": [
                ("characteristics", "organism", "accession"), False,
            ],

            "Organism Term Source REF": [
                ("characteristics", "organism", "ref"), False,
            ],

            "Organism Part Name": [
                ("characteristics", "organism_part", "name"), False,
            ],

            "Organism Part Accession Number": [
                ("characteristics", "organism_part", "accession"), False,
            ],

            "Organism Part Term Source REF": [
                ("characteristics", "organism_part", "ref"), False,
            ],

            "Organism Variant Name": [
                ("characteristics", "organism_variant", "name"), False,
            ],

            "Organism Variant Accession Number": [
                ("characteristics", "organism_variant", "accession"), False,
            ],

            "Organism Variant Term Source REF": [
                ("characteristics", "organism_variant", "ref"), False,
            ],

        },

        "Protocol Description": {

            "Chromatography Description": [
                ("description", "chroma"), False,
            ],

            "Data Transformation Description": [
                ("description", "data_trans"), False,
            ],

            "Extraction Description": [
                ("description", "extraction"), False,
            ],

            "Mass Spectrometry Description": [
                ("description", "mass_spec"), False,
            ],

            "Metabolite Identification Description": [
                ("description", "metabo_id"), False,
            ],

            "Sample Collection Description": [
                ("description", "sample_collect"), False,
            ],

            "Investigation Description": [
                ("investigation", "description"), False,
            ],

        },

        "Investigation": {

            "Investigation Identifier": [
                ("investigation", "identifier"), False,
            ],

            "Investigation Release Date": [
                ("investigation", "release_data"), False,
            ],

            "Investigation Submission Date": [
                ("investigation", "submission_date"), False,
            ],

            "Investigation Publication Authors": [
                ("investigation_publication", "author_list"), False,
            ],

            "Investigation Publication Title": [
                ("investigation_publication", "title"), False,
            ],

            "Investigation Publication DOI": [
                ("investigation_publication", "doi"), False,
            ],

            "Investigation Publication Pubmed ID": [
                ("investigation_publication", "pubmed"), False,
            ],

            "Investigation Publication Status Name": [
                ("investigation_publication", "status", "name"), False,
            ],

            "Investigation Publication Status Accession Number": [
                ("investigation_publication", "status", "accession"), False,
            ],

            "Investigation Publication Status Term Source REF": [
                ("investigation_publication", "status", "ref"), False,
            ],

        },

        "Study": {

            "Study Description": [
                ("study", "description"), False,
            ],

            "Study Indentifier": [
                ("study", "identifier"), False,
            ],

            "Study Release Date": [
                ("study", "release_date"), False,
            ],

            "Study Submission Date": [
                ("study", "submission_date"), False,
            ],

            "Study Title": [
                ("study", "title"), False,
            ],

            "Study Publication Authors": [
                ("study_publication", "author_list"), False,
            ],

            "Study Publication Title": [
                ("study_publication", "title"), False,
            ],

            "Study Publication DOI": [
                ("study_publication", "doi"), False,
            ],

            "Study Publication Pubmed ID": [
                ("study_publication", "pubmed"), False,
            ],

            "Study Publication Status Name": [
                ("study_publication", "status", "name"), False,
            ],

            "Study Publication Status Accession Number": [
                ("study_publication", "status", "accession"), False,
            ],

            "Study Publication Status Term Source REF": [
                ("study_publication", "status", "ref"), False,
            ],

        },



            # "investigation_contacts": [
            #     {
            #         "adress": "",
            #         "affiliation": "",
            #         "email": "",
            #         "fax": "",
            #         "first_name": "",
            #         "last_name": "",
            #         "mid": "",
            #         "phone": "",
            #         "roles": {
            #             "accession": "",
            #             "name": "",
            #             "ref": ""
            #         }
            #     }
            # ],

            # "study_contacts": [
            #     {
            #         "adress": "",
            #         "affiliation": "",
            #         "email": "",
            #         "fax": "",
            #         "first_name": "",
            #         "last_name": "",
            #         "mid": "",
            #         "phone": "",
            #         "roles": {
            #             "accession": "",
            #             "name": "",
            #             "ref": ""
            #         }
            #     }
            # ],

    }

    MAP = {k:v
            for submap in six.itervalues(CATEGORIZED_MAP)
                for k,v in six.iteritems(submap)
                }











    def __init__(self, usermeta_token):


        if usermeta_token is None:
            self.usermeta = None

        elif usermeta_token.endswith('.xlsx'):

            self._parse_xlsx_file(usermeta_token)


        elif usermeta_token.endswith('.json'):
            self._parse_json_file(usermeta_token)

        else:
            self._parse_json_stdin(usermeta_token)

    def _parse_json_file(self, usermeta_token):
        try:
            with open(args.usermeta) as f:
                self.usermeta = json.load(f)
        except json.decoder.JSONDecodeError:
            self.usermeta = None
            warnings.warn("JSON usermeta could not be parsed from {}.".format(usermeta_token))
        except OSError:
            self.usermeta = None
            warnings.warn("File {} not found.".format(usermeta_token))

    def _parse_json_stdin(self, usermeta_token):
        try:
            usermeta = json.loads(args.usermeta)
        except json.decoder.JSONDecodeError:
            self.usermeta = None
            warnings.warn("JSON usermeta could not be parsed from <stdin>.")

    def _parse_xlsx_file(self, usermeta_token):

        try:
            self.usermeta = collections.defaultdict(dict)
            sheet = openpyxl.load_workbook(usermeta_token).worksheets[0]

            for row in sheet.iter_rows():
                if len(row) == 2:
                    header, value = row
                else:
                    header, value = row[0], row[1:]

                if header.startswith("#"):
                    continue

                true_name, more_than_one = self.MAP[header]

        except:
            pass


    @classmethod
    def dump_xlsx(cls, output_directory, name='usermeta.xlsx'):

        wb = openpyxl.Workbook()
        x, y = 65,1

        for category, submap in six.iteritems(cls.CATEGORIZED_MAP):

            wb.worksheets[0]['{}{}'.format(chr(x), y)] = "#### {} ####".format(category.upper())
            y += 1

            for header in submap:

                wb.worksheets[0]['{}{}'.format(chr(x), y)] = header
                y += 1

        wb.save(os.path.join(output_directory, name))


if __name__=="__main__":

    UsermetaImporter.dump_xlsx(os.getcwd())
