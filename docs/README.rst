ABOUT
=====
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

GETTING STARTED
===============

This start guide just shows how to set up the application, it does not 
show the integration with saslauthd and pam and postfix lookup tables.

See :ref:`Mail server environment for django-cyradm` documentation if you need info about that.

Note that the djcyradm django-app is quite intrusive as it requires its own AUTH_MODEL,
and its own PASSWORD_HASHER, and is not using contrib.admin, so it is recommended to use a dedicated django project.


This quick start assumes Debian GNU/Linux version 10 codenamed Buster, but the principles can be applied to other systems

Installation of required software
---------------------------------

django-simple-catcha used by django-cyradm requires libfreetype and libjpeg62-turbo-dev

.. code-block:: console
    
     sudo apt-get install libfreetype6-dev libjpeg62-turbo-dev zlib1g-dev python3-pip 
     sudo pip3 install pytz


Installation of django-cyradm
-----------------------------

* Make a virtual environment with python3.7

.. code-block:: console

    python3.7 -m venv django-cyradm-venv

* Activate it

.. code-block:: console

   . django-cyradm-venv/bin/activate

* Update pip and setuptools in the new environment

.. code-block:: console

   pip  install --upgrade pip setuptools


* Install django-cyradm-0.1.2.tar.gz from https://github.com/jsm222/django-cyradm/releases/download/0.1.2/django-cyradm-0.1.2.tar.gz

.. code-block:: console

     pip install https://github.com/jsm222/django-cyradm/releases/download/0.1.2/django-cyradm-0.1.2.tar.gz

Initialize a django project
---------------------------
.. code-block:: console

     django-admin startproject cyradm
     cd cyradm

.. note::

    You can use the example-project at https://github.com/jsm222/django-cyradm
    as a starting point or you can follow the instructions below

Configuring the new project for use with django-cyradm
------------------------------------------------------
* with your editor of choice change cyradm/settings.py

In order to use translations  of language names add

.. code-block:: python

	from django.utils.translation import ugettext_lazy as _

after

.. code-block:: python

	import os



add the following to INSTALLED_APPS:

.. code-block:: python

    INSTALLED_APPS=[
        ...
        'captcha',
        'axes',
        'django_tables2',
      	'bootstrap3',
       	'session_security',
        'rules.apps.AutodiscoverRulesConfig',
        'django_filters',
        'djcyradm'
        ]
  
Remove django.contrib.admin from INSTALLED_APPS, it is not used or tested by django-cyradm  

enable session_security middleware by adding

.. code-block:: python

    MIDDLEWARE = [
        ...
    	'session_security.middleware.SessionSecurityMiddleware',
        ...
        ]

Make sure that it is placed *after* authentication middlewares.



For the purpose of quick starting disable (temporarily) the syncing with the imap 
server add:

.. code-block:: python

    DJCYRADM_SYNCIMAP = False



Set the special model djcyradm.Mailusers to be the AUTH_USER_MODEL

.. code-block:: python

	AUTH_USER_MODEL = 'djcyradm.MailUsers'


Specify the login url and the entry page for logged in users here done by view names from djcyradm.urls

.. code-block:: python

	LOGIN_URL="login"
	LOGIN_REDIRECT_URL="mail-users"

add the list of supported languages
 
.. code-block:: python

	LANGUAGES = [
	   ('da', _('Danish')),
   	   ('en', _('English')),
   
	]


to use translations
add 

.. code-block:: python

        'django.middleware.locale.LocaleMiddleware',

after

.. code-block:: python

        'django.contrib.sessions.middleware.SessionMiddleware',

and before  

.. code-block:: python

        'django.middleware.common.CommonMiddleware',        

for example 

.. code-block:: python

    MIDDLEWARE = [
        ...
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
        ...
    
    ]


add and configure the following if you intend to sync with imap

Subfolders are the default created folders for each mailbox, DOMAIN is an arbitrary
of your domains, but I suggest the FQDN of your mailhost.
The ADMINUSER is marked as main_cyrus_admin and does not belong to a domain.
If syncing with cyrus-imap the ADMINUSER must be listed under admins in imapd.conf
Avoid to add a @ in the Cyrus ADMINUSER as it limits administration to the domain after the @

.. code-block:: python

    DJCYRADM_IMAP = {
        "SUBFOLDERS" : ['Sent','Spam','Trash','Drafts'],
        "CYRUS":{
            "HOST":"localhost",
            "PORT": 143,
            "STARTTLS":True,
            "ADMINUSER":"cyrus",
            "ADMINPASS":"cyrus", 
            "DOMAIN":"example.com",
            }
        }


.. code-block:: console

    sudo apt-get install python3-dev libmariadbclient-dev
    pip3 install mysqlclient

configure the database here as example using mysql


.. code-block:: python


    DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'mail',
        'USER': 'mail',
        'PASSWORD': 'secret',
        }
    }

.. code-block:: console

   mysql -u root -p

In the mysql create the database correspondingly

.. code-block:: sql

    > CREATE DATABASE mail;
    > CREATE USER 'mail'@'localhost' identified by 'secret';
    > GRANT ALL PRIVILEGES on mail.* to 'mail'@'localhost';
    

In order to share passwords between djcyradm.Mailusers and the pam backend
set the following custom hasher in PASSWORD_HASHERS, make sure it is the only one listed.

.. code-block:: python


	PASSWORD_HASHERS = ['djcyradm.hashers.CryptPasswordHasher']



Configure session_security the values are suggestions and are in seconds
see session_security docs for more info
add


.. code-block:: python

	SESSION_EXPIRE_AT_BROWSER_CLOSE = True
	SESSION_SECURITY_WARN_AFTER=300
	SESSION_SECURITY_EXPIRE_AFTER=330

Configure the axes lockout url to use a simple captcha to unlock locked 
accounts add

.. code-block:: python

    AXES_LOCKOUT_URL='/djcyradm/locked'


enable the authorization backend rules, which controls access rights:
Note that the order of AUTHENTICATION_BACKENDS is significant, also add

.. code-block:: python

    'axes.backends.AxesBackend'

as the first entry.


.. code-block:: python

    AUTHENTICATION_BACKENDS = (
        'axes.backends.AxesBackend',
        'rules.permissions.ObjectPermissionBackend',
        'django.contrib.auth.backends.ModelBackend',
    )

add

.. code-block:: python

    'axes.middleware.AxesMiddleware'

to

.. code-block:: python

    MIDDLEWARE = [
        ...
    ]


edit cyradm/urls.py and change it to the folllowing

.. code-block:: python

    from django.urls import path,include

.. code-block:: python

    urlpatterns = [
        path('djcyradm/', include('djcyradm.urls')),
        path('session_security/', include('session_security.urls'))
        ]



Initialize the database

.. code-block:: console

    python manage.py migrate

*if you get a warning about strict mode, follow the link outputted in the
warning and follow instructions*

Initalize the group and permission database data

.. code-block:: console

    python manage.py loaddata djcyradm_initialdata

Initalize the main cyrus admin from the settings in DJCYRADM_IMAP invoke

.. code-block:: console

    python manage.py djcyradm_initialize



Run the server: (do not use in prodcution)

*note the djcyradm comes with an incomplete  test suite currently only suitable to use for users 
knowing selenium and geckodriver*

.. code-block:: console

    python manage.py runserver

visit http://127.0.0.1:8000/djcyradm/login/

and log in using the cyrus settings in cyradm/settings.conf e.g 
ADMINUSER ADMINPASS 
