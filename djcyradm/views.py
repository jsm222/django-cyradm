from axes.utils import reset
from ipware import get_client_ip
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.contrib import messages
from django.contrib.auth.views import LoginView, redirect_to_login, LogoutView
from django.contrib.messages import INFO, WARNING
from django.db.models import Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.utils.translation import ngettext_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView, FormView
from django_tables2 import SingleTableView
from rules.contrib.views import PermissionRequiredMixin, LoginRequiredMixin

from djcyradm.filters import MailUsersFilter, DomainsFilter, \
    VirtualDeliveryFilter
from djcyradm.imap import Imap, logout
from .forms import MailUsersForm, DomainsForms, MailUsersPasswordForm, \
    VirtualDeliveryForm, MailUsersPasswordResetForm, \
    VirtualDeliveryForwarderForm, VirtualDeliveryExternalForm, \
    AxesCaptchaForm, RecoverPasswordForm, \
    MailUsersRecoveryEmailForm, EmailConfirmTokenGenerator
from .models import MailUsers, Domains, VirtualDelivery
from .tables import MailUsersTable, DomainsTable, VirtualDeliveryTable


class LoggedInPermissionsMixin(PermissionRequiredMixin):
    """
    Raises only an exception if the user is an authenticated
    user that does not have the permission_required.
    """
    raise_exception = True

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            if self.raise_exception:
                raise PermissionDenied(self.get_permission_denied_message())
        return redirect_to_login(self.request.get_full_path(),
                                 self.get_login_url(),
                                 self.get_redirect_field_name())


class MailUserCreate(LoggedInPermissionsMixin, CreateView):
    model = MailUsers
    form_class = MailUsersForm
    template_name = "djcyradm/form.html"
    permission_required = 'djcyradm.add_mailusers'
    raise_exception = True
    permission_denied_message = _("You are not allowed to add accounts")

    def get_form_kwargs(self):
        kw = super(MailUserCreate, self).get_form_kwargs()
        kw['request'] = self.request
        return kw


class MailUserUpdate(LoggedInPermissionsMixin, UpdateView):
    model = MailUsers
    form_class = MailUsersForm
    template_name = "djcyradm/form.html"
    permission_required = 'djcyradm.change_mailusers'
    raise_exception = True
    permission_denied_message = _("You cannot change accounts \
                                   or you are trying to change \
                                   the main cyrus admin \
                                   if the later use %(cmd)s") % \
        {'cmd': "manage.py initialize --update"}

    def get_form_kwargs(self):
        kw = super(MailUserUpdate, self).get_form_kwargs()
        kw['request'] = self.request
        return kw

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(MailUserUpdate, self).get_context_data(**kwargs)
        # Add in a QuerySet of all the books
        context['link'] = {'txt': _("Configure mail forwarding"),
                           'href': 'mailforward/'
                           }

        return context


class MailUserUpdatePassword(LoggedInPermissionsMixin, UpdateView):
    model = MailUsers
    form_class = MailUsersPasswordForm
    template_name = "djcyradm/form.html"
    permission_required = 'djcyradm.change_mailusers_password'
    permission_denied_message = _("You are not allowed to change"
                                  " this password."
                                  " (Use manage.py for main cyrus admin)")
    raise_exception = True

    def get_form_kwargs(self):
        kw = super(MailUserUpdatePassword, self).get_form_kwargs()
        kw['request'] = self.request
        return kw


class MailUserResetPassword(LoggedInPermissionsMixin, UpdateView):
    model = MailUsers
    template_name = "djcyradm/form.html"
    form_class = MailUsersPasswordResetForm
    permission_denied_message = _("You are not allowed to reset this password")
    permission_required = 'djcyradm.change_mailusers'
    raise_exception = True


@receiver(signal=post_delete)
def post_delete_mail_account(sender, instance, **kwargs):
    """
    Deletes the actual imap account on deletion of the database object
    if settings.IMAPSYNC it true
    """
    if sender == MailUsers:
        with logout(Imap()) as imap:
            imap.delete_mailbox(username=instance.username)


