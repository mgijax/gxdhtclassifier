import sys
import textTuningLib as tl
import sklearnHelperLib as skHelper
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import StandardScaler, MaxAbsScaler
from sklearn.ensemble import RandomForestClassifier
#-----------------------
args = tl.args
randomSeeds = tl.getRandomSeeds( { 	# None means generate a random seed
                'randForSplit'      : args.randForSplit,
                'randForClassifier' : args.randForClassifier,
                } )
pipeline = Pipeline( [
('vectorizer', CountVectorizer(
#('vectorizer', TfidfVectorizer(
                #strip_accents=True,
                #decode_error='strict',
                #lowercase=True,
                stop_words='english',
                binary=True,
                token_pattern=r'\b([a-z_]\w+)\b',
                #min_df=0.02,
                #max_df=0.75,
                ),),
('featureEvaluator', skHelper.FeatureDocCounter()),
('classifier', RandomForestClassifier(verbose=1, class_weight='balanced',
                random_state=randomSeeds['randForClassifier'], n_jobs=-1) ),
] )
parameters={'vectorizer__ngram_range':[(1,2),],
	'vectorizer__min_df':[0.02, ],
	'vectorizer__max_df':[0.75, ],

#	'classifier__max_features': [0.2, 0.5],
#	'classifier__max_depth': [15],
	'classifier__min_samples_split': [100],
#       'classifier__min_samples_leaf': [15,],
       'classifier__n_estimators': [100,],
        }
note='\n'.join(["raw sample text, RF, text transforms experiments", ]) + '\n'
p = tl.TextPipelineTuningHelper( pipeline, parameters,
                    randomSeeds=randomSeeds, note=note,).fit()
print(p.getReports())
