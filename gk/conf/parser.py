from __future__ import print_function
import ConfigParser
import os
import pickle
import re
import sys
import gk
from gk import rc
from gk import common
from gk import conf
from gk import store

__version__ = "1.0.0"
__author__ = "Sean Hsieh"
__all__ = [
    "compile",
    ]

def compile(verbose = False):
    repoconf = conf.RepoConf()
    config = ConfigParser.SafeConfigParser()
    config.SECTCRE = re.compile(r"\[(?P<header>.*)\]")
    config.optionxform = str
    config.read(rc.repo_conf())
    sections = None
    repoconf.repoRulesList = []

    try:
        sections = config.sections()
    except (NoSectionError, NoOptionError):
        return False
    else:
        try:
            repoconf.defaultAccess = (config.get("global", "default-access").lower() in ["1", "yes", "y", "true"])
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            pass

    try:
        groups_options = config.options("groups")
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        groups = None
    else:
        groups = {}
        for g in groups_options:
            groups[g] = config.get("groups", g)

    projects = {"@all": rc.REPONAME_PATT}
    try:
        projects_options = config.options("projects")
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        pass
    else:
        for p in projects_options:
            projects[p] = config.get("projects", p)

    repo_rules = []
    for sect in sections:
        if sect.find("repo:") == 0 and sect.strip() != "repo:":
            repo_patt = sect.replace("repo:", "").strip()

            for patt in repo_patt.split():
                if re.search(rc.REPONAME_PATT, patt) == None and re.search(rc.REPOPATT_PATT, patt) == None:
                    gk.bye("* Invalid repo pattern '%s' in [repo: %s]" % (patt, repo_patt))

            repoex = conf.replace_group(repo_patt, projects)

            try:
                rule_options = config.options(sect)
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as e:
                gk.bye("* section [%s] parsing failed: %s" % (sect, repr(e)))
            else:
                rr = conf.RepoRules()
                rr.repoex = repoex
                for ro in rule_options:
                    if re.match("option ", ro):
                        rr.options[ro.replace("option ", "").strip()] = config.get(sect, ro)
                        continue

                    r = conf.Rule()
                    r.members = conf.replace_group(config.get(sect, ro), groups)

                    try:
                        perms, refex = ro.split()
                    except ValueError:
                        perms = ro.strip()
                        refex = ""

                    if  re.search(rc.PERM_PATT, perms) == None:
                        gk.bye("* Invalid perm pattern '%s' in section [%s], option '%s'" % (perms, sect, ro))

                    if refex != "" and re.search(rc.REF_OR_FILENAME_PATT, refex) == None and re.search(rc.REFPATT_PATT, refex) == None:
                        gk.bye("* Invalid ref pattern '%s' in section [%s], option '%s'" % (refex, sect, ro))

                    r.perms = perms.upper()
                    r.isVref = (refex.find("VREF/") == 0)

                    # Add "refs/heads/" as prefix, if refex is not leading with "refs/" or "VREF/", and it's not a empty string "".
                    if re.match(r"VREF/.+|refs/.+", refex) is None and refex != "":
                        refex = "refs/heads/" + refex

                    r.refex = refex
                    rr.rules.append(r)

                # a real repo rule saves to gk-conf in repo directory
                if re.search(rc.REPONAME_PATT, repo_patt) and not re.search(r"^@|EXTCMD", repo_patt) and repo_patt.find("CREATOR") == -1:
                    repo_rules.append(rr)
                    if verbose:
                        rr.print()
                    continue

                repoconf.repoRulesList.append(rr)

    # common repo pattern rules save to rc.rc["GK_ADMIN_BASE"] + "/conf/gitkeeper.conf-compiled.p"
    with open(rc.rc["GK_ADMIN_BASE"] + "/conf/gitkeeper.conf-compiled.p", "wb") as f:
        pickle.dump(repoconf, f)
        if verbose:
            repoconf.print()

    for r in repo_rules:
        # repoex should have one item only for a real repo
        repo = r.repoex[0]
        if rc.repo_missing(repo):
            common.chdir(rc.rc["GK_REPO_BASE"])
            store.new_repo(repo)
            common.chdir(rc.rc["GK_ADMIN_BASE"])

        with open(rc.rc["GK_REPO_BASE"] + "/" + repo + ".git/gk-conf", "wb") as f:
            pickle.dump(r, f)

    del config

