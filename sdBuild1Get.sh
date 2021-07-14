#!/bin/bash
# get raw data files

#######################################
# filenames for raw data pulled from db
#######################################
htSets="geo nongeo"

#######################################
function Usage() {
#######################################
    cat - <<ENDTEXT

$0 [--server name] [--limit n]

    Get raw sample files from the db.
    Puts all files into the current directory.
    Files created: counts $htSets

    --server	Database server: dev (default) or test or prod
    --limit	limit on sql query results (default = 0 = no limit)
ENDTEXT
    exit 5
}
#######################################
# basic setup
#######################################
baseDir=`dirname $0`
. $baseDir/Configuration

getRaw="$PYTHON $GXDhtClassifierHome/sdGetKnownSamples.py"
getRawLog=getRaw.log		# log file from sdGetRaw

#######################################
# cmdline options
#######################################
limit="0"			# getRaw record limit, "0" = no limit
				#(set small for debugging)
server="dev"

while [ $# -gt 0 ]; do
    case "$1" in
    -h|--help)   Usage ;;
    --limit)     limit="$2"; shift; shift; ;;
    --server)    server="$2"; shift; shift; ;;
    -*|--*) echo "invalid option $1"; Usage ;;
    *) break; ;;
    esac
done
#######################################
# Pull raw subsets from db
#######################################
echo "getting raw data from db: ${server}" | tee -a $getRawLog
date >> $getRawLog
rm -f counts
$getRaw --server $server  counts | tee -a $getRawLog counts
for f in $htSets; do
    set -x
    $getRaw --server $server -l $limit $f > $f 2>> $getRawLog
    set +x
done
