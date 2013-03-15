from __future__ import print_function
import ConfigParser
import errno
import os
import os.path
import re
import subprocess
import sys
import time
import gk
from gk import rc
from gk import common
from gk import conf
from gk import git

__version__ = "1.0.0"
__author__ = "Sean Hsieh"
__all__ = [
    "check_vrefs",
    "permit"
    ]

_vref_caches = {}
repoconf = None
ZERO_SHA = "0" * 40

def TRUE(val):
    return val in ["yes", "y", "1", "t", "true"]

def getVREFMaker(vref):
    vl = vref.split("/")
    return common.which(vl[0] + "/" + vl[1])

def args(ref, oldsha, newsha):
    # this is special to git -- the hash of an empty tree
    empty = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    oldtree = empty if oldsha == ZERO_SHA else oldsha
    newtree = empty if newsha == ZERO_SHA else newsha
    
    # for branch create or delete, merge_base stays at "0"*40
    merge_base = ZERO_SHA if oldsha == ZERO_SHA and newsha == ZERO_SHA else git.cmd(["merge-base", oldsha, newsha])

    mode = "W"
    # tag rewrite
    mode = "+" if ref.find("refs/tags/") == 0 and oldsha != ZERO_SHA else mode
    
    # we treat ref create/delete as force update
    mode = "+" if merge_base == ZERO_SHA else mode
    # non-ff push to ref (including ref delete)
    mode = "+" if oldsha != merge_base else mode

    mode = "D" if TRUE(repoconf.options.get("DELETE_IS_D")) and newsha == ZERO_SHA else mode
    mode = "C" if TRUE(repoconf.options.get("CREATE_IS_C")) and oldsha == ZERO_SHA else mode

    # and now "M" commits.  All the other accesses (W, +, C, D) were mutually
    # exclusive in some sense.  Sure a W could be a C or a + could be a D but
    # that's by design.  A merge commit, however, could still be any of the
    # others (except a "D").

    # so we have to *append* 'M' to mode (if the repo has MERGE_CHECK in
    # effect and this push contains a merge inside)

    if TRUE(repoconf.options.get("MERGE_CHECK")):
        if oldsha == ZERO_SHA or newsha == ZERO_SHA:
            gk.warning("    * ref create/delete ignored for purposes of merge-check")
        else:
            mode += "M" if git.cmd(["rev-list", "-n", "1", "--merges", oldsha + ".." + newsha]) != "" else ""

    return oldtree, newtree, mode

def VREF_Hour(vref, ref, oldsha, newsha, oldtree, newtree, mode):
    return "VREF/Hour/%02d" % time.localtime().tm_hour, 0

def VREF_NAME(vref, ref, oldsha, newsha, oldtree, newtree, mode):
    # Run only once, cache the result here
    try:
        return VREF_NAME.cached_name, 0
    except AttributeError:
        gk.debug("    * No result cache found !")
        # My server uses Python 2.6 re.sub() without flags parameter to set MULTILINE :(, so I hack here
        if sys.hexversion >= 0x02070000:
            VREF_NAME.cached_name = re.sub("^", "VREF/NAME/", git.cmd(["diff", "--name-only", oldtree, newtree]), flags = re.MULTILINE)
        else:
            r = git.cmd(["diff", "--name-only", oldtree, newtree])
            r = re.sub("^", "VREF/NAME/", r)
            VREF_NAME.cached_name = re.sub("\n", "\nVREF/NAME/", r)

        return VREF_NAME.cached_name, 0

vref_table = {
    "VREF/Hour/": VREF_Hour,
    "VREF/NAME/": VREF_NAME
}

