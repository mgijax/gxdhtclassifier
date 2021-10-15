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
from utilsLib import TextMapping, TextMappingFromStrings, \
                        TextTransformer, escAndWordBoundaries

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
        # E14 is often a cell line, not an age
        r'\b(?:' +
            r'e\s?\d[.]\d\d?' +    # E single digit w/ decimal place or two
            r'|e\s?1\d[.]\d\d?' +  # E double digit w/ decimal place or two
            r'|e\s?[4-9]' +        # E single digit
            r'|e\s1\d' +           # E (w/ space) double digits
            r'|e1[012356789]' +    # E (no space) double digits - omit E14
            r'|e\s?20' +           # E double digits
            r'|embryonic\sdays?\s\d\d?(?:[.]\d\d?)?' + # spelled out, opt decim
        r')\b', '__mouse_age', context=0),
    TextMapping('dpc',
        r'\b(?:' +
            r'days?\spost\s(?:conception|conceptus|coitum)' +
            r'|\d\d?dpc' +         # dpc w/ a digit or two before (no space)
            r'|dpc' +              # dpc as a word by itself
        r')\b', '__mouse_age', context=0),
    TextMapping('ts',
        r'\b(?:' +
            r'theiler\sstages?|TS(?:\s|-)?\d\d?' +      
        r')\b', '__mouse_age', context=0),
    TextMapping('ee',   # early embryo
        r'\b(?:' +
            r'blastocysts?|blastomeres?|fetus|fetuses' +
            r'|(?:(?:early|mid|late)(?:\s|-))?streak|morula|somites?' +
            r'|(?:' +
                r'(?:[1248]|one|two|four|eight)(?:\s|-)cell\s' +
                r'(?:' +   # "embryo" or "stage" must come after [1248] cell
                    r'stages?|' +
                    r'(?:' +
                        r'(?:(?:mouse|mice|cloned)\s)?embryos?' +
                    r')' +
                r')' +
            r')' +
        r')\b', '__mouse_age'),
    TextMapping('postnatal',
        r'\b(?:' +
            r'postnatal|neonatal|new(?:\s|-)?borns?|adults?|ages?' +
            r'|P\d\d?' +  # note this matches P53 P63 P73 - common gene syn's
        r')\b', '__mouse_age', context=0),
    ]

TreatmentMappings = [
    TextMapping('untreated',
        r'\b(?:' +
        r'(?:untreated|non-?treated)' +
        r'|(?:not\s(?:(?:pre|post|co)(?:\s|-)?)?treated)' +
        r'|(?:no\s(?:(?:pre|post|co)(?:\s|-)?)?treate?ments?)' +
        r'|(?:no\s(?:(?:special||previous|prior|additional)\s)?treate?ments?)' +
        r'|(?:without\s(?:(?:pre|post|co)(?:\s|-)?)?treate?ments?)' +
        r'|(?:without\s(?:(?:any|special|previous|prior|additional)\s)?treate?ments?)' +
        r')\b', '__untreated', context=0),
    TextMapping('treated',
        r'\b(?:' +
        r'(?:(?:(?:pre|post|co)(?:\s|-)?)?treated)' +
        r'|(?:(?:(?:pre|post|co)(?:\s|-)?)?treate?ments?)' +
        r')\b', '__treated', context=0),
    ]

