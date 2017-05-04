import imaplib
import locale

import re
from contextlib import contextmanager

from humanize import naturalsize
from django.utils.translation import ugettext_lazy as _, get_language, to_locale

from django.conf import settings  # important to use django.conf for tests override_settings:

list_response_pattern = re.compile(r'(.* \(STORAGE (?P<used>\d+)\s+(?P<limit>\d+)\))')


@contextmanager
def logout(imap):
    try:
        yield imap
    finally:
        imap.logout()


class Imap:
    DEFAULTS = {

        "SUBFOLDERS": ['Sent', 'Spam', 'Trash', 'Drafts'],
        "CYRUS": {
            "HOST": "localhost",
            "PORT": "143",
            "STARTTLS": True,
            "ADMINUSER": "cyrus",  # no @ must be in admins in imapd.conf
            "ADMINPASS": "cyrus",  # Will be hashed in db
            "DOMAIN": "example.com"  # One of your domains, is not used with cyrusadmin user
        }
    }

    imapconn = None

    def __init__(self):
        settings.SYNCIMAP = getattr(settings, "DJCYRADM_SYNCIMAP", None)
        if settings.SYNCIMAP is None:
            error = _("Missing setting %(setting)s") % {'setting': 'DJCYRADM_SYNCIMAP'}
            print(error)
            raise Exception(error)

        if settings.DJCYRADM_SYNCIMAP is not True:
            return
        self.imapconn = self.login()

    def login(self):
        if settings.DJCYRADM_SYNCIMAP is not True:
            return None
        djcyradm_imap = getattr(settings, "DJCYRADM_IMAP", Imap.DEFAULTS)
        m = imaplib.IMAP4(host=djcyradm_imap['CYRUS']['HOST'], port=djcyradm_imap['CYRUS']['PORT'])
        if djcyradm_imap['CYRUS']['STARTTLS']:
            m.starttls()
        m.login(djcyradm_imap['CYRUS']['ADMINUSER'], djcyradm_imap['CYRUS']['ADMINPASS'])
        return m

    def parse_list_response(self, line):
        used = 0
        quota = 0
        if list_response_pattern.match(line):
            m, used, quota = list_response_pattern.match(line).groups()
        return used, quota

    def get_quota(self, username=None):
        if settings.DJCYRADM_SYNCIMAP is not True:
            return None
        m = self.imapconn
        result, typ = m.getquota(root="user."+username)
        ret = ''
        if result == 'OK':
            ret_list = []
            quota = self.parse_list_response(str(typ[0]))
            if int(quota[1]) > 0:
                ret_list.append(naturalsize(int(quota[0]) * 1024, binary=True, format="%.3f"))
                ret_list.append(naturalsize(int(quota[1]) * 1024, format="%.3f", binary=True))
                ret_list.append(round(int(quota[0]) / int(quota[1]) * 100, 5))
                used = ret_list[0].split(" ")
                quota = ret_list[1].split(" ")
                locale.setlocale(locale.LC_NUMERIC, locale.locale_alias[to_locale(get_language())])
                usedf = locale.format("%.2f", value=float(used[0]))
                quotaf = locale.format("%.2f", float(quota[0]))
                ret = usedf + used[1] + '/' + quotaf + quota[1] + " " + str(locale.format("%.5f", ret_list[2])) + '%'
            elif quota[1] == 0:
                ret = _("unknown / no limit")
            return ret

    def create_mailbox(self, username=None, folders=None, quota=None, new_user=True):
        if settings.DJCYRADM_SYNCIMAP is not True:
            return
        m = self.imapconn
        if new_user:
            m.create("user."+username)
            user, domain = username.split("@")
            if folders is not None:
                for folder in folders:
                    m.create("user."+user+"."+folder+"@"+domain)

        if quota is not None and quota != "" and int(quota) > 0:
            m.setquota(root="user."+username, limits="(STORAGE " + str(quota)+")")
        else:
            m.setquota("user." + username, "(STORAGE -1)")  # unlimited  does not remove quota root from cyrus

    def delete_mailbox(self, username=None):
        if settings.DJCYRADM_SYNCIMAP is not True:
            return
        djcyradm_imap = getattr(settings, "DJCYRADM_IMAP", Imap.DEFAULTS)
        m = self.imapconn
        m.setacl("user." + username, who=djcyradm_imap['CYRUS']['ADMINUSER'], what="ex")
        m.delete("user." + username)

    def logout(self):
        if settings.DJCYRADM_SYNCIMAP is not True:
            return
        self.imapconn.logout()

