import io
import os

from django.conf import settings

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from applications.pdf_utils import (
    register_arabic_font,
    rtl_text,
    ARABIC_FONT_NAME,
)

from applications.utils import (
    generate_qr_png_bytes,
)


def build_interview_summons_pdf(
    application,
    interview_schedule,
    tracking_url,
):

    register_arabic_font()

    buffer = io.BytesIO()

    p = canvas.Canvas(
        buffer,
        pagesize=A4
    )

    width, height = A4

    green = (0.11, 0.64, 0.51)

    light_green = (0.97, 0.99, 0.98)

    border = (0.84, 0.90, 0.87)

    text_gray = (0.35, 0.35, 0.35)

    def set_stroke_rgb(color_tuple):
        p.setStrokeColorRGB(*color_tuple)

    def set_fill_rgb(color_tuple):
        p.setFillColorRGB(*color_tuple)

    def draw_rtl_right(
        text,
        x,
        y,
        font_size=12,
        color=(0, 0, 0)
    ):

        p.setFont(
            ARABIC_FONT_NAME,
            font_size
        )

        p.setFillColorRGB(*color)

        p.drawRightString(
            x,
            y,
            rtl_text(text)
        )

    def draw_ltr_left(
        text,
        x,
        y,
        font_size=11,
        color=(0, 0, 0)
    ):

        p.setFont(
            "Helvetica",
            font_size
        )

        p.setFillColorRGB(*color)

        p.drawString(
            x,
            y,
            str(text or "")
        )

    def draw_field_box(
        y_top,
        label,
        value,
        box_height=52
    ):

        p.setLineWidth(1)

        set_stroke_rgb(border)

        set_fill_rgb(light_green)

        p.roundRect(
            45,
            y_top - box_height,
            width - 90,
            box_height,
            10,
            stroke=1,
            fill=1
        )

        draw_rtl_right(
            label,
            width - 60,
            y_top - 16,
            font_size=10,
            color=text_gray
        )

        value_str = str(value or "")

        is_ltr_like = any(
            ch.isascii()
            and (
                ch.isalpha()
                or ch.isdigit()
            )
            for ch in value_str
        )

        if is_ltr_like:

            draw_ltr_left(
                value_str,
                65,
                y_top - 34,
                font_size=13,
            )

        else:

            draw_rtl_right(
                value_str,
                width - 60,
                y_top - 34,
                font_size=13,
            )

    set_stroke_rgb(border)

    p.setLineWidth(1)

    p.roundRect(
        30,
        30,
        width - 60,
        height - 60,
        18,
        stroke=1,
        fill=0
    )

    header_x = 30

    header_y = height - 95

    header_w = width - 60

    header_h = 65

    radius = 18

    p.setFillColorRGB(*green)

    p.rect(
        header_x,
        header_y,
        header_w,
        header_h - radius,
        stroke=0,
        fill=1
    )

    p.rect(
        header_x + radius,
        header_y + header_h - radius,
        header_w - (2 * radius),
        radius,
        stroke=0,
        fill=1
    )

    p.circle(
        header_x + radius,
        header_y + header_h - radius,
        radius,
        stroke=0,
        fill=1
    )

    p.circle(
        header_x + header_w - radius,
        header_y + header_h - radius,
        radius,
        stroke=0,
        fill=1
    )

    logo_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "assets",
        "images",
        "favicon.png"
    )

    if os.path.exists(logo_path):

        p.drawImage(
            logo_path,
            header_x + 18,
            header_y + 12,
            width=36,
            height=36,
            mask="auto"
        )

    draw_rtl_right(
        "استدعاء للمقابلة",
        header_x + header_w - 35,
        header_y + 40,
        font_size=20,
        color=(1, 1, 1)
    )

    draw_rtl_right(
        "إشعار رسمي متعلق بالمقابلة",
        header_x + header_w - 35,
        header_y + 18,
        font_size=10,
        color=(0.92, 0.98, 0.96)
    )

    y = height - 125

    draw_rtl_right(
        (
            "يرجى الحضور في الموعد المحدد "
            "والاحتفاظ بهذا الاستدعاء."
        ),
        width - 55,
        y,
        font_size=10,
        color=text_gray
    )

    y -= 28

    fields = [

        (
            "رقم الطلب",
            application.application_number
        ),

        (
            "رمز التتبع",
            application.tracking_code
        ),

        (
            "المنصب",
            application.poste.title
            if application.poste
            else ""
        ),

        (
            "المترشح",
            (
                application.candidate.full_name
                if application.candidate
                else ""
            )
        ),

        (
            "تاريخ المقابلة",
            interview_schedule.interview_date.strftime(
                "%Y-%m-%d"
            )
        ),

        (
            "وقت المقابلة",
            interview_schedule.interview_time.strftime(
                "%H:%M"
            )
        ),

        (
            "مكان المقابلة",
            interview_schedule.location
        ),
    ]

    for label, value in fields:

        draw_field_box(
            y,
            label,
            value
        )

        y -= 62

    if interview_schedule.note:

        draw_field_box(
            y,
            "ملاحظات",
            interview_schedule.note,
            box_height=75,
        )

        y -= 85

    qr_bytes = generate_qr_png_bytes(
        tracking_url
    )

    qr_image = ImageReader(
        io.BytesIO(qr_bytes)
    )

    qr_size = 92

    qr_x = width - 155

    qr_y = 95

    p.drawImage(
        qr_image,
        qr_x,
        qr_y,
        width=qr_size,
        height=qr_size,
        preserveAspectRatio=True,
        mask="auto"
    )

    draw_rtl_right(
        "متابعة الطلب",
        qr_x - 20,
        qr_y + 75,
        font_size=12,
        color=green
    )

    draw_rtl_right(
        "يمكنكم مسح رمز QR لمتابعة الطلب.",
        qr_x - 20,
        qr_y + 52,
        font_size=10,
        color=text_gray
    )

    p.setLineWidth(0.7)

    set_stroke_rgb(border)

    p.line(
        50,
        65,
        width - 50,
        65
    )

    p.setFont(
        ARABIC_FONT_NAME,
        9
    )

    p.setFillColorRGB(*text_gray)

    p.drawCentredString(
        width / 2,
        48,
        rtl_text(
            "منصة الترشح - وزارة اقتصاد المعرفة "
            "والمؤسسات الناشئة والمؤسسات المصغرة"
        )
    )

    p.showPage()

    p.save()

    pdf = buffer.getvalue()

    buffer.close()

    return pdf