import sys
import textTuningLib as tl
import sklearnHelperLib as skHelper
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
#from sklearn.preprocessing import StandardScaler, MaxAbsScaler
from sklearn.ensemble import GradientBoostingClassifier
#-----------------------
args = tl.args
randomSeeds = tl.getRandomSeeds( { 	# None means generate a random seed
                'randForSplit'      : args.randForSplit,
                'randForClassifier' : args.randForClassifier,
                } )
pipeline = Pipeline( [
('vectorizer', CountVectorizer(
#('vectorizer', TfidfVectorizer(
                #strip_accents=None,
                #decode_error='strict',
                #lowercase=True,
                stop_words='english',
                binary=True,
                token_pattern=r'\b([a-z_]\w+)\b',
                min_df=0.01,    # for GB, .01 did a little better than .02
                max_df=0.75,
                ngram_range=(1,2),
                ),),
('featureEvaluator', skHelper.FeatureDocCounter()),
('classifier', GradientBoostingClassifier(verbose=1, 
                random_state=randomSeeds['randForClassifier'],
                learning_rate=0.2,
                n_estimators=200,
                subsample=0.8,
                max_features='sqrt',
                max_depth=4,
                min_samples_split=35,
                min_samples_leaf=20,
                ) ),
] )
parameters={
#        'vectorizer__ngram_range': [(1,2),],
#        'vectorizer__min_df': [0.02,],
#        'vectorizer__max_df': [0.75,],
#	'classifier__learning_rate': [0.1, 0.15, 0.2,],
#	'classifier__n_estimators': [100, 150, 200],
#	'classifier__max_depth': [3, 4, ],
#	'classifier__min_samples_split': range(5,36,5),
#	'classifier__min_samples_leaf': range(10,31, 5),
#	'classifier__max_features': [20, 25, 30, 35, 40, None, ],
#	'classifier__subsample': [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0,],
        }
note='\n'.join([ "GB, tuning", ]) + '\n'
p = tl.TextPipelineTuningHelper( pipeline, parameters, randomSeeds=randomSeeds,
                note=note,).fit()
print(p.getReports())
