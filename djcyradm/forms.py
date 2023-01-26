from captcha.fields import CaptchaField
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm, \
    AuthenticationForm, AdminPasswordChangeForm
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.messages import WARNING
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email, EmailValidator
from django.db.models import Q
from django.forms import ModelForm, CharField, BooleanField,\
    ModelChoiceField, Form, EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from djcyradm.imap import Imap
from djcyradm.imap import logout
from djcyradm.models import MailUsers, Domains, VirtualDelivery
from djcyradm.rules import can_add_alias
from djcyradm import overrides  # noqa do not remove


class AxesCaptchaForm(Form):
    captcha = CaptchaField()


class MailConcatMixin(object):
    def concat_email(self, userfieldname="username", domainfieldname="domain",
                     check_same_domain=True, error=1):
        is_email = True
        ret = False
        try:
            validate_email(self.cleaned_data.get(userfieldname))
        except ValidationError:
            is_email = False
        if is_email:
            ret = self.cleaned_data.get(userfieldname)
        if is_email and check_same_domain:
            if not self.cleaned_data.get(domainfieldname).domain_name == \
                    self.cleaned_data.get(userfieldname).split("@")[1]:
                if error == 1:
                    err_txt = _("%(domain)s is not the domain\
                    of the user: %(userdomain)s") % \
                        {
                        "domain": self.cleaned_data.get(userfieldname).
                        split("@")[1],
                        'userdomain': self.cleaned_data.get(domainfieldname).
                        domain_name
                        }
                    self.add_error(userfieldname, ValidationError(err_txt))

                else:
                    self.add_error(userfieldname, ValidationError(
                        _("%(domain)s is not the alias\
                         domain %(userdomain)s") % {
                            "domain": self.cleaned_data.
                            get(userfieldname).split("@")[1],
                            'userdomain': self.cleaned_data.
                            get(domainfieldname).domain_name
                            }
                        ))
                return False
        elif not is_email:
            try:
                validate_email(
                    self.cleaned_data
                    .get(userfieldname) +
                    "@" +
                    self.cleaned_data.get(domainfieldname).
                    domain_name)
                self.cleaned_data[userfieldname] += "@" + \
                    self.cleaned_data.get(domainfieldname).domain_name
                ret = self.cleaned_data[userfieldname]
            except ValidationError:
                self.add_error(userfieldname, ValidationError(
                    _("%(email)s is not a valid email") % {
                        'email': self.cleaned_data.get(userfieldname) +
                        "@" + self.cleaned_data.get(
                            domainfieldname).domain_name}))
                return False
        return ret


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs = {
            'title': _("Please enter your username")}
        self.fields['password'].widget.attrs = {
            'title': _("Please enter your password")}

    def confirm_login_allowed(self, user):
        super(LoginForm, self).confirm_login_allowed(user)


class MailUsersPasswordResetForm(AdminPasswordChangeForm):
    username = None
    newuser = False

    def __init__(self, pk=None, **kwargs):
        user = kwargs.pop('instance')
        self.username = user.username
        self.newuser = MailUsers.objects.filter(pk=user.id,
                                                password__isnull=True).exists()
        super(MailUsersPasswordResetForm, self).__init__(user=user, **kwargs)

    def save(self, commit=True):
        pwd = super(MailUsersPasswordResetForm, self).save(commit=True)
        if self.newuser:
            Imap().subscribe(self.username, self.cleaned_data['password1'])
        return pwd


class MailUsersPasswordForm(PasswordChangeForm):
    def __init__(self, pk=None, **kwargs):
        # important to "pop" added kwarg before call to parent's constructor
        self.request = kwargs.pop('request')
        user = kwargs.pop('instance')
        super(MailUsersPasswordForm, self).__init__(user=user, **kwargs)


