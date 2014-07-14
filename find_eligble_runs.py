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


def has_required_files(directory_to_check, string_of_files):
    list_of_files = string_of_files.split(',')
    for file_to_check in list_of_files:
        logger.info("Checking for %s " %os.path.join(directory_to_check,file_to_check))
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
    append_fh.write("\n")
    append_fh.close()

def check_directory(check_directory):
    """
Checks to see if a directory has a single .csv file, if so it returns the path to the csv file
    :param dir to check:
    :return csv file to be processed:
    """
    logger.info("checking %s for sample_sheets " %(check_directory, ) )
    csvFiles = glob.glob(check_directory +"/*.csv")
    logger.info("found sample sheets %s " % (csvFiles, ))
    if len(csvFiles) != 1:
        if len(csvFiles) > 1:
            logger.warn("Multiple sample sheets -- remove redundant in %s " % (check_directory, ))
            return None
        else:
            logger.warn("Cannot find sample sheet in %s " % (check_directory,))
            return None
    logger.info("Directory looks complete %s" % (check_directory, ))
    return csvFiles[0]

def illumina_directory_form(d):
    if len(os.path.basename(d).split('_')) == 4:
        logger.info('directory has correct number of _')
        if d.endswith('XX'):
            return True
        logger.info('does not end with XX perhaps change')
    return False

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
    """
Funtion to take directory path, size of index, and path to sample sheet. Runs the bclToFastq
    :rtype : str:
    """
    output = os.path.join(base_directory, "Unaligned%s" % (size, ))
    logger.info("configureBclToFastq for size %s" % (size, ))
    if size > 1:
        bcl_process = subprocess.Popen(
            ['/opt/illumina/bin/configureBclToFastq.pl', '--sample-sheet', sample_sheet, '--input-dir',
             base_directory + '/Data/Intensities/BaseCalls', '--output-dir', output, '--ignore-missing-bcl',
             '--ignore-missing-stat', '--fastq-cluster-count=0', "--use-bases-mask=y*,I%sN*,y*" % (size,)], stdout=subprocess.PIPE)
        logger.info(bcl_process.communicate()[0])
    else:
        bcl_process = subprocess.Popen(
            ['/opt/illumina/bin/configureBclToFastq.pl', '--sample-sheet', sample_sheet, '--input-dir',
             base_directory + '/Data/Intensities/BaseCalls', '--output-dir', output, '--ignore-missing-bcl',
             '--ignore-missing-stat', '--fastq-cluster-count=0'], stdout=subprocess.PIPE)
    logger.info(bcl_process.communicate()[0])
    return output


def in_waiting_directory(d):
    if config.get('validate_waiting', 'locked') == 'False':
        config.set('validate_waiting', 'locked', 'True')
        fh = open(config.get('validate_waiting', 'output_file'), 'r')
        for line in fh:
            line = line.strip('\n')
            if os.path.dirname(line) == d:
                logger.info("already found file %s" % (d,))
                config.set('validate_waiting', 'locked', 'False')
                return True
        fh.close()
        config.set('validate_waiting', 'locked', 'False')
        return False
    else:
        logger.warn("validate_waiting unexpectedly locked")
        logger.info("assume present")
        return True

# Set up reading of config file
config = ConfigParser.ConfigParser()
if len(sys.argv) == 2:
    config.readfp(open(sys.argv[1]))
else:
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
        total += 1
        logger.info('Starting to process %s ', (d, ))
        if config.get('find_eligible_runs', 'locked') == 'False':
            config.set('find_eligible_runs', 'locked', 'True')
            if not illumina_directory_form(d):
                logger.info("This does not look like a results directory %s " %(d))
                logger.info("Adding to done directory")
                append_to_already_run(d,done_directories)
            if has_required_files(d, config.get('find_eligible_runs','check_files')): # check to make sure it is ready
                if os.path.isdir(d):
                    rtw = os.path.join(readySymDir, os.path.basename(d))
                else:
                    rtw = os.path.join(readySymDir, os.path.basename(os.path.dirname(d)))
                if not os.path.exists(rtw):
                    os.symlink(d, rtw)
                else:
                    logger.warn("link already exists for %s in %s "% (d, rtw ))
                #now that it is done process the sample sheet and run the bclToFastq
                csv = check_directory(rtw)
                if csv is not None:
                        for s in config.get('find_eligible_runs','index_sizes').split(','):  # sizes of indexes
                            s = int(s)
                            csvFound = process_sample_sheet(s, rtw, csv)
                            if csvFound is not None:
                                logger.info(
                                    "Found good sample sheet for size % running bclToFastQ for %s in %s" % (s, csvFound, d))
                                #Found and wrote a particular size csvFile need to note it and get ready to run it
                                try:
                                    proc = run_sample_sheet(rtw, s, csvFound)
                                    #write proc to dir to run makes on
                                    output_fh = open(config.get('find_eligible_runs', 'output_file'), 'a')
                                    output_fh.write("%s\n" % (proc,))
                                    output_fh.close()
                                    count += 1
                                     #have linked the directory to the ready folder should now append it to the done file
                                    append_to_already_run(d,done_directories)
                                except Exception, e:
                                    logger.warn("Error on bcltoFastq %s" % (e, ))
                            else:
                                    logger.warn("Did not find a single csv file in %s " % (rtw, ))

            else:
                logger.info("%s did not have all required files " %(d, ))

            config.set('find_eligible_runs', 'locked', 'False')
        else:
            logger.warn("Lockfile set not able to process")



logger.info("Found %s directories that have data" % (total, ))
logger.info("Found %s directories that need processed" % (count,))
