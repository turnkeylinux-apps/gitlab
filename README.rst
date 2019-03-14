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
   - Set GitLab admin user ('root') password and email set on
     firstboot (convenience, security).
   - Set GitLab domain to serve on first boot (convenience).

- Includes postfix MTA (bound to localhost) for sending of email (e.g.
  password recovery). Also includes webmin postfix module for
  convenience.

Credentials *(passwords set at first boot)*
-------------------------------------------

-  Webmin, SSH: username **root**
-  GitLab: username **root**

.. _GitLab: https://about.gitlab.com/
.. _TurnKey Core: https://www.turnkeylinux.org/core
.. _Omnibus package: https://docs.gitlab.com/omnibus/
