"""Content-Security-Policy header with a per-request nonce (framapetitions: S13/GD-15).

The policy comes from ``settings.CSP_DIRECTIVES``; the ``{nonce}`` source is replaced by the
nonce of the request, which templates read as ``{{ request.csp_nonce }}``.
``settings.CSP_REPORT_ONLY`` sends the policy in report-only mode (nothing is blocked).
"""
import secrets

from django.conf import settings

NONCE_PLACEHOLDER = "{nonce}"


def build_policy(directives, nonce):
    parts = []
    for name, sources in directives.items():
        sources = ["'nonce-%s'" % nonce if source == NONCE_PLACEHOLDER else source for source in sources]
        parts.append(" ".join([name] + sources))
    return "; ".join(parts)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)
        directives = getattr(settings, "CSP_DIRECTIVES", None)
        if directives:
            header = "Content-Security-Policy"
            if getattr(settings, "CSP_REPORT_ONLY", False):
                header += "-Report-Only"
            # a view may set its own policy
            if not response.has_header(header):
                response[header] = build_policy(directives, request.csp_nonce)
        return response
