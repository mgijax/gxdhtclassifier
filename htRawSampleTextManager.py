#!/usr/bin/env python3
'''
  Purpose:
           Classes that know how to gather and format raw sample text for
           GXD ht experiments

  If you run this module as a script, it takes an _experiment_key and writes
  the raw sample text for that experiment out to stdout.
'''
import sys
import os
import time
import argparse
import unittest
import htMLsample as mlSampleLib
from utilsLib import removeNonAscii, TextMapping, TextTransformer

#-----------------------------------
sampleObjType = mlSampleLib.ClassifiedHtSample

RECORDEND    = sampleObjType.getRecordEnd()
FIELDSEP     = sampleObjType.getFieldSep()

beVerbose = False
#-----------------------------------

def cleanDelimiters(text):
    """ remove RECORDEND and FIELDSEPs from text (replace w/ ' ')
    """
    return text.replace(RECORDEND,' ').replace(FIELDSEP,' ')
#-----------------------------------

def verbose(text):
    if beVerbose:
        sys.stderr.write(text)
        sys.stderr.flush()
#-----------------------------------

class RawSampleTextManager (object):
    """
    IS:  a class that knows how to gather and format the raw sample metadata
        text for experiments
    HAS:  a collection of raw sample text data for a bunch of experiments
            in the db.
    DOES: getRawSampleText( for an _experiment_key )
            getNumExperiments()         # in the collection
            getNumFieldValuePairs()     # in the collection
    """
    def __init__(self,
                db,       # initialized db module
                expTbl='gxd_htexperiment'):
        """
            expTblName is a database table with '_experiment_key' field that
                contains the experiments you want the raw sample text for.
                Default is 'gxd_htexperiment' - meaning all experiments.
                But if you pass in the name of a populated temp table,
                you can get raw sample text for just those experiments.
        """
        self.db = db
        self.expTbl = expTbl
        self.rawSampleTmpTbl = 'tmp_%s_rawsample_text' % expTbl
        self.experimentDict = {}        # experimentDict[exp_key] is a
                                        #   set of (field,value) pairs
                                        #   from the samples of that experiment
        self._buildRawSampleTmpTbl()
        self._buildExperimentDict()
    #-----------------------------------

    def _buildRawSampleTmpTbl(self):
        """
        Populate self.rawSampleTmpTbl "key:value" pairs for GEO experiments
        whose keys are int self.expTbl
        """
        startTime = time.time()
        verbose("Building raw sample tmp table for experiments in %s ..." % \
                self.expTbl)
        q = ["""
            create temporary table %s as
            select distinct rs._experiment_key, kv.key, kv.value
            from
                %s exp join GXD_HTRawSample rs on
                    (exp._experiment_key = rs._experiment_key)
                join MGI_KeyValue kv on
                    (rs._rawsample_key = kv._object_key and _mgitype_key = 47)
            order by rs._experiment_key, kv.key, kv.value
            """ % (self.rawSampleTmpTbl, self.expTbl),
            """
            create index %s_idx1 on %s(_experiment_key)
            """ % (self.rawSampleTmpTbl, self.rawSampleTmpTbl),
            ]
        results = self.db.sql(q, 'auto')
        verbose("%8.3f seconds\n\n" %  (time.time()-startTime))
    #-----------------------------------

    def _buildExperimentDict(self):
        startTime = time.time()
        verbose("Getting raw sample text from %s ..." % self.rawSampleTmpTbl)

        q = "select * from %s" % self.rawSampleTmpTbl
        results = self.db.sql(q, 'auto')
        for i,r in enumerate(results):
            try:
                expKey = str(r['_experiment_key'])
                theSet = self.experimentDict.setdefault(expKey, set())

                field = removeNonAscii(cleanDelimiters(str(r['key']))).strip()
                value = removeNonAscii(cleanDelimiters(str(r['value']))).strip()

                theSet.add((field, value))
            except:         # if some error, try to report which record
                sys.stderr.write("Error on record %d:\n%s\n" % (i, str(r)))
                raise
        verbose("%8.3f seconds\n\n" %  (time.time()-startTime))
    #-----------------------------------

    def getNumExperiments(self):
        """ Return the number of experiments with raw sample text
        """
        # To get it from the db:
        #q = """select count(distinct rs._experiment_key) as num
        #       from  %s rs
        #    """ % (self.rawSampleTmpTbl)
        #num = self.db.sql(q, 'auto')[0]['num']
        # OR just get it from the dictionary:
        num = len(self.experimentDict)
        return num
    #-----------------------------------

    def getNumFieldValuePairs(self):
        """ Return the number of distinct field-value pairs
        """
        q = """select count(*) as num from %s
            """ % (self.rawSampleTmpTbl)
        num = self.db.sql(q, 'auto')[0]['num']
        return num
    #-----------------------------------

    def getReport(self):
        """
        Return formated report on text mappings applied to raw sample fields
        """
        text = "\n"
        text += self.NaTransformer.getReport()
        text += self.treatmentProtFieldTransformer.getReport()
        text += self.treatmentFieldTransformer.getReport()
        return text
    #-----------------------------------

    def getRawSampleText(self, expKey):
        """ Return the formated, raw sample text for the experiment
        """
        expKey = str(expKey)
        if expKey not in self.experimentDict:
            return ''
        else: 
            pairs = self.experimentDict[expKey]

            fieldText = []      # list of formated field/value pairs to include
            for f,v in sorted(pairs):
                t = self.fieldValue2Text(f,v)
                if t:
                    fieldText.append(t)
            
            text = "  ".join(fieldText)
            return text
    #-----------------------------------

    # Raw sample field-value text formatting
    # Mappings used for field-value formatting/conversion
    NaMapping = TextMapping('na',       # match various forms of N/A
            r'\A(?:n[.-/]?a|not applicable|not relevant|control|cntrl|ctrl|ctl|no data)[.]?\Z', '')

                                  # match various forms of "untreated"
    untreatedRegex = str(r'\A(?:' +
            r'(?:(?:untreated|not treated|no (?:special )?treate?ments?)\b.*)' +
            r'|(?:(?:nothing|none|no)[.]?)' +
            r')\Z')

    treatmentFieldMapping = TextMapping('treatment', untreatedRegex, '')
    treatmentProtFieldMapping = TextMapping('treatmentProt', untreatedRegex, '')

    NaTransformer = TextTransformer([NaMapping])
    treatmentProtFieldTransformer = TextTransformer([treatmentProtFieldMapping])
    treatmentFieldTransformer = TextTransformer([treatmentFieldMapping])

    def fieldValue2Text(self, f, v):
        """ Return the formated field-value text"""
        # Tried various ideas.
        # See https://mgi-jira.atlassian.net/browse/YAKS-306
        #  and https://mgi-jira.atlassian.net/browse/YAKS-354
        return self.fieldValue2Text_fs_nountreat(f,v) # using this method
        #return self.fieldValue2Text_v_untreat(f,v)
        #return self.fieldValue2Text_fv_untreat(f,v)
        #return self.fieldValue2Text_fv_nountreat(f,v)
        #return self.fieldValue2Text_v_nountreat(f,v)
        #return self.fieldValue2Text_fs_untreat(f,v)

    #-----------------------------------

    commonFields = ['source',           # these are the most common field names
                    'taxid',
                    'title',
                    'taxidValue',
                    'sType',
                    'molecule',
                    'description',
                    'treatmentProt',
                    'tissue',
                    'strain',
                    'cell type',
                    'age',
                    'genotype',
                    'treatment',
                    'genotype/variation',
                    'gender',
                    'Sex',
                    ]

    def fieldValue2Text_fs_nountreat(self, f, v):       # using this method
        """
        Return formated field-value text for the given field,value pair
            Return '' for "Not Applicable" variations for any field.
            Else return 'field : value;' if a non-common field
                 return 'value;' if it is a common field
        """
        if self.NaTransformer.transformText(v) == '':
            return ''
        else:
            if f in self.commonFields: return '%s;' % (v)
            else: return '%s : %s;' % (f, v)
    #-----------------------------------
    # other different ways to format the field:value that I tried

    def fieldValue2Text_fs_untreat(self, f, v):
        """
        Return formated field-value text for the given field,value pair
            Return '' for "Not Applicable" variations for any field.
            Return '__untreated;' for 'treatment' and 'treatmentProt' fields
                whose value means "not treated"
            Else return 'field : value;' if a non-common field
                 return 'value;' if it is a common field
        """
        if self.NaTransformer.transformText(v) == '':
            return ''
        elif (f == 'treatmentProt' and
                self.treatmentProtFieldTransformer.transformText(v) == ''):
            return '__untreated;'
        elif (f == 'treatment' and
                self.treatmentFieldTransformer.transformText(v) == ''):
            return '__untreated;'
        else:
            if f in self.commonFields: return '%s;' % (v)
            else: return '%s : %s;' % (f, v)
    #-----------------------------------

    def fieldValue2Text_fv_untreat(self, f, v):
        """
        Return formated field-value text for the given field,value pair
            Return '' for "Not Applicable" variations for any field.
            Return '__untreated;' for 'treatment' and 'treatmentProt' fields
                whose value means "not treated"
            Else return 'field : value;'
        """
        if self.NaTransformer.transformText(v) == '':
            return ''
        elif (f == 'treatmentProt' and
                self.treatmentProtFieldTransformer.transformText(v) == ''):
            return '__untreated;'
        elif (f == 'treatment' and
                self.treatmentFieldTransformer.transformText(v) == ''):
            return '__untreated;'
        else:
            return '%s : %s;' % (f, v)
    #-----------------------------------

    def fieldValue2Text_fv_nountreat(self, f, v):
        """
        Return formated field-value text for the given field,value pair
            Return '' for "Not Applicable" variations for any field.
            Else return 'field : value;'
        """
        if self.NaTransformer.transformText(v) == '':
            return ''
        else:
            return '%s : %s;' % (f, v)
    #-----------------------------------

    def fieldValue2Text_v_nountreat(self, f, v):
        """
        Return formated field-value text for the given field,value pair
            Just return the value.
        """
        return '%s;' % (v)
    #-----------------------------------

    def fieldValue2Text_v_untreat(self, f, v):
        """
        Return formated field-value text for the given field,value pair
            Return '__untreated;' for 'treatment' and 'treatmentProt' fields
                whose value means "not treated"
            Else return 'value;'
        """
        if (f == 'treatmentProt' and
                self.treatmentProtFieldTransformer.transformText(v) == ''):
            return '__untreated;'
        elif (f == 'treatment' and
                self.treatmentFieldTransformer.transformText(v) == ''):
            return '__untreated;'
        else:
            return '%s;' % (v)