MiscMappings = [
    TextMapping('gt', r'\b(?:gene(?:\s|-)?trap(?:ped|s)?)\b', '__genetrap'),
    TextMapping('wt', r'\b(?:wt|wild(?:\s|-)?types?)\b', '__genotype'),

                    # include spaces around the replacement token since these
                    # notations are often not space delimited. E.g., Pax6+/+
    TextMapping('wt2',r'(?:[-+]/[-+])', ' __genotype '),  # combine these into
    TextMapping('mut2', r'\b(?:mutants?|mutations?)\b', '__genotype',context=0),
    TextMapping('mut3', r'\b(?:(?:hetero|homo)(?:zygous|zygote))\b',
                                                    '__genotype',context=0),

    TextMapping('esc',
        r'\b(?:' +
            r'(?:es|embryonic\sstem)(?:\s|-)cells?' +
            r'|embryonic\sstem\s\(es\)\scells?' +
            r'|ESCs?|MESCs?' +
        r')\b', '__escell', context=0),
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
            #'E3', # Is this usually a cell line?
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

# 3) Connie's culled list of cell lines from PRB_Cellline.rpt
conniesCellLineRegex =  \
        r'\b(?:' + '|'.join([ \
            r'BALB(?:\s+|[-/])?3T3',
            r'3T3',
            r'C2C12',
            r'C3H(?:\s+|[-/])?10T1(?:\s+|[-/])?2',
            r'CHO(?:\s+|[-/])?cells?',
            r'colon\s+cancer\s+cell(?:\s+|-)?lines?',
            r'embryonal\s+carcinoma\s+cell(?:\s+|-)?lines?',
            r'fibroblast\s+cell(?:\s+|-)?lines?',
            r'HEK293T',
            r'hybridoma\s+cell(?:\s+|-)?lines?',
            r'melan[-/]a',
            r'mltc(?:\s+|[-/])?1',
            r'myeloma\s+cell(?:\s+|-)?lines?',
            r'neuro2a',
            r'nih(?:\s+|[-/])?3t3',
            r'primary\s+cultures?',
            r'raw(?:\s+|[-/])?264(?:[.]7)?',
            r'stem(?:\s+|-)?cell(?:\s+|-)?lines?',
            r'stromal\s+cell(?:\s+|-)?lines?',
            r'Swiss(?:\s+|[-/])?3T3',
            r'cell(?:\s+|-)?lines?',          # catch all at the bottom
            ]) + r')\b'

CellLineMappings = [
            TextMapping('debpre', debsPreRegex, '__cell_line', context=0),
            DebsCellLineMapping('debcl', debsCellLines,'__cell_line',context=0),
            TextMapping('concl', conniesCellLineRegex, '__cell_line',context=0),
            ]
#############################################
# DefaultMappings are the mappings used in htMLsample.py featureTransform 
#   preprocessor

DefaultMappings = KIOmappings + AgeMappings + MiscMappings
DefaultMappings += TreatmentMappings
DefaultMappings += TumorMappings
DefaultMappings += CellLineMappings

##############################################
# Automated tests

class Transformer_tests(unittest.TestCase):

    def test_MiscMappings(self):
        t = TextTransformer(MiscMappings)
        text = "there are no mappings here"
        self.assertEqual(text, t.transformText(text))

        text = "s (-/-) -/- +/+, e"
        expt = "s ( __genotype )  __genotype   __genotype , e"
        self.assertEqual(t.transformText(text), expt)

        text = "s wt mouse mutants e"
        expt = "s __genotype __mice __genotype e"
        self.assertEqual(t.transformText(text), expt)

        text = "s (+/-) homozygous for x heterozygous for y e"
        expt = "s ( __genotype ) __genotype for x __genotype for y e"
        self.assertEqual(t.transformText(text), expt)

        text = "s mouse embryonic fibroblast lines es cell-line MEFs e"
        expt = "s __mef lines __escell-line __mef e"
        self.assertEqual(t.transformText(text), expt)

        text = "s embryonic stem cell lines es cells es-cells ES cell e"
        expt = "s __escell lines __escell __escell __escell e"
        self.assertEqual(t.transformText(text), expt)

        text = "s embryonic stem (ES) cell ESCs MESC ESC e"
        expt = "s __escell __escell __escell __escell e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_KIOmappings(self):
        t = TextTransformer(KIOmappings)
        text = "there are no kos here"
        self.assertEqual(text, t.transformText(text))

        text = "s ko's here knockout knock outs knock\nouts e"
        expt = "s __knockout's here __knockout __knockout __knockout e"
        self.assertEqual(t.transformText(text), expt)

        text = "s knock-out knockedout knocked\nouts e"
        expt = "s __knockout __knockout __knockout e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings0(self):
        t = TextTransformer(AgeMappings)
        text = "there are no mappings here"
        self.assertEqual(text, t.transformText(text))

    def test_AgeMappings1_eday(self):
        t = TextTransformer(AgeMappings)
        text = "s E0 E 1. E 2 E3, E0.5 E4-5 E9.75 e"      # single digit
        expt = "s E0 E 1. E 2 E3, __mouse_age __mouse_age-5 __mouse_age e"
        self.assertEqual(t.transformText(text), expt)

        text = "s E14 E14.5. E 14 E 14.5 E15-18 e"      # double digits
        expt = "s E14 __mouse_age. __mouse_age __mouse_age __mouse_age-18 e"
        self.assertEqual(t.transformText(text), expt)

        text = "s E13 E19 E 16 E 17.5 E20 e"            # double digits
        expt = "s __mouse_age __mouse_age __mouse_age __mouse_age __mouse_age e"
        self.assertEqual(t.transformText(text), expt)

        text = "s E21 embryonic days 15-18 embryonic day 14-15 e"
        expt = "s E21 __mouse_age-18 __mouse_age-15 e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings2_dpc(self):
        t = TextTransformer(AgeMappings)
        text = "s 2.5dpc 5 dpc 12 days post\nconception e"
        expt = "s 2.__mouse_age 5 __mouse_age 12 __mouse_age e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings3_ts(self):
        t = TextTransformer(AgeMappings)
        text = "s Theiler stages 4-5 just 1 TS23 ts 23 ts-2 e"
        expt = "s __mouse_age 4-5 just 1 __mouse_age __mouse_age __mouse_age e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings4_ee(self):
        t = TextTransformer(AgeMappings)
        text = "there are no mappings here, 1-cell, 2 cell, four cell"
        self.assertEqual(text, t.transformText(text))
        text = "s Blastocysts fetus blastomeres early-streak e"
        expt = "s __mouse_age __mouse_age __mouse_age __mouse_age e"
        self.assertEqual(t.transformText(text), expt)

        text = "s 1-cell embryo one cell mice embryos 8 cell stage e"
        expt = "s __mouse_age __mouse_age __mouse_age e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_AgeMappings5_postnatal(self):
        t = TextTransformer(AgeMappings)
        text = "s new-borns newborn postnatal e"
        expt = "s __mouse_age __mouse_age __mouse_age e"
        self.assertEqual(t.transformText(text), expt)

        text = "s neonatal adults age e"
        expt = "s __mouse_age __mouse_age __mouse_age e"
        self.assertEqual(t.transformText(text), expt)

        text = "s P0 P5 P15 e"
        expt = "s __mouse_age __mouse_age __mouse_age e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_TreatmentMappings_treated(self):
        t = TextTransformer(TreatmentMappings)
        text = "s treated cotreated pre treated post-treated e"
        expt = "s __treated __treated __treated __treated e"
        self.assertEqual(t.transformText(text), expt)

        text = "s treatments cotreatment pre treatment post-treatements e"
        expt = "s __treated __treated __treated __treated e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_TreatmentMappings_untreated(self):
        t = TextTransformer(TreatmentMappings)
        text = "s untreated not treated not pre-treated not pretreated e"
        expt = "s __untreated __untreated __untreated __untreated e"
        self.assertEqual(t.transformText(text), expt)

        text = "s no pretreatment no co-treatment no post treatements e"
        expt = "s __untreated __untreated __untreated e"
        self.assertEqual(t.transformText(text), expt)

        text = "s no special treatment no prior treatments no treatments e"
        expt = "s __untreated __untreated __untreated e"
        self.assertEqual(t.transformText(text), expt)

        text = "s without pretreatment without cotreatment without treatments e"
        expt = "s __untreated __untreated __untreated e"
        self.assertEqual(t.transformText(text), expt)

        text = "s without special treatment without previous treatments e"
        expt = "s __untreated __untreated e"
        self.assertEqual(t.transformText(text), expt)
        print('\n' + t.getMatchesReport())

    def test_TumorMappings(self):
        t = TextTransformer(TumorMappings)
        #print(t.getBigRegex()[:70])
        #print(t.getBigRegex()[-40:])
        text = "there are no mappings here, 1-cell, 2 cell, four cell"
        self.assertEqual(text, t.transformText(text))

        text = "s adenocarcinomas, tumours. adenoma e"
        expt = "s __tumor, __tumor. __tumor e" 
        self.assertEqual(expt, t.transformText(text))
        print('\n' + t.getMatchesReport())

    def test_ConniesCellLineMapping(self):
        m = TextMapping('concl', conniesCellLineRegex, '__cell_line',context=0)
        t = TextTransformer([m])
        #print(t.getBigRegex()[:70])
        #print(t.getBigRegex()[-40:])
        text = "there are no mappings here, 1-cell, 2 cell, four cell"
        self.assertEqual(text, t.transformText(text))

        text = "s BALB 3t3 BALB/3T3 BALB\t 3T3 BALB3T3 BALB-3T3 e"
        expt = "s __cell_line __cell_line __cell_line __cell_line __cell_line e"
        self.assertEqual(expt, t.transformText(text))

        text = "s C3H c3h-10T12 C3H 10T1/2 C3H10t1-2 e"
        expt =  "s C3H __cell_line __cell_line __cell_line e"
        self.assertEqual(expt, t.transformText(text))

        text = "s stem cell lines stromal cell  line foo cell-line e"
        expt = "s __cell_line __cell_line foo __cell_line e"
        self.assertEqual(expt, t.transformText(text))
        print('\n' + t.getMatchesReport())

# end class Transformer_tests ---------------------------------

def debug(text):
    if False: sys.stdout.write(text)
#---------------------------------

if __name__ == "__main__":	# automated tests
    unittest.main()
