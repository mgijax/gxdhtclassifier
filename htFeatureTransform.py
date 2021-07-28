#!/usr/bin/env python3

"""
#######################################################################
Author:  Jim
Routines for transforming tokens in article text before training/predicting.
These transformations are intended to reduce dimensionality of the feature set
(i.e., lower the number of features) AND by collapsing different forms of tokens
that mean the same thing (or for which the different forms are not relevant for
classification), we should improve the classifier's accuracy.
To some degree, this is becoming a poor man's named entity recognizer.

The kinds of transformations include
    a) mapping/collapsing different tokens to a common one, e.g.,
        e1, e2, e3, ... --> embryonic_day
        ko, knock out   --> knockout

    b) deleting certain tokens that seem meaningless e.g., 
        a1, a2, ... (these are typically in text referring to Figure a, panel 1)

Do this with regex and only one pass through the text...

#######################################################################
"""

import sys
import re

##############################################
# Tumors and tumor types regex - map all to "tumor_type"
# whole words
wholeWords = [
            'tumor',
            'tumour',
            'hepatoma',
            'melanoma',
            'teratoma',
            'thymoma',
            'neoplasia',
            'neoplasm',
            ]
# word endings
endings = [
            '[a-z]+inoma',
            '[a-z]+gioma',
            '[a-z]+ocytoma',
            '[a-z]+thelioma',
            ]
# whole words or endings
wordsOrEndings = [
            '[a-z]*adenoma',
            '[a-z]*sarcoma',
            '[a-z]*lymphoma',
            '[a-z]*papilloma',
            '[a-z]*leukemia',
            '[a-z]*leukaemia',
            '[a-z]*blastoma',
            '[a-z]*lipoma',
            '[a-z]*myoma',
            '[a-z]*acanthoma',
            '[a-z]*fibroma',
            '[a-z]*glioma',
            ]
tumorRe = '|'.join( wholeWords + endings + wordsOrEndings )
tumorRe = '(?:' + tumorRe + ')s?'	# optional 's'

##############################################
# Cell line names regex, all map to "cell_line"
cellLinePrefixes = [
            'B-?16', 	# includes 'B16',
            #'DA',      # omit, this matches various words
            #'F9',	# omit since it overlaps with F9 in figure panes
            'Hepa1',
            'K-?1735',
            'L5178Y',
            'MCA',
            'MCF-7',
            'MDA-MB',
            'NFS',
            'NIH-3T3',
            'P1798',
            'P19',
            'P388',
            'PC4',
            'RAW117',
            'RIF',
            'RMA',
            'SP2/0',
            'WEHI',
            ]
cellLinePreRe = '|'.join([ p + r'\S*' for p in cellLinePrefixes ])
cellLineNames = [ \
            '1246',
            '14-122',
            '14-166',
            '14-259',
            '15-299',
            '1C11',
            '203 cells',
            '2C3',
            '320DM',
            '32D',
            '38C13',
            '38C13',
            '3LL',
            '3SB',
            '4T1',
            '7-M12',
            '7OZ/3',
            '82-132',
            'A20',
            'A431',
            'A549',
            'AB1',
            'AC29',
            'ADJ-PC-5',
            'AKR1',
            'BAL17.7.1',
            'BCL1',
            'Bac-1.2F5',
            'C10',
            'C1300',
            'C1300-NB',
            'C1498',
            'C26',
            'C4',
            'C6',
            'C6',
            'CB101',
            'COLO',
            'CT-2A',
            'CT26',
            'CT51',
            'Caco-2',
            'Comma D',
            'D1-DMBA-3',
            'D5',
            #'E3', # clashes with embryonic day 3
            'E6496',
            'EL-4',
            'EL4',
            'ELM-D',
            'EMT6',
            'EPEN',
            'ESb',
            'F3II',
            'FSA',
            'FSa-II',
            'GL26',
            'GL261',
            'GL261',
            'Gc-4',
            'H1299',
            'HCT-116',
            'HCT-8',
            'HL-60',
            'HM7',
            'HT-29',
            'HT29',
            'HTH-K',
            'HeLa',
            'HepG2',
            'J558',
            'J558L',
            'JBS',
            'Jurkat',
            'K36',
            'K562',
            'L1',
            'L1210',
            'L929',
            'LA-N-2',
            'LK35.2',
            'LLC',
            'LM2',
            'LM2',
            'LM3',
            'LMM3',
            'LS 174T',
            'LSA',
            'LSTRA',
            'Lewis lung',
            'M1',
            'MA13/C',
            'MA16/C',
            'MA44',
            'MAC13',
            'MAC16',
            'MAC26',
            'MC-38',
            'MC12',
            'MCa-29',
            'MCa-4',
            'MDA231',
            'MEL cells',
            'MH134',
            'MIN6',
            'MLE',
            'MM3',
            'MO5',
            'MOD',
            'MOPC315',
            'N18',
            'N18TG2',
            'N1E-115',
            'N2A',
            'NBFL',
            'NL17',
            'NL22',
            'NL4',
            'NR-S1',
            'Nb2',
            'Neuro-2A',
            'OTT6050',
            'P02',
            'P03',
            'P511',
            'P815',
            'PC-3',
            'PC12',
            'PCC4',
            'R1.1',
            'RB13',
            'RENCA',
            'RI-4-11',
            'RL-12',
            'RM-1',
            'RVC',
            'RcsX',
            'S49',
            'SC-115',
            'SC115',
            'SCCVII',
            'SK-CO-1',
            'SL12',
            'SMA-560',
            'SW403',
            'SW480',
            'SW620',
            'Saos-2',
            'T-47D',
            'T241',
            'TA3/St',
            'TBJ-NB',
            'TEPC-2027',
            'TK-1',
            'TSA',
            'UV2237M',
            'WiDr',
            'X63-Ag8.653',
            'Y1',
            'YAC-1',
            'sarcoma 180',
            ]
