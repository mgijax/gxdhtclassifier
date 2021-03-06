#!/bin/bash

                        # maybe should get this from Configuration
sampleDataLib="--sampledatalib ~/work/gxdhtclassifier/htMLsample.py"

log="preProcessor.log"
inputFiles="trainSet.txt valSet.txt testSet.txt"
defaultPreprocessors="-p standard"

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 [--datadir dir] [-- -p preprocessor [-p preprocessor] ...]

    Apply preprocessors to training, validation, and test sample files

    --datadir       directory where the input files live. Default is ..
                    (it should not be '.', since we write to '.')
    -p preprocessor a preprocessor option to run (repeat -p ... to do multiple)
                    Default: "$defaultPreprocessors"

    Output files, w/ the same names as the input files are written in the
    current directory.
ENDTEXT
    exit 5
}
#######################################
# cmdline options - and defaults
#######################################
preProcessors=""
dataDir=".."            # default

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help) Usage ;;
    --datadir) dataDir="$2"; shift; shift; ;;
    --)        shift; preProcessors=$*; break ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
if [ "$preProcessors" == "" ]; then
    preProcessors="${defaultPreprocessors}"
fi

#######################################
# preprocess the files
#######################################
echo "Preprocessors: ${preProcessors}"
date > $log
for f in $inputFiles; do
    set -x
    preprocessSamples.py $sampleDataLib --report matches.$f $preProcessors $dataDir/$f > $f 2>> $log
    set +x
done
