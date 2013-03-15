from __future__ import print_function
import os
import sys
import gk
from gk import rc
from gk import common

def access_1(*args):
    repo = args[1]
    mode = args[3]
    result = args[5]
    if mode == "r" or not result:
        return

    for f in ( rc.rc["HOME"] + "/.gitkeeper.down", rc.rc["GK_REPO_BASE"] + "/" + repo + ".git/.gitkeeper.down" ):
        if os.access(f, os.F_OK):
            msg = common.cat(f)
            if msg:
                gk.bye(msg)
            else:
                gk.bye("Sorry, writes are currently disabled (no more info available)")
