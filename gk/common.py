from __future__ import print_function
import errno
import inspect
import os
import os.path
import re
import shlex
import subprocess
import sys
import types
import gk
from gk import rc

__version__ = "1.0.0"
__author__ = "Sean Hsieh"

__all__ = [
    "usage",
    "cat",
    "ln",
    "mkdir",
    "chdir",
    "put",
    "which",
    "system",
    "pipe_run",
    "Tsh",
    "tsh"
    ]

def usage():
    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    msg = ""
    fn = mod.__file__.replace(".pyc", ".py")
    with open(fn) as f:
        msg = f.read()
        m = re.search(r'^"""for usage\s(.*)^EOF"""', msg, re.MULTILINE | re.DOTALL)

    print(m.group(1) if m else "...no usage message in %s" % os.path.basename(fn).replace(".py", ""))
    sys.exit(1)

def cat(fn):
    msg = ""
    with open(fn) as f:
        msg = f.read()
    return msg

def ln(srcdir, patt, dstdir):
    patt = patt.replace("*", ".*")
    for f in os.listdir(srcdir):
        if re.match(patt, f):
            sf = os.path.join(srcdir, f)
            df = os.path.join(dstdir, f)
            if os.access(df, os.F_OK):
                try:
                    os.remove(df)
                except BaseException as e:
                    gk.error("ln('%s', '%s', '%s')",srcdir, patt, dstdir)
                    gk.bye("=> remove('%s') failed: %s" % (df, repr(e)))

            try:
                os.symlink(sf, df)
            except BaseException as e:
                gk.error("ln('%s', '%s', '%s')",srcdir, patt, dstdir)
                gk.bye("=> symlink('%s', '%s') failed: %s" % (sf, df, repr(e)))

def mkdir(path, perm = 0770):
    if os.access(path, os.F_OK):
        return
    try:
        os.makedirs(path, perm)
    except BaseException as e:
        gk.bye("mkdir('%s', '%04o') failed: %s" % (path, perm, repr(e)))

def chdir(path = None):
    if path == None:
        path = os.environ["HOME"]

    try:
        os.chdir(path)
    except BaseException as e:
        gk.bye("chdir('%s') failed: %s" % (path, repr(e)))

def put(fn, msg, mode = "w+"):
    try:
        f = open(fn, mode)
        f.write(msg)
    except BaseException as e:
        gk.bye("put('%s', '%s') failed: %s" % (fn, msg, repr(e)))
    finally:
        f.close()

# Checking files can be accessed via mode or not
_modes = { "R": os.R_OK, "W": os.W_OK, "X": os.X_OK, "r": os.R_OK, "w": os.W_OK, "x": os.X_OK }
def which(file, mode = "X"):
    path = rc.rc["GK_BASE"] + "/" + file
    return path if os.access(path, _modes[mode] | os.F_OK) else None

def unlink(fn):
    if gk.safefile(fn):
        os.remove(fn)
    else:
        gk.warning("file '%s' is missing...", fn)

def system(cmd):
    rc = os.system(cmd)
    if rc != 0:
        gk.info("system() failed: %s -> %d", cmd, rc)
        if rc == -1:
            gk.bye("failed to execute: $s" % cmd)
        elif rc & 127:
            gk.bye("child died with signal %d" % (rc & 127))
        else:
            gk.warning("child exited with value %d" % (rc >> 8))
            sys.exit(rc >> 8)

        sys.exit(1)
    else:
        gk.info("system(): %s", cmd)
        return rc

def pipe_run(cmd):
    fd = os.open("/dev/null", os.O_WRONLY)
    try:
        p = subprocess.Popen(cmd if type(cmd) == types.ListType else shlex.split(cmd), stdout = subprocess.PIPE, stderr = fd)
        #p = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = fd, shell = True)
    except OSError as e:
        gk.warning("popen(%s) failed: %s" % (cmd, repr(e)))
        return e.errno, e.strerror
    else:
        p.wait()
        details = p.stdout.read().strip()
        os.close(fd)
        gk.info("cmd: %s, rc=%s", repr(cmd), repr(p.returncode))
        return p.returncode, details

class Tsh:
    def __init__(self):
        self.rc = 0
        self.output = ""

    def lines(self):
        return len(self.output.split("\n"))

    def test(self, cmd):
        self.rc, self.output = pipe_run(cmd)
        return (self.rc == 0)

    def run(self, cmd):
        self.rc, self.output = pipe_run(cmd)
        return self.output

tsh = Tsh()
