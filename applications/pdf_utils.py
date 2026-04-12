import os

import arabic_reshaper
from bidi.algorithm import get_display
from django.conf import settings
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


ARABIC_FONT_NAME = "AmiriArabic"


def register_arabic_font():
    font_path = os.path.join(settings.BASE_DIR, "static", "fonts", "janna.ttf")

    if ARABIC_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(ARABIC_FONT_NAME, font_path))


def rtl_text(text):
    if text is None:
        return ""
    text = str(text)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)