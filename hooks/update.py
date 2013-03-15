#!/usr/bin/env python

from __future__ import print_function
import os
import re
import sys
import gk
from gk import rc
from gk import access

if __name__ == "__main__":

    if os.environ.get("GK_BYPASS_ACCESS_CHECKS"):
        gk.info("update %s (%s) bypass")
        sys.exit(0)

    try:
        ref = sys.argv[1]
        old = sys.argv[2]
        new = sys.argv[3]
    except IndexError:
        sys.exit(1)
    else:
        user = rc.rc["GK_USER"]
        repo = re.sub(r"\.git$", "", os.getcwd()).replace(rc.rc["GK_REPO_BASE"] + "/", "")

        gk.info("")
        gk.info("===== BEGIN ===== (%s at %s)", user, repo)
    
        access.load_repo_conf(repo)
        oldtree, newtree, mode = access.args(ref, old, new)
        ret = access.permit(repo, user, mode, ref)[0]
        rc.trigger("ACCESS_2", rc.rc["GK_REPO"], user, mode, ref, ret, old, new)
        r, msg = access.check_vrefs(repo, user, mode, ref, old, new, oldtree, newtree)
        print(msg, file = sys.stderr)

        if ret and r:
            gk.info("************************")
            gk.info("*** Access premitted ***")
            gk.info("************************")
            r = 0
        else:
            gk.info("*********************")
            gk.info("*** Access denied ***")
            gk.info("*********************")
            r = 1

        gk.info("====== END ======")
        gk.info("")
        sys.exit(r)

def update_hook():
    return rc.DATA()

_DATA_="""
#!/bin/bash

$GK_BASE/hooks/update.py "$1" "$2" "$3"
exit $?
"""
