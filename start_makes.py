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
import string
import random
from datetime import datetime
import time
import smtplib

def possibleRuns():
    pr = []
    fh = open(config.get('validate_waiting','output_file'), 'r')
    for line in fh:
        line = line.strip('\n')
        pr.append(line)
    return pr

def inProgressRuns(array):
    fh = open(config.get('validate_waiting','output_file'), 'w')
    for line in array:
        fh.write(line)
        fh.write('\n')

def makeFile(dir):
    os.chdir(dir)
    pid = subprocess.Popen(["nohup","make","-j","2"]).pid
    logger.info("Started make PID=%s"%(pid,))
    return True

def doneMake(dir):
    nohup  = os.path.join(dir,'nohup.out')
    if os.path.exists(nohup) == False:
        logger.warn("expected nohup file missing in %s " %(nohup,))
    else:
        fh = open(nohup, 'r')
        lastLine = fh.readlines()[-1]
        lastLine = lastLine.strip('\n')
        cols = lastLine.split('\t')
        if cols[3] == 'INFO: all completed successfully.':
            logger.info("%s completed successfully" %(dir,))
            return True
        logger.info("Found last line of %s in %s" % (lastLine,nohup))
    return False
def sshSubDir(dir,PI,number,name):
    #ssh command generation
    sshCmd = [config.get('start_makes','pageGenPath')]
    sshUrl = config.get('start_makes','pageGenHost')
    sshCmd.append('-p')
    sshCmd.append(str(number))
    sshCmd.append('-u')
    sshCmd.append(PI.lower())
    sshCmd.append('-s')
    chars = string.ascii_lowercase + string.digits
    randLet = ''.join([random.choice(chars) for x in range(6)])
    sshCmd.append(randLet+PI.lower())
    sshCmd.append(dir)
    htmlDir = config.get('start_makes','pageGenhtml')
    htmlDir += "/%s"%(name,)
    sshCmd.append(htmlDir)
    sshCmd.append('>>')
    sshCmd.append(os.path.join(dir,'pageGen.txt'))
    sshCmdStr = " ".join(sshCmd)
    logger.info(sshCmdStr)
    pid = subprocess.Popen(['ssh', sshUrl, sshCmdStr]).pid
    logger.info("ssh pid %s "% (pid,))
def addToDoneList(p):
    #need to append to done list
    done = open(config.get('Globals','doneIgnore'),'a')
    done.write(p)
    done.close()
    
def email(content):
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(config.get('Globals','emailAddr'),config.get('Globals','emailPasswd'))
    server.sendmail(config.get('Globals','emailAddr'),config.get('Globals','emailSend'),content)
    server.quit()

def rsyncFile(dir):
    #get list of directories
    dirs = glob.glob(dir+"/Project*")
    #need to get the plate id to prevent later name collisions
    print os.path.basename(os.path.dirname(dir))
    plateID = os.path.basename(os.path.dirname(dir)).split('_')[2]
    destPlace = config.get('Globals','OutDirectory')
    for d in dirs:
        if os.path.isdir(d) == True:
            #need to chop up the file name to figure out where to rsync to
            basename = os.path.basename(d)
            parts = basename.split('_')
            pi = parts[1]
            number = int(parts[-1])
            #construct new path
            newNameBase = "%s-%s_%s_%s" %(datetime.utcnow().strftime("%Y%m%d"),plateID,pi,number)
            newName =  os.path.join(destPlace,newNameBase)
            logger.info("Rsyncing to %s "% (newName,))
            while os.path.exists(newName) == True:
                logger.warn("Detected name collision before rysnc with %s " %(newName,))
                newName = os.path.join(newName, newNameBase)
            if int(number) > 100:
                logger.info("Started rsync %s " %(newName,))
                rsyncOut_pid = 100
                rsyncOut_pid = subprocess.Popen(['rsync', '-v', '-r', d, newName ]).pid
                logger.info("Rsync pid %s "%(rsyncOut_pid,))
                logger.info("Setting up output html %s,%s,%s,%s "%(d,pi,number,newNameBase))
                time.sleep(10) #give time for rsync to start making directories 
                sshSubDir(newName,pi,number,newNameBase)
            if int(number) <1 :
                newNamessh = "helium.hpc.uiowa.edu:/Shared/IVR/"+newNameBase
                logger.info("This is a Stone run rsync directly to IVR %s " %(newNamessh,))
                #rsyncOut_pid = subprocess.Popen(['rsync', '-v', '-r', d, newNamessh ]).pid
                logger.info("%s" %(d,))
    return True


    
config = ConfigParser.SafeConfigParser()
config.readfp(open('pathway.cfg'))
readySymDir = config.get('Globals','readyToRun')
readyToMake = config.get('Globals','waitingToRun')
logger = logging.getLogger(sys.argv[0])
fh = logging.FileHandler(config.get('Globals','logfile'))
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.setLevel(logging.INFO)
logger.info("Starting")
if config.get('validate_waiting','locked') == 'False':
    config.set('validate_waiting','locked','True')
    #get all lines in file
    #foreach
        #check load
        #check to see if started
            #if started see if delayed
            #if started see if finished
                #if finished make
                    #write rsync flag
                    #rsync
                    #write finished
                #if finished rsync
                    #move stone stuff
                    #ssh http command
                    #remove from file
                    #write to donefile
        #if ok
            #write check flag
            #submit make
        #also write check
    #re-write lines if any
    pr = possibleRuns()
    logger.info("See %s possible runs to process" %(len(pr)))
    notDone = []
    for p in pr:
        done = False
        if os.getloadavg()[0] >int(config.get('start_makes','maxload')):
            logger.info("Looking at %s "% (p,))
            logger.info("load is greater than %s will wait %s" %(config.get('start_makes','maxload'),os.getloadavg()[0],))
        else:
            if os.path.exists(os.path.join(p,'beingMaked')) == False:
                if makeFile(p) == True:
                    open(os.path.join(p,'beingMaked'),'w').close()
            elif os.path.exists(os.path.join(p,'beingRsynced')) == False and doneMake(p) == True:
                open(os.path.join(p,'beingRsynced'),'w').close()
                rsyncFile(p)
            elif os.path.exists(os.path.join(p,'pageGen.txt')) == True:
                fh = open(os.path.join(p,'pageGen.txt'),'r')
                content = fh.readlines()
                email(content)
                addToDoneList(p)
                if os.islink(p) == True:
                    os.remove(p)
                done = True
        if done == False:
            notDone.append(p)

    inProgressRuns(notDone)
    config.set('validate_waiting','locked','False')
else:
    logger.warn("Lockfile set not able to process")


