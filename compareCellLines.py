
# compare Debbie's cancer cell line list to PRB_cellline.rpt

import sys
from htFeatureTransform import *

debs = cellLinePrefixes + cellLineNames

found = {}              # found[debsName] = [ cell lines containing debsName ]

fn = 'PRB_cellLine.txt'

for t in open(fn, 'r').readlines():
    tl = t.lower()
    for d in debs:
        dl = d.lower()
        if tl.find(dl) > -1:      # found it
            found[d] = found.get(d,[]) + [t.strip()]

for d in sorted(found.keys()):
    print("'%s' found in" % (d))
    for t in sorted(found[d]):
        print("\t'%s'" % t)

print("Deb's cell lines not found in PRB_cellline")
for d in sorted(debs):
    if d not in found.keys():
        print("'%s'" % d)

print("Summary: Deb's list has %d, %d found in PRB_cellline, %d not found" % \
        (len(debs), len(found.keys()), len(debs) - len(found.keys())))
