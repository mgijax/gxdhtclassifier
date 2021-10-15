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
#-----------------------
pipeline = Pipeline( [
('vectorizer', CountVectorizer(
#('vectorizer', TfidfVectorizer(
                #strip_accents=None,	# if done in preprocessing
                #decode_error='strict',	# if handled in preproc
                #lowercase=False,	# if done in preprocessing
                stop_words='english',
                binary=True,
                token_pattern=r'\b([a-z_]\w+)\b',
                min_df=0.02,
                max_df=.75,
                ),),
#('featureEvaluator', skHelper.FeatureDocCounter()),
('classifier', GradientBoostingClassifier(verbose=1, 
                random_state=randomSeeds['randForClassifier'],
                #learning_rate=0.05,
                #n_estimators=1600,
                #max_depth=3,
                #min_samples_split=600,
                #min_samples_leaf=150,
                #max_features=0.7,
                #subsample=0.85,
                ) ),
] )
parameters={
        'vectorizer__ngram_range': [(1,2),],
        'vectorizer__min_df': [0.02,],
        'vectorizer__max_df': [0.75,],
	'classifier__learning_rate': [ .1, ],
	'classifier__n_estimators': [200,],
#	'classifier__max_depth': [3, 6, 9 ],
	'classifier__min_samples_split': [2, 5, 10, 20, ],
#	'classifier__min_samples_leaf': [100, 125, 150, 175],
#	'classifier__max_features': [0.6, 0.65, 0.7, 0.75, 0.8, 0.9, None, ],
#	'classifier__subsample': [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0,],
        }
note='\n'.join([ "baseline GB, feature transforms + stemming", ]) + '\n'
p = tl.TextPipelineTuningHelper( pipeline, parameters, randomSeeds=randomSeeds,
                note=note,).fit()
print(p.getReports())
