#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate the five-page Turkish PerforaAR THY3 summary."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "PerforaAR_Teknik_Raporu_TR.pdf"

PAGE_W, PAGE_H = landscape(A4)
MARGIN = 50
CONTENT_W = PAGE_W - 2 * MARGIN

BLACK = HexColor("#111111")
YELLOW = HexColor("#F5C518")
GOLD = HexColor("#C99A00")
PALE = HexColor("#FFF5C8")
PAPER = HexColor("#FAF9F4")
GREY = HexColor("#66645F")
LIGHT = HexColor("#EEECE5")
LINE = HexColor("#D4D0C5")

BODY = 12
LEADING = 18


def register_fonts() -> None:
    """Use a Turkish-capable Times New Roman compatible serif family."""
    font_root = Path(
        "/opt/codex/runtimes/codex-primary-runtime/dependencies/native/"
        "libreoffice-headless/libreoffice/share/fonts/truetype"
    )
    pdfmetrics.registerFont(TTFont("TNR", str(font_root / "LiberationSerif-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-Bold", str(font_root / "LiberationSerif-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("TNR-Italic", str(font_root / "LiberationSerif-Italic.ttf")))


def wrap(text: str, width: float, font: str, size: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if pdfmetrics.stringWidth(candidate, font, size) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def text(
    c: canvas.Canvas,
    value: str,
    x: float,
    y: float,
    width: float,
    *,
    font: str = "TNR",
    size: float = BODY,
    leading: float = LEADING,
    color: Color = BLACK,
    max_lines: int | None = None,
    align: str = "left",
) -> float:
    lines = wrap(value, width, font, size)
    if max_lines is not None:
        lines = lines[:max_lines]
    c.setFont(font, size)
    c.setFillColor(color)
    for line in lines:
        if align == "center":
            c.drawCentredString(x + width / 2, y, line)
        elif align == "right":
            c.drawRightString(x + width, y, line)
        else:
            c.drawString(x, y, line)
        y -= leading
    return y


def panel(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: Color = white,
    stroke: Color = LINE,
    radius: float = 8,
) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def header(c: canvas.Canvas, page: int, section: str) -> None:
    c.setFillColor(BLACK)
    c.rect(0, PAGE_H - 35, PAGE_W, 35, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.rect(MARGIN, PAGE_H - 35, 122, 35, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 13)
    c.drawCentredString(MARGIN + 61, PAGE_H - 24, "PERFORAAR")
    c.setFillColor(white)
    c.setFont("TNR", 11)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 23, section)

    c.setStrokeColor(BLACK)
    c.line(MARGIN, 31, PAGE_W - MARGIN, 31)
    c.setFillColor(GREY)
    c.setFont("TNR", 9)
    c.drawString(MARGIN, 18, "THY3 araştırma prototipi. Klinik kullanım için değildir.")
    c.drawRightString(PAGE_W - MARGIN, 18, str(page))


def title(c: canvas.Canvas, heading: str, subtitle: str | None = None) -> float:
    y = PAGE_H - 72
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 25)
    c.drawString(MARGIN, y, heading)
    c.setFillColor(YELLOW)
    c.rect(MARGIN, y - 13, 86, 5, fill=1, stroke=0)
    y -= 39
    if subtitle:
        y = text(c, subtitle, MARGIN, y, CONTENT_W, font="TNR-Italic", color=GREY)
        y -= 7
    return y


def new_page(c: canvas.Canvas, page: int, section: str, heading: str, subtitle: str | None = None) -> float:
    if page > 1:
        c.showPage()
    header(c, page, section)
    return title(c, heading, subtitle)


def label(c: canvas.Canvas, value: str, x: float, y: float, width: float) -> None:
    c.setFillColor(YELLOW)
    c.rect(x, y - 5, width, 25, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 12)
    c.drawString(x + 10, y + 2, value.upper())


def image_fit(
    c: canvas.Canvas,
    path: Path,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    background: Color = white,
    border: bool = True,
    pad: float = 4,
) -> None:
    c.setFillColor(background)
    c.rect(x, y, w, h, fill=1, stroke=0)
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min((w - 2 * pad) / iw, (h - 2 * pad) / ih)
    dw, dh = iw * scale, ih * scale
    c.drawImage(
        ImageReader(str(path)),
        x + (w - dw) / 2,
        y + (h - dh) / 2,
        width=dw,
        height=dh,
        preserveAspectRatio=True,
        mask="auto",
    )
    if border:
        c.setStrokeColor(LINE)
        c.rect(x, y, w, h, fill=0, stroke=1)


def simple_step(
    c: canvas.Canvas,
    number: str,
    heading: str,
    explanation: str,
    x: float,
    y: float,
    w: float,
    h: float,
) -> None:
    panel(c, x, y, w, h, fill=white, stroke=BLACK)
    c.setFillColor(BLACK)
    c.rect(x, y + h - 34, w, 34, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 13)
    c.drawString(x + 12, y + h - 23, number)
    c.setFillColor(white)
    c.drawString(x + 45, y + h - 23, heading)
    text(c, explanation, x + 12, y + h - 55, w - 24, size=11, leading=16.5, max_lines=4)


def result_card(c: canvas.Canvas, value: str, note: str, x: float, y: float, w: float) -> None:
    panel(c, x, y, w, 78, fill=BLACK, stroke=BLACK)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 20)
    c.drawString(x + 15, y + 45, value)
    text(c, note, x + 15, y + 24, w - 30, size=10.5, leading=15.75, color=white, max_lines=2)


def build_report() -> None:
    register_fonts()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("PerforaAR THY3 Teknik Özeti")
    c.setAuthor("Eyasu Desalegne Beyene")
    c.setCreator("PerforaAR")
    c.setSubject("İzlenen ultrason görüntülerinden 3B rekonstrüksiyon")

    dryad = ROOT / "results" / "dryad_thy3" / "figures"
    tus = ROOT / "results" / "tus_rec2024" / "figures"
    ar = ROOT / "results" / "tus_rec2024" / "ar_exports"

    # Page 1: Cover
    c.setFillColor(BLACK)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.rect(0, 0, 18, PAGE_H, fill=1, stroke=0)
    c.rect(55, PAGE_H - 78, 175, 34, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 15)
    c.drawCentredString(142.5, PAGE_H - 66, "PERFORAAR")

    c.setFillColor(white)
    c.setFont("TNR-Bold", 34)
    c.drawString(55, PAGE_H - 139, "THY3 Teknik Özeti")
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 24)
    c.drawString(55, PAGE_H - 180, "2B görüntülerden 3B haritaya")
    text(
        c,
        "Amaç, ultrason probu hareket ederken alınan görüntüleri birleştirmek ve oluşan üç boyutlu haritayı artırılmış gerçeklik gözlüğünde gösterebilmektir.",
        55,
        PAGE_H - 218,
        700,
        color=white,
        max_lines=3,
    )
    image_fit(c, ar / "surface_gallery.png", 55, 116, 730, 222, background=BLACK, border=False, pad=0)
    c.setStrokeColor(YELLOW)
    c.setLineWidth(1.2)
    c.rect(55, 116, 730, 222, fill=0, stroke=1)

    panel(c, 55, 55, 730, 42, fill=YELLOW, stroke=YELLOW)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 12)
    c.drawCentredString(PAGE_W / 2, 71, "Bugünkü durum: Yazılım prototipi çalışıyor. Gerçek renkli Doppler fantom testi sıradaki adımdır.")
    c.setFillColor(white)
    c.setFont("TNR", 10)
    c.drawString(55, 32, "Eyasu Desalegne Beyene")
    c.drawRightString(PAGE_W - 55, 32, "Eylül 2026")

    # Page 2: The idea
    y = new_page(c, 2, "Fikir", "PerforaAR ne yapar", "Ultrason kesitlerini aynı yerde birleştirerek üç boyutlu bir harita oluşturur.")
    text(
        c,
        "Ultrason cihazı bir anda yalnızca ince bir görüntü kesiti gösterir. Prob hareket ettikçe yeni kesitler gelir. Probun nerede olduğunu bilirsek bu kesitleri doğru yerlerine koyabilir ve bir hacim oluşturabiliriz.",
        MARGIN,
        y,
        CONTENT_W,
        max_lines=4,
    )
    step_y = 275
    step_w = 170
    gap = 22
    steps = [
        ("01", "Görüntü", "Prob her konumda bir ultrason görüntüsü alır."),
        ("02", "Takip", "Optik izleyici probun ve bacağın yerini ölçer."),
        ("03", "Birleştirme", "Yazılım görüntüleri doğru konumlarda üst üste koyar."),
        ("04", "3B sonuç", "Hacim ve yüzey modeli inceleme için hazır olur."),
    ]
    for idx, args in enumerate(steps):
        simple_step(c, *args, MARGIN + idx * (step_w + gap), step_y, step_w, 125)

    panel(c, MARGIN, 68, 450, 170, fill=PALE, stroke=GOLD)
    label(c, "Neden bacak da izlenir", MARGIN + 18, 204, 205)
    text(
        c,
        "Bacak hareket ederse yalnızca probu takip etmek yeterli olmaz. Bu nedenle bir hedef probda, ikinci hedef bacakta bulunur. Yazılım böylece haritayı bacakla birlikte hareket ettirebilir.",
        MARGIN + 18,
        169,
        414,
        max_lines=5,
    )
    image_fit(c, ar / "050__RH_Per_S_DtP__full_20fps__surface_preview.png", 520, 68, 271, 170, background=BLACK, border=True, pad=0)

    # Page 3: Dryad
    y = new_page(c, 3, "Birinci test", "Dryad renkli Doppler testi", "Soru şuydu: Yazılım, ayrı kesitleri tekrar doğru bir hacim halinde birleştirebiliyor mu?")
    panel(c, MARGIN, 334, 260, 126, fill=PALE, stroke=GOLD)
    label(c, "Ne yaptık", MARGIN + 18, 426, 110)
    text(
        c,
        "Hazır bir 3B renkli Doppler hacmini ince kesitlere ayırdık. Sonra bu kesitleri PerforaAR ile yeniden birleştirdik.",
        MARGIN + 18,
        392,
        224,
        max_lines=5,
    )
    panel(c, 327, 334, 464, 126, fill=white)
    label(c, "Sonuç", 345, 426, 100)
    text(
        c,
        "Tam veri kullanıldığında aynı hacim yeniden oluştu. Daha az kesit kullanıldığında ana damar yapısı ve akış yönü büyük ölçüde korundu.",
        345,
        392,
        428,
        max_lines=5,
    )
    image_fit(c, dryad / "awake_sparse_reconstruction.png", MARGIN, 105, 500, 205, pad=1)
    result_card(c, "0,85 Dice", "Seyrek kesitlerle damar yapısı benzerliği", 570, 232, 221)
    result_card(c, "%98 üzeri", "Akış yönü uyumu", 570, 140, 221)
    c.setFillColor(BLACK)
    c.setFont("TNR-Italic", 10.5)
    text(
        c,
        "Önemli sınır: Bu gerçek bir ultrason taraması değildir. Var olan üç boyutlu hacimden üretilmiş sanal kesitlerle yapılan yazılım testidir.",
        MARGIN,
        79,
        CONTENT_W,
        font="TNR-Italic",
        size=10.5,
        leading=15.75,
        color=GREY,
        max_lines=2,
    )

    # Page 4: TUS
    y = new_page(c, 4, "İkinci test", "TUS izlenen ultrason testi", "Bu kez gerçek iki boyutlu ultrason kareleri ve ölçülmüş prob konumları kullanıldı.")
    panel(c, MARGIN, 362, CONTENT_W, 96, fill=PALE, stroke=GOLD)
    text(
        c,
        "Yazılım gerçek kareleri konum bilgisiyle birleştirdi. Altı ayrı taramadan altı hacim ve altı üç boyutlu yüzey modeli üretildi. Ayrıca kare kaybı, gecikme ve takip gürültüsü gibi bozulmalar denendi.",
        MARGIN + 18,
        423,
        CONTENT_W - 36,
        max_lines=4,
    )

    tile_w = 235
    gap = 21
    tile_y = 145
    image_fit(c, tus / "050__RH_Per_S_DtP__slices.png", MARGIN, tile_y, tile_w, 185, pad=2)
    image_fit(c, tus / "050__RH_Per_S_DtP__trajectory.png", MARGIN + tile_w + gap, tile_y, tile_w, 185, pad=2)
    image_fit(c, ar / "050__RH_Per_S_DtP__full_20fps__surface_preview.png", MARGIN + 2 * (tile_w + gap), tile_y, tile_w, 185, background=BLACK, pad=0)
    captions = ["Oluşan hacmin kesitleri", "Probun izlenen hareketi", "Dışa aktarılan 3B nesne"]
    for idx, caption in enumerate(captions):
        c.setFillColor(BLACK)
        c.setFont("TNR-Bold", 11)
        c.drawCentredString(MARGIN + idx * (tile_w + gap) + tile_w / 2, 124, caption)

    panel(c, MARGIN, 63, CONTENT_W, 42, fill=BLACK, stroke=BLACK)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 11.5)
    c.drawCentredString(PAGE_W / 2, 79, "Bu veri B mod ultrasondur. Renkli Doppler damar modeli değildir. Test, izlenen rekonstrüksiyon zincirini gösterir.")

    # Page 5: What exists and next step
    y = new_page(c, 5, "Durum", "Bugün ne var, sırada ne var", "THY3 düzeyinde amaç, fikrin yalnızca kâğıt üzerinde olmadığını göstermektir.")
    panel(c, MARGIN, 250, 350, 208, fill=white, stroke=BLACK)
    label(c, "Bugün hazır", MARGIN + 18, 424, 125)
    ready = [
        "İzlenen görüntülerden hacim oluşturan yazılım",
        "Kesitleri ve 3B yüzeyi gösteren araştırma arayüzü",
        "Gözlük uygulamasına aktarılabilen GLB yüzeyi ve sahne bilgisi",
        "Dryad ve TUS verileriyle yapılmış iki teknik test",
    ]
    ry = 382
    for idx, item in enumerate(ready, 1):
        c.setFillColor(BLACK)
        c.roundRect(MARGIN + 18, ry - 18, 28, 24, 4, fill=1, stroke=0)
        c.setFillColor(YELLOW)
        c.setFont("TNR-Bold", 11)
        c.drawCentredString(MARGIN + 32, ry - 10, str(idx))
        text(c, item, MARGIN + 58, ry, 270, size=11, leading=16.5, max_lines=2)
        ry -= 39

    panel(c, 420, 250, 371, 208, fill=PALE, stroke=GOLD)
    label(c, "Sıradaki gerçek deney", 438, 424, 190)
    text(
        c,
        "Bilinen damar kanallarına sahip bir akış fantomu kullanılacak. Renkli Doppler görüntüleri alınırken prob ve fantom aynı anda izlenecek. Oluşan 3B damar haritası gerçek kanal geometrisiyle karşılaştırılacak.",
        438,
        387,
        335,
        max_lines=7,
    )
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 12)
    c.drawString(438, 291, "Ölçülecek üç şey")
    text(c, "Konum hatası, yüzey hatası ve gecikme", 438, 269, 335, size=11.5, leading=17.25)

    c.setStrokeColor(GOLD)
    c.setLineWidth(2.2)
    c.line(135, 190, 705, 190)
    phase_x = [135, 325, 515, 705]
    phases = ["Yazılım", "Kamu verisi", "Fantom", "Gözlük"]
    states = ["Hazır", "Test edildi", "Sıradaki", "Sonraki"]
    for x, phase, state in zip(phase_x, phases, states, strict=True):
        c.setFillColor(BLACK)
        c.circle(x, 190, 17, fill=1, stroke=0)
        c.setFillColor(YELLOW)
        c.circle(x, 190, 6, fill=1, stroke=0)
        c.setFillColor(BLACK)
        c.setFont("TNR-Bold", 12)
        c.drawCentredString(x, 157, phase)
        c.setFillColor(GREY)
        c.setFont("TNR", 10.5)
        c.drawCentredString(x, 140, state)

    panel(c, MARGIN, 58, CONTENT_W, 58, fill=BLACK, stroke=BLACK)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 12)
    c.drawCentredString(
        PAGE_W / 2,
        88,
        "THY3 mesajı: Fikir tanımlandı, prototip üretildi, iki veri setiyle denendi ve gerçek fantom testi planlandı.",
    )
    c.setFillColor(white)
    c.setFont("TNR", 10.5)
    c.drawCentredString(PAGE_W / 2, 72, "Bu aşamada klinik doğruluk iddiası yoktur.")

    c.save()
    print(OUT)


if __name__ == "__main__":
    build_report()
