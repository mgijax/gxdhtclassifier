#!/bin/bash
# train the gxdhtclassifier to create gxdhtclassifier.pkl and associated files

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 --data name [--model basename]

    Train a model on specified training data.
    Create .pkl, .features.txt files based on the model source filename.
    Puts all generated files into the current directory.

    --data	directory holding the training data sample files
                We assume these are preprocessed sample files.

    --model     filename of the model source. Default: gxdhtclassifier.py
ENDTEXT
    exit 5
}
#######################################
# basic setup
#######################################
baseDir=`dirname $0`
. $baseDir/Configuration

trainingFiles="trainSet.txt valSet.txt testSet.txt"     # Preprocessed files

#######################################
# cmdline options
#######################################
dataDir=""
modelSource="gxdhtclassifier.py"

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --data)     dataDir="$2"; shift; shift; ;;
    --model)    modelSource="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
if [ "$dataDir" == "" ]; then
    Usage
fi

#######################################
# build params for trainModel.py
#######################################
trainModelCmd="$ANACONDAPYTHON $MLtextTools/trainModel.py"
modelBasename=`basename $modelSource .py`
modelOutput="$modelBasename.pkl"
featuresOutput="$modelBasename.features.txt"
logfile="$modelBasename.log"

trainingPaths=""
for f in $trainingFiles; do     # generate pathnames to training data files
    trainingPaths="$trainingPaths $dataDir/$f"
done

#######################################
# run trainModel.py
#######################################
date > $logfile
#set -x
$trainModelCmd $sampleDataLibParam -m $modelSource -o $modelOutput -f $featuresOutput $trainingPaths | tee -a $logfile
