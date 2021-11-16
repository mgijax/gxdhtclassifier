#!/usr/bin/env python3

"""
Automated unit tests for htRawSampleTextManager.py

usage:  python test_htRawSampleTextManager.py [-v]
"""

import sys
import os
import unittest
from htRawSampleTextManager import RawSampleTextManager

import db

# get database settings from the env

dbServer = os.environ.get('PG_DBSERVER', 'mgi-testdb4.jax.org')
dbName   = os.environ.get('PG_DBNAME', 'jak')

db.set_sqlServer  (dbServer)
db.set_sqlDatabase(dbName)
db.set_sqlUser    ("mgd_public")
db.set_sqlPassword("mgdpub")

sys.stderr.write("Hitting %s.%s\n" % (dbServer, dbName))

#######################################

class RawSampleTextManager_tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rstm = RawSampleTextManager(db)

    @classmethod
    def tearDownClass(cls):
        print(cls.rstm.getReport())

    def test_getNumExperiments(self):
        num = self.rstm.getNumExperiments()
        self.assertGreater(num, 36000)

    def test_getNumFieldValuePairs(self):
        num = self.rstm.getNumFieldValuePairs()
        self.assertGreater(num, 650000)

    def test_getRawSampleText(self):
        text = self.rstm.getRawSampleText(60975)
        self.assertGreater(text.find('ovarian tumor'), -1)
        self.assertEqual(text.find('football'), -1)

    def test_tmpTable(self):
        # test populating a RawSampleTextManager from a tmp table w/ a few experiments in it
        q = ["""
            create temporary table tmp_experiments as
            select e._experiment_key
            from gxd_htexperiment e
            where e._experiment_key in (60975, 60974)
            """,
            ]
        results = db.sql(q, 'auto')
        rstm = RawSampleTextManager(db, expTbl='tmp_experiments')

        num = rstm.getNumExperiments()
        self.assertEqual(num, 2)

        text = rstm.getRawSampleText(60974)
        self.assertGreater(text.find('Swiss'), -1)


    def test_fieldValue2Text_fv_untreat_NA(self):
        r = self.rstm
        na = ''                 # expected value for a recognized "NA" value
        self.assertEqual(r.fieldValue2Text_fv_untreat('f','NA'), na)
        self.assertEqual(r.fieldValue2Text_fv_untreat('f','N/A'), na)
        self.assertEqual(r.fieldValue2Text_fv_untreat('f','N.A.'), na)
        self.assertEqual(r.fieldValue2Text_fv_untreat('f','NAT'), 'f : NAT;')
        self.assertEqual(r.fieldValue2Text_fv_untreat('f','NA T'), 'f : NA T;')
        self.assertEqual(r.fieldValue2Text_fv_untreat('f','ctrl'), na)
        self.assertEqual(r.fieldValue2Text_fv_untreat('f','Control'), na)
        self.assertEqual(r.fieldValue2Text_fv_untreat('f','Not Applicable.'),na)
        self.assertEqual(r.fieldValue2Text_fv_untreat('treatment','N/A'),na)
        self.assertEqual(r.fieldValue2Text_fv_untreat('treatmentProt','N/A'),na)

    def test_fieldValue2Text_fv_untreat_treatment(self):
        r = self.rstm
        f = 'treatment'         # treatment field name, some tests w/ this name
        u = '__untreated;'    # expected value for "untreated" value
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'untreated'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'Not Treated'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'Not Treated & foo'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'No special treatments, but'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'No'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'none.'), u)
        self.assertNotEqual(r.fieldValue2Text_fv_untreat(f,'nothing but..'), u)
        
        # not treatment field
        f = 'f'
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'No'), 'f : No;')
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'untreated'),'f : untreated;')

    def test_fieldValue2Text_fv_untreat_treatmentProt(self):
        r = self.rstm
        f = 'treatmentProt'  # treatmentProt field name, some tests w/ this name
        u = '__untreated;'    # expected value for "untreated" value
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'untreated'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'Not Treated'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'Not Treated & foo'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'No special treatments, but'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'No'), u)
        self.assertEqual(r.fieldValue2Text_fv_untreat(f,'none.'), u)
        self.assertNotEqual(r.fieldValue2Text_fv_untreat(f,'nothing but..'), u)

    def test_fieldValue2Text_v_untreat_basic(self):
        r = self.rstm
        f = 'foo'       # arbitrary field name
        v = 'some value'
        self.assertEqual(r.fieldValue2Text_v_untreat(f,v), v +';')
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'Not Treated'), 'Not Treated;')
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'NA'), 'NA;')

    def test_fieldValue2Text_v_untreat_treatmentProt(self):
        r = self.rstm
        f = 'treatmentProt'  # treatmentProt field name, some tests w/ this name
        u = '__untreated;'    # expected value for "untreated" value
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'untreated'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'Not Treated'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'Not Treated & foo'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'No special treatments, but'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'No'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'none.'), u)
        self.assertNotEqual(r.fieldValue2Text_v_untreat(f,'nothing but..'), u)

    def test_fieldValue2Text_v_untreat_treatment(self):
        r = self.rstm
        f = 'treatment'       # treatment field name, some tests w/ this name
        u = '__untreated;'    # expected value for "untreated" value
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'untreated'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'Not Treated'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'Not Treated & foo'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'No special treatments, but'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'No'), u)
        self.assertEqual(r.fieldValue2Text_v_untreat(f,'none.'), u)
        self.assertNotEqual(r.fieldValue2Text_v_untreat(f,'nothing but..'), u)
# end RawSampleTextManager_tests ------------------------
#-----------------------------------

if __name__ == '__main__':
    unittest.main()
