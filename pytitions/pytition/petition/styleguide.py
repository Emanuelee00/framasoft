"""Design system reference page (DS-05), served only when DEBUG is True."""
import re
from pathlib import Path

from django import forms
from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render


class StyleguideForm(forms.Form):
    name = forms.CharField(label="Full name", help_text="As you want it to appear to the author.")
    email = forms.EmailField(label="Email address")
    phone = forms.CharField(label="Phone number", required=False)
    reason = forms.ChoiceField(label="Reason", choices=[("spam", "Spam"), ("hate", "Hateful content")])
    message = forms.CharField(label="Message", widget=forms.Textarea, required=False)
    consent = forms.BooleanField(label="I agree to the privacy notice", help_text="Required to sign.")


TOKENS = Path(__file__).resolve().parent / "static" / "css" / "fp-tokens.css"


def _luminance(hex_color):
    channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b):
    la, lb = sorted([_luminance(a), _luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def colour_tokens():
    """(name, hex, ratio against white) for every colour token, in file order"""
    found = re.findall(r"--(fp-[\w-]+):\s*(#[0-9a-fA-F]{6})", TOKENS.read_text())
    return [(name, value, round(contrast(value, "#ffffff"), 2)) for name, value in found]


def styleguide(request):
    if not settings.DEBUG:
        raise Http404
    form = StyleguideForm(data={"name": "Camille", "email": "not-an-email", "reason": "spam"})
    form.is_valid()
    context = {
        "colours": colour_tokens(),
        "form": form,
        "page": Paginator(range(200), 10).page(5),
        "sample_petition": {
            "title": "Keep the village library open on Saturdays",
            "text": "The municipal library is the only free public place where families, students and retired people "
                    "can meet. We ask the town council to keep it open on Saturday mornings.",
            "owner": "Friends of the library",
            "url": "#",
            "twitter_image": "",
            "signature_number": 1284,
            "target": 2000,
        },
    }
    return render(request, "petition/styleguide.html", context)
