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

# Recursively replace a group name to a corresponding member name string list,
# and return the members string as a string list object
#
# parameters
#   * members   string
#       The members string to be replaced.
#
#   * groups    dict(string, string)
#       The dictionary is for group mapping to members list
#
# retrun        list(string)
def replace_group(members, groups):

    def replace_member(members, groups):
        if groups is None:
            return members

        for i, j in groups.iteritems():
            if i in members:
                members = re.sub(r"%s\b" % i, replace_member(j, groups), members)
        return members

    # convert to a set to remove those redundant members
    return list(set(replace_member(members, groups).split()))

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

            repoex = replace_group(repo_patt, projects)

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
                    r.members = replace_group(config.get(sect, ro), groups)

                    try:
                        perms, refex = ro.split()
                    except ValueError:
                        perms = ro.strip()
                        refex = ""

                    if  re.search(rc.PERM_PATT, perms) == None:
                        gk.bye("* Invalid perm pattern '%s' in section [%s], option '%s'" % (perms, sect, ro))

                    if refex != "" and re.search(rc.REF_OR_FILENAME_PATT. refex) == None:
                        gk.bye("* Invalid ref pattern '%s' in section [%s], option '%s'" % (refex, sect, ro))

                    r.perms = perms.upper()
                    r.isVref = (refex.find("VREF/") == 0)

                    # Add "refs/heads/" as prefix, if refex is not leading with "refs/" or "VREF/", and it's not a empty string "".
                    if re.match(r"VREF/.+|refs/.+", refex) is None and refex != "":
                        refex = "refs/heads/" + refex

                    r.refex = refex
                    rr.rules.append(r)

                # a real repo rule saves to gk-conf in repo directory
                if re.search(rc.REPONAME_PATT, repo_patt) and not re.search(r"^@|EXTCMD", repo_patt):
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

"""
# Checking a repository name is matching the repository name regular expression or not
#
# parameters
#   * repoex        string
#   * repo          string
#
# return            boolean
def match_repo(repoex, repo):
    for ex in repoex:
        mm = re.match(ex, repo)
        if mm and mm.group(0) == repo:
            return True
    return False

# Recursively replace a group name to a corresponding member name string list,
# and return the members string as a string list object
#
# parameters
#   * members   string
#       The members string to be replaced.
#
#   * groups    dict(string, string)
#       The dictionary is for group mapping to members list
#
# retrun        list(string)
def replace_group(members, groups):

    def replace_member(members, groups):
        if groups is None:
            return members

        for i, j in groups.iteritems():
            if i in members:
                members = re.sub(r"%s\b" % i, replace_member(j, groups), members)
        return members

    # convert to a set to remove those redundant members
    return list(set(replace_member(members, groups).split()))

# Rule class conatains rule matching elements
#
# members
#   * perms     string
#   * refex     string
#   * members   string
#   * isVref    boolean
class Rule:

# Constructor
#
# parameters
#   * config    SafeConfigParser
#   * repo      string
#   * r         string
#   * groups    dict(string, string)
    def __init__(self, config, repo, r, groups):
        self.members = replace_group(config.get(repo, r), groups)

        try:
            perms, refex = r.split()
        except ValueError:
            perms = r.strip()
            refex = ""
                
        self.perms = perms.upper()
        self.isVref = (refex.find("VREF/") == 0)

        # Add "refs/heads/" as prefix, if refex is not leading with "refs/" or "VREF/", and it's not a empty string "".
        if re.match(r"VREF/.+|refs/.+", refex) is None and refex != "":
            refex = "refs/heads/" + refex

        self.refex = refex

    def satisfyPerms(self):
        if set("W+CD") & set(self.perms) != set([]):
            if "R" not in self.perms:
                self.perms += "R"
            if "W" not in self.perms:
                self.perms += "W"

        if "C" in self.perms:
            if "+" not in self.perms:
                self.perms += "+"

        if self.perms == "-":
            if "R" not in self.perms:
                self.perms += "R"

# RepoRules class contains rules and options for matching
#
# members
#   * repoex    list(string)
#   * rules     list(class Rule)
#   * options   dict(string, string)
class RepoRules:

# Constructor
#
# parameters
#   * config        SafeConfigParser
#   * repoex        string
#   * sect          string
#   * rules_options list(string)
#   * groups        dict(string, string)
#   * projects      dict(string, string)
    def __init__(self, config, repoex, sect, rule_options, groups, projects):
        self.repoex = repoex
        self.rules = []
        self.options = {}

        for r in rule_options:
            if re.match("option ", r):
                self.options[r.replace("option ", "").strip()] = config.get(sect, r)
                continue

            self.rules.append(Rule(config, sect, r, groups))

# GkConf class contains repo matching rules
#
# members
#   * repoRulesList list(RepoRules)
#   * options       dict(string, string)
class RepoConf:
    def __init__(self, conf, repo):

        config = ConfigParser.SafeConfigParser()
        config.optionxform = str
        config.read(conf)
        sections = None
        self.repo = repo
        self.repoRulesList = []
        self.options = {}

        try:
            sections = config.sections()
        except (NoSectionError, NoOptionError):
            return False
        else:
            try:
                self.defaultAccess = (config.get("global", "default-access").lower() in ["yes", "y", "true"])
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                pass

        try:
            groups_options = config.options("groups")
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            self.groups = None
        else:
            self.groups = {}
            for g in groups_options:
                self.groups[g] = config.get("groups", g)

        self.projects = {"@all": ".*"}
        try:
            projects_options = config.options("projects")
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            pass
        else:
            for p in projects_options:
                self.projects[p] = config.get("projects", p)

        for sect in sections:
            if sect.find("repo:") == 0 and sect.strip() != "repo:":
                repoex = replace_group(sect.replace("repo:", ""), self.projects)
                if not match_repo(repoex, repo):
                    continue
                try:
                    rule_options = config.options(sect)
                except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                    pass
                else:
                    self.repoRulesList.append(RepoRules(config, repoex, sect, rule_options, self.groups, self.projects))

        # The previous option has a higher priority than the following options, if they are for the same purpose 
        for rules in self.repoRulesList:
            for i, j in rules.options.iteritems():
                if not i in self.options:
                    self.options[i] = j

        del config

def load_repo_conf(repo):
    global repoconf
    
    if repoconf:
        if repoconf.repo == repo:
            return
        else:
            del repoconf
            repoconf = None

    repoconf = RepoConf(rc.repo_conf(), repo)
    #pickle.dump(repoconf, open(rc.rc["GK_ADMIN_BASE"] + "/repo-data.conf", "wb"))
"""