class DomainsCreate(PermissionRequiredMixin, CreateView):
    model = Domains
    form_class = DomainsForms
    template_name = "djcyradm/form.html"
    permission_required = "djcyradm.add_domains"
    permission_denied_message = _("You are not allowed to create domain")
    login_url = '/cyradm/login'
    raise_exception = True


class DomainsUpdate(LoggedInPermissionsMixin, UpdateView):
    model = Domains
    form_class = DomainsForms
    template_name = "djcyradm/form.html"
    permission_required = "djcyradm.change_domains"
    permission_denied_message = _("You are not allowed to update domain")
    raise_exception = True
    selection = []


class ConfirmDisableOrDelete(View):
    def post(self, request, *args, **kwargs):
        if request.POST.get('submit'):
            request.session["selection"] = request.POST.getlist("selection")
            request.session["action"] = request.POST.get('submit')
            return redirect("{0}{1}/confirm/".format(
                            request.POST.get("do_action"),
                            request.POST.get('submit')))
        return redirect("mail-users")


class ConfirmDeleteMixin(object):
    template_name = "djcyradm/confirm.html"
    permission_denied_msg = None
    ctx_msg = None
    ctx_msg_plural = None
    ctx_msg_plural_enable = None
    ctx_msg_enable = None
    perm = None
    perm_obj = None
    del_obj = None
    redirect_to = "mail-users"
    selection = []

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(self.redirect_to)
        qf = {}
        self.qf = {}
        cur_val = True
        selection = request.session['selection']
        self.selection = selection
        request.session["selection"] = []
        qf['id__in'] = selection

        if request.session.get('action') == 'enable':
            cur_val = False
            self.ctx_msg = self.ctx_msg_enable
            self.ctx_msg_plural = self.ctx_msg_plural_enable
        if request.session.get('action') == 'enable' \
           or request.session.get('action') == 'disable':
            qf['is_active'] = cur_val

        self.qf = qf
        if self.del_obj.objects.filter(**qf).count() == 0:
            messages.add_message(request, INFO, _("No changes made"))
            return redirect(to=self.redirect_to)

        if len(selection) == 0:
            return redirect(to=self.redirect_to)

        if request.user.is_authenticated and \
                request.user.has_perm(
                    self.perm,
                    None if self.perm_obj is None else self.perm_obj
                    .objects.filter(pk__in=selection)):

            return super().get(request, args, kwargs)
        else:
            return TemplateResponse(
                status=403, request=request, template='403.html',
                context={"exception": self.permission_denied_msg,
                         "href": reverse(self.redirect_to)})

    def get_context_data(self):
        msg = ngettext_lazy(self.ctx_msg,
                            self.ctx_msg_plural,
                            len(self.selection))

        return {"objects": self.del_obj.objects.filter(**self.qf), "msg": msg}


