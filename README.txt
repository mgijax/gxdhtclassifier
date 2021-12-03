GXD HT experiment classifier

ML classifier for determining whether GEO HT experiments are relevant for GXD
sample curation

High Level Contents:

gxdhtclassifier.py  - the source for the classifier (untrained)
gxdhtclassifier.train.sh - trains the classifier
Train/gxdhtclassifier.pkl - the trained classifier

htMLsample.py   - defines HtSample classes that represent GXD HT experiments as
                    ML samples for training, preprocessing, predicting, etc.
                  This is the "sampledatalib" module needed by all the
                    MLtextTools utilities for reading/writing sample files.

ht*.py          - modules that support sample file generation & processing

sdBuild*.sh scripts - generate & preprocess training data ("KnownSamples")
                        from the database. "sd" is for "sampledata"

ModelDev/       - where we experiment with and develop models,
                    preprocessing steps, etc.

Train/          - where we train the final classifier, represented as pkl file
