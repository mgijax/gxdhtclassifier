#!/bin/bash
# run trained gxdhtclassifier on a test file to verify it runs

data="testSet.txt"              # the default test file
model="../gxdhtclassifier.pkl"  # the default trained model file

preprocessing="-p standard"     # Preprocessing options to run

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 [--data filename] [--model filename]

    Run the specified trained model on the (unpreprocessed) sample file.
    Create basename.preformance.txt and basename.preds.txt output files
        based on the basename of the sample file.
    Puts all generated files into the current directory.

    --data	filename of (unpreprocessed) sample file to predict
                Default: $data

    --model     filename of the trained model.
                Default: $model
    Preprocessors that will be run: $preprocessing
ENDTEXT
    exit 5
}
#######################################
# basic setup
#######################################
baseDir=`dirname $0`
. $baseDir/Configuration

#######################################
# cmdline options
#######################################
while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --data)     data="$2";  shift; shift; ;;
    --model)    model="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done

#######################################
# build params for predict.py
#######################################
predictCmd="$ANACONDAPYTHON $MLtextTools/predict.py"
dataBasename=`basename $data .txt`
predOutput="$dataBasename.preds.txt"            # prediction output file
perfOutput="$dataBasename.performance.txt"      # performance summary output

#######################################
# run predict.py
#######################################
echo $predictCmd $sampleDataLibParam -m $model $preprocessing --performance $perfOutput $data
$predictCmd $sampleDataLibParam -m $model $preprocessing --performance $perfOutput $data > $predOutput
echo "wrote $perfOutput and $predOutput"