class AccountConfirmDelete(ConfirmDeleteMixin, TemplateView):
    permission_denied_msg = _("You are not allowed to delete accounts")
    ctx_msg = "Do you really want to delete the listed account\
    and all aliases belonging to them?"
    ctx_msg_plural = "Do you really want to delete the listed \
    accounts and all aliases belonging to them?"
    perm = 'djcyradm.delete_mailusers'
    perm_obj = MailUsers
    del_obj = MailUsers
    redirect_to = "mail-users"

    def post(self, request, *args, **kwargs):
        select = request.POST.getlist("selection")
        if request.user.is_authenticated \
           and request.user.has_perm('djcyradm.delete_mailusers',
                                     MailUsers.objects.filter(id__in=select)):
            deleted = VirtualDelivery.objects.filter(
                Q(dest__id__in=select) |
                Q(alias__in=MailUsers.objects.filter(id__in=select)
                  .values_list("username"))).delete()
            numdel = 0
            if deleted[0] == 0:
                numdel = 0
            else:
                numdel = deleted[1].get("djcyradm.VirtualDelivery")
            messages.add_message(request, INFO,
                                 ngettext_lazy("Deleted %(num)d alias",
                                               "Deleted %(num)d aliases",
                                               numdel % {'num': numdel}))
            if str(request.user.id) in select:
                messages.add_message(request, WARNING,
                                     _("You cannot delete the\
signed in account %(account)s") % {'account': request.user.username})
                select.remove(str(request.user.id))
            deleted = MailUsers.objects.filter(is_main_cyrus_admin=False,
                                               id__in=select).delete()
            numdel = 0
            if deleted[0] == 0:
                numdel = 0
            else:
                deleted[1].get("djcyradm.MailUsers")
            messages.add_message(request, INFO,
                                 ngettext_lazy("Deleted %(num)d account",
                                               "Deleted %(num)d accounts",
                                               numdel) %
                                 {'num': numdel})
            return redirect(to="mail-users")
        else:
            return TemplateResponse(
                status=403, request=request, template='403.html',
                context={'href': reverse(self.redirect_to),
                         'exception': _('You are not allowed\
to delete accounts')})


class AccountConfirmDisable(ConfirmDeleteMixin, TemplateView):
    permission_denied_msg = _("You are not allowed to disable accounts")
    ctx_msg = "Do you really want to disable the listed account?"
    ctx_msg_plural = "Do you really want to disable the listed accounts?"
    qf = {'is_main_cyrus_admin': False}
    ctx_msg_enable = "Do you really want to enable the listed account?"
    ctx_msg_plural_enable = "Do you really want to enable the listed accounts?"
    perm_obj = MailUsers
    del_obj = MailUsers
    perm = 'djcyradm.delete_mailusers'

    def post(self, request, *args, **kwargs):
        select = request.POST.getlist("selection")
        if request.user.is_authenticated \
           and request.user.has_perm("djcyradm.delete_mailusers",
                                     MailUsers.objects.filter(id__in=select)):
            if str(request.user.id) in select:
                messages.add_message(request,
                                     WARNING,
                                     _("You cannot disable\
the signed in account %(account)s") % {'account': request.user.username})
                select.remove(str(request.user.id))

            set_active = request.session['action'] == 'enable'
            cur_val = not set_active
            num_rows = MailUsers.objects.filter(is_active=cur_val,
                                                is_main_cyrus_admin=False,
                                                id__in=select). \
                update(is_active=set_active)
            if set_active:
                messages.\
                    add_message(request,
                                INFO,
                                ngettext_lazy("Enabled %(num)d account",
                                              "Enabled %(num)d accounts",
                                              num_rows) % {'num': num_rows})
            else:
                messages.\
                    add_message(request,
                                INFO,
                                ngettext_lazy("Disabled %(num)d account",
                                              "Disabled %(num)d accounts",
                                              num_rows) % {'num': num_rows})
            return redirect(to="mail-users")
        else:
            return TemplateResponse(
                status=403, request=request, template='403.html',
                context={'href': reverse(self.redirect_to),
                         'exception': _('You are not allowed\
to delete accounts')})


def locked_out(request):
    if request.POST:
        form = AxesCaptchaForm(request.POST)
        if form.is_valid():
            ip, is_routable = get_client_ip(request)
            reset(ip=ip)
            return HttpResponseRedirect(reverse_lazy('login'))
    else:
        form = AxesCaptchaForm()

    return render(request, 'djcyradm/locked_out.html', context=dict(form=form))


