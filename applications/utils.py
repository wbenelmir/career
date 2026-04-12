import base64
from io import BytesIO

import qrcode
from django.urls import reverse


def build_tracking_url(request, tracking_code: str) -> str:
    relative_url = reverse(
        "tracking:tracking_result_direct",
        kwargs={"tracking_code": tracking_code}
    )
    return request.build_absolute_uri(relative_url)


def generate_qr_png_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_qr_base64(data: str) -> str:
    return base64.b64encode(generate_qr_png_bytes(data)).decode("utf-8")