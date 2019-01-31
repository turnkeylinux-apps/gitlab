#!/usr/bin/python
"""Set GitLab admin password, email and domain to serve

Option:
    --pass=     unless provided, will ask interactively
    --email=    unless provided, will ask interactively
    --domain=   unless provided, will ask interactively
                (can include schema)
                DEFAULT=www.example.com
    --schema=   unless provided (explicitly or via domain), will ask interactively
                DEFAULT=http
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

DEFAULT_DOMAIN = "www.example.com"
DEFAULT_SCHEMA = "http"

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "h",
                                       ['help', 'pass=', 'email=', 'domain='])
    except getopt.GetoptError, e:
        usage(e)

    email = ""
    domain = ""
    password = ""
    schema = ""
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

    if not domain.startswith('https://') and not domain.startswith('http://'):

        if not schema:
            if 'd' not in locals():
    	        d = Dialog("TurnKey GNU/Linux - First boot configuration")

    	    schema_check = d.yesno(
                "Domain Schema",
                "Select the default GitLab URL schema.\n\n" +
                "NOTE: If you select https but have not configured DNS for your domain, inialistation will fail.\n\n" +
                "If in doubt, please select 'http' (can be reconfigured later).",
                "http", "https")

        if not schema_check:
            schema = "http"
        else:
            schema = "https"

        if schema == "DEFAULT":
            domain = DEFAULT_SCHEMA

        domain = schema + "://" + domain

    inithooks_cache.write('APP_DOMAIN', domain)
    
    console_script = """ "
      ActiveRecord::Base.logger.level = 1;
      u = User.where(id: 1).first;
      u.password = '%s';
      u.email = '%s';
      u.skip_reconfirmation!;
      u.save!; 
      exit" """ % (password, email)

    print("Reconfiguring GitLab. This might take a while. Please wait...")

    config = "/etc/gitlab/gitlab.rb"
    system("sed -i \"/^external_url/ s|'.*|'%s'|\" %s" % (domain, config))
    system("sed -i \"/^gitlab_rails\['gitlab_email_from'\]/ s|=.*|= '%s'|\" %s" % (email, config))

    system("echo '%s' | gitlab-rails console production" % console_script)

    system("gitlab-ctl reconfigure")
    
if __name__ == "__main__":
    main()

