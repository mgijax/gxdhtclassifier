#!/usr/bin/env python3

"""
#######################################################################
Author:  Jim
TODO UPDATE THIS
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
import unittest
from utilsLib import TextMapping, TextTransformer

# Questions:
# early_embryo: should we require 'embryos?' after 'one cell', etc.?
# collapse +/+ and -/- into just "genotype_"? Include "wild type"?
# what are FACs? are there various spellings?

# The order of the TextMappings is significant if multiple mappings can
#   match the same text, e.g., "mouse" & "mouse embryonic fibroblasts".
#   The earlier TextMapping takes precedence.

KIOmappings = [
    TextMapping('ko', r'\b(?:ko|knock(?:ed|s)?(?:\s|-)?outs?)\b','__knockout'),
    TextMapping('ki', r'\b(?:knock(?:ed)?(?:\s|-)?ins?)\b', '__knockin'),
    TextMapping('kd', r'\b(?:knock(?:ed)?(?:\s|-)?downs?)\b', '__knockdown'),
    ]

EmbryoMappings = [
    TextMapping('eday',
        r'\b(?:(?:e\s?|(?:e(?:mbryonic)?\sdays?\s))\d\d?(?:[.]\d\d?)?)\b',
                                                            '__embryonicday'),
    # original:  - too broad, needed to add "stage|embryo" after "cell"
    # r'\b(?:(?:(?:[1248]|one|two|four|eight)(?:\s|-)cells?)|blastocysts?)\b',
    TextMapping('ee',
        r'\b(?:blastocysts?|blastomeres?|' +
            r'(?:' +
                r'(?:[1248]|one|two|four|eight)(?:\s|-)cell\s' +
                r'(?:' +
                    r'stages?|' +
                    r'(?:' +
                        r'(?:(?:mouse|mice|cloned)\s)?embryos?' +
                    r')' +
                r')' +
            r')' +
        r')\b', '__earlyembryo'),
    ]
MiscMappings = [
    TextMapping('gt', r'\b(?:gene(?:\s|-)?trap(?:ped|s)?)\b', '__genetrap'),
    TextMapping('wt', r'\b(?:wt|wild(?:\s|-)?types?)\b', '__wildtype'),

                    # include spaces around the replacement token since these
                    # notations are often not space delimited. E.g., Pax6+/+
    TextMapping('wt2',r'(?:[+]/[+])', ' __wildtype '),  # combine these into
    TextMapping('mut',r'(?:-/-)', ' __mut_mut '),        #  'genotype_'?

    TextMapping('esc',
        r'\b(?:(?:es|embryonic\sstem)(?:\s|-)cells?)\b', '__escell'),
    TextMapping('mef',
        r'\b(?:(?:mouse|mice)\sembryo(?:nic)?\sfibroblasts?|mefs?)\b','__mef'),

    TextMapping('mice', r'\b(?:mice|mouse|murine)\b', '__mice'),
    ]

DefaultMappings = KIOmappings + EmbryoMappings + MiscMappings
#---------------------------------

class Transformer_tests(unittest.TestCase):

    def test_MiscMappings(self):
        t = TextTransformer(MiscMappings)
        text = "there are no mappings here"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)

        text = "start (-/-) -/- +/+, wt mouse end"
        done = "start ( __mut_mut )  __mut_mut   __wildtype , __wildtype __mice end"
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)

        text = "start mouse embryonic fibroblast lines es cell-line MEFs embryonic stem cell lines end"
        done = "start __mef lines __escell-line __mef __escell lines end"
        transformed = t.transformText(text)
        #print('\n' + transformed)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())

    def test_KIOmappings(self):
        t = TextTransformer(KIOmappings)
        text = "there are no kos here"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)
        text = """but ko's here knockout knock outs knock\nouts knock-out
                    knockedout knocked\nouts"""
        done = """but __knockout's here __knockout __knockout __knockout __knockout
                    __knockout __knockout"""
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())

    def test_EmbryoMappings(self):
        t = TextTransformer(EmbryoMappings)
        text = "there are no embryo mappings here"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)
        text = "start E14 E14.5. E1.75 e1-5 E\nday 4.5 embryonic day 15-18 E14, end"
        done = "start __embryonicday __embryonicday. __embryonicday __embryonicday-5 __embryonicday __embryonicday-18 __embryonicday, end"
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())

    def test_EarlyEmbryoMappings(self):
        t = TextTransformer(EmbryoMappings)
        text = "there are no embryo mappings here, 1-cell, 2 cell, four cell"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)
        text = "start Blastocysts 1-cell embryo one cell embryo 8 cell stage end"
        done = "start __earlyembryo __earlyembryo __earlyembryo __earlyembryo end"
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())
# end class Transformer_tests ---------------------------------

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
    'tt'   : Mapping(r'(?P<tt>' + tumorRe + ')', 'tumor_type'),
    'cl'   : Mapping(r'(?P<cl>' + cellLinePreRe + ')', 'cell_line'),
    'cn'   : Mapping(r'(?P<cn>' + cellLineRe + ')', 'cell_line'),


    }
#---------------------------------

def debug(text):
    if False: sys.stdout.write(text)
#---------------------------------

if __name__ == "__main__":	# automated tests
    unittest.main()
