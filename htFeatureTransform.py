#!/usr/bin/env python3

"""
#######################################################################
Author:  Jim
TextMappings for gxd ht experiment classification.
Text transformations that collapse different forms of tokens that for our 
purposes mean the same thing.

Includes:
cell line mappings, tumor mappings, embryonic age, etc.

Defines a variable:
    DefaultMappings
    which is used in the featureTransform preprocessor in  htMLsample.py


Has automated tests for many of the mappings. To run the tests:
    python htFeatureTransform.py [-v]

#######################################################################
"""
import sys
import re
import unittest
from utilsLib import TextMapping, TextMappingFromStrings, TextMappingFromFile,\
                        TextTransformer, escAndWordBoundaries
# Questions:
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

AgeMappings = [
    TextMapping('eday',
        # Original: was too broad
        # r'\b(?:(?:e\s?|(?:e(?:mbryonic)?\sdays?\s))\d\d?(?:[.]\d\d?)?)\b',
        # E1 E2 E3 are rarely used & often mean other things
        r'\b(?:' +
            r'e\s?\d[.]\d\d?' +    # E single digit w/ decimal place or two
            r'|e\s?1\d[.]\d\d?' +  # E double digit w/ decimal place or two
            r'|e\s?[4-9]' +        # E single digit
            r'|e\s?1[0-9]' +       # E double digits
            r'|e\s?20' +           # E double digits
            r'|embryonic\sdays?\s\d\d?(?:[.]\d\d?)?' + # spelled out, opt decim
        r')\b', '__embryonic_age'),
    TextMapping('dpc',
        r'\b(?:' +
            r'days?\spost\s(?:conception|conceptus|coitum)' +
            r'|\d\d?dpc' +         # dpc w/ a digit or two before (no space)
            r'|dpc' +              # dpc as a word by itself
        r')\b', '__embryonic_age', context=0),
    TextMapping('ts',
        r'\b(?:' +
            r'theiler\sstages?|TS(?:\s|-)?\d\d?' +      
        r')\b', '__embryonic_age', context=0),
    # Original:  - too broad, needed to add "stage|embryo" after "cell"
    # r'\b(?:(?:(?:[1248]|one|two|four|eight)(?:\s|-)cells?)|blastocysts?)\b',
    TextMapping('ee',
        r'\b(?:' +
            r'blastocysts?|blastomeres?' +
            r'|(?:(?:early|mid|late)(?:\s|-))?streak|morula|somites?' +
            r'|(?:' +
                r'(?:[1248]|one|two|four|eight)(?:\s|-)cell\s' +
                r'(?:' +
                    r'stages?|' +
                    r'(?:' +
                        r'(?:(?:mouse|mice|cloned)\s)?embryos?' +
                    r')' +
                r')' +
            r')' +
        r')\b', '__embryonic_age'),
    TextMapping('postnatal',
        r'\b(?:' +
            r'postnatal|new(?:\s|-)?borns?|adults?|ages?' +
        r')\b', '__mouse_age', context=0),
    ]

MiscMappings = [
    TextMapping('gt', r'\b(?:gene(?:\s|-)?trap(?:ped|s)?)\b', '__genetrap'),
    TextMapping('wt', r'\b(?:wt|wild(?:\s|-)?types?)\b', '__wildtype'),

                    # include spaces around the replacement token since these
                    # notations are often not space delimited. E.g., Pax6+/+
    TextMapping('wt2',r'(?:[+]/[+])', ' __wildtype '),  # combine these into
    TextMapping('mut',r'(?:-/-)', ' __mutant '), #  'genotype_'?
    TextMapping('mut2', r'\b(?:mutants?|mutations?)\b', '__mutant', context=0),

    TextMapping('esc',
        r'\b(?:(?:es|embryonic\sstem)(?:\s|-)cells?)\b', '__escell'),
    TextMapping('mef',
        r'\b(?:(?:mouse|mice)\sembryo(?:nic)?\sfibroblasts?|mefs?)\b','__mef'),

    TextMapping('mice', r'\b(?:mice|mouse|murine)\b', '__mice'),
    ]
##############################################
# Tumors and tumor types mappings - map all to "__tumor"

wholeWords = [          # whole words
            'tumor',
            'tumour',
            'hepatoma',
            'melanoma',
            'teratoma',
            'thymoma',
            'neoplasia',
            'neoplasm',
            ]
endings = [             # word endings
            '[a-z]+inoma',
            '[a-z]+gioma',
            '[a-z]+ocytoma',
            '[a-z]+thelioma',
            ]
