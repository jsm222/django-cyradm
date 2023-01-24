ABOUT
====================
django-cyradm is a web interface to manage postfix controlling accounts, aliases and virtual (hosted) domains. Optionally it manages a belonging imap server for creating/deleting mailboxes and setting storage quotas. The project is meant to be suitable for small mail hosts using sql lookup tables with postfix. 

DEMO
====

a online demo is available at https://djcyradm.schmitz.computer/djcyradm/login

The credentials are username: cyrus password: cyrus

The demo syncs with an imap server but postfix is not configured in the demo environment.


FEATURES
=========

* Any django database backend is supported, but the backend must also be supported by postfix. In the documentation postfix with mysql or postgresql are used. 
* As an imap server cyrus-imap is the only one tested, but the project does not contain cyrus specific code.
* imap syncing can easily be turned on and off.
* Support for mailforwarding, and external aliases
* External recovery email setting to restore account passwords. 
* A virtual domain can be marked as an alias domain, in which no accounts can be created, but a configurable limited number of external or internal aliases can be created.
* The administration of one or more hosted (virtual) domains can be delegated to a user, belonging to the domain admins group
* The admins can set limit for each domains resources, e.g number of accounts aliases and external aliases.
* The domain admins can set limits on each account in their admin domains (limited by limits set by the admins on the domains)
* The account users can configure their alisases passwords and mailforwarding.
* Easy initilizing of the cyrus admin
* Deactivating and activating accounts and aliases.
* Presenting users to captcha on to many failed attempts (provided by django-axes and django-simple-captcha

DOCS
====
https://djcyradm.schmitz.computer