class VirtualDeliveryForm(MailConcatMixin, ModelForm):
    def __init__(self, *args, **kwargs):
        # important to "pop" added kwarg before call to parent's constructor
        self.request = kwargs.pop('request')
        super(VirtualDeliveryForm, self).__init__(*args, **kwargs)
        # also Special case of domain admin without admin
        if self.request.user.has_perm("djcyradm.is_account_user"):
            # of own domain
            self.fields['dest'].queryset = MailUsers.objects.filter(
                pk=self.request.user.id, is_main_cyrus_admin=False)
            self.fields['alias_domain'].queryset = Domains.objects.filter(
                pk=self.request.user.domain.id)
        elif self.request.user.has_perm('djcyradm.is_admin'):
            self.fields['dest'].queryset = MailUsers.objects.filter(
                is_main_cyrus_admin=False)
            self.fields['alias_domain'].queryset = Domains.objects.all()
        elif self.request.user.has_perm('djcyradm.is_domain_admin'):
            self.fields['dest'].queryset = MailUsers.objects.filter(
                domain__in=self.request.user.domains.all(),
                is_main_cyrus_admin=False)
            self.fields['alias_domain'].queryset = Domains.objects.filter(
                pk__in=self.request.user.domains.all())

    def is_valid(self):
        if super(VirtualDeliveryForm, self).is_valid():
            ret = self.concat_email(
                domainfieldname='alias_domain',
                userfieldname='alias', check_same_domain=True,
                error=2)
            if ret is not False:
                if MailUsers.objects.filter(username=ret).exists():
                    self.add_error("alias", ValidationError(
                        _("A user has the wanted alias as username")))
                    return False
                if self.instance.pk is None \
                        and VirtualDelivery.objects.filter(alias=ret).exists():

                    self.add_error("alias", ValidationError(
                        _("Alias already exists")))
                    return False
                if self.instance.pk is not None and \
                        VirtualDelivery.objects.filter(
                            Q(alias=ret), ~Q(pk=self.instance.pk)).exists():
                    self.add_error("alias", ValidationError(
                        _("Alias already exists")))
                    return False
                self.instance.alias = ret
                self.instance.full_dest = self.instance.dest.username
                if not can_add_alias(self.instance.dest) and \
                        self.instance.pk is None:
                    self.add_error("dest", ValidationError(
                        _("No more aliases for this destination")))
                    return False

                return True
        return False

    # alias = CharField(error_messages={'unique': u'Alias already exists'})
    dest = ModelChoiceField(required=True, queryset=None, label=_(
        "Destination"), help_text=_("Choose destination"))

    class Meta:
        model = VirtualDelivery
        fields = ['alias', 'alias_domain', 'dest']


