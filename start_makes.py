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
import string
import random
from datetime import datetime
import time
import smtplib


def possible_runs():
    possible_runs = []
    pr_file_handle = open(config.get('find_eligible_runs', 'output_file'), 'r')
    for line in pr_file_handle:
        line = line.strip('\n')
        possible_runs.append(line)
    return possible_runs


def in_progress_runs(array):
    ipr_fh = open(config.get('find_eligible_runs', 'output_file'), 'w')
    for line in array:
        ipr_fh.write(line)
        ipr_fh.write('\n')


def make_file(dir):
    os.chdir(dir)
    return_value = subprocess.call("nohup make -j 8", shell=True)
    logger.info("Started make it returned %s" % (return_value,))
    return True


def done_make(dir):
    nohup = os.path.join(dir, 'nohup.out')
    if not os.path.exists(nohup):
        logger.warn("expected nohup file missing in %s " % (nohup, ))
    else:
        dm_fh = open(nohup, 'r')
        lastLine = dm_fh.readlines()[-1]
        lastLine = lastLine.strip('\n')
        cols = lastLine.split('\t')
        if cols[3] == 'INFO: all completed successfully.':
            logger.info("%s completed successfully" % (dir, ))
            return True
        logger.info("Found last line of %s in %s" % (lastLine, nohup))
    return False


def sshSubDir(directory, PI, number, name):
    # ssh command generation
    sshCmd = [config.get('start_makes', 'pageGenPath')]
    sshUrl = config.get('start_makes', 'pageGenHost')
    sshCmd.append('-p')
    sshCmd.append(str(number))
    sshCmd.append('-u')
    sshCmd.append(PI.lower())
    sshCmd.append('-s')
    chars = string.ascii_lowercase + string.digits
    randLet = ''.join([random.choice(chars) for x in range(6)])
    sshCmd.append(randLet + PI.lower())
    sshCmd.append(directory)
    htmlDir = config.get('start_makes', 'pageGenhtml')
    htmlDir += "/%s" % (name, )
    sshCmd.append(htmlDir)
    sshCmd.append('>>')
    sshCmd.append(os.path.join(directory, 'pageGen.txt'))
    sshCmdStr = " ".join(sshCmd)
    logger.info(sshCmdStr)
    # need to collect the std out from this command to get the username and password
    pid = subprocess.Popen(['ssh', sshUrl, sshCmdStr],stdout=subprocess.PIPE)
    logger.info("ssh return value %s " % (pid.communicate()[0], ))


def addToDoneList(path_done):
    # need to append to done list
    done = open(config.get('Globals', 'doneIgnore'), 'a')
    done.write(path_done)
    done.close()


def email(content):
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(config.get('Globals', 'emailAddr'), config.get('Globals', 'emailPasswd'))
    server.sendmail(config.get('Globals', 'emailAddr'), config.get('Globals', 'emailSend'), content)
    server.quit()


def rsyncFile(dir):
    # get list of directories
    dirs = glob.glob(dir + "/Project*")
    # need to get the plate id to prevent later name collisions
    print os.path.basename(os.path.dirname(dir))
    plateID = os.path.basename(os.path.dirname(dir)).split('_')[2]
    destPlace = config.get('Globals', 'OutDirectory')
    for d in dirs:
        if os.path.isdir(d):
            #need to chop up the file name to figure out where to rsync to
            basename = os.path.basename(d)
            parts = basename.split('_')
            pi = parts[1]
            number = int(parts[-1])
            #construct new path
            newNameBase = "%s-%s_%s_%s" % (datetime.utcnow().strftime("%Y%m%d"), plateID, pi, number)
            newName = os.path.join(destPlace, newNameBase)
            logger.info("Rsyncing to %s " % (newName,))
            if not os.path.exists(newName):
                    os.makedirs(newName)
            #shouldn't need this but leaving it here as a note rsync should handle writing under this
            #while os.path.exists(newName):
            #    logger.warn("Detected name collision before rysnc with %s " % (newName,))
            #    newName = os.path.join(newName, newNameBase)
            if int(number) > 100:
                logger.info("Started rsync %s " % (newName,))
                rsync_ret_code= subprocess.call("rsync -v -r -u %s %s" % (d, newName), shell=True)
                if rsync_ret_code >= 0:
                        logger.warn("rsync ret code failed %s" % (rsync_ret_code, ))
                        logger.warn("Tried rsyncing  %s to %s " % (d, newName))
                logger.info("Finished rsync %s to %s " % (d, newName))
                logger.info("Setting up output html %s,%s,%s,%s " % (d, pi, number, newNameBase))
                time.sleep(10)  # give time for rsync to start making directories
                sshSubDir(newName, pi, number, newNameBase)
            if int(number) < 1:
                new_name_ssh = "helium.hpc.uiowa.edu:/Shared/IVR/" + newNameBase
                logger.info("This is a Stone run rsync directly to IVR %s " % (new_name_ssh,))
                rsync_ret_code = subprocess.call("rsync -v -r %s %s" % (d, new_name_ssh), shell=True)
                logger.info("rsync return code %s" % (rsync_ret_code,))
    return True


config = ConfigParser.SafeConfigParser()
if len(sys.argv) == 2:
    config.readfp(open(sys.argv[1]))
else:
    config.readfp(open('pathway.cfg'))
readySymDir = config.get('Globals', 'readyToRun')
logger = logging.getLogger(sys.argv[0])
fh = logging.FileHandler(config.get('Globals', 'logfile'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)
logger.info("Starting")


if config.get('start_makes', 'locked') == 'False':
    config.set('start_makes', 'locked', 'True')
    pr = possible_runs()
    logger.info("See %s possible runs to process" % (len(pr)))
    notDone = []
    for p in pr:
        done = False
        logger.info("Looking at %s " % (p,))
        if os.getloadavg()[0] > int(config.get('start_makes', 'maxload')):
            logger.info(
                "load is greater than %s will wait %s" % (config.get('start_makes', 'maxload'), os.getloadavg()[0],))
        else:
            if not os.path.exists(os.path.join(p, 'beingMaked')):
                open(os.path.join(p, 'being_Maked'), 'w').close()
                make_file(p)
            if not os.path.exists(os.path.join(p, 'beingRsynced')) and done_make(p):
                open(os.path.join(p, 'being_Rsynced'), 'w').close()
                rsyncFile(p)
            elif os.path.exists(os.path.join(p, 'pageGen.txt')):
                # pageGene should have been written by the ssh method called from rsyncFile --messy fixme
                fh = open(os.path.join(p, 'pageGen.txt'), 'r')
                content = fh.readlines()
                email(content)
                addToDoneList(p)
                if os.path.islink(p):
                    os.remove(p)
                done = True
        if not done:
            notDone.append(p)

    in_progress_runs(notDone)
    config.set('start_makes', 'locked', 'False')
else:
    logger.warn("Lockfile set not able to process")


