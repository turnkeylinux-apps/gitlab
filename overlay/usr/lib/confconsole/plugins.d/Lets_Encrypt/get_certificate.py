"""Get Let's Encrypt SSl cert"""

import requests
import subprocess

# import inithooks_cache (from absolute path) for managing domain caching
import sys
sys.path.append('/usr/lib/inithooks/bin')
from libinithooks import inithooks_cache

LE_INFO_URL = 'https://acme-v02.api.letsencrypt.org/directory'

TITLE = 'Certificate Creation Wizard (GitLab)'

DESC = """Please enter the GitLab domain to generate certificate for.

This is pre-populated with the domain set at firstboot. Please update this
here to change the set domain and attempt to generate a Let's Encrypt cert.

Please note that this leverages GitLab Omnibus package's bundled
support for Let's Encrypt.

For more details, please see:
https://docs.gitlab.com/omnibus/settings/ssl/
"""


example_domain = 'www.example.com'

# XXX Debug paths


def load_domain() -> str:
    ''' Loads domain from inithooks cache '''
    return str(inithooks_cache.read('APP_DOMAIN'))


def save_domain(domain):
    ''' Saves domain configuration '''
    inithooks_cache.write('APP_DOMAIN', domain)


def strip_schema(url: str) -> str:
    '''Return domain with http/https schema stripped'''
    if url.startswith('http://'):
        return url[7:]
    elif url.startswith("https://"):
        return url[8:]
    return url


def invalid_domain(domain):
    ''' Validates well known limitations of domain-name specifications
    doesn't enforce when or if special characters are valid. Returns a
    string if domain is invalid explaining why otherwise returns False'''
    if domain == '':
        return 'Error: A domain must be provided'
    if len(domain) != 0:
        if len(domain) > 254:
            return 'Error: Domain must not exceed 254 characters'
        for part in domain.split('.'):
            if not 0 < len(part) < 64:
                return ('Error: Domain segments may not be larger than 63'
                        ' characters or less than 1')
    return False


def run():
    field_width = 60

    canceled = False

    tos_url = None
    try:
        response = requests.get(LE_INFO_URL)
        tos_url = response.json()['meta']['termsOfService']
    except requests.exceptions.RequestException as e:
        msg = f"Failed to connect get data from '{LE_INFO_URL}': '{e}'"
    if not tos_url:
        console.msgbox('Error', msg, autosize=True)
        return

    ret = console.yesno(
        'DNS must be configured before obtaining certificates. '
        'Incorrectly configured DNS and excessive attempts could '
        'lead to being temporarily blocked from requesting '
        'certificates.\n\nDo you wish to continue?',
        autosize=True
    )
    if ret != 'ok':
        return

    ret = console.yesno(
        "Before getting a Let's Encrypt certificate, you must agree to the"
        " current Terms of Service."
        f"\n\nYou can find the current Terms of Service here: \n\n{tos_url}"
        "\n\nDo you agree to the Let's Encrypt Terms of Service?",
        autosize=True
    )
    if ret != 'ok':
        return

    # should have a cached valid domain from firstboot
    domain = strip_schema(load_domain())
    # but double check and use example if not
    if invalid_domain(domain):
        domain = example_domain
    domain = f"https://{domain}"

    while True:
        while True:
            field = [
                ('Domain', 1, 0, domain, 1, 10, field_width, 255),
            ]
            ret, value = console.form(TITLE, DESC, field, autosize=True)
            if len(value) >= 1:
                value = value[0]
            if ret != 'ok':
                canceled = True
                break

            msg = invalid_domain(value)
            if msg:
                console.msgbox('Error', msg)
                continue

            if ret == 'ok':
                ret2 = console.yesno("This will overwrite previous settings"
                                     " and check for certificate, continue?")
                if ret2 == 'ok':
                    save_domain(value)
                    break

        if canceled:
            break

        config = "/etc/gitlab/gitlab.rb"
        # should be https already - but ensure it
        domain = f"https://{strip_schema(domain)}"

        subprocess.run(["sed", "-i",
                        f"/^external_url/ s|'.*|'{domain}'|", config])
        subprocess.run(["sed", "-i",
                        r"/letsencrypt\['enable'\]/ s|^# *||", config])
        subprocess.run(["sed", "-i",
                        r"/^letsencrypt\['enable'\]/ s|=.*|= true|", config])
        subprocess.run(["sed", "-i",
                        r"/letsencrypt\['auto_renew'\]/ s|^# *||", config])
        subprocess.run(["sed", "-i",
                        r"/^letsencrypt\['auto_renew'\]/ s|=.*|= true|",
                        config])
        print('Running gitlab-ctl reconfigure. This might take a while...')
        exit_code = subprocess.run(['gitlab-ctl', 'reconfigure']).returncode

        if exit_code != 0:
            console.msgbox(
                "GitLab Error!",
                "Something went wrong! :("
                f"\n\nPlease check that the domain {domain} resolves to a"
                " publicly accessable IP address for this server and that"
                " ports 80 and 443 are publicly accessible."
                "\n\nIt is also possible that there is some other issue with"
                f" your config file ({config})."
                "\n\nFor full details, please try running 'gitlab-ctl"
                " reconfigure' from the commandline."
                "\n\nAlso see:\n"
                "\nhttps://docs.gitlab.com/omnibus/settings/ssl/")
        else:
            save_domain(domain)