# end class RawSampleTextManager -----------------------------------
#-----------------------------------

def getArgs():

    parser = argparse.ArgumentParser( \
        description='Get raw sample text for a GEO experiment, write to stdout')

    parser.add_argument('exp_key', default=None,
        help="experiment key to get raw sample text for, or 'report' " +
            "to see all text transformations on all raw samples")

    parser.add_argument('-q', '--quiet', dest='verbose', action='store_false',
        required=False, help="skip helpful messages to stderr")

    defaultHost = os.environ.get('PG_DBSERVER', 'bhmgidevdb01')
    defaultDatabase = os.environ.get('PG_DBNAME', 'prod')

    parser.add_argument('-s', '--server', dest='server', action='store',
        required=False, default=defaultHost,
        help='db server. Shortcuts:  adhoc, prod, dev, test. (Default %s)' %
                defaultHost)

    parser.add_argument('-d', '--database', dest='database', action='store',
        required=False, default=defaultDatabase,
        help='which database. Example: mgd (Default %s)' % defaultDatabase)

    args =  parser.parse_args()

    if args.server == 'adhoc':
        args.host = 'mgi-adhoc.jax.org'
        args.db = 'mgd'
    elif args.server == 'prod':
        args.host = 'bhmgidb01.jax.org'
        args.db = 'prod'
    elif args.server == 'dev':
        args.host = 'mgi-testdb4.jax.org'
        args.db = 'jak'
    elif args.server == 'test':
        args.host = 'bhmgidevdb01.jax.org'
        args.db = 'prod'
    else:
        args.host = args.server
        args.db = args.database

    return args
