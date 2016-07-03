"""
mzml2isa
=============================================================================
mzml2isa is a parser/converter that translates mass spectrometry .mzML files 
(a format based on XML[1]_) to ISA-TAB format (Investigation-Study-Assay with
TAB separated values)[2]_.

Format reference:
-----------------------------------------------------------------------------
- [1] http://www.psidev.info/mzml_1_0_0
- [2] http://isa-tools.org/format.html

About
-----------------------------------------------------------------------------
The mzml2isa parser was created by Tom Lawson (University of Birmingham, UK) 
as part of a NERC funded placement at EBI Cambridge in June 2015. Python 3
port and small enhancements were carried out by Martin Larralde (ENS Cachan, 
France) in June 2016 during an internship at the EBI Cambridge.

Authors:
-----------------------------------------------------------------------------
- Thomas Lawson       [tnl495@bham.ac.uk]
- Martin Larralde     [martin.larralde@ens-cachan.fr]

Help provided from:
-----------------------------------------------------------------------------
- Reza Salek          [reza.salek@ebi.ac.uk]
- Ken Haug            [kenneth@ebi.ac.uk]
- Christoph Steinbeck [steinbeck@ebi.ac.uk]

Supervisors: 
-----------------------------------------------------------------------------
- Prof. Mark Viant (University of Birmingham, UK)
- Prof. Uriel Hazan (Ecole Normale Superieure de Cachan, France)
"""


__author__ = 'Thomas Lawson, Martin Larralde'


__credits__ = 'Thomas Lawson, Martin Larralde, Reza Salek, Ken Haug, Christoph Steinbeck'

__version__ = '0.4.6'

