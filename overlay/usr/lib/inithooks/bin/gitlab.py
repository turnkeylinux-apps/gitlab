#!/usr/bin/python3
"""Set GitLab root user password, email and domain to serve

Option:
    --pass=     unless provided, will ask interactively
    --email=    unless provided, will ask interactively
    --domain=   unless provided, will ask interactively
                - can include schema
                DEFAULT=www.example.com
    --schema=   unless provided will default to 'http'
                - ignored if domain includes schema

"""

import getopt
import os
import sys
from libinithooks import inithooks_cache
from subprocess import run

from libinithooks.dialog_wrapper import Dialog

DEFAULT_DOMAIN = "www.example.com"


def usage(s=None):
    if s:
        print("Error:", s, file=sys.stderr)
    print("Syntax: %s [options]" % sys.argv[0], file=sys.stderr)
    print(__doc__, file=sys.stderr)
    sys.exit(1)


def main():
    try:
        opts, args = getopt.gnu_getopt(
                sys.argv[1:], "h",
                ['help', 'pass=', 'email=', 'domain=', 'schema=']
                )
    except getopt.GetoptError as e:
        usage(e)

    password = os.environ.get("APP_PASS", "")
    email = ""
    domain = ""
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
            "Enter new password for the GitLab 'root' account.",
            pass_req=8)

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

    if not domain.startswith('http'):
        if schema:
            if not schema.endswith("://"):
                schema = f"{schema}://"
            domain = f"{schema}{domain}"
        else:
            domain = f"http://{domain}"
    run(["sed", "-i", f"/^external_url/ s|'.*|'{domain}'|", config],
        check=True)
    run(["sed", "-i",
         fr"/^gitlab_rails\['gitlab_email_from'\]/ s|=.*|= '{email}'|",
         config], check=True)
    run(["gitlab-ctl", "reconfigure"], check=True)

    print("Setting GitLab 'root' user email. This might take a while.")
    email_env = os.environ.copy()
    email_env.pop('APP_PASS', None)
    email_env['TKL_ROOT_EMAIL'] = email
    update_email = run(
        ["gitlab-rails", "runner",
         "root = User.find_by!(username: 'root'); "
         "root.skip_reconfirmation!; "
         "root.update!(email: ENV.fetch('TKL_ROOT_EMAIL'))"],
        env=email_env,
        text=True,
        capture_output=True,
    )
    if update_email.stdout:
        print(update_email.stdout, end="")
    if update_email.stderr:
        print(update_email.stderr, file=sys.stderr, end="")
    if update_email.returncode:
        sys.exit(update_email.returncode)

    print("Setting GitLab 'root' user password. This might take a while.")
    reset = run(
        ["gitlab-rake", "gitlab:password:reset[root]"],
        input=f"{password}\n{password}\n",
        text=True,
        capture_output=True,
    )
    if reset.stdout:
        print(reset.stdout, end="")
    if reset.stderr:
        print(reset.stderr, file=sys.stderr, end="")
    sys.exit(reset.returncode)


if __name__ == "__main__":
    main()
