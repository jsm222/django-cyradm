Mail server environment for django-cyradm
=========================================

This documentation is for Debian 8 Jessie.
This part assumes you have completed  :ref:`GETTING STARTED` and are using 
mysql. The steps for postgresql are similar but not documented here.
The document might be helpfull for other linux and BSD systems as well.
Please search for other postgresql specific documentation, if you choose
to use postgresl.

OVERVIEW
--------
pam_sql is used as backend for saslauthd, in order to
make saslauthd lookup authentication data in the django-cyradm database.
More specific in the djcyardm_mailsers table.
The users are virtual users e.g not getting an unix account.
The pw_check method of cyrus-imap and postfix is then set to saslauthd. 
Postfix needs lookup tables, so the 
postfix installation must support the database of the django-app.


INSTALLATION
------------

Installing and configuring pam sql backend
..........................................

.. code-block:: console

    sudo apt-get install libpam-mysql

Change the file /etc/pam-mysql.conf ensure the following values are set to match
your database settings from earlier.

.. code-block:: ini

    users.host=localhost
    users.database=mail
    users.db_user=mail
    users.db_passwd=secret
    users.table=djcyradm_mailusers
    users.user_column=username
    users.password_column=password
    users.where_clause = is_active=1
    users.password_crypt=1



Installing and configuring saslauthd
....................................

Note that saslauthd caches credentials as default for half an hour to 8 hours 
depeding on version. So if you need deactivated users to be deactived fast 
restart saslauthd, or use the -t option or remove the -c option. 
see man saslauthd. Note that the webinterface does not cache credentials. 

.. code-block:: console

    sudo apt-get install sasl2-bin



Edit /etc/default/saslauthd and set START to yes and add the -r option

.. code-block:: ini

    START=yes
    OPTIONS="-c -r -m /var/run/saslauthd"

Create /etc/pam.d/imap with the following content:
    
.. code-block:: ini
    
    auth       required    pam_mysql.so config_file=/etc/pam-mysql.conf
    account    sufficient  pam_mysql.so config_file=/etc/pam-mysql.conf

Restart saslauthd

.. code-block:: console

    sudo systemctl restart saslauthd


Test if the cyrus user can authenticate with testsaslauthd, use your cyrus
credentials from ADMINUSER and ADMINPASS in settings

.. code-block:: console

    sudo /usr/sbin/testsaslauthd -u cyrus -p cyrus -s imap

it should output

.. code-block:: console

    0: OK "Success."

Installing and configuring cyrus imapd
......................................
    
.. code-block:: console

    sudo apt-get install cyrus-imapd



In order to allow cyrus to use the default test cert do:
.. code-block:: console
    
    sudo usermod cyrus -g ssl-cert

*Note enter N to keep your modifed /etc/pam.d/imap file when asked*
edit /etc/imapd.conf ensure that the following options are set

::

    allowplaintext: yes

    sasl_mech_list: LOGIN PLAIN

    sasl_pwcheck_method: saslauthd

    tls_cert_file: /etc/ssl/certs/ssl-cert-snakeoil.pem

    tls_key_file: /etc/ssl/private/ssl-cert-snakeoil.key

    sasl_pwcheck_method: saslauthd

    tls_cert_file: /etc/ssl/certs/ssl-cert-snakeoil.pem

    tls_key_file: /etc/ssl/private/ssl-cert-snakeoil.key

    defaultdomain: YOUR FQDN

    virtdomains: userid 
    
    admins: cyrus



Installing and configuring postifx
..................................

See also: https://wiki.debian.org/PostfixAndSASL#Using_saslauthd_with_PAM

.. code-block:: console

    sudo apt-get install postfix postfix-mysql

Create a file /etc/postfix/sasl/smtpd.conf: 

::

    pwcheck_method: saslauthd
    mech_list: PLAIN LOGIN

Copy /etc/default/saslauthd to /etc/default/saslauthd-postfix
    
.. code-block:: console

   sudo cp /etc/default/saslauthd /etc/default/saslauthd-postfix

edit the options in /etc/default/saslauthd-postfix to set the socket in the postfix chroot

::

    OPTIONS="-c -r -m /var/spool/postfix/var/run/saslauthd"

Create required subdirectories in postfix chroot directory:

