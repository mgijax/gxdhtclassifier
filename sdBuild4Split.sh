#!/bin/bash
#    Split raw files into random test, train, validation files
#    Puts all output files into the current directory.

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 [--seed nnnn]  [--datadir dir]

    Split sample files into random test, train, validation files

    --seed      integer:  random seed for the split. Default is time based.

    --datadir	directory where the input files live. Default is .
    Puts all output files into the current directory.
ENDTEXT
    exit 5
}
#######################################
# basic setup
#######################################
baseDir=`dirname $0`
. $baseDir/Configuration

splitCmd="$PYTHON $MLtextTools/splitSamples.py $sampleDataLibParam"
preprocessCmd="$PYTHON $MLtextTools/preprocessSamples.py $sampleDataLibParam"

splitTestLog=splitSamples.log   # where to write log to

testFraction="0.15"		# 15% of GEO expmts for test set
valFraction="0.235"		# want 20% of GEO expmts for validation set
				#  since we are pulling from test leftovers
				#  this is 20%/(1-15%) = .235 of test leftovers
#######################################
# cmdline options
#######################################
dataDir="."
seedParam=""

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --datadir) dataDir="$2"; shift; shift; ;;
    --seed)    seedParam="--seed $2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
if [ "$dataDir" == "" ]; then
    Usage
fi
splitCmd="$splitCmd $seedParam"         # add optional seed

#######################################
# Input file names
#######################################
filesToSplit="geo"      # files to pull validation & test sets from
otherFiles="nongeo"     # other files to use for training

#######################################
# add pathname to filenames
#######################################
pathsToSplit=""
for f in $filesToSplit; do
    pathsToSplit="$pathsToSplit $dataDir/$f"
done
otherPaths=""
for f in $otherFiles; do
    otherPaths="$otherPaths $dataDir/$f"
done
#######################################
# from raw files, pull out testSet.txt, valSet.txt, trainSet.txt
#######################################
date >$splitTestLog
echo "### randomly selecting test set" | tee -a $splitTestLog
set -x
# random test set + leftovers
$splitCmd -f $testFraction --retainedfile testSet.txt  --leftoverfile LeftoversTest.txt $pathsToSplit >>$splitTestLog 2>&1

# random validation set from test set leftovers
echo "### randomly selecting validation set" | tee -a $splitTestLog
$splitCmd -f $valFraction --retainedfile valSet.txt  --leftoverfile LeftoversVal.txt LeftoversTest.txt >>$splitTestLog 2>&1

# trainSet is valSet leftovers + $before
# (preprocess w/ no preprocessing steps just intelligently concats files)
echo "### concatenating leftovers to  training set" | tee -a $splitTestLog
$preprocessCmd LeftoversVal.txt $otherPaths > trainSet.txt 2>> $splitTestLog
set +x
