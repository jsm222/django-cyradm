from django.contrib.auth import hashers
from django.contrib.auth.hashers import get_hasher


def my_identify_hasher(self):
    # Gets the default instead of parsing the algorithm from password.
    return get_hasher()


hashers.identify_hasher = my_identify_hasher
