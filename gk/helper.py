from __future__ import print_function
import errno
import os
import re
import sys
import gk
from gk import rc
from gk import common
from gk import access

__version__ = "1.0.0"
__author__ = "Sean Hsieh"

__all__ = [
    "creator",
    "owns",
    "valid_user",
    "is_admin"
    ]

def creator(repo):
    rc.sanity_repo(repo)

    if rc.repo_missing(repo):
        return rc.rc["GK_USER"]

    f = rc.rc["GK_REPO_BASE"] + "/" + repo + ".git/gk-creator"

    if os.access(f, os.F_OK | os.R_OK):
        return common.cat(f)
    else:
        return ""

# owns()

# return true if rc.rc["GK_USER"] is set and is the creator of the given repo

# shell equivalent
#   if gitkeeper creator repo GK_USER; then ...
def owns(repo):
    valid_user();

    # prevent unnecessary disclosure of repo existence info
    if rc.repo_missing(repo):
        False

    return creator(repo) == rc.rc["GK_USER"]

def valid_user():
    if "GK_USER" not in rc.rc:
        gk.bye("GK_USER not set!")

# is_admin()

# return true if rc.rc["GK_USER"] is set and has W perms to the admin repo

# shell equivalent
#   if gitkeeper access -q gitkeeper-admin GK_USER W; then ...

def is_admin():
    valid_user();
    return access.permit("gitkeeper-admin", rc.rc["GK_USER"], "W", "any")[0]

