from __future__ import print_function
import inspect
import logging
import os
import pprint
import re
import string
import sys
import types
import gk

__version__ = "1.0.0"
__author__ = "Sean Hsieh"

__all__ = [
    "REMOTE_COMMAND_PATT",
    "REF_OR_FILENAME_PATT",
    "REPONAME_PATT",
    "REPOPATT_PATT",
    "USERNAME_PATT",
    "UNSAFE_PATT",
    "rc",
    "DATA",
    "data",
    "default",
    "query_rc",
    "repo_conf",
    "repo_missing",
    "sanity_repo"
    ]

REMOTE_COMMAND_PATT  =          r"^[-0-9a-zA-Z._@/+ :,%=\'\"]*$"
REF_OR_FILENAME_PATT =          r"^[0-9a-zA-Z][-0-9a-zA-Z._@/+ :,]*$"
REFPATT_PATT         = r"^\^?\??[[0-9a-zA-Z][-0-9a-zA-Z._@/+:,\\^$|()[\]*?{},]*$"
REPONAME_PATT        =        r"^@?[0-9a-zA-Z][-0-9a-zA-Z._@/+]*$"
REPOPATT_PATT        = r"^\^?@?\??[[0-9a-zA-Z][-0-9a-zA-Z._@/+\\^$|()[\]*?{},]*$"
USERNAME_PATT        =        r"^@?[0-9a-zA-Z][-0-9a-zA-Z._@+]*$"

PERM_PATT            = r"(^-$|^R$|^C$|^RW\+?C?D?M?)"
UNSAFE_PATT          = r"[`~#\$\&()|;<>]"

rc = {}

# Receive environment variables into rc
#rc["GK_BINDIR"]     = os.environ.get("GK_BINDIR", None)
#rc["GK_LIBDIR"]     = os.environ.get("GK_LIBDIR", None)
rc["HOME"]          = os.environ["HOME"]
rc["GK_BASE"]       = os.environ.get("GK_BASE", None)

rc["GK_USER_NAME"]  = os.environ.get("GK_USER_FULLNAME", None)
rc["GK_USER"]       = os.environ.get("GK_USER", None) if os.environ.get("GK_USER", None) else os.environ.get("USER", None)
rc["GK_REPO"]       = os.environ.get("GK_REPO", None)

# These keys could be overridden by the rc file later

rc["GK_ADMIN_BASE"] = os.environ.get("HOME") + "/.gitkeeper";
rc["GK_REPO_BASE"]  = os.environ.get("GK_REPO_BASE", None)

current_data_version = "1.0"

if os.environ["PATH"].find(rc["GK_BASE"]) == -1:
    os.environ["PATH"] = "%s:%s" %(rc["GK_BASE"], os.environ["PATH"])

# Simulate Perl __DATA__ section
# Here we put a code string to get the data, everyone wants to use it just exec it.
# And don't forget to call rc.DATA() to get the data string.
def DATA():
    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    with open(mod.__file__.replace(".pyc", ".py")) as f:
        for line in f:
            if line.startswith('_DATA_'):
                return ''.join(line for line in f).replace('\"\"\"', "")

    return None

def default(arg):
    if arg == "default-filename":
        return os.environ.get("HOME") + "/.gitkeeper.rc"
    elif arg == 'default-text':
        #exec(_data_)
        return DATA()
    elif arg == "filename":
        # where is the rc file?

        # search $HOME first
        path = os.environ.get("HOME") + "/.gitkeeper.rc"
        return path if gk.safefile(path) else None
    elif arg == "current-data-version":
        return current_data_version
    else:
        bye("unknown argument to default: \"%s\"" % arg)

def query_rc():
    pprint.pprint(rc, indent = 2)
    sys.exit(0)

def repo_conf():
    path = rc["GK_ADMIN_BASE"] + "/conf/gitkeeper.conf"
    if gk.safefile(path):
        return path
    else:
        gk.bye("cannot find repo.conf")

def repo_missing(repo):
    gk.info(rc["GK_REPO_BASE"] + "/" + repo + ".git")
    return gk.safefile(rc["GK_REPO_BASE"] + "/" + repo + ".git") is False

def sanity_repo(repo):
    if re.search(REPONAME_PATT, repo) is None:
        gk.bye("\"%s\" contains bad characters" % repo)
    if re.search(r"/$", repo):
        gk.bye("\"%s\" ends with a \"/\"" % repo)
    if re.search(r"^/", repo):
        gk.bye("\"%s\" begins with a \"/\"" % repo)
    if re.search(r"\.\.", repo):
        gk.bye("\"%s\" contains \"..\"" % repo)