def invokeVREFMaker(vref, ref, oldsha, newsha, oldtree, newtree, mode):
    try:
        result, returncode = _vref_caches[vref]
    except KeyError:
        result = ""
        returncode = 0
    else:
        gk.debug("    * VREF Maker cache found!")
        return result, returncode

    # You can overwrite the internal VREF commands, if you have your owned VREF Maker existing in VREF directory.
    vref_path = getVREFMaker(vref)
    if vref_path:
        vl = vref.split("/")
    
        if len(vl) < 2:
            return result, 0

        args = [vref_path, ref, oldsha, newsha, oldtree, newtree, mode, vref]

        i = 2
        while i < len(vl):
            args.append(vl[i])
            i += 1

        fd = os.open("/dev/null", os.O_WRONLY)
        vrefmaker = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = fd)
        result = vrefmaker.stdout.read().strip()
        #gk.debug(result)
        vrefmaker.wait()
        os.close(fd)
        returncode = vrefmaker.returncode
        _vref_caches[vref] = [result, returncode]
    else:
        # Check from the internel VREF Maker mapping table
        mm = re.match(r"VREF/.+/", vref)
        vc = mm.group(0) if mm else ""
        try:
            func = vref_table[vc]
            gk.debug("    * Invoking internal %s", vc)
            result, returncode = func(vref, ref, oldsha, newsha, oldtree, newtree, mode)
        except KeyError:
            gk.error("    * \"%s\" cannot be invoked!", vref)
        else:
            _vref_caches[vref] = [result, returncode]

    return result, returncode

"""
def invokeVREFMaker(ref, oldsha, newsha, vref, mode):
    try:
        result, returncode = _vref_caches[vref]
    except KeyError:
        pass
    else:
        gk.debug("    * VREF Maker cache found!")
        return result, returncode

    result = ""
    oldtree = None
    newtree = None

    vl = vref.split("/")
    
    if len(vl) < 2:
        return result, 0

    r = git.cmd(["cat-file", "-p", oldsha])
    if r != "" and r is not None:
        m = re.search("tree [0-9a-f]*", r)
        if m:
            oldtree = m.group(0).lstrip("tree ")

    r = git.cmd(["cat-file", "-p", newsha])
    if r != "" and r is not None:
        m = re.search("tree [0-9a-f]*", r)
        if m:
            newtree = m.group(0).lstrip("tree ")

    if oldtree is not None and newtree is not None:
        fd = os.open("/dev/null", os.O_WRONLY)
        args = [getVREFMaker(vref), ref, oldsha, newsha, oldtree, newtree, mode, vref]

        i = 2
        while i < len(vl):
            args.append(vl[i])
            i += 1

        gk.debug("    args: %s", repr(args))
        vrefmaker = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = fd)
        result = vrefmaker.stdout.read().strip()
        vrefmaker.wait()
        os.close(fd)
        returncode = vrefmaker.returncode

    _vref_caches[vref] = [result, returncode]

    return result, returncode
"""

