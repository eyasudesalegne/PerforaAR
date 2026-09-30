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
MARGIN_X = 48
CONTENT_W = PAGE_W - 2 * MARGIN_X
BODY_SIZE = 12
BODY_LEADING = 18

BLACK = HexColor("#111111")
CHARCOAL = HexColor("#252525")
YELLOW = HexColor("#F5C518")
YELLOW_DARK = HexColor("#C99A00")
PALE_YELLOW = HexColor("#FFF6CF")
PAPER = HexColor("#FAF9F4")
SOFT_GREY = HexColor("#F0EFEA")
MID_GREY = HexColor("#66645F")
LINE = HexColor("#D6D2C7")


def register_fonts() -> None:
    """Register a Turkish-capable Times New Roman compatible family."""
    font_root = Path(
        "/opt/codex/runtimes/codex-primary-runtime/dependencies/native/"
        "libreoffice-headless/libreoffice/share/fonts/truetype"
    )
    pdfmetrics.registerFont(
        TTFont("TNR", str(font_root / "LiberationSerif-Regular.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("TNR-Bold", str(font_root / "LiberationSerif-Bold.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("TNR-Italic", str(font_root / "LiberationSerif-Italic.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("TNR-BoldItalic", str(font_root / "LiberationSerif-BoldItalic.ttf"))
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
    font: str = "TNR",
    size: float = BODY_SIZE,
    leading: float = BODY_LEADING,
    color: Color = CHARCOAL,
    max_lines: int | None = None,
    align: str = "left",
) -> float:
    lines = fit_lines(text, width, font, size)
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


def rounded_panel(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: Color = white,
    stroke: Color = LINE,
    radius: float = 8,
    line_width: float = 0.8,
) -> None:
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(line_width)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)


def page_header(c: canvas.Canvas, page: int, section: str) -> None:
    c.setFillColor(BLACK)
    c.rect(0, PAGE_H - 34, PAGE_W, 34, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.rect(MARGIN_X, PAGE_H - 34, 118, 34, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 13)
    c.drawCentredString(MARGIN_X + 59, PAGE_H - 23, "PERFORAAR")
    c.setFillColor(white)
    c.setFont("TNR", 11)
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 22, section)

    c.setStrokeColor(BLACK)
    c.setLineWidth(0.8)
    c.line(MARGIN_X, 30, PAGE_W - MARGIN_X, 30)
    c.setFillColor(MID_GREY)
    c.setFont("TNR", 9)
    c.drawString(MARGIN_X, 17, "Araştırma prototipi. Klinik kullanım için değildir.")
    c.drawCentredString(PAGE_W / 2, 17, "GitHub projesi: eyasudesalegne - PerforaAR")
    c.drawRightString(PAGE_W - MARGIN_X, 17, str(page))


def page_title(c: canvas.Canvas, title: str, subtitle: str | None = None) -> float:
    y = PAGE_H - 68
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 25)
    c.drawString(MARGIN_X, y, title)
    c.setFillColor(YELLOW)
    c.rect(MARGIN_X, y - 12, 92, 5, fill=1, stroke=0)
    y -= 37
    if subtitle:
        y = draw_text(
            c,
            subtitle,
            MARGIN_X,
            y,
            CONTENT_W,
            font="TNR-Italic",
            size=12,
            leading=18,
            color=MID_GREY,
            max_lines=2,
        )
        y -= 8
    return y


def new_page(
    c: canvas.Canvas,
    page: int,
    section: str,
    title: str,
    subtitle: str | None = None,
) -> float:
    if page > 1:
        c.showPage()
    page_header(c, page, section)
    return page_title(c, title, subtitle)


def section_label(c: canvas.Canvas, text: str, x: float, y: float, width: float) -> None:
    c.setFillColor(YELLOW)
    c.rect(x, y - 5, width, 25, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 12)
    c.drawString(x + 10, y + 2, text.upper())


def metric_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    value: str,
    label: str,
) -> None:
    rounded_panel(c, x, y, w, h, fill=BLACK, stroke=BLACK)
    c.setFillColor(YELLOW)
    c.rect(x, y + h - 7, w, 7, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("TNR-Bold", 22)
    c.drawString(x + 16, y + h - 36, value)
    draw_text(
        c,
        label,
        x + 16,
        y + h - 56,
        w - 30,
        size=10.5,
        leading=15.75,
        color=white,
        max_lines=2,
    )


def numbered_items(
    c: canvas.Canvas,
    items: Iterable[str],
    x: float,
    y: float,
    width: float,
    *,
    start: int = 1,
    size: float = BODY_SIZE,
    leading: float = BODY_LEADING,
    gap: float = 8,
) -> float:
    number = start
    for item in items:
        lines = fit_lines(item, width - 44, "TNR", size)
        block_h = max(26, len(lines) * leading)
        c.setFillColor(BLACK)
        c.roundRect(x, y - 18, 28, 24, 4, fill=1, stroke=0)
        c.setFillColor(YELLOW)
        c.setFont("TNR-Bold", 11)
        c.drawCentredString(x + 14, y - 10, f"{number:02d}")
        draw_text(
            c,
            item,
            x + 42,
            y,
            width - 42,
            size=size,
            leading=leading,
        )
        y -= block_h + gap
        number += 1
    return y


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
        c.setLineWidth(0.8)
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
    caption_h: float = 27,
    background: Color = white,
    caption_color: Color = BLACK,
) -> None:
    rounded_panel(c, x, y, w, h, fill=background, radius=7)
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
    c.setFont("TNR-Bold", 10.5)
    c.drawCentredString(x + w / 2, y + 9, caption)


def draw_table(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    col_widths: Sequence[float],
    rows: Sequence[Sequence[str]],
    *,
    font_size: float = 12,
    leading: float = 18,
    cell_pad: float = 9,
    min_row_h: float = 38,
    centered_columns: set[int] | None = None,
) -> float:
    centered_columns = centered_columns or set()
    y = y_top
    total_w = sum(col_widths)
    for ridx, row in enumerate(rows):
        is_header = ridx == 0
        font = "TNR-Bold" if is_header else "TNR"
        line_sets = [
            fit_lines(str(value), width - 2 * cell_pad, font, font_size)
            for value, width in zip(row, col_widths, strict=True)
        ]
        row_h = max(min_row_h, max(len(lines) for lines in line_sets) * leading + 2 * cell_pad)
        y -= row_h
        fill = BLACK if is_header else (white if ridx % 2 else PALE_YELLOW)
        text_color = white if is_header else CHARCOAL
        c.setFillColor(fill)
        c.rect(x, y, total_w, row_h, fill=1, stroke=0)
        if is_header:
            c.setFillColor(YELLOW)
            c.rect(x, y + row_h - 5, total_w, 5, fill=1, stroke=0)
        xpos = x
        for col_idx, (lines, width) in enumerate(zip(line_sets, col_widths, strict=True)):
            c.setStrokeColor(LINE if not is_header else BLACK)
            c.setLineWidth(0.6)
            c.rect(xpos, y, width, row_h, fill=0, stroke=1)
            c.setFillColor(text_color)
            c.setFont(font, font_size)
            text_h = len(lines) * leading
            ty = y + (row_h + text_h) / 2 - leading + 3
            for line in lines:
                if col_idx in centered_columns:
                    c.drawCentredString(xpos + width / 2, ty, line)
                else:
                    c.drawString(xpos + cell_pad, ty, line)
                ty -= leading
            xpos += width
    return y


def connector(c: canvas.Canvas, x1: float, y1: float, x2: float, y2: float) -> None:
    c.setStrokeColor(YELLOW_DARK)
    c.setFillColor(YELLOW_DARK)
    c.setLineWidth(2.2)
    c.line(x1, y1, x2, y2)
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        c.line(x2, y2, x2 - 8 * direction, y2 + 5)
        c.line(x2, y2, x2 - 8 * direction, y2 - 5)
    else:
        direction = 1 if y2 > y1 else -1
        c.line(x2, y2, x2 - 5, y2 - 8 * direction)
        c.line(x2, y2, x2 + 5, y2 - 8 * direction)


def workflow_row(
    c: canvas.Canvas,
    steps: Sequence[tuple[str, str]],
    x: float,
    y: float,
    total_w: float,
    h: float,
) -> None:
    gap = 19
    box_w = (total_w - gap * (len(steps) - 1)) / len(steps)
    mid_y = y + h / 2
    for idx in range(len(steps) - 1):
        x1 = x + (idx + 1) * box_w + idx * gap + 3
        x2 = x + (idx + 1) * (box_w + gap) - 3
        connector(c, x1, mid_y, x2, mid_y)
    for idx, (title, description) in enumerate(steps, 1):
        bx = x + (idx - 1) * (box_w + gap)
        rounded_panel(c, bx, y, box_w, h, fill=white, stroke=BLACK, radius=7)
        c.setFillColor(BLACK)
        c.rect(bx, y + h - 32, box_w, 32, fill=1, stroke=0)
        c.setFillColor(YELLOW)
        c.setFont("TNR-Bold", 12)
        c.drawString(bx + 11, y + h - 21, f"{idx:02d}")
        c.setFillColor(white)
        c.setFont("TNR-Bold", 12)
        c.drawString(bx + 39, y + h - 21, title)
        draw_text(c, description, bx + 11, y + h - 50, box_w - 22, size=10.5, leading=15.75, max_lines=4)


def scan_caption(code: str) -> str:
    return code.replace("__", " - ").replace("_", " ")


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
    c.setTitle("PerforaAR 3B Rekonstrüksiyon ve AR Görselleştirme Teknik Raporu")
    c.setAuthor("Eyasu Desalegne Beyene")
    c.setCreator("PerforaAR Teknik Dokümantasyon")
    c.setSubject("PerforaAR yazılımı, doğrulama deneyleri ve 3B görselleştirme")

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

    # 1 Cover
    c.setFillColor(BLACK)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.rect(0, 0, 18, PAGE_H, fill=1, stroke=0)
    c.rect(54, PAGE_H - 74, 165, 32, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 15)
    c.drawCentredString(136.5, PAGE_H - 63, "PERFORAAR")
    c.setFillColor(white)
    c.setFont("TNR-Bold", 32)
    c.drawString(54, PAGE_H - 128, "İzlenen Ultrason Verilerinden")
    c.drawString(54, PAGE_H - 170, "3B Rekonstrüksiyon")
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 23)
    c.drawString(54, PAGE_H - 207, "Teknik ve Görsel Rapor")
    draw_text(
        c,
        "Yazılım mimarisi, doğrulama deneyleri, üç boyutlu nesne örnekleri ve artırılmış gerçeklik aktarım yaklaşımı",
        54,
        PAGE_H - 241,
        650,
        size=12,
        leading=18,
        color=white,
        max_lines=2,
    )
    draw_image_fit(c, ar_dir / "surface_gallery.png", 54, 103, 734, 215, background=BLACK, border=False, pad=0)
    c.setStrokeColor(YELLOW)
    c.setLineWidth(1.3)
    c.rect(54, 103, 734, 215, fill=0, stroke=1)
    c.setFont("TNR", 11)
    c.setFillColor(white)
    c.drawString(54, 76, "Hazırlayan: Eyasu Desalegne Beyene")
    c.drawCentredString(PAGE_W / 2, 76, "Sürüm 2.0")
    c.drawRightString(PAGE_W - 54, 76, "Eylül 2026")
    c.setFillColor(YELLOW)
    c.rect(54, 50, 734, 2, fill=1, stroke=0)
    c.setFont("TNR-Italic", 10)
    c.setFillColor(white)
    c.drawString(54, 33, "Bu belge araştırma ve mühendislik değerlendirmesi içindir.")

    # 2 Purpose
    y = new_page(c, 2, "Belge kapsamı", "Raporun amacı ve sınırları")
    rounded_panel(c, MARGIN_X, 290, 470, 176, fill=white)
    section_label(c, "Bu rapor neyi gösterir", MARGIN_X + 18, 431, 220)
    draw_text(c, "PerforaAR yazılımının mevcut sürümü iki kamusal veri seti üzerinde sınanmıştır. Bu rapor, izlenen ultrason görüntülerinden hacim üretimini, kalite denetimini, üç boyutlu yüzey oluşturmayı ve artırılmış gerçeklik için hazırlanan sahne bilgisini tek belgede toplar.", MARGIN_X + 18, 397, 434)
    rounded_panel(c, 537, 290, 257, 176, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    section_label(c, "Kapsam sınırı", 555, 431, 150)
    draw_text(c, "TUS hacimleri gri ölçekli B mod anatomisini gösterir. Bunlar damar segmentasyonu değildir. Dryad deneyi sanal kesit kullanır. Sonuçlar klinik doğruluk veya hasta güvenliği iddiası oluşturmaz.", 555, 397, 220)
    for idx, (value, label) in enumerate([("2", "Kamusal veri seti"), ("6", "TUS rekonstrüksiyonu"), ("90", "Stres testi koşulu"), ("35", "Raporlanan görsel")]):
        metric_card(c, MARGIN_X + idx * 190, 168, 176, 91, value, label)
    rounded_panel(c, MARGIN_X, 62, CONTENT_W, 78, fill=SOFT_GREY)
    draw_text(c, "Belgenin okuma sırası: önce sistem yaklaşımı ve veri sözleşmesi, sonra Dryad ve TUS sonuçları, ardından üç boyutlu nesneler, gözlük arayüzü ve tamamlanması gereken doğrulamalar.", MARGIN_X + 18, 116, CONTENT_W - 36)

    # 3 System approach
    y = new_page(c, 3, "Sistem yaklaşımı", "Seçilen yöntem: 2B renkli Doppler, optik izleyici ve katı bacak referansı")
    draw_text(c, "Probla elde edilen ardışık görüntüler, ölçülmüş pozlarla ortak bir koordinat sistemine taşınır. Bacak üzerindeki ikinci hedef uzuv hareketini ayırır. Aynı bölgeye ait geçerli gözlemler birleştirilerek üç boyutlu kanıt haritası üretilir.", MARGIN_X, y, CONTENT_W)
    workflow_row(c, [("Alım", "Görüntü ve zaman damgası kaydedilir."), ("Takip", "Prob ve bacak hedefi aynı anda ölçülür."), ("Kalibrasyon", "Görüntü noktaları fiziksel ölçüye çevrilir."), ("Bileştirme", "Geçerli gözlemler hacimde birleştirilir."), ("Görselleştirme", "Hacim ve yüzey denetlenerek gösterilir.")], MARGIN_X, 270, CONTENT_W, 126)
    rounded_panel(c, MARGIN_X, 73, 360, 164, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    section_label(c, "Neden iki hedef gerekir", MARGIN_X + 18, 205, 205)
    draw_text(c, "Yalnızca prob izlenirse bacak hareket ettiğinde harita eski konumda kalır. Bacak hedefi, gözlemleri uzva bağlı bir çerçevede saklamayı ve daha sonra doğru konuma taşımayı sağlar.", MARGIN_X + 18, 171, 324)
    rounded_panel(c, 424, 73, 370, 164, fill=white)
    section_label(c, "Geçersiz kare kararı", 442, 205, 190)
    draw_text(c, "Prob veya bacak hedefi görünmüyorsa kare kullanılmaz. İnterpolasyon yalnızca önceden tanımlanmış zaman ve hareket sınırları içinde uygulanır. Her red kararı denetim kaydında tutulur.", 442, 171, 334)

    # 4 Data contract and coordinates
    y = new_page(c, 4, "Veri sözleşmesi ve koordinat zinciri", "Her görüntü karesi, konum ve kalite bilgisiyle birlikte işlenir")
    rounded_panel(c, MARGIN_X, 230, 345, 234, fill=white)
    section_label(c, "Her geçerli kare için kayıt", MARGIN_X + 18, 430, 230)
    numbered_items(c, ["Ultrason veya Doppler görüntüsü", "Görüntü zaman damgası", "Prob hedefinin ölçülmüş pozu", "Bacak referansının ölçülmüş pozu", "Kalibrasyon kimliği ve takip durumu"], MARGIN_X + 18, 393, 309, size=11.5, leading=17.25, gap=4)
    rounded_panel(c, 414, 230, 380, 234, fill=BLACK, stroke=BLACK)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 13)
    c.drawString(434, 430, "DÖNÜŞÜM SIRASI")
    ty = 392
    for idx, item in enumerate(["Görüntü noktası prob hedefine taşınır.", "Prob hedefi optik izleyici çerçevesine taşınır.", "Bacak hedefinin ölçümü çıkarılır.", "Sonuç bacak referansı içinde saklanır."], 1):
        c.setFillColor(YELLOW)
        c.circle(449, ty + 2, 13, fill=1, stroke=0)
        c.setFillColor(BLACK)
        c.setFont("TNR-Bold", 11)
        c.drawCentredString(449, ty - 2, str(idx))
        ty = draw_text(c, item, 475, ty + 5, 295, color=white, max_lines=2)
        ty -= 10
    rounded_panel(c, MARGIN_X, 63, CONTENT_W, 136, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    section_label(c, "Kalite kapısı", MARGIN_X + 18, 165, 125)
    draw_text(c, "Takip kaybı, aşırı kayıt hatası, zaman uyuşmazlığı veya bozuk görüntü saptandığında ilgili kare hacme eklenmez. Kayıt kalitesi kabul sınırını aşarsa gözlük üzerindeki bindirme görünür biçimde zayıflatılır veya kapatılır.", MARGIN_X + 18, 131, CONTENT_W - 36)

    # 5 Architecture
    y = new_page(c, 5, "Yazılım mimarisi", "Modüler yapı, denetlenebilir çıktı ve güvenli başarısızlık ilkesi")
    modules = [("Alım adaptörü", "Görüntü, zaman, poz ve yakalama durumunu alır."), ("Kanıt üretimi", "Maske veya yoğunluk bilgisini ortak biçime çevirir."), ("Uzamsal bileştirme", "Tekrar gözlemlerini fiziksel hacimde birleştirir."), ("Aday haritası", "Konum, derinlik, güven ve sıralama bilgisi üretir."), ("Kayıt modülü", "Hacim ile bacak referansı arasındaki ilişkiyi kurar."), ("Görselleştirme", "Hacim, kesit, yüzey ve kalite görünümünü sunar."), ("Denetim kaydı", "Ayarları, uyarıları ve kullanıcı işlemlerini saklar."), ("Kalite kapıları", "Takip veya veri hatasında gösterimi güvenli biçimde durdurur.")]
    for idx, (title, desc) in enumerate(modules):
        col, row = idx % 2, idx // 2
        x = MARGIN_X + col * 382
        yy = 377 - row * 91
        rounded_panel(c, x, yy, 365, 78, fill=white, stroke=BLACK)
        c.setFillColor(BLACK)
        c.rect(x, yy, 47, 78, fill=1, stroke=0)
        c.setFillColor(YELLOW)
        c.setFont("TNR-Bold", 13)
        c.drawCentredString(x + 23.5, yy + 46, f"{idx + 1:02d}")
        c.setFillColor(BLACK)
        c.drawString(x + 62, yy + 53, title)
        draw_text(c, desc, x + 62, yy + 32, 289, size=10.5, leading=15.75, max_lines=2)
    rounded_panel(c, MARGIN_X, 58, CONTENT_W, 42, fill=BLACK, stroke=BLACK)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 12)
    c.drawString(MARGIN_X + 16, 75, "Emniyet ilkesi")
    c.setFillColor(white)
    c.setFont("TNR", 11.5)
    c.drawString(MARGIN_X + 122, 75, "Sistem belirsiz durumda sessizce devam etmez. Kullanıcıya açık uyarı verir ve bindirmeyi sınırlar.")

    # 6 Viewer design
    y = new_page(c, 6, "3B rekonstrüksiyon görüntüleyicisi", "Araştırmacı arayüzü: inceleme, kalite denetimi ve dışa aktarma")
    rounded_panel(c, MARGIN_X, 67, 515, 398, fill=SOFT_GREY, stroke=BLACK, radius=10)
    c.setFillColor(BLACK)
    c.rect(MARGIN_X, 426, 515, 39, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 13)
    c.drawString(MARGIN_X + 16, 440, "PerforaAR 3B Görüntüleyici")
    c.setFillColor(white)
    c.rect(MARGIN_X + 16, 91, 126, 319, fill=1, stroke=0)
    cy = 385
    for idx, label in enumerate(["Tarama", "Eşik", "Opaklık", "X ekseni", "Y ekseni", "Z ekseni"]):
        c.setFillColor(BLACK)
        c.setFont("TNR-Bold", 10.5)
        c.drawString(MARGIN_X + 28, cy, label)
        c.setFillColor(SOFT_GREY)
        c.roundRect(MARGIN_X + 28, cy - 24, 101, 16, 3, fill=1, stroke=0)
        if idx:
            c.setFillColor(YELLOW)
            c.rect(MARGIN_X + 34, cy - 18, 47 + idx * 6, 4, fill=1, stroke=0)
        cy -= 47
    tx = MARGIN_X + 160
    for idx, label in enumerate(["Etkileşimli 3B", "Kesitler", "Kalite", "Aktarım"]):
        c.setFillColor(YELLOW if idx == 0 else white)
        c.roundRect(tx, 392, 82, 24, 4, fill=1, stroke=0)
        c.setFillColor(BLACK)
        c.setFont("TNR-Bold", 9.5)
        c.drawCentredString(tx + 41, 401, label)
        tx += 89
    draw_image_fit(c, ar_dir / "050__RH_Per_S_DtP__full_20fps__surface_preview.png", MARGIN_X + 160, 120, 335, 257, background=BLACK, border=False, pad=0)
    c.setFillColor(BLACK)
    c.roundRect(MARGIN_X + 160, 86, 158, 24, 4, fill=1, stroke=0)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 10.5)
    c.drawCentredString(MARGIN_X + 239, 95, "3B yüzey oluştur")
    c.setFillColor(white)
    c.roundRect(MARGIN_X + 329, 86, 166, 24, 4, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.drawCentredString(MARGIN_X + 412, 95, "Sahne bilgisini kaydet")
    rounded_panel(c, 582, 67, 212, 398, fill=white, stroke=BLACK)
    section_label(c, "Çalışma alanları", 600, 431, 158)
    numbered_items(c, ["Fiziksel koordinatlarda hacim ve yüzey incelemesi", "Aksiyel, koronal ve sagittal kesit görünümü", "Prob yörüngesi ve geçerli piksel maskesi denetimi", "GLB yüzeyi ve sahne bilgisinin dışa aktarımı"], 600, 393, 176, size=10.5, leading=15.75, gap=12)
    rounded_panel(c, 600, 84, 176, 72, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 11)
    c.drawString(614, 132, "Çıktılar")
    draw_text(c, "NIfTI hacmi, GLB yüzeyi, JSON sahne kaydı ve PNG önizleme", 614, 112, 148, size=10.5, leading=15.75, max_lines=3)

    # 7 Datasets
    y = new_page(c, 7, "Veri setleri ve kanıt düzeyi", "Her deney farklı bir teknik soruyu yanıtlar")
    dataset_rows = [["Kaynak", "İçerik", "PerforaAR içindeki rol", "Temel sınırlılık"], ["Dryad 4D CUSI", "Gerçek üç boyutlu renkli Doppler ve power Doppler NIfTI hacimleri", "Dönüşüm, bileştirme ve seyrek kesit yazılım testi", "Fare beyni. İki boyutlu kareler referans hacimden sanal olarak türetilmiştir."], ["TUS REC2024", "Gerçek iki boyutlu B mod kareleri ve ölçülmüş prob pozları", "Serbest el üç boyutlu rekonstrüksiyon ve stres testleri", "Renkli Doppler ve perforatör etiketi yoktur. Referans iç üretimdir."], ["Planlanan fantom", "İzlenen renkli Doppler ve bilinen kanal geometrisi", "Bağımsız uzamsal doğruluk ve merkez çizgisi hatası", "Henüz gerçekleştirilmemiştir."], ["Planlanan gönüllü", "Etik onaylı ve girişimsel olmayan tarama", "Tekrarlanabilirlik ve kullanılabilirlik", "Klinik etkinlik testi değildir."]]
    draw_table(c, MARGIN_X, 469, [125, 195, 205, 222], dataset_rows, font_size=11, leading=16.5, min_row_h=45)

    # 8 Evidence ladder
    y = new_page(c, 8, "Kanıt zinciri", "Tamamlanan çalışmalar ve sıradaki doğrulama basamakları")
    stages = [("Yazılım testleri", "Tamamlandı", "Geometri, bileştirme ve dosya işlemleri otomatik testlerle doğrulandı."), ("Dryad sanal kesit testi", "Tamamlandı", "Renkli Doppler hacminde dönüşüm ve seyrek örnekleme davranışı ölçüldü."), ("TUS izlenen B mod pilotu", "Tamamlandı", "Gerçek kareler ve ölçülmüş pozlarla altı hacim üretildi."), ("Vasküler akış fantomu", "Sıradaki", "Bilinen damar geometrisiyle milimetre tabanlı bağımsız doğruluk ölçülecek."), ("Gönüllü fizibilitesi", "Sonraki aşama", "Etik onay sonrası tekrarlanabilirlik ve kullanılabilirlik değerlendirilecek.")]
    sy = 398
    for idx, (title, state, description) in enumerate(stages, 1):
        rounded_panel(c, MARGIN_X + 62, sy, 670, 67, fill=white, stroke=BLACK)
        c.setFillColor(BLACK)
        c.circle(MARGIN_X + 25, sy + 33.5, 23, fill=1, stroke=0)
        c.setFillColor(YELLOW)
        c.setFont("TNR-Bold", 15)
        c.drawCentredString(MARGIN_X + 25, sy + 28, f"{idx:02d}")
        c.setFillColor(BLACK)
        c.setFont("TNR-Bold", 13)
        c.drawString(MARGIN_X + 80, sy + 42, title)
        c.setFillColor(YELLOW_DARK)
        c.setFont("TNR-Bold", 11)
        c.drawRightString(MARGIN_X + 714, sy + 42, state)
        draw_text(c, description, MARGIN_X + 80, sy + 21, 600, size=10.5, leading=15.75, max_lines=2)
        if idx < len(stages):
            connector(c, MARGIN_X + 25, sy - 2, MARGIN_X + 25, sy - 18)
        sy -= 82

    # 9 Dryad method and metrics
    y = new_page(c, 9, "Dryad THY3 yazılım doğrulaması", "Sanal izlenen kesitlerden renkli Doppler hacmi oluşturma")
    for idx, (value, label) in enumerate([("GEÇTİ", "Önceden tanımlı aşama ölçütleri"), ("40 mikron", "İzotropik örnekleme"), ("2 hacim", "Uyanık ve anestezi koşulu"), ("160 mikron", "Seyrek düzlem aralığı")]):
        metric_card(c, MARGIN_X + idx * 190, 370, 176, 93, value, label)
    rounded_panel(c, MARGIN_X, 156, 315, 188, fill=white)
    section_label(c, "Yöntem", MARGIN_X + 18, 311, 105)
    numbered_items(c, ["Power hacminde en yüksek yüzde bir, sabit damar maskesi olarak seçildi.", "Kesitler çıkarıldı ve bilinen konumlar atandı.", "Tam, seyrek ve kare kaybı koşulları çalıştırıldı.", "Dice, yüzey Dice, power hatası ve akış yönü uyumu hesaplandı."], MARGIN_X + 18, 275, 279, size=10.5, leading=15.75, gap=4)
    dryad_rows = [["Koşul", "Uyanık Dice", "Uyanık yüzey", "Anestezi Dice", "Anestezi yüzey", "Akış yönü"], ["Tam", "1,0000", "1,0000", "1,0000", "1,0000", "%100,00"], ["Seyrek", "0,8513", "0,9732", "0,8343", "0,9631", "%98,49 ve %98,63"], ["Seyrek ve yüzde 20 kayıp", "0,7080", "0,8392", "0,7253", "0,8577", "%93,69 ve %95,01"]]
    draw_table(c, 383, 344, [90, 67, 70, 72, 74, 74], dryad_rows, font_size=10.5, leading=15.75, min_row_h=43, centered_columns={1, 2, 3, 4, 5})
    rounded_panel(c, MARGIN_X, 61, CONTENT_W, 72, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    draw_text(c, "Tam düzlem tekrarı kayıpsızdır. Seyrek örneklemede ana damar gövdeleri ve akış yönü büyük ölçüde korunur. Hata ince damar sınırlarında ve küçük dallarda yoğunlaşır.", MARGIN_X + 18, 108, CONTENT_W - 36, size=11.5, leading=17.25)

    # 10 and 11 Dryad figures
    y = new_page(c, 10, "Dryad sonucu: uyanık koşul", "Referans, seyrek rekonstrüksiyon ve mutlak hata")
    draw_image_fit(c, dryad_dir / "awake_sparse_reconstruction.png", MARGIN_X, 87, CONTENT_W, 378, pad=2)
    draw_text(c, "Şekil 1. Sol sütun referans hacmi, orta sütun seyrek rekonstrüksiyonu, sağ sütun mutlak hatayı gösterir. Üst sıra power Doppler, alt sıra akış yönüdür.", MARGIN_X, 68, CONTENT_W, size=10.5, leading=15.75, color=MID_GREY, max_lines=2)
    y = new_page(c, 11, "Dryad sonucu: anestezi koşulu", "Daha büyük hacimde seyrek örnekleme ve akış yönü korunumu")
    draw_image_fit(c, dryad_dir / "anesthetized_sparse_reconstruction.png", MARGIN_X, 87, CONTENT_W, 378, pad=2)
    draw_text(c, "Şekil 2. Seyrek koşul 61 düzlem içerir. Damar maskesi Dice değeri 0,8343, iki voksel toleranslı yüzey Dice değeri 0,9631 ve akış yönü uyumu yüzde 98,63 olarak ölçülmüştür.", MARGIN_X, 68, CONTENT_W, size=10.5, leading=15.75, color=MID_GREY, max_lines=2)

    # 12 TUS overview
    y = new_page(c, 12, "TUS REC2024 izlenen rekonstrüksiyon", "Gerçek ultrason kareleri, prob kalibrasyonu ve ölçülmüş pozlar")
    for idx, (value, label) in enumerate([("72 eşleşme", "Doğrulanan kare ve dönüşüm çifti"), ("6 hacim", "Üretilen iç referans"), ("90 koşul", "Çalıştırılan stres testi"), ("0,1267", "En yüksek ham union NRMSE")]):
        metric_card(c, MARGIN_X + idx * 190, 372, 176, 91, value, label)
    rounded_panel(c, MARGIN_X, 159, 360, 185, fill=white)
    section_label(c, "Rekonstrüksiyon adımları", MARGIN_X + 18, 311, 215)
    numbered_items(c, ["Kare ve poz verisinin sıra ve bütünlük kontrolü", "Görüntü noktalarının kamera çerçevesine taşınması", "Geçerli piksel maskesi ve ağırlıklı voksel bileştirme", "Küçük ve çevrili hacim boşluklarının doldurulması", "İki milimetre izotropik NIfTI üretimi"], MARGIN_X + 18, 276, 324, size=10.5, leading=15.75, gap=2)
    tus_key = [["Kod", "Anlam", "Yön"], ["RH ve LH", "Sağ ve sol ön kol", "Bölge"], ["Per ve Par", "Dik ve paralel prob", "Prob"], ["S, C ve L", "Tarama yörüngesi", "Yörünge"], ["PtD", "Proksimalden distale", "İleri"], ["DtP", "Distalden proksimale", "Ters"]]
    draw_table(c, 426, 344, [95, 195, 78], tus_key, font_size=10.5, leading=15.75, min_row_h=37, centered_columns={0, 2})
    rounded_panel(c, MARGIN_X, 61, CONTENT_W, 72, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    draw_text(c, "İç referans, tam kare hızında ölçülmüş pozlarla oluşturulan hacimdir. Bağımsız anatomik doğruluk referansı değildir. Stres testleri yazılımın veri kaybı ve takip bozulmasına tepkisini karşılaştırır.", MARGIN_X + 18, 108, CONTENT_W - 36, size=11.5, leading=17.25)

    # 13 Slices
    y = new_page(c, 13, "Hacim kesitleri ve kapsama", "Altı rekonstrüksiyonun aksiyel, koronal, sagittal ve kapsama görünümleri")
    positions = [(MARGIN_X, 337), (429, 337), (MARGIN_X, 192), (429, 192), (MARGIN_X, 47), (429, 47)]
    for code, (x, yy) in zip(scan_codes, positions, strict=True):
        image_tile(c, tus_dir / f"{code}__slices.png", x, yy, 365, 135, scan_caption(code), caption_h=25)

    # 14 Trajectories
    y = new_page(c, 14, "Prob yörüngeleri", "Ölçülmüş kamera koordinatlarında kare merkezleri ve tarama geometrisi")
    positions_traj = [(MARGIN_X + i * 255, 276) for i in range(3)] + [(MARGIN_X + i * 255, 66) for i in range(3)]
    for code, (x, yy) in zip(scan_codes, positions_traj, strict=True):
        image_tile(c, tus_dir / f"{code}__trajectory.png", x, yy, 237, 194, scan_caption(code), caption_h=27)

    # 15 Masks
    y = new_page(c, 15, "Geçerli piksel maskeleri", "Ultrason fanı dışındaki siyah alanların bileştirmeden çıkarılması")
    for code, (x, yy) in zip(scan_codes, positions, strict=True):
        image_tile(c, tus_dir / f"{code}__valid_mask.png", x, yy, 365, 135, scan_caption(code), caption_h=25)

    # 16 Degradation
    y = new_page(c, 16, "Stres testi bozulma profilleri", "Her taramada tam kare hızlı iç referansa göre ham union NRMSE")
    for code, (x, yy) in zip(scan_codes, positions, strict=True):
        image_tile(c, tus_dir / f"{code}__degradation.png", x, yy, 365, 135, scan_caption(code), caption_h=25)

    # 17 Benchmark
    y = new_page(c, 17, "Performans ve hata yorumu", "Piksel örnekleme adımı, işlem hızı ve rekonstrüksiyon kalitesi")
    draw_image_fit(c, tus_dir / "benchmark_stride.png", MARGIN_X, 160, 488, 305, pad=3)
    benchmark_rows = [["Ayar", "İşlem hızı", "NRMSE"], ["Stride 8", "1068,21 kare saniye", "0,0399"], ["Stride 4", "359,20 kare saniye", "0,0184"], ["Stride 2", "75,52 kare saniye", "0,0095"], ["Stride 1", "20,98 kare saniye", "İç referans"]]
    draw_table(c, 553, 465, [74, 112, 55], benchmark_rows, font_size=10.5, leading=15.75, min_row_h=47, centered_columns={0, 1, 2})
    rounded_panel(c, MARGIN_X, 62, CONTENT_W, 74, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    draw_text(c, "Daha sık piksel örnekleme hata ölçütünü iyileştirirken işlem süresini artırır. En yüksek ham union NRMSE, 052 RH Par L DtP taramasında iki milimetre öteleme gürültüsü altında 0,1267 olarak ölçülmüştür.", MARGIN_X + 18, 110, CONTENT_W - 36, size=11.5, leading=17.25)

    # 18 Mesh production
    y = new_page(c, 18, "3B nesne üretimi", "NIfTI hacminden fiziksel ölçekte üçgen yüzeye")
    draw_image_fit(c, ar_dir / "surface_gallery.png", MARGIN_X, 211, CONTENT_W, 255, background=BLACK, pad=0)
    workflow_row(c, [("Hacim", "İki milimetre örnekleme ve fiziksel konum"), ("Eşik", "Sıfır olmayan yoğunlukların yüzde 35 değeri"), ("Yumuşatma", "Bir voksel Gaussian sigma"), ("Yüzey", "Marching cubes ve iki adımlı örnekleme"), ("Aktarım", "Milimetre ölçeğinde GLB ve sahne kaydı")], MARGIN_X, 73, CONTENT_W, 112)
    c.setFillColor(YELLOW)
    c.rect(MARGIN_X, 50, CONTENT_W, 5, fill=1, stroke=0)
    c.setFillColor(BLACK)
    c.setFont("TNR-Bold", 10.5)
    c.drawCentredString(PAGE_W / 2, 35, "Bu yüzeyler B mod anatomi görselleştirmesidir. Damar segmentasyonu değildir.")

    # 19 to 21 Surface variants
    subject_pages = [(19, "050 numaralı tarama: dik prob ve S yörüngesi", scenes[0:2]), (20, "051 numaralı tarama: paralel prob ve C yörüngesi", scenes[2:4]), (21, "052 numaralı tarama: paralel prob ve L yörüngesi", scenes[4:6])]
    for page_no, title, pair in subject_pages:
        y = new_page(c, page_no, "3B nesne varyantları", title)
        for idx, scene in enumerate(pair):
            x = MARGIN_X + idx * 382
            path = ar_dir / f"{scene['stem']}__surface_preview.png"
            label = scene["stem"].replace("__full_20fps", "").replace("__", " - ").replace("_", " ")
            image_tile(c, path, x, 252, 365, 214, label, caption_h=29, background=BLACK, caption_color=white)
            dims = " ile ".join(f"{v:.0f}" for v in scene["physical_extent_mm"])
            shape = " ile ".join(str(v) for v in scene["voxel_shape_xyz"])
            vertices = f"{scene['mesh_vertex_count']:,}".replace(",", ".")
            faces = f"{scene['mesh_face_count']:,}".replace(",", ".")
            rows = [["Özellik", "Değer"], ["Fiziksel boyut", f"{dims} mm"], ["Hacim matrisi", shape], ["Köşe ve yüz sayısı", f"{vertices} köşe, {faces} yüz"], ["Yüzey eşiği", f"{scene['surface_threshold']:.1f}".replace(".", ",")]]
            draw_table(c, x, 231, [127, 238], rows, font_size=10.5, leading=15.75, min_row_h=38)

    # 22 AR integration workflow
    y = new_page(c, 22, "AR sahne paketi ve gözlük entegrasyonu", "Geometri, koordinat bilgisi ve kayıt kalitesi birlikte taşınır")
    workflow_row(c, [("NIfTI", "Voksel aralığı, affine ve fiziksel başlangıç"), ("GLB", "Üçgen yüzey ve milimetre ölçeği"), ("Sahne kaydı", "Koordinat sözleşmesi ve üretim bilgisi"), ("Bacak kaydı", "Hacimden katılımcı referansına dönüşüm"), ("Gözlük", "Dünya ankrajı, görünüm ve kalite durumu")], MARGIN_X, 318, CONTENT_W, 132)
    rounded_panel(c, MARGIN_X, 88, 355, 190, fill=white)
    section_label(c, "Sahne kaydı içeriği", MARGIN_X + 18, 246, 190)
    numbered_items(c, ["NIfTI affine matrisi ve sağ elli eksen tanımı", "Voksel şekli, aralığı ve fiziksel uzanım", "Yüzey üretim parametreleri", "Kaynak hacim ve kayıt gereksinimi"], MARGIN_X + 18, 210, 319, size=10.5, leading=15.75, gap=5)
    rounded_panel(c, 420, 88, 374, 190, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    section_label(c, "Kayıt kapısı", 438, 246, 125)
    draw_text(c, "Katılımcıya özel hacim ile bacak dönüşümü ölçülmeden ve hedef kayıt hatası kabul sınırını geçmeden model hasta üzerinde bindirme olarak gösterilmemelidir.", 438, 210, 338)

    # 23 Glass interface
    y = new_page(c, 23, "Gözlük arayüzü taslağı", "Cerrahi alanda sade görünüm, açık kalite durumu ve hızlı kapatma")
    rounded_panel(c, MARGIN_X, 68, 510, 397, fill=BLACK, stroke=BLACK, radius=12)
    c.setFillColor(YELLOW)
    c.rect(MARGIN_X + 18, 426, 474, 3, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("TNR-Bold", 13)
    c.drawString(MARGIN_X + 24, 442, "PERFORAAR ARAŞTIRMA MODU")
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 11)
    c.drawRightString(MARGIN_X + 486, 442, "TAKİP UYGUN")
    draw_image_fit(c, ar_dir / "051__LH_Par_C_PtD__full_20fps__surface_preview.png", MARGIN_X + 18, 127, 327, 282, background=BLACK, border=False, pad=0)
    rounded_panel(c, MARGIN_X + 360, 263, 132, 146, fill=CHARCOAL, stroke=YELLOW_DARK)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 11)
    c.drawString(MARGIN_X + 375, 386, "DURUM")
    sy = 359
    for label, value in [("Kayıt", "Uygun"), ("Derinlik", "18 mm"), ("Güven", "Orta"), ("Opaklık", "Yüzde 62")]:
        c.setFillColor(white)
        c.setFont("TNR", 10.5)
        c.drawString(MARGIN_X + 375, sy, label)
        c.setFillColor(YELLOW)
        c.setFont("TNR-Bold", 10.5)
        c.drawRightString(MARGIN_X + 477, sy, value)
        sy -= 26
    bx = MARGIN_X + 18
    for idx, label in enumerate(["GÖSTER", "DONDUR", "YENİDEN KAYDET", "TEMİZLE"]):
        bw = 108 if idx < 2 else 120
        c.setFillColor(YELLOW if idx in {0, 3} else white)
        c.roundRect(bx, 88, bw, 27, 4, fill=1, stroke=0)
        c.setFillColor(BLACK)
        c.setFont("TNR-Bold", 10)
        c.drawCentredString(bx + bw / 2, 98, label)
        bx += bw + 10
    rounded_panel(c, 578, 68, 216, 397, fill=white, stroke=BLACK)
    section_label(c, "Arayüz ilkeleri", 596, 431, 158)
    numbered_items(c, ["Anatomi görünümünü kapatmayan sade yerleşim", "Takip ve kayıt kalitesinin sürekli görünmesi", "Derinlik, güven ve belirsizlik bilgisinin açık yazımı", "Tek hareketle bindirmeyi durdurma ve temizleme", "Araştırma modu ve klinik olmayan kullanım uyarısı"], 596, 394, 180, size=10.5, leading=15.75, gap=9)

    # 24 Completed status
    y = new_page(c, 24, "Mevcut durum: tamamlanan işler", "Kod, test ve üretilmiş varlıklar")
    completed_rows = [["Bileşen", "Durum", "Kanıt"], ["3B hacim rekonstrüksiyonu", "Tamamlandı", "Dryad ve TUS deneyleri ile altı NIfTI hacmi üretildi."], ["Etkileşimli görüntüleme", "Tamamlandı", "Kesit, hacim, eşik, kırpma, opaklık ve kalite görünümü çalışıyor."], ["GLB yüzey aktarımı", "Tamamlandı", "Altı fiziksel ölçekli yüzey ve altı önizleme üretildi."], ["Sahne bilgisi aktarımı", "Tamamlandı", "Altı JSON kaydı koordinat ve üretim bilgisini taşıyor."], ["Otomatik testler", "Tamamlandı", "Geometri, bileştirme, landmark ve görüntüleyici testleri geçiyor."], ["Teknik raporlama", "Tamamlandı", "Yöntem, sonuç, sınırlılık ve görseller tek raporda toplandı."]]
    draw_table(c, MARGIN_X, 468, [220, 130, 397], completed_rows, font_size=12, leading=18, min_row_h=47, centered_columns={1})

    # 25 Pending status
    y = new_page(c, 25, "Mevcut durum: tamamlanması gereken işler", "Klinik kullanım düşünülmeden önce kapatılması gereken boşluklar")
    pending_rows = [["Bileşen", "Durum", "Gerekli adım"], ["İzlenen renkli Doppler alımı", "Bekliyor", "Prob, bacak hedefi, görüntü ve poz zamanlarının aynı kayıtta birleştirilmesi"], ["Damar segmentasyonu", "Bekliyor", "Etiketli renkli Doppler ve doğrulanmış maske ile merkez çizgisi"], ["Bağımsız fantom doğruluğu", "Sıradaki", "Bilinen kanal geometrisinde merkez çizgisi ve yüzey mesafesi"], ["Gözlük istemcisi", "Tasarım aşaması", "Hedef cihaz, OpenXR uygulaması ve kayıt kalite kapısı"], ["Gönüllü değerlendirmesi", "Kapsam dışı", "Etik onay ve ayrı araştırma protokolü"]]
    draw_table(c, MARGIN_X, 468, [220, 140, 387], pending_rows, font_size=12, leading=18, min_row_h=52, centered_columns={1})
    rounded_panel(c, MARGIN_X, 62, CONTENT_W, 74, fill=BLACK, stroke=BLACK)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 12)
    c.drawString(MARGIN_X + 18, 110, "Karar noktası")
    draw_text(c, "Yeni bir görsel varyanttan önce gerçek izlenen renkli Doppler alımı ve bağımsız vasküler fantom doğrulaması yapılmalıdır.", MARGIN_X + 18, 88, CONTENT_W - 36, color=white, max_lines=2)

    # 26 Next experiment
    y = new_page(c, 26, "Sıradaki deney: vasküler akış fantomu", "Bilinen geometriyle bağımsız uzamsal doğruluk ölçümü")
    workflow_row(c, [("Fantom", "Bilinen çap ve merkez çizgisine sahip akış kanalı"), ("Alım", "İzlenen renkli Doppler kareleri ve zaman eşleştirmesi"), ("Rekonstrüksiyon", "Kalibrasyon ve bacak referansıyla üç boyutlu harita"), ("Karşılaştırma", "Referans geometriye yüzey ve merkez çizgisi mesafesi"), ("Rapor", "Hata dağılımı, dayanıklılık ve gecikme")], MARGIN_X, 318, CONTENT_W, 132)
    rounded_panel(c, MARGIN_X, 75, 360, 202, fill=white)
    section_label(c, "Birincil ölçümler", MARGIN_X + 18, 244, 175)
    numbered_items(c, ["Merkez çizgisi hatası, milimetre", "Yüzey mesafesi, milimetre", "Hedef kayıt hatası", "Kare kaybına dayanıklılık", "Uçtan uca gecikme"], MARGIN_X + 18, 207, 324, size=10.5, leading=15.75, gap=3)
    rounded_panel(c, 424, 75, 370, 202, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    section_label(c, "Başarı ölçütü", 442, 244, 145)
    draw_text(c, "Ölçütler deneyden önce sabitlenmeli, tüm tekrarlar aynı kalibrasyonla çalıştırılmalı ve hata dağılımı tek bir ortalama yerine yüzde 95 sınırıyla birlikte raporlanmalıdır. Takip kaybı ve gecikme koşulları ayrıca gösterilmelidir.", 442, 207, 334)

    # 27 Reproducibility and conclusion
    y = new_page(c, 27, "Tekrarlanabilirlik ve kaynaklar", "Sürüm kontrollü çıktılar, veri kökeni ve sonuç")
    rounded_panel(c, MARGIN_X, 254, 355, 211, fill=white)
    section_label(c, "Sürüm kontrollü çıktılar", MARGIN_X + 18, 431, 210)
    numbered_items(c, ["Dryad metrikleri, veri kökeni ve iki doğrulama şekli", "Altı TUS NIfTI hacmi, 90 koşulun ölçütleri ve kalite görselleri", "Altı GLB yüzeyi, altı JSON sahne kaydı ve altı PNG önizleme", "Veri hazırlama, rekonstrüksiyon, performans ve aktarım komutları", "Geometri, bileştirme, landmark ve görüntüleyici testleri"], MARGIN_X + 18, 394, 319, size=10.5, leading=15.75, gap=3)
    rounded_panel(c, 420, 254, 374, 211, fill=PALE_YELLOW, stroke=YELLOW_DARK)
    section_label(c, "Kaynaklar", 438, 431, 110)
    numbered_items(c, ["PerforaAR kaynak kodu, GitHub projesi eyasudesalegne - PerforaAR", "Dryad, Four Dimensional Computational Ultrasound Imaging of Brain Hemodynamics, DOI 10.5061 dryad.w0vt4b8z8", "Science Advances makalesi, DOI 10.1126 sciadv.adk7957", "TUS REC2024 Validation Dataset sürüm 2.0.0, DOI 10.5281 zenodo.12979481"], 438, 394, 338, size=10.5, leading=15.75, gap=6)
    rounded_panel(c, MARGIN_X, 65, CONTENT_W, 158, fill=BLACK, stroke=BLACK)
    c.setFillColor(YELLOW)
    c.setFont("TNR-Bold", 13)
    c.drawString(MARGIN_X + 20, 192, "SON DEĞERLENDİRME")
    draw_text(c, "PerforaAR, izlenen ultrason verisinden üç boyutlu hacim, kalite çıktısı ve fiziksel ölçekli yüzey üreten zincirin çalıştığını göstermektedir. Dryad testi dönüşüm ve seyrek örnekleme davranışını, TUS pilotu ise gerçek kareler ve ölçülmüş pozlarla hacim oluşumunu doğrular. Klinik yorum için gerçek izlenen renkli Doppler ve bağımsız fantom doğrulaması hâlâ gereklidir.", MARGIN_X + 20, 164, CONTENT_W - 40, color=white)

    c.save()
    print(OUT)


if __name__ == "__main__":
    build_report()