class MailUsersForm(MailConcatMixin, ModelForm):
    reset_password = BooleanField(required=False, label=_("Reset password"))

    def __init__(self, *args, **kwargs):
        # important to "pop" added kwarg before call to parent's constructor
        self.request = kwargs.pop('request')
        super(MailUsersForm, self).__init__(*args, **kwargs)
        self.fields['domain'].queryset = Domains.objects.filter(
            is_alias_domain=False)
        if self.request.user.has_perm("djcyradm.is_domain_admin"):
            self.fields['domain'].queryset = \
                Domains.objects.filter(
                   is_alias_domain=False,
                   pk__in=(self.request.user.domains.all())
                   )
        if not self.request.user.has_perm("djcyradm.is_admin"):
            self.fields.pop("groups")
            self.fields.pop("domains")
        if self.instance.pk is not None:
            self.fields['username'].disabled = True
            self.fields['domain'].disabled = True

    def save(self, commit=True):
        new_user = (self.instance.pk is None)
        user = super(MailUsersForm, self).save(commit=True)
        if not self.request.user.has_perm('djcyradm.is_admin') and \
                self.request.user.has_perm('djcyradm.is_domain_admin'):
            if new_user or self.request.user.id != self.instance.pk:
                user.groups.set(Group.objects.filter(
                    name='accountusers').all())
                user.save()
        with logout(Imap()) as imap:
            djcyradm_imap = getattr(settings, "DJCYRADM_IMAP", imap.DEFAULTS)
            imap.create_mailbox(self.instance.username,
                                djcyradm_imap["SUBFOLDERS"],
                                self.instance.quota,
                                new_user=new_user)
        return user

    def is_valid(self):
        if super(MailUsersForm, self).is_valid():
            if self.instance.pk is None:
                self.instance.reset_password = True
            else:
                self.instance.reset_password = \
                    self.cleaned_data["reset_password"]
            valid = True
            ret = self.concat_email()
            if ret is not False:
                self.instance.username = ret
            else:
                return False
            if VirtualDelivery.objects.filter(alias=self.instance.username,
                                              is_forwarder=False).exists():
                existing_alias = VirtualDelivery.objects.get(
                    alias=self.instance.username)
                self.add_error("username",
                               _("An alias %(alias)s exists for\
                                the wanted username") %
                               {
                                'alias': existing_alias
                               })
                valid = False
            if self.instance.pk is None:
                d = self.cleaned_data['domain']
                if self.cleaned_data['domain'].\
                    max_accounts_per_domain is not None \
                        and MailUsers.objects.filter(
                            domain=d).count() > d.max_accounts_per_domain:
                    self.add_error("domain", ValidationError(_(
                        "No more users for this domain limit %d reached") %
                        self.instance.domain.max_accounts_per_domain))
                    valid = False
                if MailUsers.objects.filter(
                        username=self.cleaned_data["username"]).exists():
                    self.add_error("username", ValidationError(
                        _("User already exists")))
                    valid = False
            if not self.request.user.has_perm("djcyradm.is_admin") and \
                self.cleaned_data.get("domains") is not None and \
                self.cleaned_data.get("domains").count() > 0 and \
                self.instance.id is not None and \
                set(self.cleaned_data.get("domains").all()) != set(
                    MailUsers.objects.get(pk=self.instance.id).domains.all()):

                self.add_error(None, ValidationError(
                    _("You are not allowed to change the Admin domains")))
                valid = False
            if self.request.user.id == self.instance.pk and \
                    self.request.user.has_perm("djcyradm.is_admin"):

                if self.request.user.has_perm("djcyradm.is_admin") and \
                        not self.cleaned_data["groups"].filter(
                            name="admins").exists():
                    self.add_error("groups", ValidationError(
                        _("You cannot change your own group membership")))
                    valid = False
                if self.request.user.has_perm("djcyradm.is_domain_admin") and \
                        not self.cleaned_data["groups"]\
                        .filter(name="domainadmins").exists():
                    self.add_error("groups", ValidationError(
                        _("You cannot change your own group membership")))
                    valid = False

            if self.request.user.has_perm("djcyradm.is_admin") and\
                self.cleaned_data["groups"].filter(
                    name="domainadmins").exists() and\
                    self.cleaned_data.get("domains").count() == 0:
                self.add_error("domains",
                               ValidationError(_("A domain administrator must\
                                administrate at least one domain")))
                valid = False

            if self.request.user.has_perm("djcyradm.is_admin") and\
                self.cleaned_data["groups"].filter(
                    name="accountusers").exists() and\
                    len(self.cleaned_data.get("domains")) > 0:
                self.add_error("domains", ValidationError(
                    _("An account user cannot administrate domains")))
                valid = False
            if self.cleaned_data['max_aliases'] is not None and\
                self.cleaned_data['domain']\
                    .max_aliases_per_account is not None and\
                    int(self.cleaned_data['max_aliases']) > int(
                    self.cleaned_data['domain'].max_aliases_per_account):
                self.add_error("max_aliases", ValidationError(
                    _("The max number of aliases per account\
                      for domain %(domain)s  is %(limit)d") % {
                            'domain': self.cleaned_data['domain'].domain_name,
                            'limit': self.cleaned_data['domain'].
                            max_aliases_per_account}))
                valid = False

            if self.cleaned_data['quota'] is not None and self.cleaned_data[
                'domain'].max_quota_per_account is not None and \
                    int(self.cleaned_data['quota']) > int(
                    self.cleaned_data['domain'].max_quota_per_account):
                self.add_error("quota", ValidationError(
                    _("The max quota for domain %(domain)s is %(limit)d") % {
                        'domain': str(
                            self.cleaned_data['domain'].domain_name),
                        'limit': self.cleaned_data['domain']
                        .max_quota_per_account
                      }))
                valid = False
            return valid
        return False

    class Meta:
        model = MailUsers
        labels = {
            'domains': _("Admin of domains"),
            'email':   _('Recovery email')
        }
        exclude = ['password', 'is_main_cyrus_admin']
        fields = ['username', 'domain', 'groups', 'quota',
                  'password', 'max_aliases', 'domains', 'reset_password']


