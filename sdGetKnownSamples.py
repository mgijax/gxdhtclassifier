#!/usr/bin/env python3
'''
  Purpose:
           run sql to get GEO experiment known samples to use for training
                & validation/testing
           (minor) Data transformations include:
            replacing non-ascii chars with ' '
            replacing FIELDSEP and RECORDSEP chars in the doc text w/ ' '

  Outputs:      Delimited file to stdout
                See htMLsample.ClassifiedSample for output format
'''
import sys
import os
import time
import argparse
import unittest
import db
import htMLsample as mlSampleLib
from utilsLib import removeNonAscii, TextMapping, TextTransformer
#-----------------------------------

sampleObjType = mlSampleLib.ClassifiedHtSample

# for the Sample output file
RECORDEND    = sampleObjType.getRecordEnd()
FIELDSEP     = sampleObjType.getFieldSep()
#-----------------------------------

def getArgs():

    parser = argparse.ArgumentParser( \
        description='Get SampleSets for training gxdhtclassifier, write to stdout')

    parser.add_argument('option', action='store', default='counts',
        choices=['counts', 'geo', 'nongeo', 'test'],
        help='which subset of training samples to get or "counts"' +
             ' or just run automated tests')

    parser.add_argument('-l', '--limit', dest='nResults',
        required=False, type=int, default=0, 		# 0 means ALL
        help="limit results to n references. Default is no limit")

    parser.add_argument('--textlength', dest='maxTextLength',
        type=int, required=False, default=None,
        help="only include the 1st n chars of text fields (for debugging)")

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
        args.host = args.server + '.jax.org'
        args.db = args.database

    return args
#-----------------------------------

args = getArgs()

#-----------------------------------
# Supported Sample Sets - each is populated in its own temp table
GEO_OUTPUT_TITLE  = 'GEO experiments evaluated by Connie'
GEO_TMPTBL = 'tmp_geoexp'
NON_GEO_OUTPUT_TITLE  = 'Non-GEO, Yes experiments evaluated by Connie'
NON_GEO_TMPTBL = 'tmp_nongeoexp'
RAW_SAMPLE_TMPTBL = "tmp_rawsample_text"

