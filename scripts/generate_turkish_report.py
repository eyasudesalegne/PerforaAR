#!/usr/bin/env python3
# ruff: noqa: E501
"""Generate the Turkish PerforaAR technical and visual report."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
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
MARGIN_X = 42
TOP_Y = PAGE_H - 42
BOTTOM_Y = 38

NAVY = HexColor("#0B1F33")
INK = HexColor("#172B3A")
TEAL = HexColor("#149D9A")
TEAL_DARK = HexColor("#0C6E70")
CYAN = HexColor("#57C4C2")
ORANGE = HexColor("#E77745")
GREEN = HexColor("#2D8A66")
RED = HexColor("#B94A48")
MID = HexColor("#526777")
LIGHT = HexColor("#F3F6F8")
PALE_TEAL = HexColor("#E7F5F4")
PALE_ORANGE = HexColor("#FFF0E8")
LINE = HexColor("#D8E1E7")


def register_fonts() -> None:
    font_root = Path(
        "/opt/codex/runtimes/codex-primary-runtime/dependencies/native/"
        "libreoffice-headless/libreoffice/share/fonts/truetype"
    )
    pdfmetrics.registerFont(TTFont("DV", str(font_root / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DV-Bold", str(font_root / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DV-Oblique", str(font_root / "DejaVuSans-Oblique.ttf")))
    pdfmetrics.registerFont(
        TTFont("DV-Condensed", str(font_root / "DejaVuSansCondensed.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("DV-Condensed-Bold", str(font_root / "DejaVuSansCondensed-Bold.ttf"))
    )


def fit_lines(text: str, width: float, font: str, size: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
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


def draw_text(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    font: str = "DV",
    size: float = 9.2,
    leading: float | None = None,
    color: Color = INK,
    max_lines: int | None = None,
) -> float:
    leading = leading or size * 1.38
    lines = fit_lines(text, width, font, size)
    if max_lines is not None:
        lines = lines[:max_lines]
    c.setFont(font, size)
    c.setFillColor(color)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def draw_bullets(
    c: canvas.Canvas,
    items: Iterable[str],
    x: float,
    y: float,
    width: float,
    *,
    size: float = 8.9,
    gap: float = 5,
) -> float:
    for item in items:
        c.setFillColor(TEAL)
        c.circle(x + 3, y - 3, 2.2, fill=1, stroke=0)
        y = draw_text(c, item, x + 14, y, width - 14, size=size, leading=size * 1.35)
        y -= gap
    return y


def rounded_box(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: Color = LIGHT,
    stroke: Color = LINE,
    radius: float = 9,
) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def page_header(c: canvas.Canvas, page: int, section: str) -> None:
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 29, PAGE_W, 29, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("DV-Bold", 9.2)
    c.drawString(MARGIN_X, PAGE_H - 19, "PerforaAR")
    c.setFont("DV", 8.2)
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 19, section)
    c.setStrokeColor(LINE)
    c.line(MARGIN_X, 28, PAGE_W - MARGIN_X, 28)
    c.setFillColor(MID)
    c.setFont("DV", 6.8)
    c.drawString(MARGIN_X, 16, "Araştırma prototipi - klinik kullanım için değildir")
    c.drawCentredString(PAGE_W / 2, 16, "github.com/eyasudesalegne/PerforaAR")
    c.drawRightString(PAGE_W - MARGIN_X, 16, f"{page:02d}")


def page_title(c: canvas.Canvas, title: str, subtitle: str | None = None) -> float:
    y = PAGE_H - 57
    c.setFont("DV-Bold", 20)
    c.setFillColor(NAVY)
    c.drawString(MARGIN_X, y, title)
    y -= 20
    if subtitle:
        c.setFont("DV", 8.6)
        c.setFillColor(MID)
        c.drawString(MARGIN_X, y, subtitle)
        y -= 11
    c.setFillColor(TEAL)
    c.rect(MARGIN_X, y, 72, 3, fill=1, stroke=0)
    return y - 18


def metric_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    value: str,
    label: str,
    *,
    accent: Color = TEAL,
) -> None:
    rounded_box(c, x, y, w, h, fill=white)
    c.setFillColor(accent)
    c.rect(x, y, 5, h, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("DV-Bold", 18)
    c.drawString(x + 17, y + h - 27, value)
    draw_text(c, label, x + 17, y + h - 43, w - 27, size=7.3, color=MID)


def draw_image_fit(
    c: canvas.Canvas,
    path: Path,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    background: Color = white,
    border: bool = True,
    pad: float = 5,
) -> None:
    c.setFillColor(background)
    c.rect(x, y, w, h, fill=1, stroke=0)
    with Image.open(path) as im:
        iw, ih = im.size
    scale = min((w - 2 * pad) / iw, (h - 2 * pad) / ih)
    dw, dh = iw * scale, ih * scale
    dx, dy = x + (w - dw) / 2, y + (h - dh) / 2
    c.drawImage(
        ImageReader(str(path)),
        dx,
        dy,
        width=dw,
        height=dh,
        preserveAspectRatio=True,
        mask="auto",
    )
    if border:
        c.setStrokeColor(LINE)
        c.setLineWidth(0.7)
        c.rect(x, y, w, h, fill=0, stroke=1)


def image_tile(
    c: canvas.Canvas,
    path: Path,
    x: float,
    y: float,
    w: float,
    h: float,
    caption: str,
    *,
    caption_h: float = 22,
    background: Color = white,
    caption_color: Color = NAVY,
) -> None:
    rounded_box(c, x, y, w, h, fill=background, radius=7)
    draw_image_fit(
        c,
        path,
        x + 3,
        y + caption_h,
        w - 6,
        h - caption_h - 3,
        border=False,
        background=background,
    )
    c.setFillColor(caption_color)
    c.setFont("DV-Condensed-Bold", 7.2)
    c.drawCentredString(x + w / 2, y + 8, caption)


def section_label(c: canvas.Canvas, text: str, x: float, y: float) -> None:
    c.setFillColor(TEAL_DARK)
    c.setFont("DV-Bold", 9.4)
    c.drawString(x, y, text.upper())


def simple_table(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    col_widths: Sequence[float],
    rows: Sequence[Sequence[str]],
    *,
    header: bool = True,
    row_h: float = 24,
    font_size: float = 7.5,
) -> float:
    y = y_top
    total_w = sum(col_widths)
    for ridx, row in enumerate(rows):
        y -= row_h
        if header and ridx == 0:
            fill = NAVY
            text_color = white
            font = "DV-Bold"
        else:
            fill = white if ridx % 2 else LIGHT
            text_color = INK
            font = "DV"
        c.setFillColor(fill)
        c.rect(x, y, total_w, row_h, fill=1, stroke=0)
        xpos = x
        for value, width in zip(row, col_widths, strict=True):
            c.setStrokeColor(LINE)
            c.rect(xpos, y, width, row_h, fill=0, stroke=1)
            lines = fit_lines(str(value), width - 10, font, font_size)[:2]
            c.setFillColor(text_color)
            c.setFont(font, font_size)
            ty = y + row_h - 9
            for line in lines:
                c.drawString(xpos + 5, ty, line)
                ty -= font_size + 2
            xpos += width
    return y


def arrow(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float) -> None:
    c.setStrokeColor(TEAL_DARK)
    c.setFillColor(TEAL_DARK)
    c.setLineWidth(1.5)
    c.line(x1, y1, x2, y2)
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        c.line(x2, y2, x2 - 7 * direction, y2 + 4)
        c.line(x2, y2, x2 - 7 * direction, y2 - 4)
    else:
        direction = 1 if y2 > y1 else -1
        c.line(x2, y2, x2 - 4, y2 - 7 * direction)
        c.line(x2, y2, x2 + 4, y2 - 7 * direction)


def new_page(c: canvas.Canvas, page: int, section: str, title: str, subtitle: str | None = None) -> float:
    if page > 1:
        c.showPage()
    page_header(c, page, section)
    return page_title(c, title, subtitle)


def scan_caption(code: str) -> str:
    return code.replace("__", " / ").replace("_", " ")


def load_scene_metadata() -> list[dict]:
    scene_dir = ROOT / "results" / "tus_rec2024" / "ar_exports"
    output = []
    for path in sorted(scene_dir.glob("*__ar_scene.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["stem"] = path.name.replace("__ar_scene.json", "")
        output.append(data)
    return output


def build_report() -> None:
    register_fonts()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("PerforaAR - 3B Rekonstrüksiyon ve AR Görselleştirme Teknik Raporu")
    c.setAuthor("Eyasu Desalegne Beyene")
    c.setCreator("PerforaAR Teknik Dokümantasyon")
    c.setSubject("PerforaAR yazılımı, doğrulama deneyleri ve 3B görselleştirme çıktıları")

    dryad_dir = ROOT / "results" / "dryad_thy3" / "figures"
    tus_dir = ROOT / "results" / "tus_rec2024" / "figures"
    ar_dir = ROOT / "results" / "tus_rec2024" / "ar_exports"
    scenes = load_scene_metadata()

    scan_codes = [
        "050__RH_Per_S_DtP",
        "050__RH_Per_S_PtD",
        "051__LH_Par_C_DtP",
        "051__LH_Par_C_PtD",
        "052__RH_Par_L_DtP",
        "052__RH_Par_L_PtD",
    ]

    # 1 - Cover
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, 0, 14, PAGE_H, fill=1, stroke=0)
    c.setFillColor(CYAN)
    c.circle(87, PAGE_H - 82, 26, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("DV-Bold", 24)
    c.drawCentredString(87, PAGE_H - 91, "P")
    c.setFillColor(white)
    c.setFont("DV-Bold", 13)
    c.drawString(126, PAGE_H - 70, "PERFORAAR")
    c.setFont("DV", 7.8)
    c.setFillColor(HexColor("#9EB4C5"))
    c.drawString(126, PAGE_H - 84, "ARAŞTIRMA PROTOTİPİ / TEKNİK RAPOR")
    c.setFillColor(white)
    c.setFont("DV-Bold", 29)
    c.drawString(54, PAGE_H - 153, "İzlenen 2B Ultrason Verilerinden")
    c.drawString(54, PAGE_H - 190, "3B Rekonstrüksiyon ve AR Görselleştirme")
    c.setFont("DV", 11)
    c.setFillColor(HexColor("#C8D6DF"))
    draw_text(
        c,
        "Yazılım mimarisi, doğrulama deneyleri, rekonstrüksiyon örnekleri ve artırılmış gerçeklik aktarım sözleşmesi",
        56,
        PAGE_H - 222,
        520,
        font="DV",
        size=10.5,
        leading=15,
        color=HexColor("#C8D6DF"),
    )
    draw_image_fit(
        c,
        ar_dir / "surface_gallery.png",
        53,
        104,
        735,
        238,
        background=HexColor("#061321"),
        border=False,
        pad=0,
    )
    c.setStrokeColor(HexColor("#23435C"))
    c.rect(53, 104, 735, 238, fill=0, stroke=1)
    c.setFont("DV", 7.6)
    c.setFillColor(HexColor("#9EB4C5"))
    c.drawString(55, 85, "Hazırlayan: Eyasu Desalegne Beyene")
    c.drawCentredString(PAGE_W / 2, 85, "Sürüm 1.0")
    c.drawRightString(PAGE_W - 54, 85, "Eylül 2026")
    c.setFillColor(HexColor("#6E8798"))
    c.setFont("DV", 6.8)
    c.drawString(55, 63, "Bu belge araştırma ve mühendislik değerlendirmesi içindir; klinik karar veya hasta yönlendirmesi amacı taşımaz.")

    # 2 - Purpose and contents
    y = new_page(c, 2, "Belge kapsamı", "Raporun amacı ve okuma kılavuzu")
    rounded_box(c, MARGIN_X, 318, 355, 190, fill=PALE_TEAL)
    section_label(c, "Bu rapor neyi belgeler?", MARGIN_X + 20, 481)
    draw_text(
        c,
        "PerforaAR'ın mevcut yazılım sürümünü, iki kamusal veri setiyle yapılan doğrulama çalışmalarını ve üretilen 3B görselleştirme varlıklarını tek bir teknik dosyada toplar. Amaç, sistemin bugün gerçekten yaptığı işleri ve henüz tamamlanmamış klinik adımları aynı açıklıkla göstermektir.",
        MARGIN_X + 20,
        460,
        315,
        size=9.2,
        leading=13.3,
    )
    draw_bullets(
        c,
        [
            "Dryad renk/power Doppler hacimlerinden sanal izlenen kesit rekonstrüksiyonu",
            "TUS-REC2024 gerçek 2B ultrason kareleri ve ölçülmüş prob pozlarıyla hacim oluşturma",
            "Fiziksel ölçekte NIfTI, GLB ve AR sahne meta verisi üretimi",
            "Kalite kontrol şekilleri, stres testleri ve performans ölçümleri",
        ],
        MARGIN_X + 20,
        390,
        315,
        size=8.3,
        gap=2,
    )
    rounded_box(c, 420, 318, 379, 190, fill=white)
    section_label(c, "İçindekiler", 440, 481)
    contents = [
        ("01", "Sistem yaklaşımı ve mimari", "3-5"),
        ("02", "Veri setleri ve kanıt düzeyleri", "6"),
        ("03", "Dryad THY3 yazılım doğrulaması", "7-9"),
        ("04", "TUS-REC2024 izlenen rekonstrüksiyon", "10-15"),
        ("05", "3B nesneler ve AR aktarımı", "16-20"),
        ("06", "Durum, sınırlılıklar ve sonraki adımlar", "21-22"),
    ]
    cy = 454
    for no, label, pages in contents:
        c.setFillColor(TEAL)
        c.setFont("DV-Bold", 8)
        c.drawString(440, cy, no)
        c.setFillColor(INK)
        c.setFont("DV", 8.5)
        c.drawString(470, cy, label)
        c.setFillColor(MID)
        c.drawRightString(780, cy, pages)
        c.setStrokeColor(LINE)
        c.line(440, cy - 8, 780, cy - 8)
        cy -= 27
    metric_card(c, MARGIN_X, 224, 176, 70, "2", "Kamusal veri seti", accent=TEAL)
    metric_card(c, MARGIN_X + 190, 224, 176, 70, "6", "TUS 3B rekonstrüksiyonu", accent=ORANGE)
    metric_card(c, MARGIN_X + 380, 224, 176, 70, "90", "TUS stres-test koşulu", accent=GREEN)
    metric_card(c, MARGIN_X + 570, 224, 176, 70, "34", "Raporlanan sonuç görseli", accent=TEAL_DARK)
    rounded_box(c, MARGIN_X, 72, PAGE_W - 2 * MARGIN_X, 128, fill=LIGHT)
    section_label(c, "Kapsam sınırı", MARGIN_X + 18, 174)
    draw_text(
        c,
        "Mevcut sürüm bir araştırma prototipidir. TUS hacimleri gri ölçekli B-mod ultrason anatomisini gösterir; renkli Doppler damar segmentasyonu değildir. Dryad deneyi ise var olan 3B hacimlerden türetilmiş sanal 2B kesitleri kullanır. Bu nedenle sonuçlar yazılımın dönüşüm, bileştirme, dayanıklılık ve dosya aktarımı işlevlerini destekler; klinik perforatör doğruluğu, cerrahi fayda veya hasta güvenliği iddiası oluşturmaz.",
        MARGIN_X + 18,
        151,
        PAGE_W - 2 * MARGIN_X - 36,
        size=9.1,
        leading=13.4,
    )

    # 3 - Concept
    y = new_page(c, 3, "Sistem yaklaşımı", "2B renkli Doppler + optik izleyici + katı referans", "Seçilen mühendislik yolu")
    draw_text(
        c,
        "PerforaAR, probla elde edilen ardışık 2B Doppler düzlemlerini optik izleyici pozlarıyla aynı koordinat sistemine taşır. Aynı bölgeye ait tekrar gözlemleri birleştirerek üç boyutlu bir kanıt haritası oluşturur. Bacak üzerindeki ikinci katı hedef, probdan bağımsız hasta/uzuv hareketini ayırmak için zorunludur.",
        MARGIN_X,
        y,
        750,
        size=9.4,
        leading=13.5,
    )
    box_y, box_h, box_w, gap = 315, 92, 130, 18
    labels = [
        ("01", "2B renkli Doppler", "Görüntü ve zaman damgası"),
        ("02", "Çift optik izleme", "Prob ve bacak referansı"),
        ("03", "Kalibrasyon", "Pikselden milimetreye"),
        ("04", "3B füzyon", "Tekrar gözlemleri ve belirsizlik"),
        ("05", "Kayıt ve AR", "Bacak referansından gözlüğe"),
    ]
    for i, (num, label, sub) in enumerate(labels):
        x = MARGIN_X + i * (box_w + gap)
        rounded_box(c, x, box_y, box_w, box_h, fill=white)
        c.setFillColor(TEAL)
        c.setFont("DV-Bold", 8)
        c.drawString(x + 12, box_y + box_h - 20, num)
        c.setFillColor(NAVY)
        c.setFont("DV-Bold", 9.2)
        c.drawString(x + 12, box_y + 46, label)
        draw_text(c, sub, x + 12, box_y + 28, box_w - 24, size=7.1, leading=9.5, color=MID)
        if i < len(labels) - 1:
            arrow(c, x + box_w + 3, box_y + box_h / 2, x + box_w + gap - 3, box_y + box_h / 2)
    rounded_box(c, MARGIN_X, 115, 364, 165, fill=PALE_TEAL)
    section_label(c, "Her geçerli kare için veri sözleşmesi", MARGIN_X + 18, 254)
    contracts = [
        "Doppler görüntüsü",
        "Görüntü zaman damgası",
        "Prob hedefinin pozu",
        "Bacak referansının pozu",
        "Kalibrasyon kimliği ve takip durumu",
    ]
    draw_bullets(c, contracts, MARGIN_X + 18, 231, 328, size=8.5, gap=3)
    rounded_box(c, 424, 115, 375, 165, fill=white)
    section_label(c, "Neden iki hedef?", 442, 254)
    draw_text(
        c,
        "Yalnızca prob takip edilirse bacak hareket ettiğinde yeniden oluşturulan harita eski konumunda kalır. Bacak referansının pozu çıkarıldığında gözlemler uzva bağlı bir koordinat çerçevesinde saklanır. Böylece prob ve bacak aynı anda hareket etse bile harita tekrar kaydedilebilir.",
        442,
        231,
        338,
        size=8.8,
        leading=12.5,
    )
    c.setFillColor(ORANGE)
    c.setFont("DV-Bold", 8.2)
    c.drawString(442, 148, "Geçersiz durum:")
    draw_text(c, "Hedeflerden biri görünmüyorsa kare reddedilir veya yalnızca önceden doğrulanmış bir interpolasyon kuralı uygulanır.", 525, 148, 250, size=8.1, leading=11.5)

    # 4 - Architecture
    y = new_page(c, 4, "Yazılım mimarisi", "Dönüşüm zinciri, modüller ve denetlenebilir çıktılar")
    rounded_box(c, MARGIN_X, 372, 757, 96, fill=NAVY, stroke=NAVY)
    c.setFillColor(CYAN)
    c.setFont("DV-Bold", 8)
    c.drawString(MARGIN_X + 18, 444, "KOORDİNAT DÖNÜŞÜMÜ")
    c.setFillColor(white)
    c.setFont("DV-Bold", 15)
    c.drawString(MARGIN_X + 18, 412, "pL = inv(TR←L) · TR←P · TP←U · pU")
    c.setFont("DV", 8.1)
    c.setFillColor(HexColor("#BFD0DB"))
    c.drawString(MARGIN_X + 18, 391, "U: ultrason görüntüsü  |  P: prob hedefi  |  L: bacak referansı  |  R: optik izleyici")
    module_data = [
        ("01", "Alım adaptörü", "Görüntü, zaman, poz ve yakalama durumunu alır."),
        ("02", "Damar kanıtı", "İlk aşamada manuel maske; ileride doğrulanmış segmentasyon."),
        ("03", "Uzamsal füzyon", "Tekrar gözlemlerini birleştirir, belirsizliği korur."),
        ("04", "Aday haritası", "Konum, derinlik, kanıt, güven ve sıralama bileşenleri."),
        ("05", "Kayıt", "Bacak referansını kamera/gözlük çerçevesine bağlar."),
        ("06", "Görselleştirme", "3B hacim, kesit, kapsama ve dışa aktarma."),
        ("07", "Denetim kaydı", "Kalibrasyon, ayar, uyarı, gecikme ve kullanıcı işlemi."),
        ("08", "Kalite kapıları", "Takip, kayıt ve veri bütünlüğü başarısızsa görüntüyü durdurur."),
    ]
    start_y = 324
    for i, (num, label, desc) in enumerate(module_data):
        col = i % 2
        row = i // 2
        x = MARGIN_X + col * 387
        yy = start_y - row * 67
        rounded_box(c, x, yy, 370, 54, fill=white)
        c.setFillColor(TEAL)
        c.circle(x + 25, yy + 27, 14, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("DV-Bold", 7.5)
        c.drawCentredString(x + 25, yy + 24.5, num)
        c.setFillColor(NAVY)
        c.setFont("DV-Bold", 8.6)
        c.drawString(x + 50, yy + 34, label)
        draw_text(c, desc, x + 50, yy + 19, 300, size=7.2, leading=9.5, color=MID)
    c.setFillColor(PALE_ORANGE)
    c.roundRect(MARGIN_X, 47, 757, 34, 7, fill=1, stroke=0)
    c.setFillColor(RED)
    c.setFont("DV-Bold", 7.6)
    c.drawString(MARGIN_X + 14, 60, "Emniyet ilkesi")
    c.setFillColor(INK)
    c.setFont("DV", 7.5)
    c.drawString(MARGIN_X + 90, 60, "Takip veya kayıt kalitesi doğrulanmış sınırı aşarsa bindirme görünür biçimde zayıflatılır ya da kapatılır.")

    # 5 - Viewer
    y = new_page(c, 5, "3B rekonstrüksiyon görüntüleyicisi", "Araştırmacı konsolu: inceleme, kalite kontrolü ve AR dışa aktarımı")
    # Wireframe
    rounded_box(c, MARGIN_X, 108, 500, 360, fill=HexColor("#F9FBFC"), radius=10)
    c.setFillColor(NAVY)
    c.rect(MARGIN_X, 435, 500, 33, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("DV-Bold", 9)
    c.drawString(MARGIN_X + 14, 447, "PerforaAR · 3D Reconstruction Viewer")
    c.setFillColor(HexColor("#E8EEF2"))
    c.rect(MARGIN_X, 108, 132, 327, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont("DV-Bold", 7.8)
    c.drawString(MARGIN_X + 12, 414, "Hacim seçimi")
    for j, label in enumerate(["Tarama", "Eşik", "Opaklık", "X / Y / Z kırpma"]):
        yy = 388 - j * 55
        c.setFont("DV", 6.7)
        c.setFillColor(MID)
        c.drawString(MARGIN_X + 12, yy + 17, label)
        c.setFillColor(white)
        c.roundRect(MARGIN_X + 12, yy - 3, 108, 17, 3, fill=1, stroke=0)
        if j:
            c.setFillColor(TEAL)
            c.rect(MARGIN_X + 18, yy + 3, 65 + j * 5, 3, fill=1, stroke=0)
    tab_x = MARGIN_X + 147
    tabs = ["Etkileşimli 3B", "Kesitler", "AR dışa aktarım", "Alım QA"]
    for j, label in enumerate(tabs):
        tw = 82 if j < 2 else 93
        c.setFillColor(TEAL if j == 0 else HexColor("#DFE8ED"))
        c.roundRect(tab_x, 405, tw, 21, 4, fill=1, stroke=0)
        c.setFillColor(white if j == 0 else MID)
        c.setFont("DV-Bold", 6.4)
        c.drawCentredString(tab_x + tw / 2, 413, label)
        tab_x += tw + 5
    c.setFillColor(HexColor("#071522"))
    c.roundRect(MARGIN_X + 147, 148, 334, 243, 7, fill=1, stroke=0)
    c.setStrokeColor(HexColor("#284E62"))
    for frac in (0.25, 0.5, 0.75):
        c.line(MARGIN_X + 160, 158 + 215 * frac, MARGIN_X + 468, 158 + 215 * frac)
        c.line(MARGIN_X + 160 + 300 * frac, 160, MARGIN_X + 160 + 300 * frac, 378)
    c.setFillColor(CYAN)
    c.setStrokeColor(CYAN)
    c.setLineWidth(1)
    c.ellipse(MARGIN_X + 235, 205, MARGIN_X + 410, 330, fill=1, stroke=0)
    c.setFillColor(TEAL_DARK)
    c.ellipse(MARGIN_X + 270, 235, MARGIN_X + 365, 300, fill=1, stroke=0)
    c.setFillColor(HexColor("#D7E4EB"))
    c.roundRect(MARGIN_X + 147, 118, 155, 20, 4, fill=1, stroke=0)
    c.roundRect(MARGIN_X + 312, 118, 169, 20, 4, fill=1, stroke=0)
    c.setFillColor(MID)
    c.setFont("DV", 6.4)
    c.drawCentredString(MARGIN_X + 224, 126, "GLB oluştur")
    c.drawCentredString(MARGIN_X + 397, 126, "Koordinat meta verisi")
    rounded_box(c, 566, 108, 233, 360, fill=white)
    section_label(c, "Dört çalışma alanı", 584, 442)
    feature_blocks = [
        ("Etkileşimli 3B", "Fiziksel koordinatlarda hacim ve izoyüzey; döndürme, yakınlaştırma, kırpma ve eşik."),
        ("Ortogonel kesitler", "Aksiyel, koronal ve sagittal düzlemler; eşzamanlı hacim kapsamı incelemesi."),
        ("AR dışa aktarım", "Milimetre ölçeğinde GLB yüzeyi ve NIfTI affine içeren JSON sahne paketi."),
        ("Alım kalite kontrolü", "Prob yörüngesi, geçerli piksel maskesi, kapsama ve stres-test bozulması."),
    ]
    fy = 411
    for idx, (label, desc) in enumerate(feature_blocks, 1):
        c.setFillColor(TEAL)
        c.circle(590, fy + 2, 9, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("DV-Bold", 6.4)
        c.drawCentredString(590, fy, str(idx))
        c.setFillColor(NAVY)
        c.setFont("DV-Bold", 8.3)
        c.drawString(607, fy + 4, label)
        fy = draw_text(c, desc, 607, fy - 9, 170, size=7.4, leading=10.2, color=MID)
        fy -= 17
    c.setFillColor(PALE_TEAL)
    c.roundRect(582, 126, 201, 56, 6, fill=1, stroke=0)
    c.setFillColor(TEAL_DARK)
    c.setFont("DV-Bold", 7.1)
    c.drawString(594, 161, "Çıktı")
    draw_text(c, "NIfTI hacmi + GLB ağ modeli + JSON kayıt sözleşmesi + PNG önizleme", 594, 148, 176, size=7.1, leading=9.5)

    # 6 - datasets
    y = new_page(c, 6, "Veri setleri ve kanıt düzeyi", "Her deney farklı bir soruyu yanıtlar; hiçbiri tek başına klinik doğrulama değildir")
    rows = [
        ["Kaynak", "Girdi", "Bu projedeki rol", "Temel sınırlılık"],
        ["Dryad 4D CUSI", "Gerçek 3B renk/power Doppler NIfTI", "Dönüşüm, bileştirme ve seyrek kesit yazılım testi", "Fare beyni; 2B kareler sanal ve referans hacimden türetilmiş"],
        ["TUS-REC2024", "Gerçek 2B B-mod kareleri + ölçülmüş prob pozları", "Serbest-el 3B ultrason rekonstrüksiyonu ve stres testleri", "Renkli Doppler/perforatör etiketi yok; referans öz-üretilmiş"],
        ["Planlanan fantom", "İzlenen 2B renkli Doppler + bilinen kanal geometrisi", "Bağımsız uzamsal doğruluk ve merkez çizgisi hatası", "Henüz gerçekleştirilmedi"],
        ["Planlanan gönüllü", "Etik onaylı non-invaziv tarama", "Tekrarlanabilirlik ve kullanılabilirlik", "Klinik etkinlik testi değildir"],
    ]
    simple_table(c, MARGIN_X, 474, [118, 190, 220, 229], rows, row_h=58, font_size=7.3)
    c.setFillColor(NAVY)
    c.setFont("DV-Bold", 10)
    c.drawString(MARGIN_X, 156, "Kanıt zinciri")
    stages = [
        ("Tamamlandı", "Yazılım birim testleri", GREEN),
        ("Tamamlandı", "Dryad sanal kesit testi", GREEN),
        ("Tamamlandı", "TUS tracked B-mod pilotu", GREEN),
        ("Sıradaki", "Vasküler akış fantomu", ORANGE),
        ("Sonraki", "Gönüllü fizibilitesi", MID),
    ]
    sy = 92
    sw = 139
    for i, (state, label, color) in enumerate(stages):
        x = MARGIN_X + i * (sw + 15)
        rounded_box(c, x, sy, sw, 51, fill=white)
        c.setFillColor(color)
        c.circle(x + 16, sy + 35, 4, fill=1, stroke=0)
        c.setFillColor(color)
        c.setFont("DV-Bold", 6.5)
        c.drawString(x + 26, sy + 32, state.upper())
        draw_text(c, label, x + 12, sy + 17, sw - 24, size=7.4, leading=9, color=INK)
        if i < 4:
            arrow(c, x + sw + 3, sy + 25, x + sw + 12, sy + 25)

    # 7 - Dryad method and results
    y = new_page(c, 7, "Dryad THY3 yazılım doğrulaması", "Dryad hacimlerinden sanal izlenen kesit rekonstrüksiyonu")
    metric_card(c, MARGIN_X, 397, 172, 70, "PASS", "Önceden tanımlı Stage 0 kriterleri", accent=GREEN)
    metric_card(c, MARGIN_X + 188, 397, 172, 70, "40 μm", "Belgelenmiş izotropik örnekleme", accent=TEAL)
    metric_card(c, MARGIN_X + 376, 397, 172, 70, "2 hacim", "Uyanık ve anestezi koşulu", accent=ORANGE)
    metric_card(c, MARGIN_X + 564, 397, 193, 70, "160 μm", "Seyrek koşul düzlem aralığı", accent=TEAL_DARK)
    rounded_box(c, MARGIN_X, 222, 320, 153, fill=white)
    section_label(c, "Yöntem", MARGIN_X + 18, 348)
    draw_bullets(
        c,
        [
            "Power hacminde en yüksek %1, sabit damar maskesi olarak tanımlandı.",
            "x-z düzlemleri çıkarılıp y ekseni boyunca bilinen pozlar atandı.",
            "Tam, her dördüncü düzlem ve %20 iç-kare kaybı koşulları çalıştırıldı.",
            "Dice, yüzey Dice, power hatası ve imzalı akış yönü uyumu hesaplandı.",
        ],
        MARGIN_X + 18,
        326,
        282,
        size=7.7,
        gap=2,
    )
    table_rows = [
        ["Koşul", "Uyanık Dice", "Uyanık yüzey", "Anestezi Dice", "Anestezi yüzey", "Akış yönü"],
        ["Tam", "1,0000", "1,0000", "1,0000", "1,0000", "%100,00"],
        ["Seyrek", "0,8513", "0,9732", "0,8343", "0,9631", "%98,49 / %98,63"],
        ["Seyrek + %20 kayıp", "0,7080", "0,8392", "0,7253", "0,8577", "%93,69 / %95,01"],
    ]
    simple_table(c, 380, 375, [85, 62, 64, 70, 72, 66], table_rows, row_h=38, font_size=5.9)
    rounded_box(c, MARGIN_X, 76, 757, 119, fill=PALE_ORANGE)
    section_label(c, "Yorum", MARGIN_X + 18, 169)
    draw_text(
        c,
        "Tam düzlem tekrarı her iki hacimde de kayıpsızdır. Seyrek örneklemede ana damar gövdeleri ve akış yönü büyük ölçüde korunmuştur; hata ince damar sınırlarında ve küçük dallarda yoğunlaşır. Sonuç, koordinat dönüşümü ve interpolasyon uygulamasını destekler. Ancak aynı 3B referanstan çıkarılan 2B düzlemler kullanıldığı için bağımsız ultrason alımı, optik takip doğruluğu veya insan perforatörü performansı hakkında sonuç üretmez.",
        MARGIN_X + 18,
        145,
        720,
        size=8.6,
        leading=12.2,
    )

    # 8-9 Dryad figures
    y = new_page(c, 8, "Dryad sonucu: uyanık koşul", "Referans ve seyrek rekonstrüksiyonun power ile imzalı akış karşılaştırması")
    draw_image_fit(c, dryad_dir / "awake_sparse_reconstruction.png", MARGIN_X, 78, 757, 410, pad=1)
    draw_text(c, "Şekil 1. Sol sütun referans hacmi, orta sütun seyrek düzlem rekonstrüksiyonunu, sağ sütun mutlak hatayı gösterir. Üst sıra power Doppler; alt sıra pozitif/negatif hız yönüdür.", MARGIN_X, 61, 757, size=7.4, leading=9.5, color=MID)

    y = new_page(c, 9, "Dryad sonucu: anestezi koşulu", "Daha büyük hacimde seyrek örnekleme ve akış yönü korunumu")
    draw_image_fit(c, dryad_dir / "anesthetized_sparse_reconstruction.png", MARGIN_X, 78, 757, 410, pad=1)
    draw_text(c, "Şekil 2. Seyrek koşul 61 düzlem içerir. Damar-maskesi Dice 0,8343; iki voksel toleranslı yüzey Dice 0,9631; akış işareti uyumu %98,63'tür.", MARGIN_X, 61, 757, size=7.4, leading=9.5, color=MID)

    # 10 TUS overview
    y = new_page(c, 10, "TUS-REC2024 izlenen rekonstrüksiyon pilotu", "Gerçek 2B ultrason kareleri, prob kalibrasyonu ve ölçülmüş pozlar")
    metric_card(c, MARGIN_X, 402, 172, 67, "72 / 72", "Doğrulanan kare/transform tarama çifti", accent=GREEN)
    metric_card(c, MARGIN_X + 188, 402, 172, 67, "6", "Üretilen referans hacim", accent=TEAL)
    metric_card(c, MARGIN_X + 376, 402, 172, 67, "90", "Rekonstrüksiyon koşulu", accent=ORANGE)
    metric_card(c, MARGIN_X + 564, 402, 193, 67, "0,1267", "En yüksek ham union NRMSE", accent=RED)
    rounded_box(c, MARGIN_X, 222, 382, 157, fill=white)
    section_label(c, "Rekonstrüksiyon adımları", MARGIN_X + 18, 351)
    draw_bullets(
        c,
        [
            "Kare/transform çiftlerinin boyut, sıra ve bütünlük kontrolü",
            "Tcamera←image = Tcamera←tool · Ttool←image bileşimi",
            "Geçerli ultrason piksel maskesi ve ağırlıklı voksel bileştirme",
            "Yalnızca küçük, çevrili hacim boşluklarının doldurulması",
            "2 mm izotropik NIfTI; aynı qform/sform ve milimetre birimi",
        ],
        MARGIN_X + 18,
        330,
        345,
        size=7.6,
        gap=1,
    )
    rounded_box(c, 444, 222, 355, 157, fill=PALE_TEAL)
    section_label(c, "Stres testleri", 462, 351)
    draw_text(c, "Kare hızı, kare kaybı, gecikme, pozisyon gürültüsü, dönme gürültüsü ve kalibrasyon sapması ayrı koşullar olarak değerlendirilmiştir.", 462, 328, 318, size=8.2, leading=11.7)
    c.setFillColor(NAVY)
    c.setFont("DV-Bold", 8)
    c.drawString(462, 270, "Birincil ölçüt")
    draw_text(c, "Union NRMSE; yalnızca ortak bölgeleri kullanarak kayıp kapsamayı gizlemez.", 535, 270, 237, size=7.7, leading=10.7)
    c.setFont("DV-Bold", 8)
    c.drawString(462, 236, "Referans tanımı")
    draw_text(c, "full_20fps ölçülmüş pozlarla oluşturulan iç referanstır; bağımsız anatomik doğruluk referansı değildir.", 535, 236, 237, size=7.7, leading=10.7)
    rows = [
        ["Kod", "Açıklama", "Tarama yönü"],
        ["RH / LH", "Sağ / sol ön kol", "-"],
        ["Per / Par", "Prob: dik / paralel", "-"],
        ["S / C / L", "Tarama yörüngesi", "-"],
        ["PtD", "Proksimalden distale", "İleri"],
        ["DtP", "Distalden proksimale", "Ters"],
    ]
    simple_table(c, MARGIN_X, 195, [90, 310, 170], rows, row_h=23, font_size=7.2)

    # 11 slices
    y = new_page(c, 11, "TUS hacim kesitleri ve kapsama", "Altı rekonstrüksiyonun aksiyel, koronal, sagittal ve kapsama görünümleri")
    tile_w, tile_h = 370, 139
    positions = [(MARGIN_X, 347), (MARGIN_X + 387, 347), (MARGIN_X, 194), (MARGIN_X + 387, 194), (MARGIN_X, 41), (MARGIN_X + 387, 41)]
    for code, (x, yy) in zip(scan_codes, positions, strict=True):
        image_tile(c, tus_dir / f"{code}__slices.png", x, yy, tile_w, tile_h, scan_caption(code), caption_h=19)

    # 12 trajectories
    y = new_page(c, 12, "Prob yörüngeleri", "Ölçülmüş kamera koordinatlarında kare merkezleri ve tarama geometrisi")
    tile_w, tile_h = 239, 194
    positions = [(MARGIN_X + i * 259, 284) for i in range(3)] + [(MARGIN_X + i * 259, 68) for i in range(3)]
    for code, (x, yy) in zip(scan_codes, positions, strict=True):
        image_tile(c, tus_dir / f"{code}__trajectory.png", x, yy, tile_w, tile_h, scan_caption(code), caption_h=21)

    # 13 masks
    y = new_page(c, 13, "Geçerli piksel maskeleri", "Ultrason fanı dışındaki siyah bölgelerin 3B bileştirmeden çıkarılması")
    tile_w, tile_h = 370, 139
    for code, (x, yy) in zip(scan_codes, positions := [(MARGIN_X, 347), (MARGIN_X + 387, 347), (MARGIN_X, 194), (MARGIN_X + 387, 194), (MARGIN_X, 41), (MARGIN_X + 387, 41)], strict=True):
        image_tile(c, tus_dir / f"{code}__valid_mask.png", x, yy, tile_w, tile_h, scan_caption(code), caption_h=19)

    # 14 degradation
    y = new_page(c, 14, "Stres-test bozulma profilleri", "Her taramada full_20fps iç referansına göre ham union NRMSE")
    tile_w, tile_h = 370, 139
    for code, (x, yy) in zip(scan_codes, positions, strict=True):
        image_tile(c, tus_dir / f"{code}__degradation.png", x, yy, tile_w, tile_h, scan_caption(code), caption_h=19)

    # 15 benchmark
    y = new_page(c, 15, "Performans ve hata yorumu", "Piksel örnekleme adımı, işlem hızı ve rekonstrüksiyon kalitesi")
    draw_image_fit(c, tus_dir / "benchmark_stride.png", MARGIN_X, 201, 490, 275, pad=3)
    rounded_box(c, 551, 201, 248, 275, fill=white)
    section_label(c, "Referans iş istasyonu ölçümü", 569, 448)
    bench = [
        ("Stride 8", "1068,21 kare/sn", "NRMSE 0,0399"),
        ("Stride 4", "359,20 kare/sn", "NRMSE 0,0184"),
        ("Stride 2", "75,52 kare/sn", "NRMSE 0,0095"),
        ("Stride 1", "20,98 kare/sn", "İç referans"),
    ]
    by = 412
    for label, speed, quality in bench:
        c.setFillColor(NAVY)
        c.setFont("DV-Bold", 8.2)
        c.drawString(569, by, label)
        c.setFillColor(TEAL_DARK)
        c.setFont("DV-Bold", 8.2)
        c.drawString(635, by, speed)
        c.setFillColor(MID)
        c.setFont("DV", 7.2)
        c.drawRightString(780, by, quality)
        c.setStrokeColor(LINE)
        c.line(569, by - 9, 780, by - 9)
        by -= 40
    c.setFillColor(PALE_TEAL)
    c.roundRect(569, 220, 211, 54, 6, fill=1, stroke=0)
    draw_text(c, "Stride 1: 451 kare, 21,49 saniye, 190,4 MB tepe bellek.", 581, 252, 188, size=7.5, leading=10.3)
    rounded_box(c, MARGIN_X, 66, 757, 110, fill=LIGHT)
    section_label(c, "Sonuçların anlamı", MARGIN_X + 18, 150)
    draw_text(
        c,
        "Hız-kalite dengesi beklenen yöndedir: daha sık piksel örnekleme hata ölçütlerini iyileştirirken işlem süresini artırır. Altı taramanın stres testlerinde en kötü ham union NRMSE, 052/RH_Par_L_DtP taramasında 2 mm öteleme gürültüsü altında 0,1267'dir. Gecikme ve dönme gürültüsü de prob yörüngesine bağlı olarak görünür bozulma oluşturur. Bu sonuçlar takip ve zaman eşleştirme kalitesinin AR bindirmesi için yazılım performansı kadar kritik olduğunu gösterir.",
        MARGIN_X + 18,
        127,
        720,
        size=8.4,
        leading=11.8,
    )

    # 16 gallery and mesh method
    y = new_page(c, 16, "3B nesne üretimi", "NIfTI hacminden fiziksel ölçekte üçgen yüzey ağına")
    draw_image_fit(c, ar_dir / "surface_gallery.png", MARGIN_X, 208, 757, 275, background=HexColor("#061321"), pad=0)
    rounded_box(c, MARGIN_X, 70, 757, 113, fill=white)
    section_label(c, "Dışa aktarma parametreleri", MARGIN_X + 18, 157)
    params = [
        ("Eşik", "Sıfır olmayan yoğunlukların %35 yüzdeliği"),
        ("Yumuşatma", "1 voksel Gaussian sigma"),
        ("Yüzey", "Marching cubes, adım boyutu 2"),
        ("Koordinat", "NIfTI fiziksel çerçevesi; sağ elli x/y/z"),
        ("Birim", "Milimetre; voksel aralığı 2 × 2 × 2 mm"),
    ]
    px = MARGIN_X + 18
    for label, value in params:
        c.setFillColor(TEAL_DARK)
        c.setFont("DV-Bold", 7.4)
        c.drawString(px, 132, label)
        draw_text(c, value, px, 116, 132, size=6.8, leading=8.7, color=MID, max_lines=2)
        px += 143
    c.setFillColor(PALE_ORANGE)
    c.roundRect(MARGIN_X + 18, 82, 720, 21, 5, fill=1, stroke=0)
    c.setFillColor(RED)
    c.setFont("DV-Bold", 7.1)
    c.drawCentredString(PAGE_W / 2, 89, "Bu yüzeyler gri ölçekli B-mod anatomi görselleştirmesidir; damar segmentasyonu değildir.")

    # 17-19 per subject previews
    subject_pages = [
        (17, "050 numaralı tarama: dik prob ve S yörüngesi", scenes[0:2]),
        (18, "051 numaralı tarama: paralel prob ve C yörüngesi", scenes[2:4]),
        (19, "052 numaralı tarama: paralel prob ve L yörüngesi", scenes[4:6]),
    ]
    for page_no, title, pair in subject_pages:
        y = new_page(c, page_no, "3B nesne varyantları", title, "Aynı bölgenin distal-proksimal ve proksimal-distal tarama yönleri")
        for idx, scene in enumerate(pair):
            x = MARGIN_X + idx * 385
            path = ar_dir / f"{scene['stem']}__surface_preview.png"
            image_tile(
                c,
                path,
                x,
                234,
                370,
                226,
                scene["stem"].replace("__full_20fps", "").replace("__", " / ").replace("_", " "),
                caption_h=23,
                background=HexColor("#071522"),
                caption_color=white,
            )
            rows = [
                ["Özellik", "Değer"],
                ["Fiziksel boyut", " × ".join(f"{v:.0f}" for v in scene["physical_extent_mm"]) + " mm"],
                ["Hacim matrisi", " × ".join(str(v) for v in scene["voxel_shape_xyz"])],
                ["Köşe / yüz", f"{scene['mesh_vertex_count']:,} / {scene['mesh_face_count']:,}".replace(",", ".")],
                ["Yüzey eşiği", f"{scene['surface_threshold']:.1f}".replace(".", ",")],
            ]
            simple_table(c, x, 211, [124, 246], rows, row_h=26, font_size=7.2)
        draw_text(c, "Görünümler: eğik, lateral ve superior. Boyutlar modelleme biriminden türetilmiş değildir; doğrudan NIfTI fiziksel koordinatlarında milimetre olarak korunur.", MARGIN_X, 57, 757, size=7.4, leading=9.5, color=MID)

    # 20 AR contract
    y = new_page(c, 20, "AR sahne paketi ve gözlük entegrasyonu", "GLB geometri ile JSON koordinat sözleşmesi birlikte kullanılır")
    nodes = [
        (MARGIN_X, 325, 138, 84, "NIfTI hacmi", "2 mm voksel, affine ve fiziksel başlangıç"),
        (225, 325, 138, 84, "GLB yüzeyi", "Üçgen ağ; milimetre ölçeği korunur"),
        (408, 325, 138, 84, "Bacak kaydı", "Hacim çerçevesinden katılımcı referansına"),
        (591, 325, 208, 84, "Unity / OpenXR gözlük", "Dünya ankrajı, görünüm, opaklık ve güven durumu"),
    ]
    for idx, (x, yy, w, h, label, desc) in enumerate(nodes):
        rounded_box(c, x, yy, w, h, fill=white)
        c.setFillColor(TEAL)
        c.setFont("DV-Bold", 7)
        c.drawString(x + 12, yy + h - 19, f"0{idx + 1}")
        c.setFillColor(NAVY)
        c.setFont("DV-Bold", 8.8)
        c.drawString(x + 12, yy + 46, label)
        draw_text(c, desc, x + 12, yy + 30, w - 24, size=6.8, leading=8.8, color=MID)
        if idx < len(nodes) - 1:
            arrow(c, x + w + 5, yy + h / 2, nodes[idx + 1][0] - 5, yy + h / 2)
    rounded_box(c, MARGIN_X, 143, 359, 144, fill=PALE_TEAL)
    section_label(c, "JSON sahne sözleşmesi", MARGIN_X + 18, 260)
    draw_bullets(
        c,
        [
            "Şema: perforaar.ar-scene.v1",
            "NIfTI affine matrisi ve sağ elli x/y/z tanımı",
            "Voksel şekli, aralığı ve fiziksel uzanım",
            "Yüzey üretim parametreleri ve kaynak hacim",
            "registration_required = true",
        ],
        MARGIN_X + 18,
        238,
        320,
        size=7.6,
        gap=2,
    )
    rounded_box(c, 424, 143, 375, 144, fill=white)
    section_label(c, "Gözlükte gösterilecek asgari bilgiler", 442, 260)
    draw_bullets(
        c,
        [
            "Kayıtlı anatomi veya damar bindirmesi",
            "Derinlik, güven ve belirsizlik kodlaması",
            "Takip/kayıt durumu ve araştırma modu etiketi",
            "Göster/gizle, opaklık, dondur, yeniden kaydet ve acil temizle",
        ],
        442,
        238,
        338,
        size=7.6,
        gap=3,
    )
    c.setFillColor(PALE_ORANGE)
    c.roundRect(MARGIN_X, 77, 757, 43, 7, fill=1, stroke=0)
    draw_text(c, "Kayıt kapısı: Katılımcıya özel hacim-bacak dönüşümü ölçülmeden ve hedef kayıt hatası kabul sınırını geçmeden model hasta üzerinde bindirme olarak gösterilmemelidir.", MARGIN_X + 16, 102, 725, font="DV-Bold", size=7.8, leading=10.7, color=RED)

    # 21 status and next steps
    y = new_page(c, 21, "Mevcut durum ve sıradaki teknik işler", "Tamamlanan bileşenler ile klinik kullanımdan önce gereken doğrulamalar")
    rows = [
        ["Bileşen", "Durum", "Kanıt / eksik adım"],
        ["3B hacim rekonstrüksiyonu", "Tamamlandı", "Dryad ve TUS testleri; altı NIfTI hacmi"],
        ["3B etkileşimli görüntüleme", "Tamamlandı", "Kesit, hacim, eşik, kırpma, opaklık ve kalite kontrolü"],
        ["GLB + JSON AR aktarımı", "Tamamlandı", "Altı sahne paketi; milimetre ve affine meta verisi"],
        ["Gerçek izlenen renkli Doppler alımı", "Bekliyor", "Prob + bacak hedefi + kare/poz senkronizasyonu"],
        ["Damar segmentasyonu", "Bekliyor", "Etiketli renkli Doppler ve doğrulanmış maske/merkez çizgisi"],
        ["Bağımsız fantom doğruluğu", "Sıradaki", "Bilinen kanal geometrisinde mm tabanlı merkez çizgisi ve yüzey hatası"],
        ["Gözlük istemcisi", "Tasarım aşaması", "Hedef cihaz seçimi, Unity/OpenXR ve kayıt kalite kapısı"],
        ["Gönüllü/klinik değerlendirme", "Kapsam dışı", "Etik onay ve ayrı protokol gerektirir"],
    ]
    simple_table(c, MARGIN_X, 477, [215, 112, 430], rows, row_h=37, font_size=7.4)
    rounded_box(c, MARGIN_X, 65, 757, 79, fill=NAVY, stroke=NAVY)
    c.setFillColor(CYAN)
    c.setFont("DV-Bold", 8)
    c.drawString(MARGIN_X + 18, 121, "ÖNERİLEN SONRAKİ DENEY")
    draw_text(
        c,
        "Gerçek 2B renkli Doppler kareleri, senkronize optik pozlar ve bilinen damar/kanal geometrisi içeren vasküler akış fantomu. Birincil çıktılar merkez çizgisi hatası, yüzey mesafesi, kayıt hatası, kare kaybına dayanıklılık ve uçtan uca gecikme olmalıdır.",
        MARGIN_X + 18,
        99,
        720,
        size=8.2,
        leading=11.3,
        color=white,
    )

    # 22 reproducibility and references
    y = new_page(c, 22, "Tekrarlanabilirlik ve teknik referanslar", "Sürüm kontrollü çıktılar, veri kaynakları ve kullanım notu")
    rounded_box(c, MARGIN_X, 286, 365, 187, fill=white)
    section_label(c, "Sürüm kontrollü çıktılar", MARGIN_X + 18, 446)
    draw_bullets(
        c,
        [
            "results/dryad_thy3/: metrikler, köken bilgisi ve iki doğrulama şekli",
            "results/tus_rec2024/: altı NIfTI hacmi, 90 koşulun ölçütleri ve kalite görselleri",
            "results/tus_rec2024/ar_exports/: altı GLB, altı JSON ve altı PNG önizleme",
            "scripts/: veri hazırlama, rekonstrüksiyon, performans testi ve AR dışa aktarım komutları",
            "tests/: geometri, füzyon, rekonstrüksiyon, landmark ve görüntüleyici testleri",
        ],
        MARGIN_X + 18,
        423,
        329,
        size=7.6,
        gap=3,
    )
    rounded_box(c, 424, 286, 375, 187, fill=PALE_TEAL)
    section_label(c, "Kaynaklar", 442, 446)
    refs = [
        "PerforaAR kaynak kodu: https://github.com/eyasudesalegne/PerforaAR",
        "Dryad: Four-Dimensional Computational Ultrasound Imaging of Brain Hemodynamics. DOI: 10.5061/dryad.w0vt4b8z8",
        "İlgili makale: Science Advances. DOI: 10.1126/sciadv.adk7957",
        "TUS-REC2024 Validation Dataset v2.0.0. DOI: 10.5281/zenodo.12979481",
    ]
    ry = 418
    for i, ref in enumerate(refs, 1):
        c.setFillColor(TEAL_DARK)
        c.setFont("DV-Bold", 7.4)
        c.drawString(442, ry, f"{i}.")
        ry = draw_text(c, ref, 458, ry, 318, size=7.2, leading=10.1)
        ry -= 10
    rounded_box(c, MARGIN_X, 102, 757, 154, fill=LIGHT)
    section_label(c, "Son değerlendirme", MARGIN_X + 18, 229)
    draw_text(
        c,
        "PerforaAR'ın mevcut sürümü, izlenen ultrason rekonstrüksiyonu ile 3B görselleştirme zincirinin çalıştığını tekrarlanabilir çıktılarla göstermektedir. Dryad testi renk/power Doppler hacimlerinde dönüşüm ve seyrek kesit davranışını; TUS pilotu ise gerçek 2B karelerden poz-temelli B-mod hacim oluşumunu göstermiştir. Altı hacim, fiziksel ölçekte GLB nesnelerine ve kayıt sözleşmesi taşıyan JSON dosyalarına aktarılmıştır.",
        MARGIN_X + 18,
        205,
        720,
        size=8.6,
        leading=12.2,
    )
    draw_text(
        c,
        "Bir sonraki karar noktası yeni bir görsel varyant üretmek değil, gerçek izlenen renkli Doppler alımı ve bağımsız vasküler fantom doğrulamasıdır. Bu adım tamamlanmadan 3B yüzeyler damar modeli veya cerrahi rehber olarak sunulmamalıdır.",
        MARGIN_X + 18,
        144,
        720,
        font="DV-Bold",
        size=8.5,
        leading=12.1,
        color=TEAL_DARK,
    )

    c.save()
    print(OUT)


if __name__ == "__main__":
    build_report()
