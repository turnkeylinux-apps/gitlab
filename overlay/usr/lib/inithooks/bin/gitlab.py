#!/usr/bin/python
"""Set GitLab admin password, email and domain to serve

Option:
    --pass=     unless provided, will ask interactively
    --email=    unless provided, will ask interactively
    --domain=   unless provided, will ask interactively
                DEFAULT=www.example.com
"""

import sys
import getopt
import inithooks_cache

from dialog_wrapper import Dialog
from executil import ExecError, system


def usage(s=None):
    if s:
        print >> sys.stderr, "Error:", s
    print >> sys.stderr, "Syntax: %s [options]" % sys.argv[0]
    print >> sys.stderr, __doc__
    sys.exit(1)

DEFAULT_DOMAIN="www.example.com"

def system_gitlab(cmd):
    system("sudo -u git -H sh -c", "cd /home/git/gitlab; %s" % cmd)

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
            "Enter new password for the GitLab 'admin' account.",
            pass_req = 8)

    if not email:
        if 'd' not in locals():
            d = Dialog('TurnKey Linux - First boot configuration')

        email = d.get_email(
            "GitLab Email",
            "Enter email address for the GitLab 'admin' account.",
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
    
    console_script = """ "
      ActiveRecord::Base.logger.level = 1;
      u = User.where(id: 1).first;
      u.password = '%s';
      u.email = '%s';
      u.skip_reconfirmation!;
      u.save!; " """ % (password, email)

    print("Please wait...")
    system_gitlab("RAILS_ENV=production bundle exec rails r %s 2>&1 1>/dev/null" % console_script)

    config = "/home/git/gitlab/config/gitlab.yml"
    system("sed -i \"s|host:.*|host: %s|\" %s" % (domain, config))
    system("sed -i \"s|email_from:.*|email_from: %s|\" %s" % (email, config))

    system_gitlab("git config --global user.email %s" % email)

    # restart gitlab if it's running
    try:
        system("service gitlab restart")
    except ExecError:
        pass

if __name__ == "__main__":
    main()

