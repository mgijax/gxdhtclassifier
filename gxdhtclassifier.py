#
# GXD HT relevance classifier for GEO experiments
# Initial version, Nov 17, 2021
# Updated March 2024 for https://mgi-jira.atlassian.net/browse/WTS2-1397
#   Anaconda 0.11.1  Python 3.10.9  Sklearn 1.2.1
#
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.ensemble import RandomForestClassifier

pipeline = Pipeline( [
('vectorizer', CountVectorizer(
                strip_accents=None,
                stop_words='english',
                binary=True,
                min_df=0.02,
                max_df=0.75,
                ngram_range=(1,2),
                max_features=None,
                token_pattern=r'\b([a-z_]\w+)\b',
                analyzer='word',
                decode_error='strict',
                encoding='utf-8',
                input='content',
                lowercase=True,
                tokenizer=None,
                vocabulary=None,
                ),),
('classifier', RandomForestClassifier(
                class_weight='balanced',
                n_jobs=-1,
                verbose=1,
                max_depth=None,
                max_features='sqrt',
                max_leaf_nodes=None,
                max_samples=None,
                min_impurity_decrease=0.0,
                #min_impurity_split=None,   # removed as of sklearn 0.19
                min_samples_leaf=1,
                min_samples_split=100,
                min_weight_fraction_leaf=0.0,
                n_estimators=100,
                bootstrap=True,
                ccp_alpha=0.0,
                criterion='gini',
                oob_score=False,
                warm_start=False,
                #random_state=198,
                ),),
] )