class DomainsForms(ModelForm):
    def __init__(self, *args, **kwargs):
        # important to "pop" added kwarg before call to parent's constructor

        super(ModelForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None and\
                MailUsers.objects.filter(domain=self.instance).exists():
            # Do not change basic settings of domain if it has accounts:
            self.fields['domain_name'].disabled = True
            self.fields['is_alias_domain'].disabled = True

    class Meta:
        model = Domains
        exclude = []


class VirtualDeliveryCyclicCheckMixin(object):

    def check_cycle(self, first_full_dest="", error_field="full_dest"):
        alias = first_full_dest
        if "," in alias:
            alias = alias.split(",")[-1]
        seen = [self.instance.alias]
        os = ""
        while VirtualDelivery.objects.filter(alias=alias).exists():
            os += alias + " > "
            alias = VirtualDelivery.objects.get(alias=alias).full_dest
            if "," in alias:
                alias = alias.split(",")[-1]
            os += alias + " ==> "
            if alias in seen:
                self.add_error(error_field, ValidationError(
                    _("Alias is making a cyclic reference %(aliases)s") %
                    {
                        'aliases': os
                    }))
                return False
            seen.append(alias)

        if Domains.objects.filter(
            domain_name=alias.split("@")[1]).exists() and \
                not MailUsers.objects.filter(username=alias).exists():
            messages.add_message(request=self.request, message=_(
                "The final destination %(finaldest)s does not exist "
                "for the alias %(alias)s on this system check "
                "if necessary the  mx of %(domain)s") % {
                'finaldest': alias,
                'domain': alias.split("@")[1],
                'alias': str(self.instance)},
                level=messages.WARNING)
        return True


class VirtualDeliveryForwarderForm(VirtualDeliveryCyclicCheckMixin, ModelForm):
    alias = CharField(required=True, disabled=True, label=_(
        "Forward from"), validators=[EmailValidator])
    forward_to = CharField(required=True, label=_(
        "Forward to"), validators=[EmailValidator])
    keep_copy = BooleanField(
        required=False, initial=True, label=_("Keep copy"))

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        kwargs["initial"] = {
             "forward_to": kwargs.get('instance').full_dest.split(",")[-1],
             "keep_copy": ("," in kwargs.get('instance').full_dest)
            }
        super(ModelForm, self).__init__(*args, **kwargs)
        self.instance.forward_to = self.instance.full_dest.split(",")[-1]

    def is_valid(self):

        if super(VirtualDeliveryForwarderForm, self).is_valid():
            try:
                validate_email(self.cleaned_data['forward_to'])
            except ValidationError:
                self.add_error("forward_to", _(
                    "Please enter exactly one valid email address"))
                return False
            return self.check_cycle(first_full_dest=self.cleaned_data
                                    ["forward_to"], error_field="forward_to")
        return False

    def save(self, commit=True):
        forward = super(VirtualDeliveryForwarderForm, self).save(commit=False)
        if self.cleaned_data['keep_copy']:
            forward.full_dest = self.cleaned_data['alias'] + \
                "," + self.cleaned_data['forward_to']
        else:
            forward.full_dest = self.cleaned_data['forward_to']
        forward.alias_domain = Domains.objects.get(
            domain_name=(forward.alias.split("@")[1]))
        forward.is_forwarder = True

        return forward.save()

    class Meta:
        model = VirtualDelivery
        fields = ['alias']


class VirtualDeliveryExternalForm(MailConcatMixin,
                                  VirtualDeliveryCyclicCheckMixin,
                                  ModelForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(ModelForm, self).__init__(*args, **kwargs)
        if self.request.user.has_perm("djcyradm.add_virtualdelivery_external"):
            if self.request.user.has_perm("djcyradm.is_admin"):
                self.fields['alias_domain'].queryset = Domains.objects.all()
            elif self.request.user.has_perm("djcyradm.is_domain_admin"):
                self.fields['alias_domain'].queryset = Domains.objects.filter(
                    pk__in=self.request.user.domains.all())

    def is_valid(self):
        if super(VirtualDeliveryExternalForm, self).is_valid():
            ret = self.concat_email(domainfieldname='alias_domain',
                                    userfieldname='alias',
                                    check_same_domain=True,
                                    error=2)
            if ret:
                self.instance.is_external_alias = True
                if MailUsers.objects.filter(username=ret).exists():
                    self.add_error("alias", ValidationError(
                        _("A user has the wanted alias as username")))
                    return False
                if self.instance.pk is None and\
                        VirtualDelivery.objects.filter(alias=ret).exists():
                    self.add_error("alias", ValidationError(
                        _("Alias already exists")))
                    return False
                if self.instance.pk is not None and\
                        VirtualDelivery.objects.filter(
                            Q(alias=ret),
                            ~Q(pk=self.instance.pk)).exists():
                    self.add_error("alias", ValidationError(
                        _("Alias already exists")))
                    return False
                self.instance.alias = ret
                try:
                    validate_email(self.instance.full_dest)
                except ValidationError:
                    self.add_error("full_dest",
                                   ValidationError(
                                        _("%(email)s is not a valid email") % {
                                            'email': self.instance.full_dest
                                        }))
                    return False
                if self.instance.full_dest == self.instance.alias:
                    self.add_error("full_dest", ValidationError(
                        _("Destination equals alias")))
                    return False
                if self.instance.alias_domain.max_external_aliases is not None\
                        and VirtualDelivery.objects.filter(
                        is_external_alias=True,
                        alias_domain=self.instance.alias_domain).count() >= \
                        self.instance.alias_domain.max_external_aliases:
                    self.add_error("alias_domain", ValidationError(
                        _("No more external aliases from this\
                          domain %(domain)s, limit %(limit)d reached") % {
                            'domain': self.instance.alias_domain,
                            'limit': self.instance.
                            alias_domain.max_external_aliases
                        }))
                    return False

                return self.check_cycle(
                        first_full_dest=self.instance.full_dest)
            return False
        return False

    def save(self, commit=True):
        virtual = super(ModelForm, self).save(commit=True)
        return virtual

    class Meta:
        model = VirtualDelivery
        fields = ['alias', 'alias_domain', 'full_dest']


class RecoverPasswordForm(Form):
    email = EmailField(validators=[EmailValidator], label=(_('Username')))

    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url')
        super(Form, self).__init__(*args, **kwargs)

    def clean_email(self):
        if MailUsers.objects.filter(
                username=self.cleaned_data['email']).exists():
            p = PasswordResetTokenGenerator()
            user = MailUsers.objects.get(username=self.cleaned_data['email'])
            token = p.make_token(user)
            domain = MailUsers.objects.get(
                is_main_cyrus_admin=True).domain.domain_name
            try:
                validate_email(user.email)
                send_mail(
                    _("Password reset instructions"),
                    _("Please visit the following link\
                      to reset your password %(link)s") %
                    {'link': self.url +
                        reverse('recover_account', args=(user.pk, token))},
                    'no-reply@' + domain,
                    [user.email]
                )
            except ValidationError:
                pass


class EmailConfirmTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk) + user.password +
            user.email + str(user.email_confirmed)
        )


