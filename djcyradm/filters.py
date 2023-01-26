from django.db.models import Q
import django_filters
from django.utils.translation import gettext_lazy as _
from djcyradm.models import MailUsers, Domains, VirtualDelivery
from django.contrib.auth.models import Group


def alias_domain_qs(r):
    if r.user.has_perm("djcyradm.is_admin"):
        return Domains.objects.filter(
            virtualdelivery__in=VirtualDelivery.objects.all()).distinct()
    if r.user.has_perm("djcyradm.is_domain_admin"):
        return Domains.objects.filter(
            Q(id=r.user.domain.id) |
            Q(admindomains=r.user,
              virtualdelivery__in=VirtualDelivery.objects.all())).distinct()
    return Domains.objects.filter(id=r.user.domain.id)


def domain_qs(r):
    if r.user.has_perm('djcyradm.is_admin'):
        return Domains.objects.all()
    elif r.user.has_perm('djcyradm.is_domain_admin'):
        return Domains.objects.filter(admindomains=r.user)
    else:
        return Domains.objects.filter(id=r.user.domain.id)


def alias_dest_users_qs(r):
    if r.user.has_perm('djcyradm.is_admin'):
        return MailUsers.objects.filter(
            is_main_cyrus_admin=False,
            virtualdelivery__in=VirtualDelivery.objects.filter(
                dest__isnull=False)).distinct()
    if r.user.has_perm('djcyradm.is_domain_admin'):
        return MailUsers.objects.filter(
            Q(pk=r.user.id) | Q(
                domain__in=r.user.domains.all(),
                is_main_cyrus_admin=False))

    return MailUsers.objects.filter(pk=r.user.id)


def users_qs(r):
    if r.user.has_perm('djcyradm.is_admin'):
        return MailUsers.objects.filter(is_main_cyrus_admin=False)
    elif r.user.has_perm('djcyradm.is_domain_admin'):
        return MailUsers.objects.filter(domain__in=r.user.domains.all(),
                                        is_main_cyrus_admin=False)
    return MailUsers.objects.filter(pk=r.user.id)


class MailUsersFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(label=_("Id"))
    username = django_filters.CharFilter(label=_("Username"),
                                         lookup_expr='startswith')
    domain = django_filters.ModelChoiceFilter(queryset=domain_qs,
                                              label=_("Domain"))
    groups = django_filters.ModelChoiceFilter(queryset=Group.objects.all(),
                                              label=_("Groups"))
    is_active = django_filters.BooleanFilter(label=_("Is active"))

    class Meta:
        model = MailUsers
        fields = ['id', 'username', 'domain', 'groups', 'is_active']


class DomainsFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(label=_("Id"))
    domain_name = django_filters.ModelChoiceFilter(
        queryset=domain_qs,
        label=_("Domain name"),
        lookup_expr='startswith')
    max_quota_per_account = django_filters.NumberFilter(
        label=_("Max quota per account"))
    max_aliases_per_account = django_filters.NumberFilter(
        label=_("Max aliases per account"))
    max_accounts_per_domain = django_filters.NumberFilter(
        label=_("Max accounts per domain"))
    is_alias_domain = django_filters.BooleanFilter(
        label=_("Is alias domain"))

    class Meta:
        model = Domains
        fields = ['id', 'domain_name', 'max_quota_per_account',
                  'max_accounts_per_domain', 'max_aliases_per_account',
                  'is_alias_domain']


class VirtualDeliveryFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(label=_("Id"))
    alias = django_filters.CharFilter(label=_("Alias"),
                                      lookup_expr='startswith')
    alias_domain = django_filters.ModelChoiceFilter(queryset=alias_domain_qs,
                                                    label=_("Alias domain"))
    dest = django_filters.ModelChoiceFilter(queryset=alias_dest_users_qs,
                                            label=_("Destination"))
    is_external_alias = django_filters.BooleanFilter(
            label=_("Is external alias"))
    is_forwarder = django_filters.BooleanFilter(label=_("Is mail forward"))

    class Meta:
        model = VirtualDelivery
        exclude = ['full_dest']
        fields = ['id', 'alias', 'alias_domain', 'dest']