class DomainConfirmDelete(ConfirmDeleteMixin, TemplateView):
    template_name = "djcyradm/confirm.html"
    ctx_msg = 'Do you really want to delete the listed\
domain and all accounts an aliases belonging to them?'
    ctx_msg_plural = 'Do you really want to delete the listed\
domains and all accounts an aliases belonging to them?'
    perm = 'djcyradm.delete_domains'
    permission_denied_msg = _('You are not allowed to delete domains')
    perm_obj = Domains
    del_obj = Domains
    redirect_to = 'domains'

    def post(self, request, *args, **kwargs):
        do_select = []
        select = []
        if request.user.is_authenticated:
            select = request.POST.getlist("selection")
            exclude = MailUsers.objects.get(is_main_cyrus_admin=True).domain_id

            for d in select:
                if int(d) == int(exclude):
                    adn = MailUsers.objects.get(is_main_cyrus_admin=True)
                    messages.\
                        add_message(request,
                                    WARNING,
                                    ("Could not delete domain of"
                                     "main cyrus user %(domain)s") %
                                    {'domain': adn.domain.domain_name})
                else:
                    do_select.append(d)
        if request.user.has_perm("djcyradm.delete_domains",
                                 Domains.objects.filter(id__in=do_select)):
            deleted = VirtualDelivery.objects \
                .filter(alias_domain_id__in=select).delete()
            numdel = 0
            if deleted[0] == 0:
                numdel = 0
            else:
                deleted[1].get("djcyradm.VirtualDelivery")
            messages.add_message(request, INFO,
                                 ngettext_lazy("Deleted %(num)d alias",
                                               "Deleted %(num)d aliases",
                                               numdel) % {"num": numdel})
            deleted = MailUsers.objects.filter(is_main_cyrus_admin=False,
                                               domain_id__in=select).delete()
            numdel = 0
            if deleted[0] == 0:
                numdel = 0
            else:
                deleted[1].get("djcyradm.MailUsers")

            messages.\
                add_message(request, INFO,
                            ngettext_lazy("Deleted %(num)d account",
                                          "Deleted %(num)d accounts",
                                          numdel) % {'num': numdel})

            deleted = Domains.objects.filter(id__in=do_select).delete()
            numdel = 0
            if deleted[0] == 0:
                numdel = 0
            else:
                deleted[1].get("djcyradm.Domains")
            messages\
                .add_message(request, INFO,
                             ngettext_lazy("Deleted %(num)d domain",
                                           "Deleted %(num)d domains",
                                           numdel) % {'num': numdel})

            return redirect(to="domains")
        else:
            ctx = {'href': reverse(self.redirect_to),
                   'exception': _('You are not allowed to delete domains')}
            return TemplateResponse(status=403,
                                    request=request,
                                    template='403.html',
                                    context=ctx)


class VirtualDeliveryConfirmDelete(ConfirmDeleteMixin, TemplateView):
    template_name = "djcyradm/confirm.html"
    ctx_msg = 'Do you really want to delete the listed alias?'
    ctx_msg_plural = 'Do you really want to delete the listed aliases?'
    perm = 'djcyradm.delete_virtualdeliveries'
    perm_obj = VirtualDelivery
    del_obj = VirtualDelivery
    permission_denied_msg = _('You are not allowed to delete aliases')
    redirect_to = "aliases"

    def post(self, request, *args, **kwargs):
        select = request.POST.getlist("selection")
        if request.user.is_authenticated and request.user.has_perm(
                "djcyradm.delete_virtualdeliveries",
                VirtualDelivery.objects.filter(id__in=select)):

            deleted = VirtualDelivery.objects.filter(id__in=select).delete()
            numdel = 0
            if deleted[0] == 0:
                numdel = 0
            else:
                numdel = deleted[1].get("djcyradm.VirtualDelivery")
            messages.add_message(request, INFO,
                                 ngettext_lazy("Deleted %(num)d alias",
                                               "Deleted %(num)d aliases",
                                               numdel) % {'num': numdel})
            return redirect(to="aliases")
        else:
            context = {'exception': _("You are not allowed to delete aliases"),
                       'href': reverse(self.redirect_to)}
            return TemplateResponse(status=403, request=request,
                                    template='403.html',
                                    context=context)