def loadTmpTables():
    '''
    Select the appropriate HT experiments to be used and put them in the
    tmp tables. Columns:
        _experiment_key
        ID (GEO ID if available)
        knownClassName (evaluation state: "Yes" or "No")
        title
        description
        curationState
        studytype
        experimenttype
        modification_date
        titleLength
        descriptionLength
    '''
    # Populate GEO_TMPTBL: evaluated GEO experiments
    q = ["""
        create temporary table %s as
        select e._experiment_key, a.accid as ID, t.term as knownClassName,
            t2.term as curationState,
            t3.term as studytype,
            t4.term as experimenttype,
            to_char(e.modification_date, 'YYYY-MM-DD') as modification_date,
            length(e.name) as titleLength,
            length(e.description) as descriptionLength,
            e.name as title, e.description
        from gxd_htexperiment e
            join voc_term t on (e._evaluationstate_key = t._term_key)
            join voc_term t2 on (e._curationstate_key  = t2._term_key)
            join voc_term t3 on (e._studytype_key      = t3._term_key)
            join voc_term t4 on (e._experimenttype_key = t4._term_key)
            join acc_accession a on
                (a._object_key = e._experiment_key and a._mgitype_key = 42
                and a._logicaldb_key = 190) -- GEO series
        where
        e._evaluatedby_key = 1064 -- connie
        and t.term in ('Yes', 'No')
        """ % (GEO_TMPTBL),
        """
        create index tmp_idx1 on %s(_experiment_key)
        """ % (GEO_TMPTBL),
        ]
    results = db.sql(q, 'auto')

    # Populate NON_GEO_TMPTBL: evaluated 'Yes' experiments
    #  These are additional 'Yes' experiments
    q = ["""
        create temporary table %s as
        select e._experiment_key, a.accid as ID, t.term as knownClassName,
            t2.term as curationState,
            t3.term as studytype,
            t4.term as experimenttype,
            to_char(e.modification_date, 'YYYY-MM-DD') as modification_date,
            length(e.name) as titleLength,
            length(e.description) as descriptionLength,
            e.name as title, e.description
        from gxd_htexperiment e
            join voc_term t on (e._evaluationstate_key = t._term_key)
            join voc_term t2 on (e._curationstate_key  = t2._term_key)
            join voc_term t3 on (e._studytype_key      = t3._term_key)
            join voc_term t4 on (e._experimenttype_key = t4._term_key)
            join acc_accession a on
                (a._object_key = e._experiment_key and a._mgitype_key = 42
                and a._logicaldb_key = 189) -- Array express
        where
        e._evaluatedby_key = 1064 -- connie
        and t.term = 'Yes'
        and not exists
        (select 1 from %s te where (te._experiment_key = e._experiment_key))
        """ % (NON_GEO_TMPTBL, GEO_TMPTBL),
        """
        create index tmp_idx2 on %s(_experiment_key)
        """ % (NON_GEO_TMPTBL),
        ]
    results = db.sql(q, 'auto')

    # Populate RAW_SAMPLE_TMPTBL "key:value" pairs for GEO experiments
    startTime = time.time()
    #verbose("Building raw sample tmp table...")
    q = ["""
        create temporary table %s as
        select distinct rs._experiment_key, kv.key, kv.value
        from
            %s gt join GXD_HTRawSample rs on
                    (gt._experiment_key = rs._experiment_key)
            join MGI_KeyValue kv on
                    (rs._rawsample_key = kv._object_key and _mgitype_key = 47)
        order by rs._experiment_key, kv.key, kv.value
        """ % (RAW_SAMPLE_TMPTBL, GEO_TMPTBL),
        """
        create index tmp_idx3 on %s(_experiment_key)
        """ % (RAW_SAMPLE_TMPTBL),
        ]
    results = db.sql(q, 'auto')
    #verbose("%8.3f seconds\n\n" %  (time.time()-startTime))
#-----------------------------------

