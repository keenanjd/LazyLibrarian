import platform, subprocess, re, os, urllib2, tarfile

import lazylibrarian
from lazylibrarian import logger, version

import lib.simplejson as simplejson

def runGit(args):

    if lazylibrarian.GIT_PATH:
        git_locations = ['"'+lazylibrarian.GIT_PATH+'"']
    else:
        git_locations = ['git']

    if platform.system().lower() == 'darwin':
        git_locations.append('/usr/local/git/bin/git')


    output = err = None

    for cur_git in git_locations:

        cmd = cur_git+' '+args

        try:
            logger.debug('Trying to execute: "' + cmd + '" with shell in ' + lazylibrarian.PROG_DIR)
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, cwd=lazylibrarian.PROG_DIR)
            output, err = p.communicate()
            logger.debug('Git output: ' + output)
        except OSError:
            logger.debug('Command ' + cmd + ' didn\'t work, couldn\'t find git')
            continue

        if 'not found' in output or "not recognized as an internal or external command" in output:
            logger.debug('Unable to find git with command ' + cmd)
            output = None
        elif 'fatal:' in output or err:
            logger.error('Git returned bad info. Are you sure this is a git installation?')
            output = None
        elif output:
            break

    return (output, err)

def getVersion():

    if version.LAZYLIBRARIAN_VERSION.startswith('win32build'):

        lazylibrarian.INSTALL_TYPE = 'win'

        # Don't have a way to update exe yet, but don't want to set VERSION to None
        return 'Windows Install'

    elif os.path.isdir(os.path.join(lazylibrarian.PROG_DIR, '.git')):

        lazylibrarian.INSTALL_TYPE = 'git'
        output, err = runGit('rev-parse HEAD')

        if not output:
            logger.error('Couldn\'t find latest installed version.')
            return None

        cur_commit_hash = output.strip()

        if not re.match('^[a-z0-9]+$', cur_commit_hash):
            logger.error('Output doesn\'t look like a hash, not using it')
            return None

        return cur_commit_hash

    else:

        lazylibrarian.INSTALL_TYPE = 'source'

        version_file = os.path.join(lazylibrarian.PROG_DIR, 'version.txt')

        if not os.path.isfile(version_file):
            return None

        fp = open(version_file, 'r')
        current_version = fp.read().strip(' \n\r')
        fp.close()

        if current_version:
            return current_version
        else:
            return None

def checkGithub():

    # Get the latest commit available from github
    url = 'https://api.github.com/repos/%s/%s/commits/%s' % (lazylibrarian.GIT_USER, lazylibrarian.GIT_PROJECT, lazylibrarian.GIT_BRANCH)
    logger.info(u'Retrieving latest version information from github')
    logger.debug(u'Using url: %s' % url)
    try:
        result = urllib2.urlopen(url, timeout=20).read()
        git = simplejson.JSONDecoder().decode(result)
        lazylibrarian.LATEST_VERSION = git['sha']
    except:
        logger.warn(u'Could not get the latest commit from github')
        logger.debug(u'Git  User: %s' % str(lazylibrarian.GIT_USER))
        logger.debug(u'Current Version: %s' % str(lazylibrarian.CURRENT_VERSION))
        logger.debug(u'Latest Version: %s' % str(lazylibrarian.LATEST_VERSION))
        lazylibrarian.COMMITS_BEHIND = 0
        return lazylibrarian.CURRENT_VERSION

    # See how many commits behind we are
    if lazylibrarian.CURRENT_VERSION:
        logger.info(u'Comparing currently installed version with latest github version')
        logger.debug(u'Git User: %s' % str(lazylibrarian.GIT_USER))
        logger.debug(u'Git Branch: %s' % str(lazylibrarian.GIT_BRANCH))
        logger.debug(u'Current Version: %s' % str(lazylibrarian.CURRENT_VERSION))
        logger.debug(u'Latest Version: %s' % str(lazylibrarian.LATEST_VERSION))
        url = 'https://api.github.com/repos/%s/%s/compare/%s...%s' % (lazylibrarian.GIT_USER, lazylibrarian.GIT_PROJECT, lazylibrarian.GIT_BRANCH, lazylibrarian.CURRENT_VERSION)
        logger.debug(u'Using url: %s' % url)

        try:
            result = urllib2.urlopen(url, timeout=20).read()
            git = simplejson.JSONDecoder().decode(result)
            if git['status'] == 'behind':
              lazylibrarian.COMMITS_BEHIND = git['behind_by']
            elif git['status'] == 'identical':
              lazylibrarian.COMMITS_BEHIND = 0
            elif git['status'] == 'ahead':
              lazylibrarian.COMMITS_BEHIND = -1
        except:
            logger.warn(u'Could not get version information github')
            lazylibrarian.COMMITS_BEHIND = 0
            return lazylibrarian.CURRENT_VERSION

        if lazylibrarian.COMMITS_BEHIND >= 1:
            logger.warn(u'New version is available. You are %s commits behind' % lazylibrarian.COMMITS_BEHIND)
        elif lazylibrarian.COMMITS_BEHIND == 0:
            logger.info(u'LazyLibrarian is up to date')
        elif lazylibrarian.COMMITS_BEHIND == -1:
            logger.info(u'You are running a newer version than the official LazyLibrarian branch.')

    else:
        logger.warn(u'You are running an unknown version of LazyLibrarian. Run the updater to identify your version')
    return lazylibrarian.LATEST_VERSION