cellLineRe = '|'.join([ p for p in cellLineNames ])

##############################################
class Mapping (object):
    """
    Is a mapping between a regular expression and the text that should replace
    any text that matches the regex.
    """
    def __init__(self, regex, replacement):
        self.regex = regex
        self.replacement = replacement

##############################################
# Define the dictionary of named Mappings.
mappings = { 
    # { name: Mapping object }
    'tt'   : Mapping( r'(?P<tt>' + tumorRe + ')', 'tumor_type'),
    'cl'   : Mapping( r'(?P<cl>' + cellLinePreRe + ')', 'cell_line'),
    'cn'   : Mapping( r'(?P<cn>' + cellLineRe + ')', 'cell_line'),

    'mice' : Mapping( r'(?P<mice>mice|mouse|mous|murine)', 'mice_'),

    'ko'   : Mapping( r'(?P<ko>ko|knock(?:ed|s)?(?:\s|-)?outs?)', 'knock_out'),
    'ki'   : Mapping( r'(?P<ki>knock(?:ed)?(?:\s|-)?ins?)', 'knock_in'),
    'gt'   : Mapping( r'(?P<gt>gene(?:\s|-)?trap(?:ped|s)?)', 'gene_trap'),
    'wt'   : Mapping( r'(?P<wt>wt|wild(?:\s|-)?types?)', 'wild_type'),
    'mut'  : Mapping( r'(?P<mut>\W*-/-\W*)', ' mut_mut '),

    #'eday' : Mapping( r'(?P<eday>e[ ]?\d\d?|e(?:mbryonic)? day[ ]\d\d?)',
    'eday' : Mapping( \
            r'(?P<eday>(?:e[ ]?|(?:e(?:mbryonic)? day[ ]))\d\d?(?:[.]\d\d?)?)',
                                                            'embryonic_day'),
    #'ee'   : Mapping( r'(?P<ee>(?:(?:[1,2,4,8]|one)(?:\s|-)cell)|blastocysts?)',
    #                                                        'early_embryo'),
    #'fig'  : Mapping( r'(?P<fig>fig)', 'figure'),
    					
    # Remove "A1", "A2", "B1", ...
    # Text often refers to fig or panel "A1", etc.,
    # Should this be for all letters? I've only picked a few I've seen in papers
    # Should we do this at all?
    # (note e is part of embryonic day above)
    #'letdig' : Mapping( r'(?P<letdig>[abcdfghs]\d)', ''),
    }

##############################################
# Combine all the mappings into 1 honking regex string
#   OR them together with word boundaries around
# (For some reason factoring out the word boundaries (r'\b') doesn't work right:
#   bigRegex = r'\b' + '|'.join([ m.regex for m in mappings.values() ]) + r'\b'
#  Have not looked into why.)
bigRegex = '|'.join([ r'\b' + m.regex + r'\b' for m in mappings.values() ])

bigRe = re.compile(bigRegex, re.IGNORECASE)

##############################################
def transformText(text):
    """
    Return the transformed text based on the transformations defined above.
    """
    toTransform = text
    transformed = ''

#    debug( "initial: '%s'\n" % toTransform)

    while (True):		# loop for each regex match
        m = bigRe.search(toTransform)
        if not m: break		# no match found

        key, start, end = findMatchingGroup(m)

#	debug( 'matching group: %s, %d, %d' % (key, start, end) + '\n')
        # Would doing this w/o slicing toTransform be faster?
        transformed += toTransform[:start] + mappings[key].replacement
        toTransform = toTransform[end:]
#	debug( "transformed '%s'" % transformed + '\n')
#	debug( "toTransform '%s'" % toTransform + '\n')
#	debug('\n')

    transformed += toTransform
#    debug("final string '%s'" % transformed + '\n')

    return transformed
#---------------------------------

def findMatchingGroup(m):
    """
    Given an re.Match object, m,
    Find the key (name) of its group that actually matched.
    Return the key & start & end coords of the matching string
    """
    gd = m.groupdict()		# dict of groups in m
    for k in list(gd.keys()):
        if gd[k] != None:	# the one that matched something
            return (k, m.start(k), m.end(k))
    return (None, None, None) # shouldn't happen since some group should match
#---------------------------------

def debug(text):
    if False: sys.stdout.write(text)
#---------------------------------

if __name__ == "__main__":	# ad hoc tests
    if True:
        text = "...stuff then ko and knock out mouse and a wt mouse and more text"
        tests = [
                'before e12 after',
                'before E 1 after',
                'before E day 1 after',
                'before embryonic day 7 after',
                'before embryonic day 117 after',
                'before -/- e12. after',
                'before tumours and tumor after',
                'before fig s1 fig a23 g6 after',
                'before wildtypes wildtype wild type wt Wt wild\ntype wild-types after',
                'before knockout knocksouts knocked out knock out ko Ko knock\nout knock-outs after',
                'before knockin knockins knocked-in knock-in knocked in knock ins after',
                'before 1 cell 1-cell one-cell 2 cell 2-cell blastocyst after',
                'before genetrap genetraps gene trap gene-traps gene-trap gene-trapped gene trapped after',
                ]

        for text in tests:
            print(text)
            print(transformText(text))
            print()
    if True:
        tests = [	# tumor tests
                'adenoma fooadenoma xxxinoma xxxinomas neoplasm neoplasias'
                ]

        for text in tests:
            print(text)
            print(transformText(text))
            print()
    if True:
        tests = [	#  cell line prefix tests
                'B-16, B-16blah. B16 SP2/0 blah f9 F19'
                ]

        for text in tests:
            print(text)
            print(transformText(text))
            print()