# section, repo, user, mode, ref, arg
def trigger(*arguments):
    section = arguments[0]
    if section in rc:
        if type(rc[section]) != types.ListType:
            gk.bye("'%s' section in rc file is not a python list" % section)
        else:
            for s in rc[section]:
                args = s.split()
                m = re.search(r"(.+)\.(.+)$", args[0])
                
                # call internal module function
                try:
                    module, func = m.groups()
                # invoke external excutable
                except BaseException as e:
                    from gk import common
                    gk.error("exception %s" % repr(e))
                    #print("exception %s" % repr(e))
                    pgm = common.which("triggers/%s" % args[0], 'x')

                    if not pgm:
                        gk.warning("Skipped trigger command: '%s'", pgm)
                    else:
                        gk.info("trigger command: %s", pgm)
                        arguments = tuple([pgm]) + tuple(args[1:]) + arguments
                        common.system(string.join(arguments))
                else:
                    arguments = tuple(args[1:]) + arguments
                    gk.info("trigger %s.%s(%s)", module, func, repr(arguments))
                    try:
                        exec "import %s" % module
                    except ImportError:
                        gk.bye("module '%s' dose not exist!" % module)
                    
                    try:
                        exec "ff = %s.%s" % (module, func)
                    except AttributeError:
                        gk.bye("module '%s' dose not have function %s()!" % (module, func))
                    
                    ff(*arguments)

        return

    gk.info("'%s' not found in rc", section)

if rc["GK_BASE"] is None:
    gk.bye("GK_BASE is None")

rcfn = default("filename")
try:
    execfile(rcfn)
except BaseException as e:
    gk.bye("Cannot load rc from: %s, %s" % (rcfn, repr(e)))
    
for k in RC:
    rc[k] = RC[k]

if "G3T_RC" in os.environ:
    exec os.environ["G3T_RC"]

if rc["GK_REPO_BASE"] is None:
    gk.bye("GK_REPO_BASE is None")

_DATA_ ="""
RC = {
    # if you're using mirroring, you need a hostname.  This is *one* simple
    # word, not a full domain name.  See documentation if in doubt
    # "HOSTNAME"                =  "darkstar",
    "UMASK"                     :  0077,

    # look in the "GIT-CONFIG" section in the README for what to do
    "GIT_CONFIG_KEYS"           :  '',

    # comment out if you don't need all the extra detail in the logfile
    "LOG_EXTRA"                 :  1,

    # settings used by external programs; uncomment and change as needed.  You
    # can add your own variables for use in your own external programs; take a
    # look at the info and desc commands for perl and shell samples.

    # used by the CpuTime trigger
    # "DISPLAY_CPU_TIME"        :  1,
    # "CPU_TIME_WARN_LIMIT"     :  0.1,
    # used by the desc command
    # "WRITER_CAN_UPDATE_DESC"  :  1,
    # used by the info command

    # add more roles (like MANAGER, TESTER, ...) here.
    #   WARNING: if you make changes to this hash, you MUST run 'gitkeeper
    #   compile' afterward, and possibly also 'gitkeeper trigger POST_COMPILE'
    "ROLES"                     :
        {
            "READERS"           :  1,
            "WRITERS"           :  1,
        },
    # uncomment (and change) this if you wish
    "DEFAULT_ROLE_PERMS"        :  { "READERS": @all" },

    # comment out or uncomment as needed
    # these are available to remote users
    "COMMANDS"                  :
        {
            "help"              :  1,
            "desc"              :  1,
            # "fork"            :  1,
            "info"              :  1,
            # "mirror"          :  1,
            "perms"             :  1,
            # "sskm"            :  1,
            "writable"          :  1,
            # "D"               :  1,
        },

    # comment out or uncomment as needed
    # these will run in sequence during the conf file parse
    "SYNTACTIC_SUGAR"           :
        [
            # 'continuation-lines',
            # 'keysubdirs-as-groups',
        ],

    # comment out or uncomment as needed
    # these will run in sequence to modify the input (arguments and environment)
    "INPUT"                     :
        [
            # 'CpuTime::input',
            # 'Shell::input',
            # 'Alias::input',
            # 'Mirroring::input',
        ],

    # comment out or uncomment as needed
    # these will run in sequence just after the first access check is done
    "ACCESS_1"                  :
        [
            "gk.triggers.writable.access_1",
        ],

    # comment out or uncomment as needed
    # these will run in sequence just before the actual git command is invoked
    "PRE_GIT"                   :
        [
            # 'renice 10',
            # 'Mirroring::pre_git',
            # 'partial-copy',
        ],

    # comment out or uncomment as needed
    # these will run in sequence just after the second access check is done
    "ACCESS_2"                  :
        [
        ],

    # comment out or uncomment as needed
    # these will run in sequence after the git command returns
    "POST_GIT"                  :
        [
            # 'Mirroring::post_git',
            # 'CpuTime::post_git',
        ],

    # comment out or uncomment as needed
    # these will run in sequence before a new wild repo is created
    "PRE_CREATE"                :
        [
        ],

    # comment out or uncomment as needed
    # these will run in sequence after a new repo is created
    "POST_CREATE"               :
        [
            # "post-compile/update-git-configs",
            # "post-compile/update-gitweb-access-list",
            # "post-compile/update-git-daemon-access-list",
        ],

    # comment out or uncomment as needed
    # these will run in sequence after post-update
    "POST_COMPILE"              :
        [
            "post-compile/ssh-authkeys",
            # "post-compile/update-git-configs",
            # "post-compile/update-gitweb-access-list",
            # "post-compile/update-git-daemon-access-list",
        ],
    "DEFAULT_MAIL_GROUP"        : default-mail-group.conf
}
"""