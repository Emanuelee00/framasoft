# -*- coding: utf-8 -*-
"""Helpers functions for pytition project

It defines actions to help the developper across the project.
"""

import ipaddress
import logging
import requests
import lxml
from lxml.html.clean import Cleaner
from django.http import Http404, HttpResponseForbidden
from django.conf import settings
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.crypto import salted_hmac
from django.core.mail import get_connection, EmailMultiAlternatives, EmailMessage
from django.core import signing
from django.utils.translation import gettext as _
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

# Timeouts (in seconds) of the calls made to the newsletter of a petition during a signature
NEWSLETTER_HTTP_TIMEOUT = 5
NEWSLETTER_SMTP_TIMEOUT = 10

# Remove the petitions whose owner is moderated (petitions is a queryset, filtered in SQL).
# Owners and slugs are loaded with the petitions, as lists display them.
def remove_user_moderated(petitions):
    return petitions.exclude(org__moderated=True).exclude(user__moderated=True)\
        .select_related('org', 'user__user').prefetch_related('slugmodel_set')

# Remove all javascripts from HTML code
def sanitize_html(unsecure_html_content):
    cleaner = Cleaner(inline_style=False, scripts=True, javascript=True,
                      safe_attrs=lxml.html.defs.safe_attrs | set(['style', 'controls']),
                      frames=False, embedded=False,
                      meta=True, links=True, page_structure=True, remove_tags=['body'])
    try:
        cleaned = cleaner.clean_html(lxml.html.fromstring(unsecure_html_content))

        for p in cleaned.xpath('//p[video]'):
            p.drop_tag()

        secure_html_content = lxml.html.tostring(cleaned, method="html")
    except:
        secure_html_content = b''
    return secure_html_content.decode()

# Get the client IP address, considering only the trusted reverse proxies
# (settings.PYTITION_TRUSTED_PROXY_COUNT): each of them appends to X-Forwarded-For,
# so the client address is the n-th element starting from the right.
def get_client_ip(request):
    trusted_proxies = getattr(settings, 'PYTITION_TRUSTED_PROXY_COUNT', 0)
    if trusted_proxies > 0:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        chain = [ip.strip() for ip in x_forwarded_for.split(',') if ip.strip()]
        if len(chain) >= trusted_proxies:
            return chain[-trusted_proxies]
    return request.META.get('REMOTE_ADDR')

# Normalize an IP address for hashing: IPv6 addresses are reduced to their /64 network
# (a single host usually owns a whole /64), IPv4 addresses are kept. Invalid value -> ''
def normalize_ip(ip):
    try:
        addr = ipaddress.ip_address((ip or '').strip())
    except ValueError:
        return ''
    if addr.version == 6:
        return str(ipaddress.ip_network('{}/64'.format(addr), strict=False).network_address)
    return str(addr)


# Pseudonymised IP address of a signer, specific to the petition (HMAC-SHA256)
def signature_ip_hash(petition, ip):
    value = '{}:{}'.format(petition.pk, normalize_ip(ip))
    secret = settings.SIGNATURE_IP_HMAC_KEY or settings.SECRET_KEY
    return salted_hmac('petition.signature.ip', value, secret=secret, algorithm='sha256').hexdigest()


# Get the user of the current session
def get_session_user(request):
    from .models import PytitionUser
    try:
        pytitionuser = PytitionUser.objects.get(user__username=request.user.username)
    except User.DoesNotExist:
        raise Http404(_("not found"))
    return pytitionuser

# Check if an user is in an organization
# FIXME : move this as an org method ?
def check_user_in_orga(user, orga):
    if orga not in user.organizations.all():
        return HttpResponseForbidden(_("You are not part of this organization"))
    return None


# Return a 404 if a petition does not exist
def petition_from_id(id):
    from .models import Petition
    petition = Petition.by_id(id)
    if petition is None:
        raise Http404(_("Petition does not exist"))
    else:
        return petition


