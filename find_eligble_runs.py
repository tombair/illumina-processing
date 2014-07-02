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
    find_dirs_list = [d1 for d1 in os.listdir(directory)]
    return find_dirs_list


def has_required_files(directory_to_check, list_of_files):
    for file_to_check in list_of_files:
        if not os.path.exists(os.path.join(directory_to_check,file_to_check)):
            return False
    return True


def get_already_run(file_to_check):
    ds = []
    old_processes_file = open(file_to_check, 'r')
    for line in old_processes_file:
        line = line.strip('\n')
        ds.append(line)
    return ds

def append_to_already_run(directory_path,done_file_path):
    append_fh = open(done_file_path, "a")
    append_fh.write(directory_path)
    append_fh.close()
# Set up reading of config file
config = ConfigParser.ConfigParser()
config.readfp(open('pathway.cfg'))
readDirectory = config.get('Globals', 'SeqDirectory')
readySymDir = config.get('Globals', 'readyToRun')
done_directories = config.get('Globals', 'doneIgnore')

# Set up logger to handle both info and warn levels
logger = logging.getLogger(sys.argv[0])
fh = logging.FileHandler(config.get('Globals', 'logfile'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)
logger.info("Starting")


old_processes = get_already_run(done_directories)

if not os.path.exists(readDirectory):
    logger.warn("Config file might be wrong cannot find read directory check Globals -> SeqDirectory")
    sys.exit(1)
dirs = find_dirs(readDirectory)

count = 0 # counters to track what is being looked at and what has to be done yet
total = 0 

for d in dirs:
    d = os.path.join(readDirectory, d)
    if d not in old_processes: # check to see if we have already processed this file
        count += 1
        if has_required_files(d,config.get('find_eligible','check_files')): # check to make sure it is ready
            rtw = os.path.join(readySymDir, os.path.basename(os.path.dirname(file)))
            if not os.path.exists(rtw):
                os.symlink(os.path.dirname(file), rtw)
                total += 1
                #have linked the directory to the ready folder should now append it to the done file
                append_to_already_run(d,done_directories)

logger.info("Found %s directories that have data" % (total, ))
logger.info("Found %s directories that need processed" % (count,))
