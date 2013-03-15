from __future__ import print_function
import errno
import logging
import os
import re
import sys
import traceback

__version__ = "1.0.0"
__author__ = "Sean Hsieh"

__all__ = [
    "safefile",
    "bye",
    "mkdir",
    "init_log",
    "log",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "exception",
    "repo_conf",
    "repo_missing",
    "safefile"
    ]

gk_logger = None
_lvl_maps = { "debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR, "critical": logging.CRITICAL }

def safefile(file):
    return os.access(file, os.R_OK | os.W_OK | os.F_OK)

def bye(msg):
    error("bye - %s", msg)
    if os.environ.get("GK_DEBUG_LEVEL", None) == "debug":
        traceback.print_stack()
    print("bye - %s" % msg, file = sys.stderr)
    sys.exit(1)

def mkdir(*p, **m):
    try:
        os.mkdir(*p, **m)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

def init_log():
    global gk_logger

    if gk_logger:
        return
    gk_debug_level = _lvl_maps.get(os.environ.get("GK_DEBUG_LEVEL", "info"), logging.INFO)
    gk_debug_output = os.environ.get("GK_DEBUG_OUTPUT", "file")
    #print "gk_debug_level: %s, gk_debug_output: %s" % (gk_debug_level, gk_debug_output)
    if gk_debug_output == "file":
        log_path = os.environ.get("HOME", None) + "/.gk"
        log_file = log_path + "/log"
        mkdir(log_path)
        h = logging.FileHandler(filename = log_file)
    elif gk_debug_output == "stdout":
        h = logging.StreamHandler(stream = sys.stdout)
    elif gk_debug_output == "syslog":
        h = logging.handlers.SysLogHandler()
    else:
        h = logging.FileHandler(filename="/dev/null")

    gk_logger = logging.getLogger("")
    gk_logger.setLevel(gk_debug_level)
    #formatter = logging.Formatter(fmt = "%(asctime)s [%(name)s] %(message)s", datefmt = "%Y/%m/%d %H:%M:%S")
    formatter = logging.Formatter(fmt = "%(asctime)s %(message)s", datefmt = "%Y/%m/%d %H:%M:%S")
    h.setFormatter(formatter)
    gk_logger.addHandler(h)

def log(level, msg, *args, **kwargs):
    try:
        gk_logger._log(level, msg, args, **kwargs)
    except AttributeError:
        init_log()
        gk_logger._log(level, msg, args, **kwargs)

def debug(msg, *args, **kwargs):
    log(logging.DEBUG, msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    log(logging.INFO, msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    log(logging.WARNING, msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    log(logging.ERROR, msg, *args, **kwargs)

def critical(msg, *args, **kwargs):
    log(logging.CRITICAL, msg, *args, **kwargs)

def exception(msg, *args):
    log(logging.ERROR, msg, exec_info = 1, *args)