class VirtualDeliveryConfirmDisable(ConfirmDeleteMixin, TemplateView):
    template_name = "djcyradm/confirm.html"
    ctx_msg = 'Do you really want to disable the listed alias?'
    ctx_msg_plural = 'Do you really want to disable the listed aliases?'
    ctx_msg_enable = 'Do you really want to enable the listed alias?'
    ctx_msg_plural_enable = 'Do you really want to enable the listed aliases?'
    perm = 'djcyradm.delete_virtualdeliveries'
    perm_obj = VirtualDelivery
    del_obj = VirtualDelivery
    permission_denied_msg = _('You are not allowed to disable aliases')
    redirect_to = "aliases"

    def post(self, request, *args, **kwargs):
        select = request.POST.getlist("selection")
        if request.user.is_authenticated and \
            request.user.has_perm("djcyradm.delete_virtualdeliveries",
                                  VirtualDelivery.objects.filter(
                                      id__in=select)):
            set_active = request.session['action'] == 'enable'
            cur_val = not set_active
            num_rows = VirtualDelivery.objects.filter(is_active=cur_val,
                                                      id__in=select).update(
                                                          is_active=set_active)
            if set_active:
                messages.\
                    add_message(request,
                                INFO,
                                ngettext_lazy("Enabled %(num)d alias",
                                              "Enabled %(num)d aliases",
                                              num_rows) % {'num': num_rows})
            else:
                messages.\
                    add_message(request,
                                INFO,
                                ngettext_lazy("Disabled %(num)d alias",
                                              "Disabled %(num)d aliases",
                                              num_rows) % {'num': num_rows})
            return redirect(to="aliases")
        else:
            context = {'exception': _("You are not allowed to delete aliases"),
                       'href': reverse(self.redirect_to)}
            return TemplateResponse(status=403,
                                    request=request,
                                    template='403.html',
                                    context=context)


class CustomLoginView(LoginView):
    template_name = "djcyradm/login_form.html"
    redirect_authenticated_user = True


class CustomLogout(LogoutView):
    next_page = 'login'


class PagedFilteredTableView(SingleTableView):
    context_filter_name = 'filter'

    def get_context_data(self, **kwargs):
        context = super(PagedFilteredTableView, self).get_context_data()
        context[self.context_filter_name] = self.filter
        return context

    def get_table_pagination(self, table):
        if self.request.GET.get("showall") == 'true':
            return False
        return super(SingleTableView, self).get_table_pagination(table)


class DomainsTableView(LoggedInPermissionsMixin, PagedFilteredTableView):
    model = Domains
    table_class = DomainsTable
    template_name = 'djcyradm/table.html'
    filter_class = DomainsFilter
    permission_required = 'djcyradm.list_domains'
    permission_denied_message = _("You are not allowed to list domains")

    def get_queryset(self, **kwargs):
        qs = Domains.objects.filter(pk=0)
        if self.request.user.has_perm("djcyradm.is_admin"):
            qs = Domains.objects.all()
        elif self.request.user.has_perm("djcyradm.is_domain_admin"):
            qs = Domains.objects.filter(admindomains=self.request.user)
        self.filter = self.filter_class(self.request.GET,
                                        queryset=qs,
                                        request=self.request)
        return self.filter.qs

    def get_context_data(self, **kwargs):
        cd = super(DomainsTableView, self).get_context_data()
        cd["is_domains"] = True
        return cd


