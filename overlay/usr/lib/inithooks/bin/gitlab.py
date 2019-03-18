#!/usr/bin/python
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
import inithooks_cache
import os
import pwd

from dialog_wrapper import Dialog
from executil import ExecError, system


def usage(s=None):
    if s:
        print >> sys.stderr, "Error:", s
    print >> sys.stderr, "Syntax: %s [options]" % sys.argv[0]
    print >> sys.stderr, __doc__
    sys.exit(1)

DEFAULT_DOMAIN = "www.example.com"

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
    
    print("Reconfiguring GitLab. This might take a while. Please wait.")

    config = "/etc/gitlab/gitlab.rb"
    domain = "http://%s" % domain
    system("sed -i \"/^external_url/ s|'.*|'%s'|\" %s" % (domain, config))
    system("sed -i \"/^gitlab_rails\['gitlab_email_from'\]/ s|=.*|= '%s'|\" %s" % (email, config))
    system("gitlab-ctl reconfigure")

    print("Setting GitLab 'root' user password and email in database. This might take a while too. Please wait (again).")
    tmp_dir = '/run/user/0'
    tmp_file = '.gitlab-init.rb'
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    tmp_path = '/'.join([tmp_dir, tmp_file])
    tmp_contents = """
        ActiveRecord::Base.logger.level = 1
        u = User.where(id: 1).first
        u.password = u.password_confirmation = '{}'
        u.email = '{}'
        u.skip_reconfirmation!
        u.save!
        exit
    """
    flags = os.O_WRONLY | os.O_CREAT
    with os.fdopen(os.open(tmp_path, flags, 0o600), 'w') as fob:
        fob.write(tmp_contents.format(password, email))
    uid = pwd.getpwnam('git').pw_uid
    os.chown(tmp_path, uid, 0)
    try:
        system("gitlab-rails runner -e production %s" % tmp_path)
    finally:
        os.remove(tmp_path)

if __name__ == "__main__":
    main()
