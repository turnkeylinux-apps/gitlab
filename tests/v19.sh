#!/bin/bash
set -Eeuo pipefail
umask 077

result=${TKL_TEST_RESULT:?TKL_TEST_RESULT is required}
app_password=${TKL_TEST_APP_PASS:?TKL_TEST_APP_PASS is required}
source_file=/usr/local/share/turnkey-gitlab/source
fixture="turnkey-v19-$(date +%s)-$$"
token="tkl$(openssl rand -hex 20)"
work=$(mktemp -d /tmp/gitlab-v19.XXXXXXXX)
cookie=$work/cookie
page=$work/page
project_id=
key_id=

base=$(sed -n "s/^external_url '\([^']*\)'.*/\1/p" /etc/gitlab/gitlab.rb)
scheme=${base%%://*}
host=${base#*://}
host=${host%%/*}
host=${host%%:*}
if [[ $scheme == https ]]; then
    port=443
else
    port=80
fi
curl_local=(curl --insecure --silent --show-error --resolve "$host:$port:127.0.0.1")

json_field() {
    python3 -c '
import json
import sys

value = json.load(sys.stdin)[sys.argv[1]]
if value is None or value is False:
    raise SystemExit(1)
print(value)
' "$1"
}

cleanup() {
    set +e
    if [[ -n $key_id ]]; then
        "${curl_local[@]}" --request DELETE \
            --header "PRIVATE-TOKEN: $token" \
            "$base/api/v4/user/keys/$key_id" >/dev/null
    fi
    if [[ -n $project_id ]]; then
        "${curl_local[@]}" --request DELETE \
            --header "PRIVATE-TOKEN: $token" \
            "$base/api/v4/projects/$project_id" >/dev/null
    fi
    gitlab-rails runner \
        "item = PersonalAccessToken.find_by_token('$token'); item.revoke! if item" \
        >/dev/null 2>&1
    find "$work" -depth -delete
}
trap cleanup EXIT

for unit in gitlab-runsvdir.service postfix.service; do
    systemctl --quiet is-active "$unit"
    systemctl --quiet is-enabled "$unit"
done
for component in nginx postgresql redis sidekiq gitaly; do
    gitlab-ctl status "$component" | grep -Fq "run: $component:"
done

# Preserve memory for the identity flow on the constrained Docker runner.
# The checks above first prove normal init and required Sidekiq health. Stop
# background and observability workers only in this disposable container.
for component in alertmanager gitlab-exporter gitlab-kas node-exporter \
        postgres-exporter prometheus redis-exporter sidekiq; do
    gitlab-ctl stop "$component" >/dev/null
done
puma_config=/var/opt/gitlab/gitlab-rails/etc/puma.rb
sed -Ei \
    -e 's/^workers [0-9]+$/workers 1/' \
    -e 's/^  options = \{ workers: [0-9]+ \}$/  options = { workers: 1 }/' \
    "$puma_config"
grep -Fxq 'workers 1' "$puma_config"
grep -Fxq '  options = { workers: 1 }' "$puma_config"
gitlab-ctl restart puma >/dev/null

grep -Fxq 'VERSION_CODENAME=trixie' /etc/os-release
grep -Eq '^turnkey-gitlab-19\.0' /etc/turnkey_version
test -d /usr/share/webmin/postfix
test -f /usr/lib/confconsole/plugins.d/Lets_Encrypt/get_certificate.py

# shellcheck disable=SC1090
. "$source_file"
test "$(dpkg-query -W -f='${Version}' gitlab-ce)" = "$installed_version"
test "$installed_version" = 19.3.0-ce.0
test "$package_sha256" = f88f80cd61d6b2beb35aa7207591d4abdfed0e6c2c42e6ed753dd29ea5de076d
test "$(gpg --show-keys --with-colons /usr/share/keyrings/gitlab-ce.gpg |
    awk -F: '$1 == "fpr" { print $10; exit }')" = \
    "$repository_key_fingerprint"

"${curl_local[@]}" --fail --retry 30 --retry-delay 2 \
    --retry-all-errors --cookie-jar "$cookie" \
    "$base/users/sign_in" >"$page"
csrf=$(sed -n 's/.*name="authenticity_token" value="\([^"]*\)".*/\1/p' \
    "$page")
test -n "$csrf"
"${curl_local[@]}" --fail --location --cookie "$cookie" \
    --cookie-jar "$cookie" \
    --data-urlencode "authenticity_token=$csrf" \
    --data-urlencode 'user[login]=root' \
    --data-urlencode "user[password]=$app_password" \
    --data-urlencode 'user[remember_me]=0' \
    "$base/users/sign_in" >"$page"
"${curl_local[@]}" --fail --cookie "$cookie" \
    "$base/api/v4/user" | json_field username | grep -Fxq root

gitlab-rails runner \
    "item = User.find_by_username('root').personal_access_tokens.create!(scopes: ['api'], name: '$fixture', expires_at: 1.day.from_now); item.set_token('$token'); item.save!"

project=$("${curl_local[@]}" --fail --request POST \
    --header "PRIVATE-TOKEN: $token" \
    --data-urlencode "name=$fixture" \
    --data-urlencode "path=$fixture" \
    --data 'visibility=private' \
    "$base/api/v4/projects")
project_id=$(json_field id <<<"$project")
test "$(json_field path <<<"$project")" = "$fixture"

ssh-keygen -q -t ed25519 -N '' -f "$work/id"
key=$("${curl_local[@]}" --fail --request POST \
    --header "PRIVATE-TOKEN: $token" \
    --data-urlencode "title=$fixture" \
    --data-urlencode "key=$(<"$work/id.pub")" \
    "$base/api/v4/user/keys")
key_id=$(json_field id <<<"$key")
ssh-keyscan -T 10 127.0.0.1 >"$work/known_hosts" 2>/dev/null
export GIT_SSH_COMMAND="ssh -i $work/id -o IdentitiesOnly=yes -o UserKnownHostsFile=$work/known_hosts"

git -C "$work" init -q repository
git -C "$work/repository" config user.name 'TurnKey acceptance'
git -C "$work/repository" config user.email 'acceptance@example.invalid'
printf 'GitLab v19 project round trip\n' >"$work/repository/README.md"
git -C "$work/repository" add README.md
git -C "$work/repository" commit -qm 'Add acceptance marker'
git -C "$work/repository" remote add origin \
    "git@127.0.0.1:root/$fixture.git"
git -C "$work/repository" push -q -u origin HEAD:main
git clone -q "git@127.0.0.1:root/$fixture.git" "$work/readback"
grep -Fxq 'GitLab v19 project round trip' "$work/readback/README.md"

"${curl_local[@]}" --fail --header "PRIVATE-TOKEN: $token" \
    "$base/root/$fixture/-/raw/main/README.md" |
    grep -Fxq 'GitLab v19 project round trip'
gitlab-psql --no-align --tuples-only --command \
    "SELECT path FROM projects WHERE id = $project_id;" |
    grep -Fxq "$fixture"

gitlab-update --check >"$work/update"
candidate=$(sed -n 's/^candidate=//p' "$work/update")
status=$(sed -n 's/^status=//p' "$work/update")
test -n "$candidate"
grep -Fxq 'channel=official-gitlab-ce-debian-trixie' "$work/update"
grep -Fxq "integrity=APT-signed-by-$repository_key_fingerprint" "$work/update"

cat >"$result" <<EOF
package_source=Official GitLab CE Debian Trixie repository
installed_version=$installed_version
runtime_checks=normal init; root web login; project API create and web read; SSH Git push and clone; PostgreSQL readback; Sidekiq; Postfix
updater_command=gitlab-update --check
updater_result=$status; candidate=$candidate
updater_channel=official GitLab CE Debian Trixie, supervised required-stop upgrades
integrity_evidence=repository key $repository_key_fingerprint; package SHA-256 $package_sha256
EOF