def checkUpdate():
    logger.info(u'Checking for updates.')
    # Get local version if necessary and check remote branch
    if not lazylibrarian.CURRENT_VERSION:
        lazylibrarian.CURRENT_VERSION = getVersion()
    lazylibrarian.LATEST_VERSION = checkGithub()
    return

def update():


    if lazylibrarian.INSTALL_TYPE == 'win':

        logger.warn(u'Windows .exe updating not supported yet.')
        pass


    elif lazylibrarian.INSTALL_TYPE == 'git':

        output, err = runGit('pull origin ' + version.LAZYLIBRARIAN_VERSION)

        if not output:
            logger.error(u'Couldn\'t download latest version.')

        for line in output.split('\n'):

            if 'Already up-to-date.' in line:
                logger.info('No update available, not updating')
                logger.info('Output: ' + str(output))
            elif line.endswith('Aborting.'):
                logger.error('Unable to update from git: '+line)
                logger.info('Output: ' + str(output))

    else:

        tar_download_url = 'https://github.com/%s/%s/tarball/%s' % (lazylibrarian.GIT_USER, lazylibrarian.GIT_PROJECT, lazylibrarian.GIT_BRANCH)
        update_dir = os.path.join(lazylibrarian.PROG_DIR, 'update')
        version_path = os.path.join(lazylibrarian.PROG_DIR, 'version.txt')

        try:
            logger.info('Downloading update from: '+tar_download_url)
            data = urllib2.urlopen(tar_download_url)
        except (IOError, URLError):
            logger.error("Unable to retrieve new version from "+tar_download_url+", can't update")
            return

        download_name = data.geturl().split('/')[-1]

        tar_download_path = os.path.join(lazylibrarian.PROG_DIR, download_name)

        # Save tar to disk
        f = open(tar_download_path, 'wb')
        f.write(data.read())
        f.close()

        # Extract the tar to update folder
        logger.info('Extracing file' + tar_download_path)
        tar = tarfile.open(tar_download_path)
        tar.extractall(update_dir)
        tar.close()

        # Delete the tar.gz
        logger.info('Deleting file' + tar_download_path)
        os.remove(tar_download_path)

        # Find update dir name
        update_dir_contents = [x for x in os.listdir(update_dir) if os.path.isdir(os.path.join(update_dir, x))]
        if len(update_dir_contents) != 1:
            logger.error("Invalid update data, update failed: "+str(update_dir_contents))
            return
        content_dir = os.path.join(update_dir, update_dir_contents[0])

        # walk temp folder and move files to main folder
        for dirname, dirnames, filenames in os.walk(content_dir):
            dirname = dirname[len(content_dir)+1:]
            for curfile in filenames:
                old_path = os.path.join(content_dir, dirname, curfile)
                new_path = os.path.join(lazylibrarian.PROG_DIR, dirname, curfile)

                if os.path.isfile(new_path):
                    os.remove(new_path)
                os.renames(old_path, new_path)

        # Update version.txt
        try:
            ver_file = open(version_path, 'w')
            ver_file.write(lazylibrarian.LATEST_VERSION)
            ver_file.close()
        except IOError, e:
            logger.error("Unable to write current version to version.txt, update not complete: "+ex(e))
            return
