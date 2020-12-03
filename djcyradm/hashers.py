
from collections import OrderedDict
from django.utils.translation import ugettext_noop as _
from django.contrib.auth.hashers import BasePasswordHasher, mask_hash
from django.utils.crypto import get_random_string, constant_time_compare
from django.utils.encoding import force_str


class CryptPasswordHasher(BasePasswordHasher):
    """
    Password hashing using UNIX crypt (not recommended)

    The crypt module is not supported on all platforms.
    """
    algorithm = "default"
    library = "crypt"

    def salt(self):
        return get_random_string(2)

    def encode(self, password, salt):
        crypt = self._load_library()
        assert len(salt) == 2
        data = crypt.crypt(force_str(password),
                           crypt.mksalt(crypt.METHOD_SHA512))
        assert data is not None
        # we don't need to store the salt, but Django used to do this
        return data

    def verify(self, password, encoded):
        data = encoded
        crypt = self._load_library()
        return constant_time_compare(
            data,
            crypt.crypt(force_str(password), data))

    def safe_summary(self, encoded):
        return OrderedDict([
            (_('algorithm'), 'crypt512'),
            (_('salt'), ),
            (_('hash'), mask_hash(encoded, show=3)),
        ])

    def harden_runtime(self, password, encoded):
        pass