wordsOrEndings = [      # whole words or endings
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
tumorRegex = '|'.join( wholeWords + endings + wordsOrEndings )
tumorRegex = r'\b(?:(?:' + tumorRegex + r')s?)\b'	# optional 's'

TumorMappings = [ TextMapping('tumor', tumorRegex, '__tumor', context=0), ]

##############################################
# Cell line mappings
# 1) Debbie Krupke's cancer cell line prefixes
debsCellLinePrefixes = [
            'B-?16', 	# includes 'B16',
            #'DA',      # omit, this matches various words
            'F9',	# omit since it overlaps with F9 in figure panes
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
                    # word boundary, prefix, any non-whitespace, word boundary
debsPreRegex = '|'.join([ r'\b' + p + r'\S*\b' for p in debsCellLinePrefixes ])
    
# 2) Debbie Krupke's cancer cell line names
debsCellLines = [ \
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
class DebsCellLineMapping (TextMappingFromStrings):
    def _str2regex(self, s):
        # 1st try, just word boundaries and escape regex chars
        return escAndWordBoundaries(s)

# 3) Cell line names from PRB_celline report
# TODO: filename should be a config variable or something
fn = "/Users/jak/work/gxdhtclassifier/PRB_CellLine.txt"

CellLineMappings = [
            TextMapping('debpre', debsPreRegex, '__cell_line', context=0),
            DebsCellLineMapping('debcl', debsCellLines,'__cell_line',context=0),
            TextMappingFromFile('prb_cellline', fn, '__cell_line', context=0), 
            ]

#############################################
# DefaultMappings are the mappings used in htMLsample.py featureTransform 
#   preprocessor

DefaultMappings = KIOmappings + AgeMappings + MiscMappings
DefaultMappings += TumorMappings
DefaultMappings += CellLineMappings

##############################################
# Automated tests

class Transformer_tests(unittest.TestCase):

    def test_MiscMappings(self):
        t = TextTransformer(MiscMappings)
        text = "there are no mappings here"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)

        text = "start (-/-) -/- +/+, wt mouse mutants end"
        done = "start ( __mutant )  __mutant   __wildtype , __wildtype __mice __mutant end"
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

    def test_AgeMappings0(self):
        t = TextTransformer(AgeMappings)
        text = "there are no mappings here"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)

    def test_AgeMappings1(self):
        t = TextTransformer(AgeMappings)
        text = "start E14 E14.5. E1.75 e4-5 embryonic day 15-18 E14, end"
        done = "start __embryonic_age __embryonic_age. __embryonic_age __embryonic_age-5 __embryonic_age-18 __embryonic_age, end"
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings2(self):
        t = TextTransformer(AgeMappings)
        text = "start 2.5dpc 5 dpc 12 days post\nconception end"
        done = "start 2.__embryonic_age 5 __embryonic_age 12 __embryonic_age end"
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings3(self):
        t = TextTransformer(AgeMappings)
        text = "start Theiler stages 4-5 expects 1 TS23 ts 23 ts-2 end"
        done = "start __embryonic_age 4-5 expects 1 __embryonic_age __embryonic_age __embryonic_age end"
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings4(self):
        t = TextTransformer(AgeMappings)
        text = "start new-borns newborn postnatal adults age end"
        done = "start __mouse_age __mouse_age __mouse_age __mouse_age __mouse_age end"
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings5(self):
        t = TextTransformer(AgeMappings)
        text = "there are no mappings here, 1-cell, 2 cell, four cell"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)
        text = "start Blastocysts 1-cell embryo one cell embryo 8 cell stage end"
        done = "start __embryonic_age __embryonic_age __embryonic_age __embryonic_age end"
        transformed = t.transformText(text)
        self.assertEqual(transformed, done)
        print('\n' + t.getMatchesReport())

    def test_TumorMappings(self):
        t = TextTransformer(TumorMappings)
        #print('\n')
        #print(t.getBigRegex()[:70])
        #print(t.getBigRegex()[-40:])
        text = "there are no mappings here, 1-cell, 2 cell, four cell"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)

        text = "start adenocarcinomas, tumours. adenoma end"
        expected = "start __tumor, __tumor. __tumor end" 
        self.assertEqual(expected, t.transformText(text))
        print('\n' + t.getMatchesReport())

    def test_CellLineMappings(self):
        fn = 'PRB_CellLine.txt'
        m = TextMappingFromFile('prb_probe', fn, '__cell_line', context=5)
        t = TextTransformer([m])
        #print('\n')
        #print(t.getBigRegex()[:70])
        #print(t.getBigRegex()[-40:])
        text = "there are no cellline mappings here, 1-cell, 2 cell, four cell"
        transformed = t.transformText(text)
        self.assertEqual(text, transformed)

        text = "start 14-7fd end"
        expected =  "start __cell_line end"
        self.assertEqual(expected, t.transformText(text))
        print('\n' + t.getMatchesReport())
# end class Transformer_tests ---------------------------------

def debug(text):
    if False: sys.stdout.write(text)
#---------------------------------

if __name__ == "__main__":	# automated tests
    unittest.main()
