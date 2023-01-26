from django.urls import include, re_path
from djcyradm.views import locked_out

from djcyradm import views

urlpatterns = [
    re_path(r"session_security/", include("session_security.urls")),
    re_path(
        r"^mail-users/$",
        views.MailUsersTableView.as_view(),
        name="mail-users"),
    re_path(r"^login/?$", views.CustomLoginView.as_view(), name="login"),
    re_path(r"^locked/$", locked_out, name="locked_out"),
    re_path(r"^captcha/", include("captcha.urls")),
    re_path(
        r"^logout/$",
        views.CustomLogout.as_view(),
        name="logout"),
    re_path(
        r"^recover/$",
        views.RecoverPassword.as_view(),
        name="recover-password"),
    re_path(
        r"^recover/confirm-email/(?P<pk>[0-9]+)/(?P<token>\
        [0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
        views.RecoverEmailConfirm.as_view(),
        name="recover-confirm-email",
    ),
    re_path(
        r"^mailusers/(?P<pk>[0-9]+)/email/$",
        views.ChangeRecoveryEmail.as_view(),
        name="mail-users-recovery-email-change",
    ),
    re_path(
        r"^recover/(?P<pk>[0-9]+)/(?P<token>[0-9A-Za-z]{1,13}\
        -[0-9A-Za-z]{1,20})/$",
        views.RecoverAccountView.as_view(),
        name="recover_account",
    ),
    re_path(
        r"^recover/confirm/$",
        views.RecoverConfirm.as_view(),
        name="recover-confirm"),
    re_path(
        r"^mail-users/add/$",
        views.MailUserCreate.as_view(),
        name="mail-users-add"),
    re_path(r"^confirm/$", views.ConfirmDisableOrDelete.as_view(),
            name="confirm"),
    re_path(
        r"^mail-users/delete/confirm/$",
        views.AccountConfirmDelete.as_view(),
        name="delete_confirm_accounts",
    ),
    re_path(
        r"^mail-users/(disable|enable)/confirm/$",
        views.AccountConfirmDisable.as_view(),
        name="disable_confirm_accounts",
    ),
    re_path(
        r"^mail-users/(?P<pk>[0-9]+)/$",
        views.MailUserUpdate.as_view(),
        name="mail-users-update",
    ),
    re_path(
        r"^mail-users/(?P<pk>[0-9]+)/password/$",
        views.MailUserUpdatePassword.as_view(),
        name="mail-users-password-change",
    ),
    re_path(
        r"^mail-users/(?P<pk>[0-9]+)/password/reset/$",
        views.MailUserResetPassword.as_view(),
        name="mail-users-password-reset",
    ),
    re_path(
        r"^mail-users/(?P<pk>[0-9]+)/forwarding/$",
        views.VirtualDeliveryMailForward.as_view(),
        name="mail-forwarding",
    ),
    re_path(r"^domains/$", views.DomainsTableView.as_view(), name="domains"),
    re_path(r"^domains/add/$", views.DomainsCreate.as_view(),
            name="domains-add"),
    re_path(
        r"^domains/(?P<pk>[0-9]+)/$",
        views.DomainsUpdate.as_view(),
        name="domains-update",
    ),
    re_path(
        r"^domains/delete/confirm/$",
        views.DomainConfirmDelete.as_view(),
        name="delete_confirm_domains",
    ),
    re_path(
        r"^aliases/$",
        views.VirtualDeliveryTableView.as_view(),
        name="aliases"
    ),
    re_path(
        r"^aliases/add/$",
        views.VirtualDeliveryCreate.as_view(),
        name="aliases-add"
    ),
    re_path(
        r"^aliases/add/external/$",
        views.VirtualDeliveryExternalCreate.as_view(),
        name="aliases-add-external",
    ),
    re_path(
        r"^aliases/(?P<pk>[0-9]+)/$",
        views.VirtualDeliveryUpdate.as_view(),
        name="aliases-update",
    ),
    re_path(
        r"^aliases/delete/confirm/$",
        views.VirtualDeliveryConfirmDelete.as_view(),
        name="delete_confirm_aliases",
    ),
    re_path(
        r"^aliases/(disable|enable)/confirm/$",
        views.VirtualDeliveryConfirmDisable.as_view(),
        name="disable_confirm_aliases",
    ),
]
