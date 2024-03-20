This is where we train and exercise the final production version of the
gxdhtclassifier.

------
Train the classifier by running:
../gxdhtclassifier.train.sh --data data/P_notreat --model ../gxdhtclassifier.py
Producing: 
./gxdhtclassifier.pkl           # the most recent trained model
./gxdhtclassifier.features.txt  # list of features/weights from that training
./gxdhtclassifier.log           # log file from the training

------
Exercise the newly trained classifier by running:
../gxdhtclassifier.test.sh --data data/testSet.txt --model gxdhtclassifier.pkl
Producing: 
./testSet.preds.txt             # predictions from running gxdhtclassifier.pkl
                                #  on data/testSet.txt
./testSet.performance.txt       # performance metrics on those predictions
    `
    Note these metrics are not indicative of how the classifier should perform
    on new ht experiments as the testSet.txt was also included in the training
    step. So it should perform better on this testSet.txt than on new data.
    But at least this step exercises the classifier so you can tell if it runs
    ok.

------
What lives where:
data/                           # holds the unpreprocessed training data
data/P_notreat/                 # holds the preprocessed training data
                                # ('P_notreat' is some cryptic name from the
                                #   various preprocessing attempts that I tried)
data/P_notreat/trainSet.txt     # The inputs to the training
data/P_notreat/valSet.txt       # The inputs to the training
data/P_notreat/testSet.txt      # The inputs to the training

nov2021/                        # the classifier files and test results from
                                #  the original production classifier trained
                                #  in November 2021
