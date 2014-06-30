#!/home/tbair/python2.7/bin/python
# first check to see if the csv and all files are present
# process the csv file to remove - . / and spaces
# make sure the csv file has the correct number of columns
# run the bcl script
# wait
# check to see if the nohup outputs the correct ending
# email that done

import ConfigParser
import logging
import subprocess
import os
import sys
import glob
import shutil


def checkDirectory(dir):
    if not os.path.exists(dir + "/Basecalling_Netcopy_complete.txt"):
        logger.info("Netcopy not finished in %s " % (dir, ))
        return None

    csvFiles = glob.glob(dir + "/*.csv")

    if len(csvFiles) != 1:
        if len(csvFiles) > 1:
            logger.warn("Multiple sample sheets -- remove redundant in %s " % (dir, ))
            return None
        else:
            logger.warn("Cannot file sample sheet in %s " % (dir,))
            return None
    logger.info("Directory looks complete %s" % (dir, ))
    return csvFiles[0]


def processSampleSheet(size, directory, csvFile):
    csvFileOut = directory + "/processedSampleSheet%s.csv" % (size, )
    output = open(csvFileOut, 'w')
    fh = open(csvFile)
    header = fh.readline()
    header = header.strip('\n')
    header = header.strip('\r')
    cols = header.split(',')
    output.write(",".join(cols[:10]))
    output.write('\n')
    outputFlag = False
    for line in fh:
        line = line.strip('\n')
        line = line.strip('\r')
        line = line.replace('.', '_')
        line = line.replace('-', '_')
        line = line.replace(' ', '_')
        cols = line.split(',')
        index_size = len(cols[4])
        if index_size == size:
            outputFlag = True
            output.write(",".join(cols[:10]))
            output.write('\n')
    fh.close()
    output.close()
    if not outputFlag:
        os.remove(csvFileOut)
        logger.info("Not able to find any index for  %s file" % (csvFileOut, ))
        return None
    else:
        logger.info("Made %s file" % (csvFileOut, ))
        return csvFileOut


def runSampleSheet(dir, size, sampleSheet):
    output = os.path.join(dir, "Unaligned%s" % (size, ))
    bclOut = None
    logger.info("configureBclToFastq for size %s" % (size, ))
    if size > 1:
        bclOut = subprocess.check_output(
            ['/opt/illumina/bin/configureBclToFastq.pl', '--sample-sheet', sampleSheet, '--input-dir',
             dir + '/Data/Intensities/BaseCalls', '--output-dir', output, '--ignore-missing-bcl',
             '--ignore-missing-stat', '--fastq-cluster-count=0', "--use-bases-mask=y*,I%sN*,y*" % (size,)])
    else:
        bclOut = subprocess.check_output(
            ['/opt/illumina/bin/configureBclToFastq.pl', '--sample-sheet', sampleSheet, '--input-dir',
             dir + '/Data/Intensities/BaseCalls', '--output-dir', output, '--ignore-missing-bcl',
             '--ignore-missing-stat', '--fastq-cluster-count=0'])
    logger.info(bclOut)
    return output


def onWaitingList(dir):
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
fh = logging.FileHandler(config.get('Globals', 'logfile'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)
logger.info("Starting")

# get Directories
directories = glob.glob(readySymDir + "/*")
for dir in directories:
    # Check to see if we already have this one in process
    if onWaitingList(dir):
        continue
    csv = checkDirectory(dir)
    if csv is not None:
        if config.get('validate_waiting', 'locked') == 'False':
            config.set('validate_waiting', 'locked', 'True')
            for s in [0, 6, 8]:  # sizes of indexes
                csvFound = processSampleSheet(s, dir, csv)
                if csvFound is not None:
                    logger.info(
                        "Found good sample sheet for size % running bclToFastQ for %s in %s" % (s, csvFound, dir))
                    #Found and wrote a particular size csvFile need to note it and get ready to run it
                    try:
                        proc = runSampleSheet(dir, s, csvFound)
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


