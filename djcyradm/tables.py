import locale

import django_tables2 as tables
from django.utils.translation import ugettext_lazy as _,\
    get_language, to_locale
from django_tables2.utils import A
from humanize import naturalsize


from .models import MailUsers, Domains, VirtualDelivery


class SelMixin(tables.Table):
    selection = tables.CheckBoxColumn(
        accessor="pk",
        attrs={"th__input": {"onclick": "toggle(this)"}},
        orderable=False)


class DomainsTable(SelMixin, tables.Table):
    id = tables.LinkColumn(viewname="domains-update", args=[A('pk')])
    domain_name = tables.Column(verbose_name=_("Domain name"))
    max_quota_per_account = tables.Column(
        verbose_name=_("Max quota per account"))
    max_aliases_per_account = tables.Column(
        verbose_name=_("Max aliases per account"))
    max_accounts_per_domain = tables.Column(
        verbose_name=_("Max accounts per domain"))
    max_external_aliases = tables.Column(
        verbose_name=_("Max external aliases"))
    external_aliases_used = tables.Column(
        verbose_name=_("External aliases used"), accessor='pk')

    class Meta:
        model = Domains
        attrs = {'class': 'table'}
        fields = ['selection', 'id', 'domain_name', 'max_quota_per_account',
                  'max_accounts_per_domain', 'max_aliases_per_account',
                  'max_external_aliases', 'external_aliases_used',
                  'is_alias_domain']

    def render_max_quota_per_account(self, value):
        locale.setlocale(locale.LC_NUMERIC,
                         locale.locale_alias[to_locale(get_language())])
        size = naturalsize(value*1024, binary=True, format="%.3f")
        used = size.split(" ")
        usedf = locale.format("%.2f", value=float(used[0]))
        return usedf + " " + used[1] + " (" + str(value) + ")"

    def render_external_aliases_used(self, value):
        return str(VirtualDelivery.objects.filter(
            is_external_alias=True,
            alias_domain__id=value).count()
            )


class MailUsersTable(SelMixin, tables.Table):

    def __init__(self, *args, **kwargs):
        # important to "pop" added kwarg before call to parent's constructor
        self.quotas = kwargs.pop("quotas")

        super(MailUsersTable, self).__init__(*args, **kwargs)
    username = tables.Column(verbose_name=_("Username"))
    domain = tables.LinkColumn(
                               text=lambda record:
                               record.domain.domain_name,
                               viewname="domains-update",
                               verbose_name=_("Domain"),
                               accessor="domain",
                               args=[A('domain.id')])
    max_aliases = tables.Column(verbose_name=_("Max aliases"))
    max_aliases_in_domain = tables.Column(
        verbose_name=_("Max aliases (domain)"),
        accessor='domain.max_aliases_per_account')
    aliases_used = tables.Column(
        orderable=False,
        accessor='username',
        verbose_name=_("Aliases used")
        )
    quota = tables.Column(
        orderable=False,
        accessor='username',
        verbose_name=_('Quota')
        )
    admin_domains = tables.Column(
        orderable=False,
        verbose_name=_("Admindomains")
        )
    groups = tables.Column(
        orderable=False,
        verbose_name=_("Groups"),
        accessor="groups.all"
        )
    is_active = tables.BooleanColumn(verbose_name=_("Is active"))
    actions = tables.TemplateColumn(
        template_name="djcyradm/action_column.html",
        verbose_name=_('Actions')
        )

    def render_groups(self, value):
        val = ""
        for g in value:
            val += g.name + " "
        return val

    def render_quota(self, value):
        return self.quotas[value]

    def render_aliases_used(self, value):
        return str(VirtualDelivery.objects.filter(
                is_forwarder=False,
                dest__username=value).count())

    class Meta:
        model = MailUsers
        exclude = ['password']
        fields = ['selection', 'id', 'username', 'domain', 'admin_domains',
                  'max_aliases', 'max_aliases_in_domain',
                  'aliases_used', 'quota', 'groups', 'is_active', 'actions']
        attrs = {'class': 'table'}


class VirtualDeliveryTable(SelMixin, tables.Table):
    id = tables.LinkColumn(viewname='aliases-update', args=[A('pk')])
    alias = tables.Column(verbose_name=_("Alias"))
    alias_domain = tables.Column(verbose_name=_("Alias domain"))
    dest = tables.Column(verbose_name=_("Destination"), accessor='full_dest')
    is_external_alias = tables.BooleanColumn(
        verbose_name=_("Is external alias")
        )
    is_forwarder = tables.BooleanColumn(verbose_name=_("Is mail forward"))
    is_active = tables.BooleanColumn(verbose_name=_("Is active"))

    class Meta:
        model = VirtualDelivery
        exclude = ['full_dest']
        fields = ['selection', 'id', 'alias', 'alias_domain', 'dest']
        attrs = {'class': 'table'}
