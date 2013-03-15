#!/usr/bin/env python

import os
import re
import sys
import gk
from gk import rc
from gk import access

#mlogger = logging.getLogger('HOOK.pre-receive')

if __name__ == '__main__':

    repo = re.sub(r'\.git$', '', os.getcwd()).replace(rc.rc['GK_REPO_BASE'] + '/', '')
    gk.info('')
    gk.info('===== BEGIN ===== (%s at %s)', rc.rc['GK_USER'], repo)
    
    for line in sys.stdin.xreadlines():
        old, new, ref = line.strip().split(' ')
        gk.debug('ref: %s, oldsha: %s, newsha: %s', ref, old, new)
        
        if access.permit(repo, rc.rc['GK_USER'], 'W', ref, old, new):
            gk.info('************************')
            gk.info('*** Access premitted ***')
            gk.info('************************')
        else:
            gk.info('*********************')
            gk.info('*** Access denied ***')
            gk.info('*********************')

        gk.info('====== END ======')
        gk.info('')
        sys.exit(1)