.. code-block:: console
    
    sudo dpkg-statoverride --add root sasl 710 /var/spool/postfix/var/run/saslauthd

Add the user "postfix" to the group "sasl":

.. code-block:: console

    sudo adduser postfix sasl

restart saslauthd

.. code-block:: console
    
    systemctl restart saslauthd

Configure postfix to use authentication and to require tls to enable auth
(smtpd_tls_auth_only = yes)

.. code-block:: console

    sudo postconf -e 'smtpd_tls_auth_only = yes'
    sudo postconf -e 'smtpd_sasl_local_domain = $myhostname'
    sudo postconf -e 'smtpd_sasl_auth_enable = yes'
    sudo postconf -e 'broken_sasl_auth_clients = yes'
    sudo postconf -e 'smtpd_sasl_security_options = noanonymous'
    sudo postconf -e 'smtpd_recipient_restrictions = permit_sasl_authenticated, permit_mynetworks, reject_unauth_destination'

restart postfix

.. code-block:: console

    sudo systemctl restart postfix

copy the imap pam file to smtp

.. code-block:: console

    sudo cp /etc/pam.d/imap /etc/pam.d/smtp

Configure postmap lookup tables
_______________________________

.. code-block:: console

    sudo postconf -e  'virtual_mailbox_domains = mysql:/etc/postfix/virtual_mailbox_domains.cf'
    sudo postconf -e  'virtual_alias_domains= mysql:/etc/postfix/virtual_alias_domains.cf'    
    sudo postconf -e  'virtual_alias_maps = mysql:/etc/postfix/virtual_alias_maps.cf'
    

Create the following files:

/etc/postfix/virtual_mailbox_domains.cf 

.. code-block:: ini

    hosts = localhost
    dbname = mail
    user = mail
    password = secret
    query = select domain_name from djcyradm_domains where domain_name = '%s' and is_alias_domain !=1;    

/etc/postfix/virtual_alias_domains.cf

.. code-block:: ini

    hosts = localhost
    dbname = mail
    user = mail
    password = secret
    query = select domain_name from djcyradm_domains where domain_name = '%s' and is_alias_domain=1;    

:
.. code-block:: ini

    hosts = localhost
    dbname = mail
    user = mail
    password = secret
    query =  select full_dest from djcyradm_virtualdelivery where alias = '%s' and is_active = 1; 

restart postfix

.. code-block:: console

    sudo systemctl restart postfix

Configure postfix to deliver to cyrus over lmtp
_______________________________________________

in /etc/cyrus.conf set

::

  lmtpunix     cmd="lmtpd" listen="/var/imap/socket/lmtp" prefork=0
  lmtpchroot   cmd="lmtpd" listen="/var/spool/postfix/var/imap/socket/lmtp" prefork=0 maxchild=20


create the cyrus socket dir in the postfix chroot

.. code-block:: console

    sudo mkdir -p /var/spool/postfix/var/imap/socket/
    sudo chown -R root:postfix /var/spool/postfix/var/imap/

set the lmtp socket and mailbox_transport in postfix

.. code-block:: console

    sudo postconf -e 'mailbox_transport = lmtp:unix:/var/imap/socket/lmtp'
    sudo postconf -e 'virtual_transport = $mailbox_transport'

restart postfix and cyrus-imap
 

.. code-block:: console

    sudo systemctl restart postfix cyrus-imapd

set DJCYRADM_SYNCIMAP to True in cyradm/settings.py 

**Important** you need the iso-8559-1 locales on your system, at least 
da_DK.ISO-8859-1 and en_US.ISO-8859-1

Thats it start testing and create your users:
http:/127.0.0.1:8000/djcyradm/mail-users

remember to use uwsgi in prodcution and to set DEBUG=False in cyradm/settings.py

https://uwsgi-docs.readthedocs.io/en/latest/

*If using nginx be sure to use ssl and set 
proxy_set_header X-Forwarded-Proto $scheme
in order for urls send in recovery and confirmation emails to be correct*

SUPPORT
=======
Subscribe at https://lists.schmitz.computer/listinfo/django-cyradm
and ask your questions.

BUGS
====
Uss the issue tracker at https://github.com/schmitzcomputer/django-cyradm








