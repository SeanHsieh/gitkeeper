import os
import re
import sys
import gk
from gk import rc
from gk import common

def post_update():
    gk.info("post-update %s", repr(sys.argv[1:]))
    # this is the *real* post_update hook for gitkeeper

    common.tsh.test("git ls-tree --name-only master")
    if re.search(r"^(hooks|logs)$", common.tsh.output, re.MULTILINE):
        gk.bye("No files/dirs called 'hooks' or 'logs' are allowed")

    hooks_changed = False
    os.environ["GIT_WORK_TREE"] = rc.rc["GK_ADMIN_BASE"]

    common.tsh.test("git diff --name-only master")
    if re.search(r"/hooks/common/", common.tsh.output, re.MULTILINE):
        hooks_changed = True

    # the leading slash ensure that this hooks/common directory is below
    # some top level directory, not *at* the top.  That's LOCAL_CODE, and
    # it's actual name could be anything but it doesn't matter to us.

    common.tsh.test("git checkout -f --quiet master")

    os.environ.pop("GIT_WORK_TREE")

    #common.system("gitkeeper compile")
    if hooks_changed:
        common.system("gitkeeper setup --hooks-only")

    common.system("gitkeeper trigger POST_COMPILE")

    sys.exit(0)

def post_update_hook():
    return rc.DATA()

_DATA_="""
#!/usr/bin/env python

import sys
import gk
from hooks import postupdate

# gitkeeper post-update hook (only for the admin repo)
# ----------------------------------------------------------------------

postupdate.post_update()    # is not expected to return
sys.exit(1)                 # so if it does, something is wrong
"""
