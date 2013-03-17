from __future__ import print_function
import errno
import os
import pickle
import re
import sys
import gk
from gk import rc
from gk import common
from hooks import update
from hooks import postupdate

__version__ = "1.0.0"
__author__ = "Sean Hsieh"

__all__ = [
    "setup_hooks"
    "new_repo",
    "new_user_repo"
    ]

hook_reset = 0

def setup_hooks(repo):
    global hook_reset

    gk.info("setip_hooks('%s')", repo)

    # reset the gitkeeper supplied hooks, in case someone fiddled with
    # them, but only once per run
    if hook_reset == 0:
        common.mkdir(rc.rc["GK_ADMIN_BASE"] + "/hooks/common")
        common.mkdir(rc.rc["GK_ADMIN_BASE"] + "/hooks/gitkeeper-admin")
        common.put(rc.rc["GK_ADMIN_BASE"] + "/hooks/common/update", update.update_hook())
        common.put(rc.rc["GK_ADMIN_BASE"] + "/hooks/gitkeeper-admin/post-update", postupdate.post_update_hook())
        os.chmod(rc.rc["GK_ADMIN_BASE"] + "/hooks/common/update", 0755)
        os.chmod(rc.rc["GK_ADMIN_BASE"] + "/hooks/gitkeeper-admin/post-update", 0755)
        hook_reset += 1

    # propagate user-defined (custom) hooks to all repos
    if "LOCAL_CODE" in rc.rc:
        common.ln(rc.rc["LOCAL_CODE"] + "/hooks/common", "*", repo + ".git/hooks")

    # override/propagate gitkeeper defined hooks for all repos
    common.ln(rc.rc["GK_ADMIN_BASE"] + "/hooks/common", "*", repo + ".git/hooks")

    # override/propagate gitkeeper defined hooks for the admin repo
    if repo == "gitkeeper-admin":
        common.ln(rc.rc["GK_ADMIN_BASE"] + "/hooks/gitkeeper-admin", "*", repo + ".git/hooks")

def new_repo(repo):
    common.mkdir(repo + ".git")
    common.chdir(repo + ".git")
    common.system("git init --bare >&2")
    common.chdir(rc.rc["GK_REPO_BASE"])
    setup_hooks(repo)

def new_user_repo(repo, user, mode):
    common.chdir(rc.rc["GK_REPO_BASE"])
    rc.trigger("PRE_CREATE", repo, user, mode)
    new_repo(repo)
    common.put(repo + ".git/gk-creator", user)
    #common.put(repo + ".git/gk-perms", rc.rc["DEFAULT_ROLE_PERMS"] if "DEFAULT_ROLE_PERMS" in rc.rc else "")
    with open(repo + ".git/gk-perms", "wb") as f:
        pickle.dump(rc.rc["DEFAULT_ROLE_PERMS"] if "DEFAULT_ROLE_PERMS" in rc.rc else {}, f)
    rc.trigger("POST_CREATE", repo, user, mode)

    common.chdir(rc.rc["GK_ADMIN_BASE"])

def hook_repos():
    #gk.debug("")
    # all repos, all hooks
    common.chdir(rc.rc["GK_REPO_BASE"])

    for f in common.pipe_run('find . -name "*.git" -prune')[1].split():
        repo = f.replace(".git", "").replace("./", "")
        setup_hooks(repo)
