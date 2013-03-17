from __future__ import print_function
import os
import pickle
import re
import string
import gk
from gk import rc

__version__ = "1.0.0"
__author__ = "Sean Hsieh"
__all__ = [
    "Rule",
    "RepoRules",
    "RepoConf",
    "replace_group",
    "load_conf"
    ]

# Rule class conatains rule matching elements
#
# members
#   * perms     string
#   * refex     string
#   * members   string
#   * isVref    boolean
class Rule:
    def __init__(self):
        self.members = []
        self.perms = ""
        self.refex = ""
        self.isVref = False

    def print(self):
        print("    perms: %s" % self.perms)
        print("    refex: %s" % self.refex)
        print("    members: %s" % repr(self.members))
        print("    isVref: %s" % repr(self.isVref))

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
    def __init__(self):
        self.repoex = []
        self.rules = []
        self.options = {}
        self.defaultAccess = False
        self.role_perms = {}

    def print(self):
        print("repoex: %s" % repr(self.repoex))
        print("options: %s" % repr(self.options))
        print("defaultAccess: %s" % repr(self.defaultAccess))
        for rule in self.rules:
            print("")
            rule.print()

# GkConf class contains repo matching rules
#
# members
#   * repoRulesList list(RepoRules)
#   * options       dict(string, string)
class RepoConf:
    def __init__(self):
        self.repoRulesList = []
        self.defaultAccess = False
        self.options = {}
        self.lastRepo = None

    def print(self):
        for repo_rules in self.repoRulesList:
            print("")
            repo_rules.print()

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

def get_role_perms(repo):
    fn = rc.rc["GK_REPO_BASE"] + "/" + repo + ".git/gk-perms"
    perms = {}
    if os.access(fn, os.F_OK):
        try:
            with open(fn, "rb") as f:
                perms = pickle.load(f)
        except BaseException as e:
            pass

    return perms

_repoconf = None

def load_conf(repo):
    global _repoconf

    if _repoconf == None:
        # load common repo rules
        fn = rc.rc["GK_ADMIN_BASE"] + "/conf/gitkeeper.conf-compiled.p"
        if not os.access(fn, os.F_OK):
            gk.bye("* Cannot find gitkeeper.conf-compiled.p!")

        try:
            with open(fn, "rb") as f:
                _repoconf = pickle.load(f)
        except BaseException as e:
            gk.bye("* pickle.load('%s') failed: %s" % (fn, repr(e)))
        else:
            for rr in _repoconf.repoRulesList:
                rr.repoex = string.join(rr.repoex).replace("CREATOR", rc.rc["GK_USER"]).split()

    # load a real repo rules
    if not rc.repo_missing(repo) and _repoconf.lastRepo != repo:
        if _repoconf.lastRepo:
            del _repoconf.repoRulesList[0]
        
        _repoconf.lastRepo = repo
        fn = rc.rc["GK_REPO_BASE"] + "/" + repo + ".git/gk-conf"
        if os.access(fn, os.F_OK):
            try:
                with open(fn, "rb") as f:
                    repo_rules = pickle.load(f)
            except BaseException as e:
                gk.bye("* pickle.load('%s') failed: %s" % (fn, repr(e)))
            else:
                _repoconf.repoRulesList.insert(0, repo_rules)

        fn = rc.rc["GK_REPO_BASE"] + "/" + repo + ".git/gk-perms"
        if os.access(fn, os.F_OK):
            try:
                with open(fn, "rb") as f:
                    perms = pickle.load(f)
            except BaseException as e:
                gk.bye("* pickle.load('%s') failed: %s" % (fn, repr(e)))
            else:
                for rr in _repoconf.repoRulesList:
                    for r in rr.rules:
                        r.members = replace_group(string.join(r.members), perms)

        _repoconf.role_perms = get_role_perms(repo)

    return _repoconf
