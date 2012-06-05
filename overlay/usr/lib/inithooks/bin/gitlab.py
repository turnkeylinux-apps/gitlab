#!/usr/bin/python
"""Set GitLab admin password, email and domain to serve

Option:
    --pass=     unless provided, will ask interactively
    --email=    unless provided, will ask interactively
    --domain=   unless provided, will ask interactively
                DEFAULT=git.example.com
"""

import re
import sys
import getopt

from passlib.hash import bcrypt

from dialog_wrapper import Dialog
from mysqlconf import MySQL
from executil import system

def usage(s=None):
    if s:
        print >> sys.stderr, "Error:", s
    print >> sys.stderr, "Syntax: %s [options]" % sys.argv[0]
    print >> sys.stderr, __doc__
    sys.exit(1)

DEFAULT_DOMAIN="git.example.com"

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "h",
                                       ['help', 'pass=', 'email=', 'domain='])
    except getopt.GetoptError, e:
        usage(e)

    email = ""
    domain = ""
    password = ""
    for opt, val in opts:
        if opt in ('-h', '--help'):
            usage()
        elif opt == '--pass':
            password = val
        elif opt == '--email':
            email = val
        elif opt == '--domain':
            domain = val

    if not password:
        d = Dialog('TurnKey Linux - First boot configuration')
        password = d.get_password(
            "GitLab Password",
            "Enter new password for the GitLab 'admin' account.")

    if not email:
        if 'd' not in locals():
            d = Dialog('TurnKey Linux - First boot configuration')

        email = d.get_email(
            "GitLab Email",
            "Enter email address for the GitLab 'admin' account.",
            "admin@example.com")

    if not domain:
        if 'd' not in locals():
            d = Dialog('TurnKey Linux - First boot configuration')

        domain = d.get_input(
            "GitLab Domain",
            "Enter the domain to serve GitLab.",
            DEFAULT_DOMAIN)

    if domain == "DEFAULT":
        domain = DEFAULT_DOMAIN

    hashpass = bcrypt.encrypt(password, rounds=10)

    m = MySQL()
    m.execute('UPDATE gitlab_production.users SET email=\"%s\" WHERE name=\"Administrator\";' % email)
    m.execute('UPDATE gitlab_production.users SET encrypted_password=\"%s\" WHERE name=\"Administrator\";' % hashpass)

    new = []
    config = "/home/gitlab/gitlab/config/gitlab.yml"
    for s in file(config).readlines():
        s = s.rstrip()
        s = re.sub("from: (.*)", "from: %s" % email, s)
        if not "host: localhost" in s:
            s = re.sub("host: (.*)", "host: %s" % domain, s)
        new.append(s)
    fh = file(config, "w")
    print >> fh, "\n".join(new)
    fh.close()
    system("chown gitlab:git %s" % config)

    system("/etc/init.d/gitlab stop >/dev/null 2>&1")
    system("/etc/init.d/ssh start")
    system("/etc/init.d/redis-server start")
    system("cd /home/gitlab/gitlab; sudo -u gitlab bundle exec rake gitlab:app:enable_automerge RAILS_ENV=production")
    system("/etc/init.d/ssh stop")
    system("/etc/init.d/redis-server stop")


if __name__ == "__main__":
    main()