class MailUsersRecoveryEmailForm(ModelForm):
    email = EmailField(required=True, validators=[EmailValidator])

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.url = kwargs.pop('url')
        super(ModelForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        if self.instance.email == self.request.user.email and\
                self.instance.email_confirmed:
            messages.add_message(self.request, WARNING, _('No changes made'))
            return
        self.instance.email_confirmed = False
        super(MailUsersRecoveryEmailForm, self).save(commit=True)
        domain = MailUsers.objects.get(
            is_main_cyrus_admin=True).domain.domain_name
        e = EmailConfirmTokenGenerator()
        token = e.make_token(self.instance)

        send_mail(_("Recovery email confirmation instructions"),
                  _('Please visit the following\
                    link to confirm your recovery email %(link)s') %
                  {'link': self.url +
                      reverse('recover-confirm-email', args=(
                          self.instance.pk, token))},
                  'no-reply@' + domain,
                  [self.instance.email]
                  )
        messages.add_message(self.request,
                             WARNING,
                             _('Please confirm your recovery email by'
                               'following instructions sent to your'
                               'recovery email'))

    def is_valid(self):
        if super(MailUsersRecoveryEmailForm, self).is_valid():
            if VirtualDelivery.objects.filter(alias=self.instance.email,
                                              dest=self.instance).exists() or \
                    self.instance.username == self.instance.email:
                self.add_error('email',
                               ValidationError(_("Please choose an external\
                                email address for recovering your password")))
                return False
            return True
        return False

    class Meta:
        model = MailUsers
        fields = ['email']
