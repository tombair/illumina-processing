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

import smtplib


def possible_runs():
    poss_runs = []
    pr_file_handle = open(config.get('find_eligible_runs', 'output_file'), 'r')
    for line in pr_file_handle:
        line = line.strip('\n')
        poss_runs.append(line)
    return poss_runs


def in_progress_runs(array):
    ipr_fh = open(config.get('find_eligible_runs', 'output_file'), 'w')
    for line in array:
        ipr_fh.write(line)
        ipr_fh.write('\n')


def make_file(original_directory):
    os.chdir(original_directory)
    process = subprocess.Popen(['make', '-j', '8'], stdout=open("make_output",'w'),stderr=open("nohup.out",'w'), shell=True)
    out, err = process.communicate()
    logger.info("Started make it returned %s" % (err, ))
    return True


def done_make(original_directory):
    nohup = os.path.join(original_directory, 'nohup.out')
    if not os.path.exists(nohup):
        logger.warn("expected nohup file missing in %s " % (nohup, ))
    else:
        dm_fh = open(nohup, 'r')
        last_line = dm_fh.readlines()[-1]
        last_line = last_line.strip('\n')
        cols = last_line.split('\t')
        if cols is not None and len(cols) >= 4 and cols[3] == 'INFO: all completed successfully.':
            logger.info("%s completed successfully" % (original_directory, ))
            return True
        logger.info("Found last line of %s in %s" % (last_line, nohup))
    return False


def ssh_project(new_project_directory, investigator, number, new_name):
    # ssh command generation
    if os.path.exists(os.path.join(new_project_directory, 'pageGen.txt')):
        logger.info("pageGen.txt already exists in %s " % (new_project_directory,))
        return
    ssh_command_string = [config.get('start_makes', 'pageGenPath')]
    ssh_url = config.get('start_makes', 'pageGenHost')
    ssh_command_string.append('-p')
    ssh_command_string.append(str(number))
    ssh_command_string.append('-u')
    ssh_command_string.append(investigator.lower())
    ssh_command_string.append('-s')
    chars = string.ascii_lowercase + string.digits
    # noinspection PyUnusedLocal
    random_letters = ''.join([random.choice(chars) for x in range(6)])
    ssh_command_string.append(random_letters + investigator.lower())
    ssh_command_string.append(new_project_directory)
    html_directory_root = config.get('start_makes', 'pageGenHtml')
    html_directory = os.path.join(html_directory_root,new_name)
    ssh_command_string.append(html_directory)
    ssh_command_string.append('>>')
    ssh_command_string.append(os.path.join(new_project_directory, 'pageGen.txt'))
    final_ssh_command = " ".join(ssh_command_string)
    logger.info(final_ssh_command)
    # need to collect the std out from this command to get the username and password
    pid = subprocess.Popen(['ssh', ssh_url, final_ssh_command], stdout=subprocess.PIPE)
    logger.info("ssh return value %s " % (pid.communicate()[0], ))


def addToDoneList(original_directory):
    # need to append to done list
    done_fh = open(config.get('Globals', 'doneIgnore'), 'a')
    done_fh.write(original_directory)
    done_fh.close()


def email_Adam(project_directory):
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    msg = "\r\n".join([
        "From: %s" % config.get('Globals', 'emailAddr'),
        "To: %s" % 'adam-deluca@uiowa.edu',
        "Subject: Script output",
        "",
        "rsync has started for %s " % (project_directory,)
    ])
    server.login(config.get('Globals', 'emailAddr'), config.get('Globals', 'emailPasswd'))
    server.sendmail(config.get('Globals', 'emailAddr'), 'adam-deluca@uiowa.edu', msg)
    server.quit()


def email(email_content):
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    msg = "\r\n".join([
        "From: %s" % config.get('Globals', 'emailAddr'),
        "To: %s" % config.get('Globals', 'emailSend'),
        "Subject: Script output",
        "",
        email_content
    ])
    server.login(config.get('Globals', 'emailAddr'), config.get('Globals', 'emailPasswd'))
    server.sendmail(config.get('Globals', 'emailAddr'), config.get('Globals', 'emailSend'), msg)
    server.quit()


def figure_id(project_directory):
    basename = os.path.basename(project_directory)
    parts = basename.split('_')
    pi = parts[1]
    id_number = parts[-1]
    return {'pi': pi, 'id': id_number}


def getNewName(project_directory):
    try:
        assert os.path.exists(os.path.join(project_directory, "newFileName.txt"))
    except AssertionError, e:
        logger.warn("%s newFileName.txt not found in %s" % (e, project_directory))
    new_fh = open(os.path.join(project_directory, "newFileName.txt"))
    new_file = new_fh.readline().strip('\n')
    try:
        assert len(new_file) > 1
    except AssertionError, e:
        logger.warn("%s newFileName.txt present but empty in %s " % (e, project_directory,))
    return new_file


