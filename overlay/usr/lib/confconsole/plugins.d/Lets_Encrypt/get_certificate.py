"""Get Let's Encrypt SSl cert"""

import requests
from executil import system
import subprocess
from os import path, remove

# import inithooks_cache (from absolute path) for managing domain caching
import sys
sys.path.append('/usr/lib/inithooks/bin')
import inithooks_cache

LE_INFO_URL = 'https://acme-v01.api.letsencrypt.org/directory'

TITLE = 'Certificate Creation Wizard (GitLab)'

DESC = """Please enter the GitLab domain to generate certificate for.

This is pre-populated with the domain set at firstboot. Please update this
here to change the set domain and attempt to generate a Let's Encrypt cert.

Please note that this leverages GitLab Omnibus package's bundled
support for Let's Encrypt.

For more details, please see:
https://docs.gitlab.com/omnibus/settings/ssl.html
"""

example_domain = 'www.example.com'

# XXX Debug paths

def load_domain():
    ''' Loads domain from inithooks cache '''
    return inithooks_cache.read('APP_DOMAIN')

def save_domain(domain):
    ''' Saves domain configuration '''
    inithooks_cache.write('APP_DOMAIN', domain)

def invalid_domain(domain):
    ''' Validates well known limitations of domain-name specifications
    doesn't enforce when or if special characters are valid. Returns a
    string if domain is invalid explaining why otherwise returns False'''
    if domain == '':
        return ('Error: A domain must be provided in {} (with no'
            ' preceeding space)'.format(domain_path))
    if len(domain) != 0:
        if len(domain) > 254:
            return ('Error in {}: Domain name must not exceed 254'
                ' characters'.format(domain))
        for part in domain.split('.'):
            if not 0 < len(part) < 64:
                return ('Error in {}: Domain segments may not be larger'
                    ' than 63 characters or less than 1'.format(domain))
    return False

def uncomment(file_name, search_term):
    '''Dirty function that leverages sed.'''
    system("sed -i \"/{}/ s|^# *||\" {}".format(search_term, filename))

def run():
    field_width = 60
    field_name = 'domain'

    canceled = False

    try:
        response = requests.get(LE_INFO_URL)
        tos_url = response.json()['meta']['terms-of-service']
    except ConnectionError:
        msg = 'Connection error. Failed to connect to '+LE_INFO_URL
    except JSONDecodeError:
        msg = 'Data error, no JSON data found'
    except KeyError:
        msg = 'Data error, no value found for "terms-of-service"'
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
    if ret:
        return

    ret = console.yesno(
        "Before getting a Let's Encrypt certificate, you must agree "
        'to the current Terms of Service.\n\n'
        'You can find the current Terms of Service here:\n\n'
        +tos_url+'\n\n'
        "Do you agree to the Let's Encrypt Terms of Service?",
        autosize=True
    )
    if ret:
        return

    domain = load_domain()
    m = invalid_domain(domain)

    if m:
        ret = console.yesno(
                (str(m) + '\n\nWould you like to ignore and overwrite data?'))
        if not ret:
            remove(domain_path)
            domain = load_domain()
        else:
            return

    value = domain

    while True:
        while True:
            field = [
                ('Domain', value, field_width, 255),
            ]
            ret, value = console.form(TITLE, DESC, field, autosize=True)
            if len(value) >= 1:
                value = value[0]
            if ret != 0:
                canceled = True
                break

            msg = invalid_domain(value)
            if msg:
                console.msgbox('Error', msg)
                continue

            if ret is 0:
                ret2 = console.yesno('This will overwrite previous settings and check for certificate, continue?')
                if ret2 is 0:
                    save_domain(value)
                    break

        if canceled:
            break

        config = "/etc/gitlab/gitlab.rb"
        domain = "https://{}".format(domain)
        system("sed -i \"/^external_url/ s|'.*|'{}'|\" {}".format(domain, config))
        system("sed -i \"/letsencrypt\['enable'\]/ s|^# *||\" {}".format(config))
        system("sed -i \"/^letsencrypt\['enable'\]/ s|=.*|= true|\" {}".format(config))
        system("sed -i \"/letsencrypt\['auto_renew'\]/ s|^# *||\" {}".format(config))
        system("sed -i \"/^letsencrypt\['auto_renew'\]/ s|=.*|= true|\" {}".format(config))
        print('Running gitlab-ctl reconfigure. This might take a while...')
        exit_code = subprocess.call(['gitlab-ctl', 'reconfigure'])

        if exit_code != 0:
            console.msgbox('GitLab Error!', 'Something went wrong!\nPlease check that '
                'the domain {} resolves to a publicly accessable IP address for this '
                'server and that ports 80 and 443 are publicly accessible.\n\n'
                'It is also possible that there is some other issue with your config '
                'file ({}).\n\nFor full details, please try running \'gitlab-ctl '
                'reconfigure\' from the commandline.\n\nAlso see:\n'
                'https://docs.gitlab.com/omnibus/settings/ssl.html'.format(domain, config))
