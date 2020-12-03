import rules

from djcyradm.models import VirtualDelivery


@rules.predicate
def is_not_main_cyrus(user, change):
    return not change.is_main_cyrus_admin


@rules.predicate
def logged_in_is_not_main_cyrus(user):
    return not user.is_main_cyrus_admin


@rules.predicate
def is_mail_owner(user, mail_user):
    return user.id == mail_user.id and\
        mail_user.is_main_cyrus_admin is not True


@rules.predicate
def is_alias_owner(user, alias):
    return alias.dest is not None and\
        user == alias.dest or alias.alias == user.username and\
        alias.is_forwarder


@rules.predicate
def is_aliases_owner(user, aliases):
    for alias in aliases:
        if user != alias.dest and user.username != alias.alias:
            return False
    return True


def can_add_alias(user):
    if user.domain.max_aliases_per_account is None\
            and user.max_aliases is None:
        return True
    elif user.domain.max_aliases_per_account is not None\
            and user.max_aliases is not None:
        return int(user.domain.max_aliases_per_account) >=\
            VirtualDelivery.objects.filter(dest=user).count() and \
            user.max_aliases > VirtualDelivery.objects.filter(
                dest=user).count()
    elif user.max_aliases is not None and\
            user.domain.max_aliases_per_account is None:
        return user.max_aliases >\
            VirtualDelivery.objects.filter(dest=user).count()
    elif user.max_aliases is None and\
            user.domain.max_aliases_per_account is not None:
        return user.domain.max_aliases_per_account >\
            VirtualDelivery.objects.filter(dest=user).count()
    return False


@rules.predicate
def is_domain_admin_of_aliases(user, aliases):
    if not user.groups.filter(name="domainadmins").exists():
        return False
    for a in aliases:
        if a.dest is not None and a.dest.domain not in user.domains.all():
            return False
        elif a.dest is None and a.alias_domain not in user.domains.all():
            return False
    return True


@rules.predicate
def is_domain_admin_of_alias(user, alias):
    if alias.dest is not None and alias.dest.domain not in user.domains.all():
        return False
    if alias.dest is None and alias.alias_domain not in user.domains.all():
        return False


@rules.predicate
def user_is_not_main_admin(user, change):
    if isinstance(change, VirtualDelivery):
        change = change.dest
    if change is not None and change.is_main_cyrus_admin is True:
        return False
    return True


@rules.predicate
def is_domain_admin_of_accounts(user, accounts):
    for delete_me in accounts:
        if delete_me == user:
            return False
        if delete_me.domain not in user.domains.all():
            return False
    return True


@rules.predicate
def is_domain_admin_of_domain(user, change):
    if change is not None and change.domain not in user.domains.all():
        return False
    return True


@rules.predicate
def is_not_domain_admin_of_own_domain(user):
    return user.domain not in user.domains.all()


ADMINS = "admins"
DOMAIN_ADMINS = "domainadmins"
ACCOUNT_USERS = "accountusers"


is_admin = rules.Predicate(rules.is_group_member(ADMINS))
is_domain_admin = rules.Predicate(rules.is_group_member(DOMAIN_ADMINS))
is_account_user = rules.Predicate(
    rules.is_group_member(ACCOUNT_USERS) | is_domain_admin &
    is_not_domain_admin_of_own_domain)

rules.add_perm("djcyradm.is_admin", is_admin)
rules.add_perm("djcyradm.is_domain_admin", is_domain_admin)
rules.add_perm("djcyradm.is_account_user",  is_account_user)

rules.add_perm("djcyradm.is_in_djcyradm_group", is_admin |
               is_domain_admin | is_account_user)

rules.add_perm('djcyradm.change_mailusers', is_admin & user_is_not_main_admin |
               is_domain_admin & is_domain_admin_of_domain)

rules.add_perm('djcyradm.change_mailusers_password',
               is_admin & is_not_main_cyrus | is_domain_admin &
               is_domain_admin_of_domain | is_account_user & is_mail_owner)

rules.add_perm('djcyradm.change_mailusers_recovery_mail',
               is_admin & is_mail_owner | is_domain_admin & is_mail_owner |
               is_account_user & is_mail_owner)
rules.add_perm('djcyradm.is_not_main_admin',
               is_admin & logged_in_is_not_main_cyrus | is_domain_admin
               | is_account_user)
rules.add_perm('djcyradm.delete_mailusers',
               rules.always_allow | is_admin | (is_domain_admin &
                                                is_domain_admin_of_accounts))

rules.add_perm('djcyradm.is_not_admin', ~is_admin |
               is_domain_admin | is_account_user)

rules.add_perm("djcyradm.list_virtualdelivery", is_admin |
               is_domain_admin | is_account_user)

rules.add_perm("djcyradm.change_virtualdelivery",
               is_admin | is_domain_admin & is_domain_admin_of_alias |
               is_account_user & is_alias_owner)

rules.add_perm("djcyradm.change_mail_forward",
               is_admin & is_not_main_cyrus | is_domain_admin &
               is_domain_admin_of_domain | is_account_user & is_mail_owner)

rules.add_perm("djcyradm.delete_virtualdeliveries",
               is_admin | is_domain_admin & is_domain_admin_of_aliases |
               is_account_user & is_aliases_owner)

rules.add_perm("djcyradm.add_virtualdelivery_external",
               is_admin | is_domain_admin & is_domain_admin_of_domain)


rules.add_perm('djcyradm.change_domains', is_admin)

rules.add_perm("djcyradm.list_domains", is_admin | is_domain_admin)

rules.add_perm('djcyradm.delete_domains', is_admin)
