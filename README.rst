GitLab - Self Hosted Git Management & DevOps Toolchain
======================================================

`GitLab`_ is a single application for the entire software development
lifecycle. From project planning and source code management to CI/CD,
monitoring, and security. GitLab provides Git based version control,
packaged with a complete DevOps toolchain. Somewhat like GitHub, but
much, much more.

This appliance includes all the standard features in `TurnKey Core`_,
and on top of that:

- GitLab configurations:
   
   - GitLab, RubyGems, PostgreSQL, Nginx and all other required
     components installed from upstream `Omnibus package`_.

     **Security note**: Updates to GitLab may require supervision so
     they **ARE NOT** configured to install automatically. See below for
     updating GitLab. And/or see `GitLab documentation`_.

   - Set GitLab admin user ('root') password and email on
     firstboot (convenience, security).
   - Set GitLab domain to serve on first boot (convenience).
   - Enable GitLab Omnibus built-in Let's Encrypt certificates
     via Confconsole plugin (under "Lets Encrypt").

- Includes postfix MTA (bound to localhost) for sending of email (e.g.
  password recovery). Also includes webmin postfix module for
  convenience.

Supervised Manual GitLab Update
-------------------------------

Check the installed and eligible versions without changing the appliance::

    gitlab-update --check

Before an update, consult the `GitLab upgrade path`_ and the release-specific
`GitLab documentation`_. GitLab requires intermediate upgrade stops. Back up
the appliance, then install the next eligible version explicitly::

    apt update
    apt install gitlab-ce=<version>

Repeat the application acceptance checks before proceeding to another required
stop. Available versions are listed by ``apt-cache madison gitlab-ce`` and the
`GitLab release blog`_.

If APT reports an expired repository key or ``NO_PUBKEY``, follow the
`repository-key rotation procedure`_. It preserves the per-repository
``signed-by`` restriction and verifies GitLab's full published fingerprint.

Credentials *(passwords set at first boot)*
-------------------------------------------

-  Webmin, SSH: username **root**
-  GitLab: username **root**

.. _GitLab: https://about.gitlab.com/
.. _TurnKey Core: https://www.turnkeylinux.org/core
.. _Omnibus package: https://docs.gitlab.com/omnibus/
.. _GitLab documentation: https://docs.gitlab.com/omnibus/update/README.html
.. _GitLab upgrade path: https://docs.gitlab.com/update/upgrade_paths/
.. _GitLab release blog: https://about.gitlab.com/blog/categories/releases/
.. _repository-key rotation procedure: docs/update-apt-repo-key.rst