#-----------------------------------

if __name__ == "__main__":
    import db

    args = getArgs()
    beVerbose = args.verbose
    db.set_sqlServer  (args.host)
    db.set_sqlDatabase(args.db)
    db.set_sqlUser    ("mgd_public")
    db.set_sqlPassword("mgdpub")

    verbose("%s\nHitting database %s %s as mgd_public\n" % \
                                    (time.ctime(), args.host, args.db,))

    # get raw sample text for all experiments
    rstm = RawSampleTextManager(db, expTbl="gxd_htexperiment")

    if args.exp_key == "report":
        # iterate through all GEO experiments, getting their text, then report
        #  the text transformations that were performed.
        q = """ select e._experiment_key
                from gxd_htexperiment e join acc_accession a on
                (a._object_key = e._experiment_key and a._mgitype_key = 42
                and a._logicaldb_key = 190) -- GEO series
            """
        results = db.sql(q, 'auto')
        for i,r in enumerate(results):
            text = rstm.getRawSampleText(r['_experiment_key'])
        print("Num experiments: %d" % rstm.getNumExperiments())
        print("Num field-value pairs: %d" % rstm.getNumFieldValuePairs())
        print(rstm.getReport())
    else:       # get text for one _experiment_key
        text = rstm.getRawSampleText(args.exp_key)
        print(text)
