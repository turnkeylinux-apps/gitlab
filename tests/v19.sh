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
grep -Fxq 'VERSION_CODENAME=trixie' /etc/os-release
grep -Eq '^turnkey-gitlab-19\.0' /etc/turnkey_version
test -d /usr/share/webmin/postfix
test -f /usr/lib/confconsole/plugins.d/Lets_Encrypt/get_certificate.py

# shellcheck disable=SC1090
. "$source_file"
: "${installed_version:?installed_version is missing from $source_file}"
: "${package_sha256:?package_sha256 is missing from $source_file}"
: "${repository_key_fingerprint:?repository_key_fingerprint is missing from $source_file}"
test "$(dpkg-query -W -f='${Version}' gitlab-ce)" = "$installed_version"
test "$installed_version" = 19.3.0-ce.0
test "$package_sha256" = f88f80cd61d6b2beb35aa7207591d4abdfed0e6c2c42e6ed753dd29ea5de076d
test "$(gpg --show-keys --with-colons /usr/share/keyrings/gitlab-ce.gpg |
    awk -F: '$1 == "fpr" { print $10; exit }')" = \
    "$repository_key_fingerprint"

"${curl_local[@]}" --fail --cookie-jar "$cookie" \
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
    "$base/api/v4/user" | jq -e '.username == "root"' >/dev/null

gitlab-rails runner \
    "item = User.find_by_username('root').personal_access_tokens.create!(scopes: ['api'], name: '$fixture', expires_at: 1.day.from_now); item.set_token('$token'); item.save!"

project=$("${curl_local[@]}" --fail --request POST \
    --header "PRIVATE-TOKEN: $token" \
    --data-urlencode "name=$fixture" \
    --data-urlencode "path=$fixture" \
    --data 'visibility=private' \
    "$base/api/v4/projects")
project_id=$(jq -er '.id' <<<"$project")
test "$(jq -r '.path' <<<"$project")" = "$fixture"

ssh-keygen -q -t ed25519 -N '' -f "$work/id"
key=$("${curl_local[@]}" --fail --request POST \
    --header "PRIVATE-TOKEN: $token" \
    --data-urlencode "title=$fixture" \
    --data-urlencode "key=$(<"$work/id.pub")" \
    "$base/api/v4/user/keys")
key_id=$(jq -er '.id' <<<"$key")
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
gitlab-ctl status sidekiq | grep -Fq 'run: sidekiq:'
ruby=$work/background-job.rb
cat >"$ruby" <<'RUBY'
require 'sidekiq/api'
project_id = Integer(ENV.fetch('TKL_PROJECT_ID'), 10)
statistics = ['repository_size']
lease_key = ['project_cache_worker', project_id, *statistics].join(':')
jid = ProjectCacheWorker.perform_async(project_id, [], statistics)
deadline = 90.seconds.from_now
loop do
  followup = Sidekiq::ScheduledSet.new.find do |job|
    job.klass == 'UpdateProjectStatisticsWorker' &&
      job.args[0] == lease_key && job.args[1] == project_id
  end
  if followup
    followup.delete
    puts "Sidekiq project cache round trip: #{jid}"
    break
  end
  retry_job = Sidekiq::RetrySet.new.find_job(jid)
  raise "ProjectCacheWorker entered retry: #{retry_job.error_message}" if retry_job
  raise 'ProjectCacheWorker timed out' if Time.current >= deadline
  sleep 1
end
RUBY
TKL_PROJECT_ID=$project_id gitlab-rails runner "$ruby"

gitlab-update --check >"$work/update"
candidate=$(sed -n 's/^candidate=//p' "$work/update")
status=$(sed -n 's/^status=//p' "$work/update")
test -n "$candidate"
grep -Fxq 'channel=official-gitlab-ce-debian-trixie' "$work/update"
grep -Fxq "integrity=APT-signed-by-$repository_key_fingerprint" "$work/update"

cat >"$result" <<EOF
package_source=Official GitLab CE Debian Trixie repository
installed_version=$installed_version
runtime_checks=normal init; root web login; project API create and web read; SSH Git push and clone; PostgreSQL readback; Sidekiq project cache job; Postfix
updater_command=gitlab-update --check
updater_result=$status; candidate=$candidate
updater_channel=official GitLab CE Debian Trixie, supervised required-stop upgrades
integrity_evidence=repository key $repository_key_fingerprint; package SHA-256 $package_sha256
EOF