# Check if a petition is publicly accessible
def check_petition_is_accessible(request, petition):
    if petition.published and not petition.moderated:
        return True
    if request.user.is_authenticated:
        user = get_session_user(request)
        if petition.owner_type == "user" and user == petition.owner:
            return True
        if petition.owner_type == "org" and user in petition.owner.members.all():
            return True
    if petition.moderated:
        raise Http404(_("This Petition has been moderated!"))
    if not petition.published:
        raise Http404(_("This Petition is not published yet!"))


# Get settings
def settings_context_processor(request):
    return {'settings': settings}

# Get footer content
def footer_content_processor(request):
    footer_content = None
    if settings.FOOTER_TEMPLATE:
        footer_content = render_to_string(settings.FOOTER_TEMPLATE)
    return {'footer_content': footer_content}

# Signed token giving access to the "manage my signature" page (no database field needed)
MANAGE_SALT = "petition.signature.manage"

def make_manage_token(signature):
    return signing.dumps({"s": signature.pk, "p": signature.petition_id}, salt=MANAGE_SALT)

def build_manage_url(request, signature):
    return request.build_absolute_uri(reverse("manage_signature", args=[make_manage_token(signature)]))

# Send Confirmation email
def send_confirmation_email(request, signature):
    petition = signature.petition
    url = request.build_absolute_uri(reverse("confirm", args=[petition.id, signature.confirmation_hash]))
    ctx = {'firstname': signature.first_name, 'url': url,
           'petition_title': strip_tags(petition.title),
           'petition_url': request.build_absolute_uri(petition.url),
           'creator_name': petition.owner_name,
           'manage_url': build_manage_url(request, signature),
           'days': settings.UNCONFIRMED_SIGNATURE_RETENTION_DAYS}
    html_message = render_to_string("petition/confirmation_email.html", ctx)
    message = strip_tags(html_message)
    with get_connection() as connection:
        msg = EmailMultiAlternatives(_("Confirm your signature to our petition"),
                           message, to=[signature.email], connection=connection,
                           reply_to=[petition.confirmation_email_reply])
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)

# Tell an existing signatory that someone tried to sign again with their address
def send_already_signed_email(request, signature):
    _send_signature_link_email(request, signature, "petition/already_signed_email.txt")

# Send a new link to the "manage my signature" page
def send_manage_link_email(request, signature):
    _send_signature_link_email(request, signature, "petition/manage_link_email.txt")

def _send_signature_link_email(request, signature, template):
    petition = signature.petition
    ctx = {'petition_title': strip_tags(petition.title), 'manage_url': build_manage_url(request, signature)}
    body = render_to_string(template, ctx)
    with get_connection() as connection:
        EmailMessage(_("Your signature on the petition"), body, to=[signature.email],
                     reply_to=[settings.DEFAULT_NOREPLY_MAIL], connection=connection).send(fail_silently=False)

# Send welcome mail on account creation
def send_welcome_mail(user_infos):
    html_message = render_to_string("registration/confirmation_email.html", user_infos)
    message = strip_tags(html_message)
    with get_connection() as connection:
        msg = EmailMultiAlternatives(_("Account created !"),
                                     message, to=[user_infos["email"]], connection=connection,
                                     reply_to=[settings.DEFAULT_NOREPLY_MAIL])
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)


# Send moderation mail to user
def send_moderation_mail(email, username, reason, element_type, element):
    html_message = render_to_string("admin/emails/moderation_email.html", {'username': username, 'reason': reason, 'element_type': element_type, 'element': element})
    message = strip_tags(html_message)
    with get_connection() as connection:
        msg = EmailMultiAlternatives(_("Moderation"),
                                     message, to=[email], connection=connection,
                                     reply_to=[settings.DEFAULT_NOREPLY_MAIL])
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)

# Send monitoring mail to user
def send_monitoring_mail(email, username, element_type, element, reason):
    html_message = render_to_string("admin/emails/monitoring_email.html", {'username': username, 'reason': reason, 'element_type': element_type, 'element': element,})
    message = strip_tags(html_message)
    with get_connection() as connection:
        msg = EmailMultiAlternatives(_("Strong monitoring"),
                                     message, to=[email], connection=connection,
                                     reply_to=[settings.DEFAULT_NOREPLY_MAIL])
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)        

