"""
Content
-----------------------------------------------------------------------------
This module contains two classes used for parsing the obo based ontology 
shipping with the parser. The class **oboparse** has been modified from the
nextgenetics.net blog[1]_  and is used to identify what children or parents
a ontological terms has. The class **oboTranslator** has been modified from
the pymzml package[2]_ and is used to get the associated name of a term based
on its accession number.

Reference:
-----------------------------------------------------------------------------
- [1] http://blog.nextgenetics.net/?e=6
- [2] http://pymzml.github.io

About
-----------------------------------------------------------------------------
The mzml2isa parser was created by Tom Lawson (University of Birmingham, UK) 
as part of a NERC funded placement at EBI Cambridge in June 2015. Python 3
port and small enhancements were carried out by Martin Larralde (ENS Cachan, 
France) in June 2016 during an internship at the EBI Cambridge.

License
-----------------------------------------------------------------------------
GNU General Public License version 3.0 (GPLv3)
"""

import os

class oboparse(object):
    # Class based around the code found in this excellent blog: http://blog.nextgenetics.net/?e=6
    def __init__(self, obo_file_path):
        """ Opens the obo file and parses its content into **self.terms**

        :param list obo_file_path: path to the obo file.
        """



        oboFile = open(obo_file_path,'r')

        #declare a blank dictionary
        #keys are the goids
        terms = {}

        #skip the file header lines
        self.getTerm(oboFile)

        #infinite loop to go through the obo file.
        #Breaks when the term returned is empty, indicating end of file
        while 1:
            #get the term using the two parsing functions
            term = self.parseTagValue(self.getTerm(oboFile))
            if len(term) != 0:
                termID = term['id'][0]

                #only add to the structure if the term has a is_a tag
                #the is_a value contain GOID and term definition
                #we only want the GOID
                if 'is_a' in term:
                    termParents = [p.split()[0] for p in term['is_a']]

                    if termID not in terms:
                        #each goid will have two arrays of parents and children
                        terms[termID] = {'p':[],'c':[]}

                    #append parents of the current term
                    terms[termID]['p'] = termParents

                    #for every parent term, add this current term as children
                    for termParent in termParents:
                        if termParent not in terms:
                            terms[termParent] = {'p':[],'c':[]}
                        terms[termParent]['c'].append(termID)
            else:
                break

        self.terms = terms

    def getTerm(self, stream):
        block = []
        for line in stream:
            if line.strip() == "[Term]" or line.strip() == "[Typedef]":
                break
            else:
                if line.strip() != "":
                    block.append(line.strip())

        return block

    def parseTagValue(self, term):
        data = {}

        for line in term:
            tag = line.split(': ',1)[0]
            try:
                value = line.split(': ',1)[1]
            except IndexError:
                value = line.split(':',1)[1]

            if tag not in data:
                data[tag] = []

            data[tag].append(value)

        return data

    def getDescendents(self, goid):
        recursiveArray = [goid]
        if goid in self.terms:
            children = self.terms[goid]['c']
            if len(children) > 0:
                for child in children:
                    recursiveArray.extend(self.getDescendents(child))

        return set(recursiveArray)

    def getAncestors(self, goid):
        recursiveArray = [goid]
        if goid in self.terms:
            parents = self.terms[goid]['p']
            if len(parents) > 0:
                for parent in parents:
                    recursiveArray.extend(self.getAncestors(parent))

        return set(recursiveArray)


class oboTranslator(object):
    # Class Taken and modified from pymzml
    def __init__(self, version='1.1.0'):
        self.version = version
        self.allDicts = []
        self.id = {}
        self.name = {}
        self.definition = {}
        self.lookups = [ self.id, self.name, self.definition ]
        # replace_by could be another one ...

        self.parseOBO()

    def __setitem__(self, key, value):
        return

    def __getitem__(self, key):
        for lookup in self.lookups:
            if key in lookup.keys():
                if key[:2] == 'MS':
                    try:
                        return lookup[key]['name']
                    except:
                        pass
                return lookup[key]
        return 'None'

    def parseOBO(self):
        """
        Parse the obo file in folder obo/
        (would be great to have all versions. Must convience PSI to add version
        number at the file .. :))
        """

        dirname = os.path.dirname(os.path.realpath(__file__))
        oboFile = os.path.join(dirname,"psi-ms.obo")

        #print oboFile
        if os.path.exists(oboFile):
            with open(oboFile) as obo:
                collections = {}
                collect = False
                for line in obo:
                    if line.strip() in ('[Term]', ''):
                        collect = True
                        if not collections:
                            continue
                        self.add(collections)
                        collections = {}
                    else:
                        if line.strip() != '' and collect is True:
                            k = line.find(":")
                            collections[line[:k]] = line[k + 1:].strip()
        else:
            print("No obo file version")

            raise Exception("Could not find obo file.")
        return

    def add(self, collection_dict):
        self.allDicts.append(collection_dict)
        if 'id' in collection_dict.keys():
            self.id[collection_dict['id']] = self.allDicts[len(self.allDicts) - 1]
        if 'name' in collection_dict.keys():
            self.name[collection_dict['name']] = self.allDicts[len(self.allDicts) - 1]
        if 'def' in collection_dict.keys():
            self.definition[collection_dict['def']] = self.allDicts[len(self.allDicts) - 1]
        else:
            pass
        return

    def checkOBO(self, idTag, name):
        if self.id[idTag]['name'] == name:
            return True
        else:
            return False