class MailUsersTableView(LoggedInPermissionsMixin, PagedFilteredTableView):
    model = MailUsers
    table_class = MailUsersTable
    permission_required = 'djcyradm.is_in_djcyradm_group'
    template_name = 'djcyradm/table.html'
    filter_class = MailUsersFilter
    raise_exception = True
    permission_denied_message = _("Your credentials are valid,\
but you have not been assigned any groups. Contact your administrator.")

    def get_table_kwargs(self):

        kw = super(MailUsersTableView, self).get_table_kwargs()
        with logout(Imap()) as imap:
            quotas = {}
            usernames = self.get_queryset().values_list("username", flat=True)
            for username in usernames:
                quotas[username] = imap.get_quota(username=username)

        kw["quotas"] = quotas
        return kw

    def get_queryset(self, **kwargs):
        qs = MailUsers.objects.filter(pk=0)
        if self.request.user.has_perm("djcyradm.is_admin"):
            qs = MailUsers.objects.filter(is_main_cyrus_admin=False)
        elif self.request.user.has_perm("djcyradm.is_domain_admin"):
            qs = MailUsers.objects.filter(
                                          Q(domain__in=self.request.user.
                                            domains.all(),
                                            is_main_cyrus_admin=False) |
                                          Q(id=self.request.user.id))
        elif self.request.user.has_perm("djcyradm.is_account_user"):
            qs = MailUsers.objects.filter(pk=self.request.user.id,
                                          is_main_cyrus_admin=False)
        self.filter = self.filter_class(self.request.GET, queryset=qs,
                                        request=self.request)
        return self.filter.qs


class VirtualDeliveryTableView(LoggedInPermissionsMixin,
                               PagedFilteredTableView):
    model = VirtualDelivery
    table_class = VirtualDeliveryTable
    template_name = 'djcyradm/table.html'
    filter_class = VirtualDeliveryFilter
    permission_required = 'djcyradm.list_virtualdelivery'
    permission_denied_message = _("You are not allowed to list aliases")

    def get_queryset(self, **kwargs):
        qs = VirtualDelivery.objects.filter(pk=0)
        if self.request.user.has_perm("djcyradm.is_admin"):
            qs = VirtualDelivery.objects.all()
        elif self.request.user.has_perm("djcyradm.is_domain_admin"):
            qs = VirtualDelivery.objects.filter(
                Q(dest__domain_id__in=self.request.user.domains.all()) |
                Q(alias_domain_id__in=self.request.user.domains.all()) |
                Q(dest=self.request.user) |
                Q(alias=self.request.user.username, is_forwarder=True))
        elif self.request.user.has_perm("djcyradm.is_account_user"):
            qs = VirtualDelivery.objects.filter(
                    Q(dest=self.request.user) |
                    Q(alias=self.request.user.username, is_forwarder=True)
                    )
        self.filter = self.filter_class(self.request.GET,
                                        queryset=qs,
                                        request=self.request)
        return self.filter.qs


class VirtualDeliveryCreate(LoggedInPermissionsMixin, CreateView):
    model = VirtualDelivery
    form_class = VirtualDeliveryForm
    template_name = "djcyradm/form.html"
    permission_required = 'djcyradm.add_virtualdelivery'
    permission_denied_message = _("You are not allowed to add aliases")

    def get_form_kwargs(self):
        kw = super(VirtualDeliveryCreate, self).get_form_kwargs()
        kw['request'] = self.request
        return kw


class VirtualDeliveryExternalCreate(VirtualDeliveryCreate):
    form_class = VirtualDeliveryExternalForm
    permission_required = 'djcyradm.add_virtualdelivery_external'
    permission_denied_message = \
        _("You are not allowed to add external aliases")

    def get_success_url(self):
        return reverse_lazy('aliases')


class VirtualDeliveryUpdate(LoggedInPermissionsMixin, UpdateView):
    model = VirtualDelivery
    form_class_forwarder = VirtualDeliveryForwarderForm
    form_class_external = VirtualDeliveryExternalForm
    form_class = VirtualDeliveryForm
    template_name = "djcyradm/form.html"
    permission_required = 'djcyradm.change_virtualdelivery'
    permission_denied_message = _("You are not allowed to update aliases")
    raise_exception = True

    def get_success_url(self):
        return reverse_lazy('aliases')

    def get_form_class(self):
        obj = self.get_object()
        if obj.is_forwarder:
            self.form_class = self.form_class_forwarder
        if obj.is_external_alias:
            self.form_class = self.form_class_external
        self.form_class = self.form_class
        return super(UpdateView, self).get_form_class()

    def get_form_kwargs(self):
        kw = super(VirtualDeliveryUpdate, self).get_form_kwargs()
        kw['request'] = self.request
        return kw


