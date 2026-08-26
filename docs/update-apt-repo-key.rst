TurnKey Linux GitLab - Rotate the GitLab APT repository key
============================================================

.. contents::


Context
=======

This document explains how to recover from a GitLab repository ``NO_PUBKEY``
or expired-key error. Debian Trixie does not provide ``apt-key``. The GitLab
repository is instead restricted to
``/usr/share/keyrings/gitlab-ce.gpg`` by the source's ``signed-by`` option.

Trust boundary
==============

Obtain the full current repository-metadata signing-key fingerprint from the
official `GitLab Linux package signatures`_ page through a trusted browser.
The fingerprint documented for this appliance release is
``F6403F6544A38863DAA0B6E03F01618A51312F3F``. If GitLab has published a
replacement, substitute its complete 40-character uppercase fingerprint in
the procedure below. Do not trust a short key ID or the downloaded key alone.

The procedure verifies the download before changing trust, preserves the
per-repository ``signed-by`` restriction, and updates the appliance source
record consumed by ``gitlab-update --check``. Run it as ``root``::

   set -eu
   expected_fingerprint=F6403F6544A38863DAA0B6E03F01618A51312F3F
   key_url=https://packages.gitlab.com/gpg.key
   keyring=/usr/share/keyrings/gitlab-ce.gpg
   source_list=/etc/apt/sources.list.d/gitlab-ce.list
   source_record=/usr/local/share/turnkey-gitlab/source
   source_line="deb [signed-by=$keyring] https://packages.gitlab.com/gitlab/gitlab-ce/debian/ trixie main"
   work=$(mktemp -d /tmp/gitlab-key-rotation.XXXXXXXX)
   staged_keyring=
   staged_record=
   cleanup() {
       rm -rf -- "$work"
       test -z "$staged_keyring" || rm -f -- "$staged_keyring"
       test -z "$staged_record" || rm -f -- "$staged_record"
   }
   trap cleanup EXIT
   trap 'exit 1' HUP INT TERM

   test "$(id -u)" -eq 0
   grep -Fxq "$source_line" "$source_list"
   test "$(grep -c '^repository_key_fingerprint=' "$source_record")" -eq 1
   test "$(grep -c '^repository_key_sha256=' "$source_record")" -eq 1

   curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
       "$key_url" --output "$work/gitlab.key"
   fingerprint=$(gpg --show-keys --with-colons "$work/gitlab.key" | \
       awk -F: '$1 == "fpr" { print $10; exit }')
   test "$fingerprint" = "$expected_fingerprint"
   key_sha256=$(sha256sum "$work/gitlab.key" | awk '{ print $1 }')

   staged_keyring=$(mktemp /usr/share/keyrings/gitlab-ce.gpg.XXXXXXXX)
   gpg --batch --yes --dearmor --output "$staged_keyring" \
       "$work/gitlab.key"
   chmod 0644 "$staged_keyring"
   test "$(gpg --show-keys --with-colons "$staged_keyring" | \
       awk -F: '$1 == "fpr" { print $10; exit }')" = \
       "$expected_fingerprint"

   staged_record=$(mktemp /usr/local/share/turnkey-gitlab/source.XXXXXXXX)
   sed \
       -e "s/^repository_key_fingerprint=.*/repository_key_fingerprint=$expected_fingerprint/" \
       -e "s/^repository_key_sha256=.*/repository_key_sha256=$key_sha256/" \
       "$source_record" >"$staged_record"
   chmod --reference="$source_record" "$staged_record"

   mv -f -- "$staged_keyring" "$keyring"
   staged_keyring=
   mv -f -- "$staged_record" "$source_record"
   staged_record=

   apt-get update
   gitlab-update --check | tee "$work/update-check"
   grep -Fxq "integrity=APT-signed-by-$expected_fingerprint" \
       "$work/update-check"
   grep -Fxq "repository_key_download_sha256=$key_sha256" \
       "$work/update-check"

Every trust check occurs before APT refreshes repository metadata. If the
command is interrupted between the two final moves, ``gitlab-update --check``
fails because the keyring and source record disagree. Rerun the complete
procedure rather than weakening the ``signed-by`` restriction.


.. _GitLab Linux package signatures: https://docs.gitlab.com/omnibus/update/package_signatures/
