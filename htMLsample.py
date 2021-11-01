#!/usr/bin/env python3
#
# Library to support handling of GXD HT experiment records (ML samples)
# Yikes. By "sample" here, I mean a "sample for a ML classifier", i.e.,
#   an experiment record with some text to classify
# NOT a biological sample in a high throughput experiment.
#
# There are automated unit tests for this module: JIM NOT YET
#   cd test
#   python test_htMLsample.py -v
#
import re
from baseSampleDataLib import *
import utilsLib
from htTextTransform import TextTransformer, AllMappings, \
                            AllMappingsButTreatment
#-----------------------------------

FIELDSEP     = '|'      # field separator when reading/writing sample fields
RECORDEND    = '\n'     # record ending str when reading/writing sample files

#-----------------------------------
# Regex's used in sample preprocessors
urls_re      = re.compile(r'\b(?:https?://|www[.]|doi)\S*',re.IGNORECASE)
token_re     = re.compile(r'\b([a-z_]\w+)\b',re.IGNORECASE)

stemmer = None		# see preprocessor below

# Instantiate TextTransformers used by various preprocessors
textTransformer_all = TextTransformer(AllMappings)
textTransformer_allButTreatment = TextTransformer(AllMappingsButTreatment)

#-----------------------------------

class HtSample (BaseSample):
    """
    Represents a GXD HT experiment (text title, description, etc.) that may be
    classified or not.

    HAS: ID, title, description

    Provides various methods to preprocess a sample record
    (preprocess the text prior to vectorization)
    """
    sampleClassNames = ['No','Yes']
    y_positive = 1	# sampleClassNames[y_positive] is the "positive" class
    y_negative = 0	# ... negative

    # fields of a sample as an input/output record (as text), in order
    fieldNames = [ \
            'ID'            ,
            'title'         ,
            'description'   ,
            ]
    fieldSep  = FIELDSEP
    recordEnd = RECORDEND

    preprocessorsToReport = set()  # set of objects w/ a getReports() method
                                   #   to include in getPreprocessorReport()
    #----------------------

    def constructDoc(self):
        return '\n'.join([self.getTitle(), self.getDescription()])

    def setDescription(self, t): self.values['description'] = t
    def getDescription(self,  ): return self.values['description']

    def setTitle(self, t): self.values['title'] = t
    def getTitle(self,  ): return self.values['title']

    #----------------------
    # "preprocessor" functions.
    #  Each preprocessor should modify this sample and return itself
    #----------------------

    def removeURLsCleanStem(self):	# preprocessor
        '''
        Remove URLs and punct, lower case everything,
        Convert '-/-' to 'mut_mut',
        Keep tokens that start w/ letter or _ and are 2 or more chars.
        Stem,
        Replace \n with spaces
        '''
        # NOT IMPLEMENTED
        # This is currently the only preprocessor that uses a stemmer.
        # Would be clearer to import and instantiate one stemmer above,
        # BUT that requires nltk (via anaconda) to be installed on each
        # server we use. This is currently not installed on our linux servers
        # By importing here, we can use RefSample in situations where we don't
        # call this preprocessor, and it will work on our current server setup.
        #global stemmer
        #if not stemmer:
        #    import nltk.stem.snowball as nltk
        #    stemmer = nltk.EnglishStemmer()
        #------
        #def _removeURLsCleanStem(text):
        #    output = ''
        #    for s in urls_re.split(text): # split and remove URLs
        #        s = textTransform.transformText(s).lower()
        #        for m in token_re.finditer(s):
        #            output += " " + stemmer.stem(m.group())
        #    return  output
        #------

        #self.setTitle( _removeURLsCleanStem( self.getTitle()) )
        #self.setAbstract( _removeURLsCleanStem( self.getAbstract()) )
        #self.setExtractedText( _removeURLsCleanStem( self.getExtractedText()) )
        return self
    # ---------------------------

    def textTransform_all(self):		# preprocessor
        '''
        Apply text transformations
        '''
        tt = textTransformer_all
        self.addPreprocessorToReport(tt)
        self.setTitle(tt.transformText(self.getTitle()))
        self.setDescription(tt.transformText(self.getDescription()))
        return self
    # ---------------------------

    def textTransform_allButTreatment(self):		# preprocessor
        '''
        Apply text transformations
        '''
        tt = textTransformer_allButTreatment
        self.addPreprocessorToReport(tt)
        self.setTitle(tt.transformText(self.getTitle()))
        self.setDescription(tt.transformText(self.getDescription()))
        return self
    # ---------------------------

    def stem(self):		# preprocessor
        '''
        Stem tokens. Also converts everything to lower case
        '''
        global stemmer
        if not stemmer:
            import nltk.stem.snowball as nltk
            stemmer = nltk.EnglishStemmer()
        def _stem(text):
            stemmedTokens = []
            for m in token_re.finditer(text):
                stemmedTokens.append(stemmer.stem(m.group()))
            return " ".join(stemmedTokens)

        self.setTitle(_stem(self.getTitle()))
        self.setDescription(_stem(self.getDescription()))
        return self
    # ---------------------------

    def removeURLs(self):		# preprocessor
        '''
        Remove URLs, lower case everything,
        '''
        self.setTitle( utilsLib.removeURLsLower( self.getTitle()) )
        self.setDescription( utilsLib.removeURLsLower( self.getDescription() ) )
        return self
    # ---------------------------

    def tokenPerLine(self):		# preprocessor
        """
        Convert text to have one alphanumeric token per line,
            removing punctuation.
        Makes it easier to examine the tokens/features
        """
        self.setTitle( utilsLib.tokenPerLine( self.getTitle()) )
        self.setDescription( utilsLib.tokenPerLine( self.getDescription()) )
        return self
    # ---------------------------

    def truncateText(self):		# preprocessor
        """ for debugging, so you can see a sample record easily"""
        
        self.setTitle( self.getTitle()[:10].replace('\n',' ') )
        self.setDescription( self.getDescription()[:20].replace('\n',' ') )
        return self
    # ---------------------------

    def removeText(self):		# preprocessor
        """ for debugging, so you can see a sample record easily"""
        
        self.setTitle( self.getTitle()[:10].replace('\n',' ') )
        self.setDescription( 'description...' )
        return self
    # ---------------------------

    @classmethod
    def addPreprocessorToReport(cls, processor):
        cls.preprocessorsToReport.add(processor)

    @classmethod
    def getPreprocessorReport(cls):
        """ Return report text from preprocessor objects
        """
        text = ''
        for p in cls.preprocessorsToReport:
            text += p.getReport() + '\n'
        return text

# end class HtSample ------------------------

class ClassifiedHtSample (HtSample, ClassifiedSample):
    """
    A GXD HT experiment Sample that is classified as relevant or not
    """
    fieldNames = [ \
            'knownClassName',
            'ID',
            'curationState',
            'studytype',
            'experimenttype'  ,
            'modification_date',
            'titleLength',
            'descriptionLength',
            'title',
            'description',
            ]
    extraInfoFieldNames = [ \
            'curationState',
            'studytype',
            'experimenttype',
            'modification_date',
            'titleLength',
            'descriptionLength',
            ]
    #----------------------

    def setFields(self, values,		# dict
        ):
        ClassifiedSample.setFields(self, values)
        return self

    def constructDoc(self):
        return HtSample.constructDoc(self)
        
    #def setComputedExtraInfoFields(self):
    #    self.extraInfo['abstractLen'] = str( len(self.getAbstract()) )
    #    self.extraInfo['textLen']     = str( len(self.getExtractedText()) )
    #----------------------
# end class ClassifiedHtSample ------------------------

if __name__ == "__main__":
    pass
