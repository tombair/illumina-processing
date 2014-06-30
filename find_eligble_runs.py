#!/usr/bin/python
import ConfigParser
import subprocess
import os
import sys
import glob
import fnmatch
import logging

#get a file path to look and a file to check for previous files


def find_dirs(directory):
    dirs = [d for d in os.listdir(directory)]
    return dirs


def find_files(directory, pattern):
    try:
        files = os.listdir(directory)
        for f in files:
            basename = os.path.basename(f)
            if basename == pattern:
            #if fnmatch.fnmatch(basename, pattern):
                yield os.path.join(directory, f)
    except Exception, e:
        logger.info('Got exception %s from find_files in %s' % (e, sys.argv[1]))
        yield None


def harvest_for_old_processes(file_to_check):
    ds = []
    fh = open(file_to_check)
    for line in fh:
        line = line.strip('\n')
        ds.append(line)
    return ds

config = ConfigParser.ConfigParser()
config.readfp(open('pathway.cfg'))
readDirectory = config.get('Globals', 'SeqDirectory')
readySymDir = config.get('Globals', 'readyToRun')
done = config.get('Globals', 'doneIgnore')

logger = logging.getLogger(sys.argv[0])
fh = logging.FileHandler(config.get('Globals', 'logfile'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)
logger.info("Starting")

old_processes = harvest_for_old_processes(done)
dirs = find_dirs(readDirectory)
count = 0
total = 0 
for d in dirs:
    d = os.path.join(readDirectory, d)
    files = find_files(d, 'Basecalling_Netcopy_complete.txt')
    for file in files:
        if file is not None:
            total += 1
            if os.path.exists(os.path.join(d, 'ImageAnalysis_Netcopy_complete.txt')):
                if os.path.dirname(file) not in old_processes:
                    count += 1
                    rtw = os.path.join(readySymDir, os.path.basename(os.path.dirname(file)))
                    if not os.path.exists(rtw):
                        os.symlink(os.path.dirname(file), rtw)
logger.info("Found %s directories that have data" % (total, ))
logger.info("Found %s directories that need processed" % (count,))
