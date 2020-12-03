import pprint

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from django.conf import settings
from djcyradm import overrides  # noqa
from djcyradm.models import MailUsers, Domains


class Command(BaseCommand):
    help = "Initializes your cyrus admin user"
    help = help+" from DJCYRADM_IMAP settings in settings.py"
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            dest="update",
            default=False,
            action="store_true",
            help='Updates an existing main cyrus admin',
        )

    def print_cfg_help(self, missing):
        self.stdout.write("Your are missing the key {0} from your settings")\
            .format(missing)
        self.stdout.write("Please add an DJCYRADM_IMAP section"
                          "to your settings.py as follows:")
        self.stdout.write(
                          """
DJCYRADM_IMAP={
    'CYRUS': {
        'HOST': 'localhost',
        'PORT': 143,
        'STARTTLS': True,
        'ADMINUSER': 'cyrus',  # no @ must be in admins in imapd.conf
        'ADMINPASS': 'cyrus',  # Will be hashed in db
        # One of your domains, is not used with cyrusadmin user
        'DOMAIN': 'example.com'
        },
    'SUBFOLDERS': ['Sent', 'Spam', 'Trash', 'Drafts'],
}
    """)
        self.stdout.write("See README for more information")
        return

    def handle(self, *args, **options):
        check_setting_pwd = getattr(settings, 'PASSWORD_HASHERS', [None])
        if check_setting_pwd[0] != 'djcyradm.hashers.CryptPasswordHasher' or\
                len(check_setting_pwd) != 1:
            self.stdout.write(
                "Please set your PASSWORD_HASHERS to"
                "['djcyradm.hashers.CryptPasswordHasher'] in settings.py:")
            self.stdout.write('''
PASSWORD_HASHERS = ['djcyradm.hashers.CryptPasswordHasher']
                ''')
            return
        check_setting_admin_model = getattr(settings, "AUTH_USER_MODEL", None)
        if check_setting_admin_model is None or\
                not check_setting_admin_model == 'djcyradm.MailUsers':
            self.stdout.write("Please set your AUTH_USER_MODEL to "
                              "'djcyradm.MailUsers' in settings.py:")
            self.stdout.write('''
AUTH_USER_MODEL = 'djcyradm.MailUsers'
''')
            return
        check_setting = getattr(settings, 'DJCYRADM_IMAP', None)
        if check_setting is None:
            return self.print_cfg_help("DJCYRADM_IMAP")
        if check_setting.get("CYRUS", None) is None:
            self.print_cfg_help("CYRUS")
        else:
            for a in ['HOST', 'PORT', 'STARTTLS', 'ADMINUSER',
                      'ADMINPASS', 'DOMAIN']:
                if check_setting.get("CYRUS").get(a, None) is None:
                    return self.print_cfg_help(a)

        self.stdout.write(self.style.NOTICE("Your current settings are %s %s")
                          % (settings.DJCYRADM_IMAP['CYRUS']['ADMINUSER'],
                             settings.DJCYRADM_IMAP['CYRUS']['DOMAIN']))
        pp = pprint.PrettyPrinter(width=41, compact=True)
        pwd = check_setting['CYRUS']['ADMINPASS']
        check_setting['CYRUS']['ADMINPASS'] = '*' * len(
            check_setting['CYRUS']['ADMINPASS']
            )
        pp.pprint(check_setting)
        if not Domains.objects.filter(
                domain_name=settings.DJCYRADM_IMAP['CYRUS']
                                                  ['DOMAIN']).exists():
            Domains.objects.create(
                domain_name=settings.DJCYRADM_IMAP['CYRUS']['DOMAIN'])

        if MailUsers.objects.filter(is_main_cyrus_admin=True).exists():
            if options["update"] is not True:
                user = MailUsers.objects.get(is_main_cyrus_admin=True)
                self.stdout.write(self.style.ERROR(
                    "User %s already exists"
                    "you might want to invoke with --update")
                                  % user.username)
                return
            elif options["update"]:
                user = MailUsers.objects.get(is_main_cyrus_admin=True)
                user.domain = Domains.objects.filter(
                    domain_name=settings.DJCYRADM_IMAP['CYRUS']['DOMAIN'])\
                    .first()
                user.username = settings.DJCYRADM_IMAP['CYRUS']['ADMINUSER']
                user.groups.set(Group.objects.filter(name="admins").all())
                user.password = make_password(pwd)
                user.save()
                self.stdout.write(self.style.SUCCESS(
                    "Successfully updated main cyrus admin to"
                    "username %s with password hash %s")
                                  % (user.username, user.password))
        else:
            user = MailUsers(is_active=True,
                             is_superuser=False,
                             is_main_cyrus_admin=True,
                             username=settings.DJCYRADM_IMAP['CYRUS']
                                                            ['ADMINUSER'],
                             password=make_password(pwd),
                             domain=Domains.objects.filter(
                                domain_name=settings.DJCYRADM_IMAP["CYRUS"]
                                                                  ["DOMAIN"]
                                .first())
                             )

            user.save()
            user.groups.set(Group.objects.filter(name="admins").all())
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    "Successfully created user %s with password hash %s"
                    % (
                        user.username,
                        user.password)
                      )
                    )