def makeLinks(original_directory):
    # get list of directories
    logger.info("setting up links for %s" % (original_directory,))
    dirs = glob.glob(original_directory + "/Project*")
    dest_place = config.get('Globals', 'OutDirectory')
    for proj_dir in dirs:
        logger.info("setting up sub links for %s" % (proj_dir,))
        if os.path.exists(os.path.join(proj_dir, "newFileName.txt")):
            new_name = getNewName(proj_dir)
            d_info = figure_id(proj_dir)
            new_project_directory = os.path.join(dest_place, new_name)
            try:
                assert os.path.exists(new_project_directory)
            except AssertionError, e:
                logger.warn("%s Cannot find new project directory %s " % (e, new_project_directory,))
            logger.info("Setting up output html %s,%s,%s " % (new_project_directory, d_info['pi'], d_info['id']))
            ssh_project(new_project_directory, d_info['pi'], d_info['id'], new_name)
        else:
            logger.warn("newFileName.txt not found in %s " % (proj_dir,))


def checkEmailLinks(original_directory):
    dirs = glob.glob(original_directory + "/Project*")
    destination_place = config.get('Globals', 'OutDirectory')
    flag = True
    logger.info("Checking links for %s" % (original_directory,))
    for proj_dir in dirs:
        logger.info("Checking sub links for %s" % (proj_dir,))
        new_name = getNewName(proj_dir)
        new_project_directory = os.path.join(destination_place, new_name)
        try:
            assert os.path.exists(new_project_directory)
        except AssertionError, e:
            logger.warn("%s Cannot find new project directory %s " % (e, new_project_directory,))

        if os.path.exists(os.path.join(new_project_directory, 'pageGen.txt')):
            page_fh = open(os.path.join(new_project_directory, 'pageGen.txt'))
            content = page_fh.readlines()
            for c in content:
                if c.startswith('INFO'):
                    logger.info("Emailing done results %s " % (c,))
                    email(c)
        else:
            flag = False
    return flag


def createNewName(project_directory, plate_id):
    # construct new path
    if not os.path.exists(os.path.join(project_directory, "newFileName.txt")):
        d_info = figure_id(project_directory)
        new_name_base = "%s-%s_%s_%s" % (datetime.utcnow().strftime("%Y%m%d"), plate_id, d_info['pi'], d_info['id'])
        new_fh = open(os.path.join(project_directory, "newFileName.txt"), 'w')
        new_fh.write(new_name_base)
        new_fh.close()


def rsyncFile(original_directory):
    # get list of directories
    dirs = glob.glob(original_directory + "/Project*")
    print os.path.basename(os.path.dirname(original_directory))
    plate_id = os.path.basename(os.path.dirname(original_directory)).split('_')[2]
    destination_place = config.get('Globals', 'OutDirectory')
    for proj_dir in dirs:
        createNewName(proj_dir, plate_id)
    for proj_dir in dirs:
        try:
            assert os.path.isdir(proj_dir)
        except AssertionError, e:
            logger.warn("%s Cannot find project directory %s " % (e, proj_dir,))
        d_info = figure_id(proj_dir)
        new_name_base = getNewName(proj_dir)
        new_name = os.path.join(destination_place, new_name_base)
        logger.info("Rsyncing to %s " % (new_name,))
        if not os.path.exists(new_name):
            os.makedirs(new_name)
        logger.info("Started rsync from %s to %s " % (proj_dir, new_name,))
        rsync_ret_code = subprocess.Popen("rsync -v -r -u %s %s" % (proj_dir, new_name), shell=True)
        logger.info("rsync return codes %s" % (rsync_ret_code.communicate()[0],))
        logger.info("Finished rsync %s to %s " % (proj_dir, new_name))
        if int(d_info['id']) < 1:
            email_Adam(original_directory)
            new_name_ssh = "helium.hpc.uiowa.edu:/Shared/IVR/" + new_name_base
            logger.info("This is a Stone run rsync directly from %s to IVR %s " % (proj_dir, new_name_ssh,))
            rsync_ret_code = subprocess.Popen("rsync -v -r %s %s" % (proj_dir, new_name_ssh), shell=True)
            logger.info("Stone rsync return code %s " % (rsync_ret_code.communicate()[0],))


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
        if len(p) <= 2:
            continue
        done = False
        logger.info("Looking at %s " % (p,))
        if os.getloadavg()[0] > int(config.get('start_makes', 'maxload')):
            logger.info(
                "load is greater than %s will wait %s" % (config.get('start_makes', 'maxload'), os.getloadavg()[0],))
        else:
            if not os.path.exists(os.path.join(p, 'being_Maked')):
                open(os.path.join(p, 'being_Maked'), 'w').close()
                make_file(p)
                if done_make(p):
                    open(os.path.join(p, 'done_Maked'), 'w').close()
                else:
                    logger.warn("not finding what I need in nohup.out file %s",(p,))
            if not os.path.exists(os.path.join(p, 'done_Rsynced')) and os.path.exists(os.path.join(p, 'done_Maked')):
                open(os.path.join(p, 'being_Rsynced'), 'w').close()
                rsyncFile(p)
                open(os.path.join(p, 'done_Rsynced'), 'w').close()
            if not os.path.exists(os.path.join(p, 'links_Done')) and os.path.exists(os.path.join(p, 'done_Rsynced')):
                open(os.path.join(p, 'being_Linked'), 'w').close()
                makeLinks(p)
                emailed = checkEmailLinks(p)
                if emailed:
                    if os.path.islink(p):
                        os.remove(p)
                        done = True
        if not done:
            notDone.append(p)
        else:
            open(os.path.join(p, 'links_Done'), 'w').close()
    in_progress_runs(notDone)
    config.set('start_makes', 'locked', 'False')
else:
    logger.warn("Lockfile set not able to process")


