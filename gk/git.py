import errno
import logging
import os
import re
import sys
import subprocess

__version__ = "1.0.0"
__author__ = "Sean Hsieh"
__all__ = [
    "cmd",
    "getBranchUpdateMode",
    "getUpdateMode"
    ]

modes = { "create": "C", "update": "W", "delete": "D" }

def cmd(args):
    fd = os.open("/dev/null", os.O_WRONLY)
    args = ["git"] + args
    git = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = fd)
    details = git.stdout.read().strip()
    os.close(fd)

    return details

def getBranchUpdateMode(oldrev, newrev):
    details = cmd(["rev-list", newrev + ".." + oldrev])
    fast_forward = (details == "")
    if fast_forward:
        gk.info("Fast forward update")
        return "W"
    else:
        baserev = cmd(["merge-base", oldrev, newrev])

        if baserev == newrev:
            gk.info("Rewind only update")
            """
            Rewind only update

            This update discarded existing revisions and left the branch pointing at
            a previous point in the repository history.
             * -- * -- N (newrev)
                        \\
                         O -- O -- O (oldrev)
            The removed revisions are not necessarily gone - if another reference
            still refers to them they will stay in the repository.
            """
            return "+"
        else:
            gk.info("Force update")
            """
            This update added new revisions after undoing existing revisions.  That is"
            to say, the old revision is not a strict subset of the new revision.  This"
            situation occurs when you --force push a change and generate a repository"
            containing something like this:"
             * -- * -- B -- O -- O -- O ($oldrev)"
                        \\"
                         N -- N -- N ($newrev)"
            When this happens we assume that you've already had alert emails for all"
            of the O revisions, and so we here report only the revisions in the N"
            branch from the common base, B."
            """
            return "+"

def getUpdateMode(old, new, refname):
    oldrev = cmd(["rev-parse", old])
    newrev = cmd(["rev-parse", new])
    refname_type = None

    # --- Interpret
    # 0000->1234 (create)
    # 1234->2345 (update)
    # 2345->0000 (delete)
    if re.match("0*$", oldrev) is not None:
        change_type = "create"
    else:
        if re.match("0*$", newrev) is not None:
            change_type = "delete"
        else:
            change_type = "update"

    # --- Get the revision types
    newrev_type = cmd(["cat-file", "-t", newrev])
    oldrev_type = cmd(["cat-file", "-t", oldrev])

    if change_type in ["create", "update"]:
        rev = newrev
        rev_type = newrev_type
    elif change_type == "delete":
        rev = oldrev
        rev_type = oldrev_type

    # The revision type tells us what type the commit is, combined with
    # the location of the ref we can decide between
    #  - working branch
    #  - tracking branch
    #  - unannoted tag
    #  - annotated tag

    if refname.find("refs/tags/") == 0:
        if rev_type == "commit":
            # un-annotated tag
            refname_type="tag"
        elif rev_type == "tag":
            # annotated tag
            refname_type = "annotated tag"
    elif refname.find("refs/heads/") == 0 and rev_type == "commit":
        # branch
        refname_type = "branch"
    elif refname.find("refs/remotes/") == 0 and rev_type == "commit":
        # tracking branch
        refname_type = "tracking branch"
    else:
        refname_type = "unknown type"

    if refname_type == "branch" and change_type == "update":
        m = getBranchUpdateMode(oldrev, newrev)
    else:
        m = modes[change_type]

    gk.info("refname: %s, refname_type: %s, change_type: %s", refname, refname_type, change_type)
    gk.info("rev_type: %s, oldrev: %s, newrev: %s, mode: %s", rev_type, oldrev, newrev, m)

    return m