class VirtualDeliveryUpdateExternal(VirtualDeliveryUpdate):
    form_class = VirtualDeliveryExternalForm
    permission_required = 'djcyradm.change_virtualdelivery_external'
    permission_denied_message = \
        _("You are not allowed to update external aliases")
    raise_exception = True


class VirtualDeliveryMailForward(VirtualDeliveryUpdate):
    form_class = VirtualDeliveryForwarderForm
    permission_required = "djcyradm.change_mail_forward"
    permission_denied_message = \
        _("You are not allowed to update mail forwarding")

    def get_success_url(self):
        return reverse_lazy("aliases")

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        if VirtualDelivery.objects.filter(
                alias=MailUsers.objects.get(pk=pk)).exists():
            return VirtualDelivery.objects.get(
                    alias=MailUsers.objects.get(pk=pk).username)

        # make new object do not save:
        return VirtualDelivery(alias=MailUsers.objects.get(pk=pk).username)

    def get_permission_object(self):
        return MailUsers.objects.get(pk=self.kwargs.get(self.pk_url_kwarg))


class RecoverPassword(FormView):
    form_class = RecoverPasswordForm
    template_name = 'djcyradm/form.html'
    success_url = reverse_lazy("recover-confirm")

    def get(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('mail-users')
        return super(RecoverPassword, self).get(self, request, args, kwargs)

    def get_form_kwargs(self):
        kw = super(RecoverPassword, self).get_form_kwargs()
        scheme = 'https' if self.request.is_secure() else 'http'
        kw['url'] = scheme + '://' + self.request.get_host()
        return kw


class RecoverConfirm(TemplateView):
    template_name = 'djcyradm/recover_confirm.html'


class RecoverEmailConfirm(LoginRequiredMixin, View):
    template_name = 'djcyradm/form.html'
    permission_denied_message = \
        _("You are not allowed to confirm this recovery email")
    permission_required = 'djcyradm.change_mailusers_recovery_mail'

    def get(self, request, pk, token, *args, **kwargs):
        self.pk = pk
        e = EmailConfirmTokenGenerator()
        user = MailUsers.objects.get(pk=pk)
        if not request.user.has_perm(self.permission_required, user):
            context = {'exception': self.permission_denied_message}
            return render(request, '403.html', context=context)

        elif user is not None and e.check_token(user, token):
            user.email_confirmed = True
            user.save()
            user.refresh_from_db()
            if user.email_confirmed:
                messages.\
                    add_message(request, WARNING,
                                _('Your recovery email has been confirmed'))
                return redirect('mail-users')
        else:
            # invalid link
            return render(request, 'djcyradm/invalid.html')


class RecoverAccountView(UpdateView):
    model = MailUsers
    form_class = MailUsersPasswordResetForm
    template_name = 'djcyradm/form.html'

    def get(self, request, pk, token, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('mail-users')
        p = PasswordResetTokenGenerator()
        user = MailUsers.objects.get(pk=pk)

        if user is not None and p.check_token(user, token):
            return super(RecoverAccountView, self).get(request, args, kwargs)
        else:
            # invalid link
            return render(request, 'djcyradm/invalid.html')


class ChangeRecoveryEmail(LoggedInPermissionsMixin, UpdateView):

    model = MailUsers
    form_class = MailUsersRecoveryEmailForm
    template_name = 'djcyradm/form.html'
    permission_denied_message =\
        _("You are not allowed to change this recovery email")
    permission_required = 'djcyradm.change_mailusers_recovery_mail'

    def get_form_kwargs(self):
        kw = super(ChangeRecoveryEmail, self).get_form_kwargs()
        kw['request'] = self.request
        scheme = 'https' if self.request.is_secure() else 'http'
        kw['url'] = scheme + '://' + self.request.get_host()
        return kw

    def get_success_url(self):
        return reverse_lazy("mail-users")
