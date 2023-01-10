#!/usr/bin/python3
"""Set GitLab root (admin) password, email and domain to serve

Option:
    --pass=     unless provided, will ask interactively
    --email=    unless provided, will ask interactively
    --domain=   unless provided, will ask interactively
                (can include schema)
                DEFAULT=www.example.com
"""

import sys
import getopt
from libinithooks import inithooks_cache
import os
import pwd
from subprocess import run, Popen, PIPE

from libinithooks.dialog_wrapper import Dialog


def usage(s=None):
    if s:
        print("Error:", s, file=sys.stderr)
    print("Syntax: %s [options]" % sys.argv[0], file=sys.stderr)
    print(__doc__, file=sys.stderr)
    sys.exit(1)

DEFAULT_DOMAIN = "www.example.com"

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "h",
                                       ['help', 'pass=', 'email=', 'domain='])
    except getopt.GetoptError as e:
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
        elif opt == '--schema':
            schema = val

    if not password:
        d = Dialog('TurnKey Linux - First boot configuration')
        password = d.get_password(
            "GitLab Password",
            "Enter new password for the GitLab 'root' account.",
            pass_req = 8)

    if not email:
        if 'd' not in locals():
            d = Dialog('TurnKey Linux - First boot configuration')

        email = d.get_email(
            "GitLab Email",
            "Enter email address for the GitLab 'root' account.",
            "admin@example.com")

    inithooks_cache.write('APP_EMAIL', email)

    if not domain:
        if 'd' not in locals():
            d = Dialog('TurnKey Linux - First boot configuration')

        domain = d.get_input(
            "GitLab Domain",
            "Enter the domain to serve GitLab.",
            DEFAULT_DOMAIN)

    if domain == "DEFAULT":
        domain = DEFAULT_DOMAIN

    inithooks_cache.write('APP_DOMAIN', domain)
    
    print("Reconfiguring GitLab. This might take a while.")
    config = "/etc/gitlab/gitlab.rb"
    domain = "http://%s" % domain
    run(["sed", "-i", "/^external_url/ s|'.*|'%s'|" % domain, config])
    run(["sed", "-i", "/^gitlab_rails\['gitlab_email_from'\]/ s|=.*|= '%s'|" % email, config])
    run(["gitlab-ctl", "reconfigure"])

    print("Setting GitLab 'root' user password. This might take a while.")
    p1 = Popen(["echo", "-e", "{}\n{}\n".format(password, password)], stdout=PIPE)
    p2 = Popen(["gitlab-rake", "gitlab:password:reset[root]"], stdin=p1.stdout, stdout=PIPE)
    p1.stdout.close()
    output = p2.communicate()[0]
    print(output)

if __name__ == "__main__":
    main()
