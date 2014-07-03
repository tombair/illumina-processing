#!/usr/bin/python

import ConfigParser
import logging
import subprocess
import os
import sys
import glob
import shutil


def check_directory(dir):
    csvFiles = glob.glob(dir + "/*.csv")
    if len(csvFiles) != 1:
        if len(csvFiles) > 1:
            logger.warn("Multiple sample sheets -- remove redundant in %s " % (dir, ))
            return None
        else:
            logger.warn("Cannot find sample sheet in %s " % (dir,))
            return None
    logger.info("Directory looks complete %s" % (dir, ))
    return csvFiles[0]


def process_sample_sheet(size, directory, csvFile):
    csvFileOut = directory + "/processedSampleSheet%s.csv" % (size, )
    output_csv = open(csvFileOut, 'w')
    input_csv_fh = open(csvFile)
    header = input_csv_fh.readline()
    header = header.strip('\n')
    header = header.strip('\r')
    cols = header.split(',')
    output_csv.write(",".join(cols[:10]))
    output_csv.write('\n')
    outputFlag = False # flag to keep track to see if we actually have barcode of length 'size' to write
    for line in input_csv_fh:
        line = line.strip('\n')
        line = line.strip('\r')
        line = line.replace('.', '_') # everything weird gets collapsed to _ so bclToFastq doesn't choke
        line = line.replace('-', '_')
        line = line.replace(' ', '_')
        cols = line.split(',')
        index_size = len(cols[4])
        if index_size == size:
            outputFlag = True
            output_csv.write(",".join(cols[:10]))
            output_csv.write('\n')
    input_csv_fh.close()
    output_csv.close()
    if not outputFlag:
        os.remove(csvFileOut)
        logger.info("Not able to find any index for  %s file" % (csvFileOut, ))
        return None
    else:
        logger.info("Made %s file for index size %s" % (csvFileOut, size ))
        return csvFileOut


def run_sample_sheet(base_directory, size, sample_sheet):
    output = os.path.join(base_directory, "Unaligned%s" % (size, ))
    logger.info("configureBclToFastq for size %s" % (size, ))
    if size > 1:
        bcl_process = subprocess.check_output(
            ['/opt/illumina/bin/configureBclToFastq.pl', '--sample-sheet', sample_sheet, '--input-dir',
             base_directory + '/Data/Intensities/BaseCalls', '--output-dir', output, '--ignore-missing-bcl',
             '--ignore-missing-stat', '--fastq-cluster-count=0', "--use-bases-mask=y*,I%sN*,y*" % (size,)])
    else:
        bcl_process = subprocess.check_output(
            ['/opt/illumina/bin/configureBclToFastq.pl', '--sample-sheet', sample_sheet, '--input-dir',
             base_directory + '/Data/Intensities/BaseCalls', '--output-dir', output, '--ignore-missing-bcl',
             '--ignore-missing-stat', '--fastq-cluster-count=0'])
    logger.info(bcl_process)
    return output


def in_waiting_directory(dir):
    if config.get('validate_waiting', 'locked') == 'False':
        config.set('validate_waiting', 'locked', 'True')
        fh = open(config.get('validate_waiting', 'output_file'), 'r')
        for line in fh:
            line = line.strip('\n')
            if os.path.dirname(line) == dir:
                logger.info("already found file %s" % (dir,))
                config.set('validate_waiting', 'locked', 'False')
                return True
        fh.close()
        config.set('validate_waiting', 'locked', 'False')
        return False
    else:
        logger.warn("validate_waiting unexpectedly locked")
        logger.info("assume present")
        return True


config = ConfigParser.SafeConfigParser()
config.readfp(open('pathway.cfg'))
readySymDir = config.get('Globals', 'readyToRun')
readyToMake = config.get('Globals', 'waitingToRun')
logger = logging.getLogger(sys.argv[0])
input_csv_fh = logging.FileHandler(config.get('Globals', 'logfile'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
input_csv_fh.setFormatter(formatter)
logger.addHandler(input_csv_fh)
logger.setLevel(logging.INFO)
logger.info("Starting")
print "This should not be run legacy from github delete "
sys.exit(1)
# get Directories
directories = glob.glob(readySymDir + "/*")
for dir in directories:
    # Check to see if we already have this one in process
    if in_waiting_directory(dir):
        continue
    csv = check_directory(dir)
    if csv is not None:
        if config.get('validate_waiting', 'locked') == 'False':
            config.set('validate_waiting', 'locked', 'True')
            for s in [0, 6, 8]:  # sizes of indexes
                csvFound = process_sample_sheet(s, dir, csv)
                if csvFound is not None:
                    logger.info(
                        "Found good sample sheet for size % running bclToFastQ for %s in %s" % (s, csvFound, dir))
                    #Found and wrote a particular size csvFile need to note it and get ready to run it
                    try:
                        proc = run_sample_sheet(dir, s, csvFound)
                        #write proc to dir to run makes on 
                        output_fh = open(config.get('validate_waiting', 'output_file'), 'a')
                        output_fh.write("%s\n" % (proc,))
                        output_fh.close()
                    except Exception, e:
                        logger.warn("Error on bcltoFastq %s" % (e, ))

            config.set('validate_waiting', 'locked', 'False')
            # if os.path.islink(dir):
            #    shutil.move(dir,readyToMake)
        else:
            logger.warn("Lockfile set not able to process")


