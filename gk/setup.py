from __future__ import print_function
from optparse import OptionParser
import os
import os.path
import re
import string
import sys
import gk
from gk import rc
from gk import common
from gk import store

"""for usage
Usage:  gitkeeper setup [<option>]

Setup gitkeeper, compile conf, run the POST_COMPILE trigger (see rc file) and
propagate hooks.

    -h, --help                  show this help message and exit
    -a, --admin <name>          administrator's name
    -p, --pubkey <file>         public key file name
    -k, --hooks-only            skip other steps and just propagate hooks

First run: either the pubkey or the admin name is *required*, depending on
whether you're using ssh mode or http mode.

Subsequent runs:

  - Without options, 'gitkeeper setup' is a general "fix up everything" command
    (for example, if you brought in repos from outside, or someone messed
    around with the hooks, or you made an rc file change that affects access
    rules, etc.)

  - '-p' can be used to replace the admin key; useful if you lost the admin's
    private key but do have shell access to the server.

  - '-k' is mainly for scripting use.  Do not combine with other options.

  - '-a' is ignored
EOF"""

def args():
    argv = string.join(sys.argv[1:])
    optparser = OptionParser(add_help_option = False)
    optparser.add_option("-a", "--admin", dest="admin", help="administrator's name", metavar="ADMIN_NAME", default="")
    optparser.add_option("-p", "--pubkey", dest="pubkey", help="public key file name", metavar="PUBKEY", default="")
    optparser.add_option("-k", "--hooks-only", dest="h_only", action="store_true", default=False, help="skip other steps and just propagate hooks")
    optparser.add_option("-h", "--help", dest="help", action="store_true", default=False, help="show this help message and exit")
    opt, args = optparser.parse_args(sys.argv[1:])
    if args:
        common.usage()
        #optparser.print_help()
        #gk.bye("Unexpected options: %s" % repr(args))

    if opt.help or (opt.pubkey == None and opt.admin == None) or (opt.pubkey and opt.admin) or (opt.h_only and (opt.admin or opt.pubkey)):
        common.usage()

    if opt.pubkey:
        if not re.search("\.pub$", opt.pubkey):
            gk.bye("'%s' name does not end in .pub" % opt.pubkey)

        if re.search("@", opt.pubkey):
            gk.bye("'%s' name contains '@'" % opt.pubkey)
        
        if not common.tsh.test("cat %s" % opt.pubkey):
            gk.bye("'%s' not a readable file" % opt.pubkey)

        if common.tsh.lines() != 1:
            gk.bye("'%s' must have exactly one line" % opt.pubkey)

        if not common.tsh.test("ssh-keygen -l -f %s" % opt.pubkey):
            gk.bye("'%s' does not seem to be a valid ssh pubkey file" % opt.pubkey)

        opt.admin = re.sub(r"\.pub$", "", re.sub(r".*/", "", opt.pubkey))

    return opt, argv

def setup_gkrc():
    if not rc.default("filename"):
        common.put(rc.default("default-filename"), rc.default("default-text"))

def setup_gkadmin(opt, argv):
    if opt.admin == "" and not os.access(rc.rc["GK_ADMIN_BASE"] + "/conf/gitkeeper.conf", os.F_OK):
        gk.bye("'-p' or '-a' required, see 'gitkeeper setup -h' for more")

    # reminder: 'admin files' are in ~/.gitkeeper, 'admin repo' is
    # rc.rc["GK_REPO_BASE"]/gitkeeper-admin.git

    # grab the pubkey content before we chdir() away
    pubkey_content = ''
    if opt.pubkey:
        pubkey_content = common.cat(opt.pubkey)

    # set up the admin files in admin-base

    common.mkdir(rc.rc["GK_ADMIN_BASE"])
    common.chdir(rc.rc["GK_ADMIN_BASE"])

    common.mkdir("conf")
    common.mkdir("logs")
    conf = rc.DATA().replace("%ADMIN", opt.admin)

    if not os.access("conf/gitkeeper.conf", os.F_OK):
        common.put("conf/gitkeeper.conf", conf)

    if opt.pubkey:
        common.mkdir("keydir")
        common.put("keydir/%s.pub" % opt.admin, pubkey_content)

    # set up the admin repo in repo-base

    common.chdir()
    common.mkdir(rc.rc["GK_REPO_BASE"])
    common.chdir(rc.rc["GK_REPO_BASE"])

    if not os.path.isdir("gitkeeper-admin.git"):
        store.new_repo("gitkeeper-admin")

    # commit the admin files to the admin repo

    os.environ["GIT_WORK_TREE"] = rc.rc["GK_ADMIN_BASE"]
    common.chdir(rc.rc["GK_REPO_BASE"] + "/gitkeeper-admin.git")
    common.system("git add conf/gitkeeper.conf")

    if opt.pubkey:
        common.system("git add keydir")

    if not common.tsh.test("git config --get user.email"):
        common.tsh.run("git config user.email %s@%s" % (os.environ["USER"], common.tsh.run("hostname")))

    if not common.tsh.test("git config --get user.name"):
        common.tsh.run("git config user.name '%s on %s'" % (os.environ["USER"], common.tsh.run("hostname")))

    if not common.tsh.test("git diff --cached --quiet"):
        if not common.tsh.test("git commit -am 'gitkeeper setup %s'" % argv):
            gk.bye("setup failed to commit to the admin repo: %s" % common.tsh.output)

    os.environ.pop("GIT_WORK_TREE")

# ----------------------------------------------------------------------

def setup():
    opt, argv = args()

    if not opt.h_only:
        setup_gkrc()
        setup_gkadmin(opt, argv)

        common.system("gitkeeper compile")
        common.system("gitkeeper trigger POST_COMPILE")

    store.hook_repos()    # all of them, just to be sure

# ----------------------------------------------------------------------


_DATA_ ="""
[global]
default-access          = no

[repo:gitkeeper-admin]
RW+                     = %ADMIN

[repo:testing]
RW+                     = @all
"""