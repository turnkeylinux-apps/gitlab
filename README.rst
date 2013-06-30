GitLab - Self Hosted Git Management
===================================

`GitLab`_ let's you keep & manage your code, similar to GitHub but on
your own server. GitLab helps you manage projects, issues and merge
requests and browse source code. It's a fast, secure and stable solution
based on Ruby on Rails.

This appliance includes all the standard features in `TurnKey Core`_,
and on top of that:

- GitLab configurations:
   
   - GitLab, Ruby1.9, RubyGems and all other required components
     installed from latest upstream versions.
   - Set GitLab admin password and email on firstboot (convenience,
     security).
   - Set GitLab domain to serve on first boot (convenience).
   - Pre-configured to use MySQL (recommended for production).
   - Includes Nginx pre-configured to proxy to unicorn daemon, with SSL
     support out of the box (performance, security).

- Includes postfix MTA (bound to localhost) for sending of email (e.g.
  password recovery). Also includes webmin postfix module for
  convenience.

Credentials *(passwords set at first boot)*
-------------------------------------------

-  Webmin, SSH, MySQL, phpMyAdmin: username **root**
-  GitLab: username is email set at first boot

.. _GitLab: http://gitlabhq.com
.. _TurnKey Core: http://www.turnkeylinux.org/core
