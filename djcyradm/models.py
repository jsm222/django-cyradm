from __future__ import unicode_literals

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class MailUsers(AbstractUser):
    reset_password = None
    username = models.CharField(unique=True, max_length=255,
                                help_text=_("Please enter the username"),
                                verbose_name=_("username"))
    email_confirmed = models.BooleanField(default=False)
    domain = models.ForeignKey(
        "Domains", models.DO_NOTHING,
        blank=False, null=False,
        help_text=_("Please choose the domain of the user"),
        verbose_name=_("domain")
    )
    max_aliases = models.IntegerField(
        blank=True,
        null=True,
        help_text=_("The max number of aliases the user can use"),
        verbose_name=_("Max aliases")
        )
    domains = models.ManyToManyField(
        "Domains",
        related_name="admindomains", blank=True,
        help_text=_("The domains the user can administrate"
                    ", only applies for domainadmins"),
        verbose_name=_("admindomains"))
    password = models.CharField(null=True,
                                blank=False,
                                default=None,
                                max_length=255,
                                verbose_name=_("password")
                                )
    quota = models.PositiveIntegerField(
                                        blank=True,
                                        null=True,
                                        verbose_name=_("quota"),
                                        help_text=_("Enter zero for no limit"))
    is_main_cyrus_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username

    def get_absolute_url(self):
        if self.reset_password:
            return reverse('mail-users-password-reset', kwargs={'pk': self.id})
        else:
            return reverse('mail-users')

    @property
    def admin_domains(self):
        return ', '.join([x.domain_name for x in self.domains.all()])

    class Meta:
        managed = True
        ordering = ['id']


class Domains(models.Model):
    domain_name = models.CharField(unique=True,
                                   max_length=255,
                                   verbose_name=_("Domain name"),
                                   help_text=_("Enter domain name"),
                                   error_messages={'unique':
                                                   _('Domain with that name'
                                                     ' already exists')})
    max_quota_per_account = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Max quota per account")
        )
    max_accounts_per_domain = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Max accounts per domain")
        )
    max_aliases_per_account = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Max aliases per account")
        )
    max_external_aliases = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Max external aliases in domain")
        )
    is_alias_domain = models.BooleanField(
        default=False, null=False, blank=False,
        verbose_name=_("Is alias domain"),
        help_text=_("an alias domain does not contain accounts"))

    def __str__(self):
        return self.domain_name

    def get_absolute_url(self):
        return reverse('domains')

    class Meta:
        managed = True
        ordering = ['id']


class VirtualDelivery(models.Model):
    alias = models.CharField(
        unique=True, max_length=255, verbose_name=_("Alias"),
        help_text=_("Please enter the wanted alias"),
        error_messages={'unique': _('Alias already exists')})
    dest = models.ForeignKey(
        MailUsers,
        models.DO_NOTHING,
        blank=True,
        null=True,
        db_column='dest',
        verbose_name=_("destination"),
        help_text=_("Please select a destination for the alias"))
    full_dest = models.CharField(
        unique=False,
        max_length=255,
        null=False,
        verbose_name=_("Destination email"),
        help_text=_("Please enter a destination for the alias")
        )
    alias_domain = models.ForeignKey(
        Domains,
        models.DO_NOTHING,
        blank=False,
        null=False,
        verbose_name=_("Alias domain"),
        help_text=_("Please choose the domain for the alias")
        )
    is_external_alias = models.BooleanField(
        default=False,
        null=False,
        blank=False,
        verbose_name=_("Is external alias")
        )
    is_forwarder = models.BooleanField(
        default=False,
        null=False,
        blank=False,
        verbose_name=_("Is forwarder")
        )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is active")
        )

    def get_absolute_url(self):
        return reverse('aliases')

    class Meta:
        managed = True
        ordering = ['id']

    def __str__(self):
        if "," in self.full_dest:
            return _("%(alias)s keeps and forwards to: %(email)s") %\
                {'alias': self.alias,
                 'email': self.full_dest.split(",")[1]}
        elif self.is_forwarder:
            return _("forward to: %(email)s") %\
                {'email': self.full_dest.split(",")[-1]}
        elif self.is_external_alias:
            return self.alias + "  > " + self.full_dest
        return self.alias + "  > " + self.dest.username
