from django import template
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
register = template.Library()


@register.simple_tag(takes_context=True)
def get_navigation(context):
    gn = ""
    for g in context['request'].user.groups.all():
        gn += g.name

    navigation = [
        {'text': _('Accounts'),  'perm': "djcyradm.is_in_djcyradm_group",
         'sub': [
             {'text': _('Add'),
              'href': reverse("mail-users-add"),
              'perm': "djcyradm.add_mailusers"},
             {'text': _('List'),
              'href': reverse("mail-users"),
              'perm': "djcyradm.is_in_djcyradm_group"}
         ]
         },
        {'text': _('Domains'),  'perm': "djcyradm.list_domains",
         'sub': [
             {'text': _('Add'),
              'href': reverse("domains-add"),
              'perm': "djcyradm.is_admin"
              },
             {'text': _('List'),
              'href':
              reverse("domains"),
              'perm': "djcyradm.list_domains"
              }
         ]
         },
        {'text': _('Aliases'), 'perm': "djcyradm.list_virtualdelivery",
         'sub': [
             {'text': _('Add'),
              'href': reverse("aliases-add"),
              'perm': "djcyradm.add_virtualdelivery"
              },
             {'text': _('List'),
              'href': reverse("aliases"),
              'perm': "djcyradm.list_virtualdelivery"
              },
             {'text': _('Add external'),
              'href': reverse("aliases-add-external"),
              'perm': 'djcyradm.add_virtualdelivery_external'}
         ]
         },
        {'text': context['request'].user.username + " (" + gn + ")",
         'perm': "djcyradm.is_in_djcyradm_group",
         'sub': [
             {'text': _("Change password"),
              'href': '' if not context['request']
              .user.is_authenticated else reverse(
                 "mail-users-password-change",
                 kwargs={'pk': str(context['request'].user.id)}),
                 'perm': "djcyradm.is_not_main_admin"
              },
             {'text': _("Change recovery email"),
              'href': '' if not context['request']
              .user.is_authenticated else reverse(
                 "mail-users-recovery-email-change",
                 kwargs={'pk': str(context['request'].user.id)}),
              'perm': "djcyradm.is_not_main_admin"},
             {'text': _("Configure forwarding"),
              'href': '' if not context['request']
              .user.is_authenticated else reverse
              ("mail-forwarding", kwargs={
                  'pk': str(context['request'].user.id)}),
              'perm': "djcyradm.is_account_user"},
             {'text': _('Log out'),
              'href': reverse("logout"),
              'perm': "djcyradm.is_in_djcyradm_group"}
         ]
         }
    ]

    for item in navigation:
        if item.get("perm") is not None:
            item["allowed"] = context['request'].user.has_perm(
                item.get("perm"))
        for sub_item in item.get("sub"):
            if context['request'].path == sub_item.get("href"):
                item["cls_class"] = "active"
            sub_item["allowed"] = context['request'].user.has_perm(
                sub_item.get("perm"))
    return navigation
