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
   - Enbale GitLab Omnibus built-in Let's Encrypt certificates
     via Confconsole plugin (under "Lets Encrypt").

- Includes postfix MTA (bound to localhost) for sending of email (e.g.
  password recovery). Also includes webmin postfix module for
  convenience.

Supervised Manual GitLab Update
-------------------------------

It is recommended to always first check the `GitLab documentation`_ prior to
update. It is also recommended that you ensure you have a full backup (TKLBAM
is a good option, but there are other methods). Once you are statisfied,
update to the latest stable release via apt::

    apt update
    apt install gitlab-ce

You can view available versions via the `GitLab 'release' blog tag`_. We also
highly recommend subscribing to receive email notifications.

Credentials *(passwords set at first boot)*
-------------------------------------------

-  Webmin, SSH: username **root**
-  GitLab: username **root**

.. _GitLab: https://about.gitlab.com/
.. _TurnKey Core: https://www.turnkeylinux.org/core
.. _Omnibus package: https://docs.gitlab.com/omnibus/
.. _GitLab documentation: https://docs.gitlab.com/omnibus/update/README.html
.. _GitLab 'release' blog tag: https://about.gitlab.com/blog/categories/releases/
