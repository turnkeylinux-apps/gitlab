TunrKey Linux GitLab - Update GitLab apt repo key
=================================================

.. contents::


Context
=======

This doc details how to fix a `GitLab "NO_PUBKEY" error`_ message when using
apt.

Background
==========

To ensure that the packages that you download are the ones provided by the
packager, apt repositories are cryptographically signed with a GPG key. From
time to time, these keys are "rotated" (i.e. new keys generated and this new
key used instead of the old one). When this happens, you will need to update
the GPG keyring that apt checks against when downloadng apt package lists.

GitLab upstream `provide instructions` on how to do that. However, TurnKey
Linux follows the "best practice" convention of specifying which particular
key any 3rd party repository should use. To ensure that this is honored, the
key needs to be stored in a particular location (as defined in the relevant
`sources.list entry`_) and added in a way slightly
different to the upstream instructions.

How to update the GitLab GPG key
================================

Assuming that the new keyfile provided by GitLab is the same as it was when
they rotated their keys (April 2020), then this will resolve the issue::

   curl -o /tmp/gitlab-ce.key https://packages.gitlab.com/gpg.key
   apt-key --keyring /usr/share/keyrings/gitlab-ce.gpg add /tmp/gitlab-ce.key

Note that if you are not running as root, 'sudo' will be required for the
second line.


.. _provide instructions: https://docs.gitlab.com/omnibus/update/package_signatures.html#fetching-new-keys-after-2020-04-06
.. _GitLab "NO_PUBKEY" error: https://github.com/turnkeylinux/tracker/issues/1441
.. _sources.list entry: https://github.com/turnkeylinux-apps/gitlab/blob/master/overlay/etc/apt/sources.list.d/gitlab-ce.list#L4
