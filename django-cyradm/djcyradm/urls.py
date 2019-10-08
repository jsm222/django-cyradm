from django.conf.urls import include, url
from djcyradm.views import locked_out

from djcyradm import views

urlpatterns = [
    url(r'session_security/', include('session_security.urls')),
    url(r'^mail-users/$', views.MailUsersTableView.as_view(), name='mail-users'),
    url(r'^login/?$', views.CustomLoginView.as_view(), name='login'),
    url(r'^locked/$', locked_out, name='locked_out'),
    url(r'^captcha/', include('captcha.urls')),
    url(r'^logout/$', views.CustomLogout.as_view(), name="logout"),
    url(r'^recover/$', views.RecoverPassword.as_view(), name="recover-password"),
    url(r'^recover/confirm-email/(?P<pk>[0-9]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.RecoverEmailConfirm.as_view(), name="recover-confirm-email"),
    url(r'^mailusers/(?P<pk>[0-9]+)/email/$', views.ChangeRecoveryEmail.as_view(),
        name="mail-users-recovery-email-change"),
    url(r'^recover/(?P<pk>[0-9]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
                views.RecoverAccountView.as_view(), name='recover_account'),
    url(r'^recover/confirm/$', views.RecoverConfirm.as_view(), name="recover-confirm"),
    url(r'^mail-users/add/$', views.MailUserCreate.as_view(), name='mail-users-add'),
    url(r'^confirm/$', views.ConfirmDisableOrDelete.as_view(), name="confirm"),
    url(r'^mail-users/delete/confirm/$', views.AccountConfirmDelete.as_view(), name="delete_confirm_accounts"),
    url(r'^mail-users/(disable|enable)/confirm/$', views.AccountConfirmDisable.as_view(),
        name="disable_confirm_accounts"),
    url(r'^mail-users/(?P<pk>[0-9]+)/$', views.MailUserUpdate.as_view(), name='mail-users-update'),
    url(r'^mail-users/(?P<pk>[0-9]+)/password/$', views.MailUserUpdatePassword.as_view(),
        name='mail-users-password-change'),
    url(r'^mail-users/(?P<pk>[0-9]+)/password/reset/$', views.MailUserResetPassword.as_view(),
        name='mail-users-password-reset'),
    url(r'^mail-users/(?P<pk>[0-9]+)/forwarding/$', views.VirtualDeliveryMailForward.as_view(), name='mail-forwarding'),
    url(r'^domains/$', views.DomainsTableView.as_view(), name='domains'),
    url(r'^domains/add/$', views.DomainsCreate.as_view(), name='domains-add'),
    url(r'^domains/(?P<pk>[0-9]+)/$', views.DomainsUpdate.as_view(), name='domains-update'),
    url(r'^domains/delete/confirm/$', views.DomainConfirmDelete.as_view(), name="delete_confirm_domains"),
    url(r'^aliases/$', views.VirtualDeliveryTableView.as_view(), name='aliases'),
    url(r'^aliases/add/$', views.VirtualDeliveryCreate.as_view(), name='aliases-add'),
    url(r'^aliases/add/external/$', views.VirtualDeliveryExternalCreate.as_view(), name='aliases-add-external'),
    url(r'^aliases/(?P<pk>[0-9]+)/$', views.VirtualDeliveryUpdate.as_view(), name='aliases-update'),
    url(r'^aliases/delete/confirm/$', views.VirtualDeliveryConfirmDelete.as_view(), name="delete_confirm_aliases"),
    url(r'^aliases/(disable|enable)/confirm/$', views.VirtualDeliveryConfirmDisable.as_view(),
        name="disable_confirm_aliases")]

