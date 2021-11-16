#!/usr/bin/env python3
'''
  Purpose:
           run sql to get GEO experiment known samples to use for training
                & validation/testing
           (minor) Data transformations include:
            replacing non-ascii chars with ' '
            replacing FIELDSEP and RECORDSEP chars in the doc text w/ ' '

            To run automated tests: python sdGetKnownSamples.py test

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
import htRawSampleTextManager
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
        args.host = args.server
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
#-----------------------------------

def doAutomatedTests():

    sys.stdout.write("No automated tests at this time\n")
    return

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
    rstm = htRawSampleTextManager.RawSampleTextManager(db,expTbl=GEO_TMPTBL)
    numRS = rstm.getNumExperiments()
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

    # number of non-GEO with raw source data
    sys.stdout.write("%7d have raw sample text\n" % (0))

    ### Totals
    sys.stdout.write("Total experiments\n")
    numYes += ngNumExp
    numExp += ngNumExp
    sys.stdout.write("%7d (%d%%) Yes\t%7d (%d%%) No\t%7d total\n" \
            % (numYes, 100*(numYes/numExp), numNo, 100*(numNo/numExp), numExp))

    ### Counts of Raw sample text data
    sys.stdout.write("Number of distinct raw sample field value pairs\n")
    sys.stdout.write("%9d key/value pairs\n" % (rstm.getNumFieldValuePairs()))
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
        rstm = htRawSampleTextManager.RawSampleTextManager(db,expTbl=GEO_TMPTBL)
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
