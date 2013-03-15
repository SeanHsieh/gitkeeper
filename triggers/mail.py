import errno
import os
import re
import sys
import gk
from gk import rc

__version__ = "1.0.0"
__author__ = "Sean Hsieh"

__all__ = [
    "send"
    ]

def send(repo, user, mode):
    try:
        f = open(rc.rc["GK_ADMIN_BASE"] + "/" + rc.rc["DEFAULT_MAIL_GROUP"], "r")
        recipients = f.read()
    except BaseException as e:
        gk.bye("send() fail: %s" % repr(e))
    finally:
        f.close()
    
    FULLNAME="$(getent passwd $user | cut -d ':' -f 5) (Git Commit)"

/usr/sbin/sendmail -t
"""
Full-name: "${FULLNAME}"
Bcc: $recipients
Subject: $EMAIL_PREFIX A new project "$projectdesc" created

A new repository "$repo" is created by $FULLNAME.
"""