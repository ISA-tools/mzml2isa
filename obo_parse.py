# Class based around the code found in this excellent blog: http://blog.nextgenetics.net/?e=6

class oboparse(object):
    def __init__(self, obo_file_path):
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
                if term.has_key('is_a'):
                    termParents = [p.split()[0] for p in term['is_a']]

                    if not terms.has_key(termID):
                        #each goid will have two arrays of parents and children
                        terms[termID] = {'p':[],'c':[]}

                    #append parents of the current term
                    terms[termID]['p'] = termParents

                    #for every parent term, add this current term as children
                    for termParent in termParents:
                        if not terms.has_key(termParent):
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

            if not data.has_key(tag):
                data[tag] = []

            data[tag].append(value)

        return data

    def getDescendents(self, goid):
        recursiveArray = [goid]
        if self.terms.has_key(goid):
            children = self.terms[goid]['c']
            if len(children) > 0:
                for child in children:
                    recursiveArray.extend(self.getDescendents(child))

        return set(recursiveArray)

    def getAncestors(self, goid):
        recursiveArray = [goid]
        if self.terms.has_key(goid):
            parents = self.terms[goid]['p']
            if len(parents) > 0:
                for parent in parents:
                    recursiveArray.extend(self.getAncestors(parent))

        return set(recursiveArray)


if __name__ == "__main__":

    obo = oboparse('/home/tomnl/MEGA/metabolomics/isatab/psi-ms.obo')

    print obo.terms

    print obo.getDescendents('MS:1000524')