def permit(repo, user, mode, ref = "any"):
    global repoconf

    # sanity check the only piece the user can control
    if ref != "any":
        if not (re.match(r"^VREF/NAME/", ref) or re.search(rc.REF_OR_FILENAME_PATT, ref)):
            gk.bye("Invalid characters in ref or filename: \"%s\"")

    # apparently we can't always force sanity; at least what we *return*
    # should be sane/safe.  This pattern is based on REF_OR_FILENAME_PATT.
    safe_ref = re.sub(r"[^-0-9a-zA-Z._@/+ :,]", ".", ref)
    if safe_ref != ref:
        gk.warning("safe_ref %s created from %s", safe_ref, ref)

    # when a real repo doesn't exist, ^C is a pre-requisite for any other
    # check to give valid results.
    if mode != '^C' and repo[0] != "@" and re.search(repo, rc.REPONAME_PATT) and rc.repo_missing(repo):
        mode = '^C'

    # similarly, ^C must be denied if the repo exists
    if mode == '^C' and not rc.repo_missing(repo):
        gk.info("DENIED by existence")
        return False, "%s %s %s %s DENIED by existence" % (mode, safe_ref, repo, user)

    gk.info("")
    gk.info("Process rules (uid: %s, repo: %s, obj: %s, mode: %s)...", user, repo, ref, mode)

    repoconf = conf.load_conf(repo)

    not_found = True
    mp = mode.replace("+", "\+").replace("M", ".*M")
    
    for repo_rules in repoconf.repoRulesList:
        #repoconf.currentRepo = repo_rules
        gk.debug("")
        gk.debug("[repo: %s]", repr(repo_rules.repoex))
        not_found = False
        # option deny-rules is checked per repo_rules
        deny_rules = TRUE(repo_rules.options.get("deny-rules"))
        for rule in repo_rules.rules:
            refex = rule.refex.replace("USER", user)

            if deny_rules is False and rule.perms == "-" and ref == "any":
                continue

            if not(user in rule.members or "@all" in rule.members):
                continue

            gk.debug("  [rule: %s %s: %s]", rule.perms, refex, repr(rule.members))

            mm = re.match(refex, ref)
            if refex == "" or mm:
                gk.info("    * Rule refex matched (repoex: %s, refex: %s, ref: %s), check permission...", repo_rules.repoex, refex, ref)

                # denied by a deny rule
                if rule.perms == "-":
                    gk.info("    * Denied")
                    return False, "%s %s %s %s %s DENIED by %s" % (mode, rule.perms, safe_ref, repo, user, "any" if refex == "" else refex)
                # getting a normal rule permission
                elif re.search(mp, rule.perms):
                    gk.info("    * Permitted")
                    return True, "any" if refex == "" else refex
                # not getting a normal rule permission
                else:
                    gk.info("    * Not permitted")

    if not_found:
        gk.info("* Not found any matched rule")

    ret = not_found and repoconf.defaultAccess

    return ret, "PERMITTED by fallthru" if ret else "DENIED by fallthru"

def check_vrefs(repo, user, mode, ref, oldsha, newsha, oldtree, newtree):
    gk.info("")
    gk.info("*** Check VREF Makers ***")

    for repo_rules in repoconf.repoRulesList:
        repoconf.currentRepo = repo_rules
        gk.debug("")
        gk.debug("[repo: %s]", repr(repo_rules.repoex))
        for rule in repo_rules.rules:
            if not (user in rule.members or "@all" in rule.members):
                continue

            if not rule.isVref:
                continue
                
            refex = rule.refex.replace("USER", user)
            # invoke a VREF Maker
            rs, returncode = invokeVREFMaker(refex, ref, oldsha, newsha, oldtree, newtree, mode)
            # the result may be a multi-line message, split it as a string list via '\n'
            results = rs.split("\n")
            # VREF Maker return non-zero value, deny this update anyway
            if returncode != 0:
                return False, "%s %s %s %s %s DENIED by %s" % (mode, rule.perms, ref, repo, user, refex)

            for result in results:
                # rule matched and lines not starting with "VREF/" are printed it as is
                # so VREF Maker should print out normal message before VREF/ result
                s = re.sub(r"^VREF/.+/\S+", "", result).strip()
                if s != "":
                    print(s, file = sys.stderr)
                r, ret = permit(repo, user, mode, result)
                rc.trigger("ACCESS_2", repo, user, mode, result, r)
                if not r and ret.find("by fallthru") == -1:
                    return False, "%s %s %s %s %s DENIED by %s" % (mode, rule.perms, ref, repo, user, refex)

    return True, ""