# Send mail to moderation about moderation
def send_mail_to_moderation(moderation_email, username, reason, owner_type):
    html_message = render_to_string("admin/emails/email_to_moderation.html", {'username': username, 'reason': reason, 'owner_type': owner_type})
    message = strip_tags(html_message)
    with get_connection() as connection:
        msg = EmailMultiAlternatives(_("Moderation"),
                                     message, to=[moderation_email], connection=connection,
                                     reply_to=[settings.DEFAULT_NOREPLY_MAIL])
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)

# Send mail to moderation about monitoring
def send_mail_to_moderation_monitor(moderation_email, username, reason, owner_type, priority):
    html_message = render_to_string("admin/emails/email_to_moderation_monitor.html", {'username': username, 'reason': reason, 'owner_type': owner_type})
    message = strip_tags(html_message)
    with get_connection() as connection:
        msg = EmailMultiAlternatives(_("Strong monitoring"),
                                     message, to=[moderation_email], connection=connection,
                                     reply_to=[settings.DEFAULT_NOREPLY_MAIL])
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)        

# Send mail to moderation with information eg Akismet is down
def send_mail_to_moderation_info(moderation_email, info):
    html_message = render_to_string("admin/emails/email_to_moderation_info.html", {'info': info})
    message = strip_tags(html_message)
    with get_connection() as connection:
        msg = EmailMultiAlternatives(_("Information"),
                                     message, to=[moderation_email], connection=connection,
                                     reply_to=[settings.DEFAULT_NOREPLY_MAIL])
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)


# Generate a meta url for the HTML meta property
def petition_detail_meta(request, petition_id):
    url = "{scheme}://{host}{petition_path}".format(
        scheme=request.scheme,
        host=request.get_host(),
        petition_path=reverse('detail', args=[petition_id]))
    return {'site_url': request.get_host(), 'petition_url': url}


def subscribe_to_newsletter(petition, email):
    if petition.newsletter_subscribe_method in ["POST", "GET"]:
        if petition.newsletter_subscribe_http_url == '':
            return
        data = petition.newsletter_subscribe_http_data
        if data == '' or data is None:
            data = {}
        else:
            import json
            data = data.replace("'", "\"")
            data = json.loads(data)
        if petition.newsletter_subscribe_http_mailfield != '':
            data[petition.newsletter_subscribe_http_mailfield] = email
    # the newsletter is an external service: it must never break or block the signature
    try:
        if petition.newsletter_subscribe_method == "POST":
            requests.post(petition.newsletter_subscribe_http_url, data, timeout=NEWSLETTER_HTTP_TIMEOUT)
        elif petition.newsletter_subscribe_method == "GET":
            requests.get(petition.newsletter_subscribe_http_url, data, timeout=NEWSLETTER_HTTP_TIMEOUT)
    except requests.RequestException as e:
        logger.warning("Newsletter subscription failed for petition %s: %s", petition.pk, type(e).__name__)
    if petition.newsletter_subscribe_method == "MAIL":
        # explicit SMTP backend: the mail queue backend (USE_MAIL_QUEUE) would ignore the
        # SMTP server of the petition
        with get_connection(backend="django.core.mail.backends.smtp.EmailBackend", fail_silently=True,
                            timeout=NEWSLETTER_SMTP_TIMEOUT,
                            host=petition.newsletter_subscribe_mail_smtp_host,
                            port=petition.newsletter_subscribe_mail_smtp_port,
                            username=petition.newsletter_subscribe_mail_smtp_user,
                            password=petition.newsletter_subscribe_mail_smtp_password,
                            use_ssl=petition.newsletter_subscribe_mail_smtp_tls,
                            use_tls=petition.newsletter_subscribe_mail_smtp_starttls) as connection:
            EmailMessage(petition.newsletter_subscribe_mail_subject.format(email), "",
                         petition.newsletter_subscribe_mail_from, [petition.newsletter_subscribe_mail_to],
                         connection=connection).send(fail_silently=True)

def get_update_form(user, data=None):
    from .forms import UpdateInfoForm
    if not data:
        _data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        }
    else:
        _data = data
    return UpdateInfoForm(user, _data)