class RawSampleTextManager (object):
    """
    IS:  a class that knows how to gather and format the raw sample metadata
        text for experiments
    HAS: 
    DOES: getRawSampleText( for an experiment )
    """
    def __init__(self, rawSampleTblName):
        self.experimentDict = {}        # experimentDict[exp_key] is a
                                        #   set of (field,value) pairs
                                        #   from the samples of that experiment
        self.buildExperimentDict(rawSampleTblName)
    #-----------------------------------

    def buildExperimentDict(self, rawSampleTblName):
        #verbose("Getting raw sample text from %s\n" % rawSampleTblName)

        q = "select * from %s" % rawSampleTblName
        results = db.sql(q, 'auto')
        for i,r in enumerate(results):
            try:
                expKey = r['_experiment_key']
                theSet = self.experimentDict.setdefault(expKey, set())

                field = removeNonAscii(cleanDelimiters(str(r['key']))).strip()
                value = removeNonAscii(cleanDelimiters(str(r['value']))).strip()

                theSet.add((field, value))
            except:         # if some error, try to report which record
                sys.stderr.write("Error on record %d:\n%s\n" % (i, str(r)))
                raise
    #-----------------------------------

    def getRawSampleText(self, expKey):
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
        return self.fieldValue2Text_justValue(f,v)

    #-----------------------------------
    # several different ways to format the field:value text to try

    def fieldValue2Text_1(self, f, v):
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

    def fieldValue2Text_justValue(self, f, v):
        """
        Return formated field-value text for the given field,value pair
            Just return the value.
        """
        return '%s;' % (v)
    #-----------------------------------

    def fieldValue2Text_2(self, f, v):
        """
        Return formated field-value text for the given field,value pair
            Return '' for "Not Applicable" variations for any field.
            Return '__untreated;' for 'treatment' and 'treatmentProt' fields
                whose value means "not treated"
            Else return 'value;'
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
            return '%s;' % (v)
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

# end class RawSampleTextManager -----------------------------------
#-----------------------------------
# Automated unit tests

class RawSampleTextManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rstm = RawSampleTextManager(RAW_SAMPLE_TMPTBL)

    @classmethod
    def tearDownClass(cls):
        print(cls.rstm.getReport())

    def test_fieldValue2Text_NA(self):
        r = self.rstm
        na = ''                 # expected value for a recognized "NA" value
        self.assertEqual(r.fieldValue2Text_1('f','NA'), na)
        self.assertEqual(r.fieldValue2Text_1('f','N/A'), na)
        self.assertEqual(r.fieldValue2Text_1('f','N.A.'), na)
        self.assertEqual(r.fieldValue2Text_1('f','NAT'), 'f : NAT;')
        self.assertEqual(r.fieldValue2Text_1('f','NA T'), 'f : NA T;')
        self.assertEqual(r.fieldValue2Text_1('f','ctrl'), na)
        self.assertEqual(r.fieldValue2Text_1('f','Control'), na)
        self.assertEqual(r.fieldValue2Text_1('f','Not Applicable.'), na)
        self.assertEqual(r.fieldValue2Text_1('treatment','N/A'), na)
        self.assertEqual(r.fieldValue2Text_1('treatmentProt','N/A'), na)

    def test_fieldValue2Text_treatment(self):
        r = self.rstm
        f = 'treatment'         # treatment field name, some tests w/ this name
        unt = '__untreated;'    # expected value for "untreated" value
        self.assertEqual(r.fieldValue2Text_1(f,'Not Treated'), unt)
        self.assertEqual(r.fieldValue2Text_1(f,'Not Treated & stuff'), unt)
        self.assertEqual(r.fieldValue2Text_1(f,'No special treatments, but'), unt)
        self.assertEqual(r.fieldValue2Text_1(f,'No'), unt)
        self.assertEqual(r.fieldValue2Text_1(f,'none.'), unt)
        self.assertNotEqual(r.fieldValue2Text_1(f,'nothing but..'), unt)
        
        # not treatment field
        f = 'f'
        self.assertEqual(r.fieldValue2Text_1(f,'No'), 'f : No;')
        self.assertEqual(r.fieldValue2Text_1(f,'Not Treated'),'f : Not Treated;')

    def test_fieldValue2Text_treatmentProt(self):
        r = self.rstm
        f = 'treatmentProt'  # treatmentProt field name, some tests w/ this name
        unt = '__untreated;'    # expected value for "untreated" value
        self.assertEqual(r.fieldValue2Text_1(f,'Not Treated'), unt)
        self.assertEqual(r.fieldValue2Text_1(f,'Not Treated & stuff'), unt)
        self.assertEqual(r.fieldValue2Text_1(f,'No special treatments, but'), unt)
        self.assertEqual(r.fieldValue2Text_1(f,'No'), unt)
        self.assertEqual(r.fieldValue2Text_1(f,'none.'), unt)
        self.assertNotEqual(r.fieldValue2Text_1(f,'nothing but..'), unt)

        # not treatmentProt field
        f = 'f'
        self.assertEqual(r.fieldValue2Text_1(f,'No'), 'f : No;')
        self.assertEqual(r.fieldValue2Text_1(f,'Not Treated'),'f : Not Treated;')
# end Automated unit tests ------------------------
#-----------------------------------

def doAutomatedTests():

    sys.stdout.write("%s\nHitting database %s %s as mgd_public\n" % \
                                        (time.ctime(), args.host, args.db,))
    sys.stdout.write("Running automated unit tests...\n")
    unittest.main(argv=[sys.argv[0], '-v'],)
#-----------------------------------

def doCounts():
    '''
    Get counts of experiment records from tmp tables and write them to stdout.
    Do some validations to make sure we don't have false assumptions.
    '''
    sys.stdout.write("%s\nHitting database %s %s as mgd_public\n" % \
                                        (time.ctime(), args.host, args.db,))
    ### Counts from the GEO tmptbl
    q = """select count(*) as num from %s e
        """ % (GEO_TMPTBL)
    numRows = db.sql(q, 'auto')[0]['num']

    q = """select count(distinct e._experiment_key) as num from %s e
        """ % (GEO_TMPTBL)
    numExp = db.sql(q, 'auto')[0]['num']

    assert (numRows == numExp), "Some experiment is repeated"

    q = """select count(distinct e._experiment_key) as num from %s e
           where e.knownClassName = 'Yes'
        """ % (GEO_TMPTBL)
    numYes = db.sql(q, 'auto')[0]['num']

    q = """select count(distinct e._experiment_key) as num from %s e
           where e.knownClassName = 'No'
        """ % (GEO_TMPTBL)
    numNo = db.sql(q, 'auto')[0]['num']

    assert (numYes + numNo  == numExp), "Yes/No counts don't add up"

    sys.stdout.write(GEO_OUTPUT_TITLE + '\n')
    sys.stdout.write("%7d (%d%%) Yes\t%7d (%d%%) No\t%7d total\n" \
            % (numYes, 100*(numYes/numExp), numNo, 100*(numNo/numExp), numExp))

    # number of GEO with raw source data    - expected to be most of them
    q = """select count(distinct e._experiment_key) as num
            from %s e join %s rs on (e._experiment_key = rs._experiment_key)
        """ % (GEO_TMPTBL, RAW_SAMPLE_TMPTBL)
    numRS = db.sql(q, 'auto')[0]['num']
    sys.stdout.write("%7d have raw sample text\n" % (numRS))

    ### Counts from the non-GEO tmptbl
    q = """select count(*) as num from %s e
        """ % (NON_GEO_TMPTBL)
    ngNumRows = db.sql(q, 'auto')[0]['num']

    q = """select count(distinct e._experiment_key) as num from %s e
        """ % (NON_GEO_TMPTBL)
    ngNumExp = db.sql(q, 'auto')[0]['num']

    assert (ngNumRows == ngNumExp), "Some non-GEO experiment is repeated"

    sys.stdout.write(NON_GEO_OUTPUT_TITLE + '\n')
    sys.stdout.write("%7d experiments\n" % (ngNumRows))

    # number of non-GEO with raw source data    - expected to be 0
    q = """select count(distinct e._experiment_key) as num
            from %s e join %s rs on (e._experiment_key = rs._experiment_key)
        """ % (NON_GEO_TMPTBL, RAW_SAMPLE_TMPTBL)
    numRS = db.sql(q, 'auto')[0]['num']
    sys.stdout.write("%7d have raw sample text\n" % (numRS))

    ### Totals
    sys.stdout.write("Total experiments\n")
    numYes += ngNumExp
    numExp += ngNumExp
    sys.stdout.write("%7d (%d%%) Yes\t%7d (%d%%) No\t%7d total\n" \
            % (numYes, 100*(numYes/numExp), numNo, 100*(numNo/numExp), numExp))

    ### Counts from Raw sample tmp table
    q = """select count(*) as num from %s e
        """ % (RAW_SAMPLE_TMPTBL)
    rsNumRows = db.sql(q, 'auto')[0]['num']

    sys.stdout.write(RAW_SAMPLE_TMPTBL + '\n')
    sys.stdout.write("%9d key/value pairs\n" % (rsNumRows))
#-----------------------------------

def doSamples():
    ''' Write known samples to stdout.
    '''
    startTime = time.time()
    verbose("%s\nHitting database %s %s as mgd_public\n" % \
                                        (time.ctime(), args.host, args.db,))

    # Which set of samples, which tmp table
    if args.option == "geo":
        tmptbl = GEO_TMPTBL
        rstm = RawSampleTextManager(RAW_SAMPLE_TMPTBL)
    elif args.option == "nongeo":
        tmptbl = NON_GEO_TMPTBL
        rstm = None       # non-GEO experiments don't have raw samples in db
    else:
        sys.stderr.write("Bad option: %s\n" % args.option)
        exit(5)

    # Build sql
    q = """select * from %s\n""" % (tmptbl)
    if args.nResults != 0:
        limitClause = 'limit %d\n' % args.nResults
        q += limitClause

    # Output results
    outputSampleSet = mlSampleLib.ClassifiedSampleSet(\
                                                sampleObjType=sampleObjType)
    results = db.sql(q, 'auto')
    verbose("constructing and writing %s samples:\n" % args.option)
    for i,r in enumerate(results):
        try:
            if rstm:             ## get raw sample text, if any
                expKey = r['_experiment_key']
                rawSampleText = rstm.getRawSampleText(expKey)
            else:
                rawSampleText = ''

            sample = sqlRecord2ClassifiedSample(r, rawSampleText)
            outputSampleSet.addSample(sample)
        except:         # if some error, try to report which record
            sys.stderr.write("Error on record %d:\n%s\n" % (i, str(r)))
            raise

    outputSampleSet.setMetaItem('host', args.host)
    outputSampleSet.setMetaItem('db', args.db)
    outputSampleSet.setMetaItem('time', time.strftime("%Y/%m/%d-%H:%M:%S"))
    outputSampleSet.write(sys.stdout)

    verbose("wrote %d samples:\n" % outputSampleSet.getNumSamples())
    if rstm:
        verbose(rstm.getReport())
    verbose("%8.3f seconds\n\n" %  (time.time()-startTime))

    return
#-----------------------------------

def sqlRecord2ClassifiedSample(r,               # sql Result record
                               rawSampleText,   # text from raw sample metadata 
    ):
    """
    Encapsulates knowledge of ClassifiedSample.setFields() field names
    """
    newR = {}
    newSample = sampleObjType()

    if len(rawSampleText) > 0:          # add separator to mark beginning
        rawSampleText = " .. " + rawSampleText

    ## populate the Sample fields
    newR['knownClassName']    = str(r['knownclassname'])
    newR['ID']                = str(r['id'])
    newR['curationState']     = str(r['curationstate'])
    newR['studytype']         = str(r['studytype'])
    newR['experimenttype']    = str(r['experimenttype'])
    newR['modification_date'] = str(r['modification_date'])
    newR['titleLength']       = str(r['titlelength'])
    newR['descriptionLength'] = str(r['descriptionlength'])
    newR['title']             = cleanUpTextField(r,'title')
    newR['description']       = cleanUpTextField(r,'description') +rawSampleText

    return newSample.setFields(newR)
#-----------------------------------

def cleanUpTextField(rcd,
                    textFieldName,
    ):
    text = rcd[textFieldName]
    if text == None:
        text = ''

    if args.maxTextLength:	# handy for debugging
        text = text[:args.maxTextLength]
        text = text.replace('\n', ' ')

    text = removeNonAscii(cleanDelimiters(text))
    return text
#-----------------------------------

def cleanDelimiters(text):
    """ remove RECORDEND and FIELDSEPs from text (replace w/ ' ')
    """
    return text.replace(RECORDEND,' ').replace(FIELDSEP,' ')
#-----------------------------------

def verbose(text):
    if args.verbose:
        sys.stderr.write(text)
        sys.stderr.flush()
#-----------------------------------

def main():
    db.set_sqlServer  (args.host)
    db.set_sqlDatabase(args.db)
    db.set_sqlUser    ("mgd_public")
    db.set_sqlPassword("mgdpub")

    loadTmpTables()

    if args.option == 'test': doAutomatedTests()
    elif args.option == 'counts': doCounts()
    else: doSamples()
#-----------------------------------
if __name__ == "__main__":
    main()