def permit1(repo, user, mode, ref = "any", oldsha = None, newsha = None, skip_vref = False):
    # sanity check the only piece the user can control
    if ref != "any":
        if not (re.match(r"^VREF/NAME/", ref) or re.search(rc.REF_OR_FILENAME_PATT, ref)):
            gk.bye("Invalid characters in ref or filename: \"%s\"")

    # apparently we can't always force sanity; at least what we *return*
    # should be sane/safe.  This pattern is based on REF_OR_FILENAME_PATT.
    safe_ref = re.sub(r"[^-0-9a-zA-Z._@/+ :,]", ".", ref)
    if safe_ref != ref:
        gk.warning("safe_ref %s created from %s", safe_ref, ref)

    load_repo_conf(repo)

    # when a real repo doesn't exist, ^C is a pre-requisite for any other
    # check to give valid results.
    if mode != '^C' and repo[0] != "@" and re.search(repo, rc.REPONAME_PATT) and rc.repo_missing(repo):
        mode = '^C'

    # similarly, ^C must be denied if the repo exists
    if mode == '^C' and not rc.repo_missing(repo):
        gk.info("DENIED by existence")
        return False, "%s %s %s %s DENIED by existence" % (mode, safe_ref, repo, user)

    """
    Here's how the actual rule matching happens:

        # all the rules for this user and this repo are collected and examined in the sequence they appear in the conf file

        # for each rule:

            * If the ref does not match the refex, the rule is skipped.
            * If it's a deny rule, access is denied and the matching stops.
            * If the permission field matches the specific type of write operation, access is allowed and the matching stops.
            * If access is allowed.
            *   The normal rule matching stops, but VREF rule is still matching anyway.
            *   So only a VREF deny rule will has the chance to deny access.

        # If no rule ends with a decision, ("fallthru"), applies the value of defaultAccess.
    """

    if not skip_vref and mode != "^C":
        oldtree, newtree, mode = args(ref, oldsha, newsha) if ref != "any" else (None, None, mode)

    gk.info("")
    gk.info("Process rules (uid: %s, repo: %s, obj: %s, mode: %s)...", user, repo, ref, mode)

    allowed = False
    not_found = True
    denied = False
    msg = ""
    mp = mode.replace("+", "\+").replace("M", ".*M")
    last_refex = ""
    
    for repo_rules in repoconf.repoRulesList:
        repoconf.currentRepo = repo_rules
        gk.info("")
        gk.debug("[repo: %s]", repr(repo_rules.repoex))
        not_found = False
        # option deny-rules is checked per repo_rules
        deny_rules = TRUE(repo_rules.options.get("deny-rules"))
        for rule in repo_rules.rules:
            refex = rule.refex.replace("USER", user)
            if deny_rules is False and rule.perms == "-" and ref == "any":
                continue

            if (allowed or denied) and rule.isVref is False:
                continue

            if user in rule.members or "@all" in rule.members:
                gk.debug("  [rule: %s %s: %s]", rule.perms, refex, repr(rule.members))

                if not skip_vref and ref != "any" and rule.isVref:
                    # invoke a VREF Maker
                    rs, returncode = invokeVREFMaker(refex, ref, oldsha, newsha, oldtree, newtree, mode)
                    # the result may be a multi-line message, split it as a string list via '\n'
                    results = rs.split("\n")
                    # VREF Maker return non-zero value, deny this update anyway
                    if returncode != 0:
                        denied = True
                else:
                    results = [ref]

                msg = []
                matched = False
                for result in results:
                    mm = re.match(refex, result)
                    if refex == "" or mm:
                        matched = True
                        gk.info("    * Rule refex matched (repoex: %s, refex: %s, ref: %s), check permission...", repo_rules.repoex, refex, result)

                    # lines not starting with "VREF/" are printed it as is
                    if rule.isVref:
                        s = re.sub(r"^VREF/.+/\S+", "", result).strip()
                        if s != "":
                            msg += [s]

                ps = "%s"
                if matched and denied is False:
                    # denied by a deny rule
                    if rule.perms == "-":
                        denied = True
                        ss = "Denied"
                        ps = "...DENIED...%s"
                    # getting a normal rule permission
                    elif re.search(mp, rule.perms):
                        allowed = True
                        ss = "Permitted"
                        last_refex = refex
                    # not getting a normal rule permission
                    else:
                        ss = "Not permitted"
                    gk.info("    * %s", ss)

                if msg != []:
                    for m in msg:
                        print(ps % m, file = sys.stderr)
    
                if denied:
                    return False, "%s %s %s %s %s DENIED by %s" % (mode, rule.perms, safe_ref, repo, user, "any" if refex == "" else refex)

    if not_found:
        gk.info("* Not found any matched rule")

    ret = allowed or (not_found and repoconf.defaultAccess)

    return ret, last_refex if ret else "DENIED by fallthru"