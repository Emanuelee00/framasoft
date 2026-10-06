# -*- coding: utf-8 -*-
"""Petition expiry: reminders to the creators, then permanent deletion (see the PETITION_* settings).

Used by the send_expiry_reminders and purge_personal_data commands.
"""

import html
import logging
import re
from datetime import timedelta
from urllib.parse import unquote

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage
from django.core.mail import get_connection, EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.formats import date_format
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from .models import Permission, Petition, PetitionTemplate, Signature

logger = logging.getLogger(__name__)


def reminder_recipients(petition):
    """Email addresses of the people who can extend the petition or export its signatures"""
    if petition.owner_type == "user":
        users = [petition.user.user]
    else:
        permissions = Permission.objects.filter(organization_id=petition.org_id)\
            .filter(Q(can_modify_petitions=True) | Q(can_view_signatures=True)).select_related('user__user')
        users = [permission.user.user for permission in permissions]
    return sorted({user.email for user in users if user.is_active and user.email})


def due_reminder(petition, today):
    """Reminder (number of days) to send today for this petition, or None"""
    days_left = (petition.expires_at - today).days
    if days_left < 1:
        return None
    due = [days for days in settings.PETITION_EXPIRY_REMINDER_DAYS if days_left <= days]
    if not due:
        return None
    # a late run sends only the most recent reminder, never several at once
    due = min(due)
    if petition.expiry_reminder_days is not None and petition.expiry_reminder_days <= due:
        return None
    return due


def send_reminder(petition, recipients, base_url):
    title = " ".join(html.unescape(strip_tags(petition.title)).split())
    ctx = {
        'petition_title': title,
        'org_name': petition.org.name if petition.org_id else None,
        'expires_at': petition.expires_at,
        'signature_number': petition.get_signature_number(True),
        'csv_url': base_url + reverse('get_csv_confirmed_signature', args=[petition.id]),
        'extend_url': base_url + reverse('edit_petition', args=[petition.id]) + "#expiry",
        'privacy_url': base_url + reverse('privacy_notice'),
    }
    with translation.override(settings.LANGUAGE_CODE):
        subject = _("Your petition “%(title)s” will be deleted on %(date)s") % {
            'title': title, 'date': date_format(petition.expires_at)}
        message = render_to_string("petition/expiry_reminder_email.txt", ctx)
        html_message = render_to_string("petition/expiry_reminder_email.html", ctx)
    # one message per person: the members of an organization do not see each other's address
    with get_connection() as connection:
        for email in recipients:
            msg = EmailMultiAlternatives(subject, message, to=[email], connection=connection,
                                         reply_to=[settings.DEFAULT_NOREPLY_MAIL])
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=False)


def send_expiry_reminders(dry_run=False):
    """Send the reminders due today; returns their number. Each reminder is sent once per deletion date."""
    base_url = settings.SITE_BASE_URL.rstrip("/")
    today = timezone.localdate()
    horizon = today + timedelta(days=max(settings.PETITION_EXPIRY_REMINDER_DAYS, default=0))
    petitions = Petition.objects.filter(in_bin_date__isnull=True, expires_at__gt=today, expires_at__lte=horizon)\
        .select_related('user__user', 'org').order_by('pk')
    sent = 0
    for petition in petitions:
        due = due_reminder(petition, today)
        if due is None:
            continue
        sent += 1
        if dry_run:
            continue
        try:
            send_reminder(petition, reminder_recipients(petition), base_url)
        except Exception:
            # not marked as sent: retried at the next run
            logger.exception("expiry reminder not sent for petition %s", petition.pk)
            sent -= 1
            continue
        # update(), not save(): the petition itself is not modified
        Petition.objects.filter(pk=petition.pk, expires_at=petition.expires_at).update(expiry_reminder_days=due)
    return sent


def pk_batches(queryset, batch_size):
    """pk lists of the rows of queryset, batch_size at a time, walking the primary key index"""
    last = None
    while True:
        batch = queryset.order_by('pk')
        if last is not None:
            batch = batch.filter(pk__gt=last)
        pks = list(batch.values_list('pk', flat=True)[:batch_size])
        if not pks:
            return
        yield pks
        last = pks[-1]


# One short statement per batch (autocommit): no long lock, no huge transaction.
# The queryset's conditions are applied again, for rows that changed since they were listed.
def delete_in_batches(queryset, batch_size):
    deleted = 0
    for pks in pk_batches(queryset, batch_size):
        deleted += queryset.filter(pk__in=pks).delete()[1].get(queryset.model._meta.label, 0)
    return deleted


def update_in_batches(queryset, batch_size, **values):
    updated = 0
    for pks in pk_batches(queryset, batch_size):
        updated += queryset.filter(pk__in=pks).update(**values)
    return updated


MEDIA_FIELDS = ('twitter_image', 'text', 'side_text', 'footer_text', 'footer_links')


def media_urls(petition):
    """Paths (MEDIA_URL + name) of the uploaded files a petition refers to"""
    pattern = re.escape(settings.MEDIA_URL) + r'[^"\'\s<>()]+'
    found = set()
    for field in MEDIA_FIELDS:
        found.update(re.findall(pattern, getattr(petition, field) or ""))
    return found


def is_media_used(url):
    used = Q()
    for field in MEDIA_FIELDS:
        used |= Q(**{field + '__contains': url})
    return Petition.objects.filter(used).exists() or PetitionTemplate.objects.filter(used).exists()


def delete_unused_media(urls):
    storage = FileSystemStorage()
    deleted = 0
    for url in urls:
        if is_media_used(url):
            continue  # also used by another petition or a template
        try:
            storage.delete(unquote(url[len(settings.MEDIA_URL):]))
            deleted += 1
        except (SuspiciousFileOperation, OSError):
            logger.warning("media file not deleted: %s", url)
    return deleted


def purge_expired_petitions(batch_size, dry_run=False):
    """Permanently delete the petitions whose deletion date has come, with their signatures and related rows
    (slugs, moderation and monitoring records) and the uploaded files no other petition or template uses.
    Returns (petitions, signatures)."""
    expired = Petition.objects.filter(expires_at__lte=timezone.localdate())
    if dry_run:
        return expired.count(), Signature.objects.filter(petition__in=expired).count()
    petitions = signatures = 0
    for pk in list(expired.values_list('pk', flat=True)):
        petition = expired.filter(pk=pk).first()
        if petition is None:  # extended or deleted meanwhile
            continue
        urls = media_urls(petition)
        signatures += delete_in_batches(Signature.objects.filter(petition_id=pk), batch_size)
        # the date is checked again; the remaining rows (slugs, moderation...) are few
        if expired.filter(pk=pk).delete()[0]:
            petitions += 1
            delete_unused_media(urls)
    return petitions, signatures
