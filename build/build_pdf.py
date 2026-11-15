"""Genera entrega/TP4_Entrega.pdf con la estética del TP3 (ReportLab).

El contenido, el orden y la numeración son los mismos que los del .docx: se reutilizan la lectura
de capítulos y el armado de build_docx.py; acá cambia solo cómo se dibuja cada bloque.

Uso: python3 entrega/build_pdf.py
"""
import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, ListFlowable, ListItem, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle, XPreformatted)
from reportlab.platypus.tableofcontents import TableOfContents

import build_docx as bd

SALIDA = bd.RAIZ / "entrega" / "TP4_Entrega.pdf"
FUENTES = Path("/Applications/Microsoft Word.app/Contents/Resources/DFonts")

# --- estética del TP3 --------------------------------------------------------
AZUL = colors.HexColor("#2F5496")
AZUL_OSCURO = colors.HexColor("#1F3864")
CELESTE = colors.HexColor("#EEF3F8")
GRUPO = colors.HexColor("#D9E2F3")
GRIS = colors.HexColor("#5F6B7A")
TEXTO = colors.HexColor("#1A1A1A")
LINEA = colors.HexColor("#C9D3E0")
MARGEN_IZQ = MARGEN_DER = 2.2 * cm
ANCHO = A4[0] - MARGEN_IZQ - MARGEN_DER

ENC_IZQ = "Cátedra: Desarrollo con Tecnologías Blockchain"
ENC_DER = "2026 · 5K3 · Actividad 4"
PIE_IZQ = "Actividad 4: Modelado de un contrato inteligente · Canje protegido"


def registrar_fuentes():
    for nombre, archivo in [("Calibri", "Calibri.ttf"), ("Calibri-Bold", "Calibrib.ttf"),
                            ("Calibri-Italic", "Calibrii.ttf"), ("Calibri-BoldItalic", "Calibriz.ttf")]:
        pdfmetrics.registerFont(TTFont(nombre, str(FUENTES / archivo)))
    pdfmetrics.registerFontFamily("Calibri", normal="Calibri", bold="Calibri-Bold",
                                  italic="Calibri-Italic", boldItalic="Calibri-BoldItalic")


def estilo(nombre, **kw):
    base = dict(fontName="Calibri", fontSize=10.5, leading=14.2, textColor=TEXTO, alignment=TA_JUSTIFY, spaceAfter=6)
    base.update(kw)
    return ParagraphStyle(nombre, **base)


E = {}


def crear_estilos():
    E["cuerpo"] = estilo("cuerpo")
    E["h1"] = estilo("h1", fontName="Calibri-Bold", fontSize=19, leading=23, textColor=AZUL, alignment=TA_LEFT,
                     spaceBefore=4, spaceAfter=12, keepWithNext=1)
    E["h2"] = estilo("h2", fontName="Calibri-Bold", fontSize=13.5, leading=17, textColor=AZUL, alignment=TA_LEFT,
                     spaceBefore=12, spaceAfter=6, keepWithNext=1)
    E["h3"] = estilo("h3", fontName="Calibri-Bold", fontSize=11.5, leading=15, alignment=TA_LEFT,
                     spaceBefore=9, spaceAfter=4, keepWithNext=1)
    E["h4"] = estilo("h4", fontName="Calibri-BoldItalic", fontSize=10.5, leading=14, textColor=AZUL, alignment=TA_LEFT,
                     spaceBefore=7, spaceAfter=3, keepWithNext=1)
    E["lista"] = estilo("lista", spaceAfter=2.5)
    E["celda"] = estilo("celda", fontSize=8.8, leading=11, alignment=TA_LEFT, spaceAfter=0)
    E["celda_enc"] = estilo("celda_enc", fontName="Calibri-Bold", fontSize=8.8, leading=11, alignment=TA_LEFT,
                            spaceAfter=0, textColor=colors.white)
    E["epigrafe"] = estilo("epigrafe", fontName="Calibri-Italic", fontSize=8.8, leading=11.5, textColor=GRIS,
                           alignment=TA_CENTER, spaceBefore=4, spaceAfter=12)
    E["subtitulo"] = estilo("subtitulo", textColor=GRIS, alignment=TA_LEFT, spaceAfter=8)
    E["biblio"] = estilo("biblio", leftIndent=22, firstLineIndent=-22, alignment=TA_LEFT, spaceAfter=7)
    E["codigo"] = ParagraphStyle("codigo", fontName="Courier", fontSize=7.4, leading=9.3, textColor=TEXTO)


# --- texto en línea: Markdown → marcado de ReportLab ------------------------
def en_linea(texto):
    codigos = []

    def guardar(m):
        codigos.append(m.group(1))
        return f"\x00{len(codigos) - 1}\x00"

    t = re.sub(r"`([^`]+)`", guardar, texto)
    t = escape(t)
    t = re.sub(r"\[VERIFICAR([^\]]*)\]", r'<font backColor="#FFF200">[VERIFICAR\1]</font>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<i>\1</i>", t)
    for i, c in enumerate(codigos):
        t = t.replace(f"\x00{i}\x00", f'<font face="Courier" size="8.3" color="#1F3864">{escape(c)}</font>')
    return t


# --- documento: misma interfaz que build_docx.Doc ----------------------------
class PdfDoc:
    def __init__(self):
        self.story = []
        self.indice = []
        self.figura = None   # (título, imagen) a la espera de la nota

    def parrafo(self, texto, ppr="", rpr=""):
        p = Paragraph(en_linea(texto), E["cuerpo"])
        if texto.rstrip().endswith(":"):  # introduce una lista: no queda solo al pie
            p.keepWithNext = 1
        self.story.append(p)

    def subtitulo(self, texto):
        self.story.append(Paragraph(en_linea(texto), E["subtitulo"]))

    def biblio(self, texto):
        self.story.append(Paragraph(en_linea(texto), E["biblio"]))

    def figura_titulo(self, texto):
        m = re.match(r"\*\*(Figura \d+\.)\*\*\s*\*(.+)\*$", texto)
        # si la figura sigue a un título, viajan juntos (evita títulos huérfanos al pie)
        previo = self.story.pop() if self.story and getattr(self.story[-1], "style", None) is not None \
            and self.story[-1].style.name.startswith("h") else None
        self.figura = [f"{m.group(1)} {m.group(2)}" if m else texto, None, previo]

    def figura_nota(self, texto):
        titulo, imagen, previo = self.figura
        nota = texto.replace("*Nota.*", "").strip()
        epigrafe = Paragraph(en_linea(f"{titulo.rstrip('.')}. {nota}"), E["epigrafe"])
        self.story.append(KeepTogether([b for b in (previo, imagen, epigrafe) if b is not None]))
        self.figura = None

    def titulo(self, nivel, texto, salto=False, indice=True):
        if salto:
            self.story.append(PageBreak())
        p = Paragraph(escape(texto), E[f"h{nivel}"])
        p._indice = (nivel - 1) if (indice and nivel <= 3) else None
        self.story.append(p)

    def lista(self, items, numerada):
        principales = []
        for nivel, texto in items:
            if nivel == 0 or not principales:
                principales.append([texto, []])
            else:
                principales[-1][1].append(texto)
        elementos = []
        for texto, hijos in principales:
            cont = [Paragraph(en_linea(texto), E["lista"])]
            if hijos:
                cont.append(ListFlowable([ListItem(Paragraph(en_linea(h), E["lista"]), leftIndent=12) for h in hijos],
                                         bulletType="bullet", start="◦", bulletFontName="Calibri", bulletFontSize=9,
                                         bulletColor=AZUL, leftIndent=12))
            elementos.append(ListItem(cont, leftIndent=14))
        if numerada:
            lf = ListFlowable(elementos, bulletType="1", bulletFormat="%s.", bulletFontName="Calibri-Bold",
                              bulletFontSize=10, bulletColor=AZUL, leftIndent=16)
        else:
            lf = ListFlowable(elementos, bulletType="bullet", start="•", bulletFontName="Calibri",
                              bulletFontSize=11, bulletColor=AZUL, leftIndent=14)
        self.story.append(lf)
        self.story.append(Spacer(1, 5))

    def codigo(self, lineas):
        pre = XPreformatted(escape("\n".join(lineas)), E["codigo"])
        t = Table([[pre]], colWidths=[ANCHO])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6F8")),
                               ("LINEBEFORE", (0, 0), (0, -1), 2.5, AZUL),
                               ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        self.story.append(t)
        self.story.append(Spacer(1, 8))

    def tabla(self, filas, primera_negrita=False, ancho=None):
        ncol = max(len(f) for f in filas)
        es_grupo = lambda f: f[0].strip() and all(not c.strip() for c in f[1:])
        limpio = lambda t: re.sub(r"[*`]", "", t)
        cols = [[limpio(f[c]) for f in filas if c < len(f) and not es_grupo(f)] for c in range(ncol)]
        largos = [max([min(len(t), 70) for t in col] or [1]) for col in cols]
        palabra = [max([len(w) for t in col for w in t.split()] or [1]) for col in cols]
        minimos = [min(palabra[c], 14) * 4.9 + 12 for c in range(ncol)]
        if sum(minimos) > ANCHO:
            minimos = [m * ANCHO / sum(minimos) for m in minimos]
        pesos = [max(l, 3) ** 0.85 for l in largos]
        sobrante = ANCHO - sum(minimos)
        anchos = [minimos[c] + sobrante * pesos[c] / sum(pesos) for c in range(ncol)]

        datos, estilos = [], [
            ("BACKGROUND", (0, 0), (-1, 0), AZUL_OSCURO),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINEA),
        ]
        cuerpo = 0
        for i, f in enumerate(filas):
            f = f + [""] * (ncol - len(f))
            if i == 0:
                datos.append([Paragraph(en_linea(c.strip()), E["celda_enc"]) for c in f])
                continue
            if es_grupo(f):
                datos.append([Paragraph(f"<b>{en_linea(f[0].strip())}</b>", E["celda"])] + [""] * (ncol - 1))
                estilos += [("SPAN", (0, i), (-1, i)), ("BACKGROUND", (0, i), (-1, i), GRUPO)]
                continue
            fila = []
            for c, texto in enumerate(f):
                t = en_linea(texto.strip())
                if primera_negrita and c == 0:
                    t = f"<b>{t}</b>"
                st = E["celda"]
                if len(texto.strip()) <= 2:
                    st = ParagraphStyle("centro", parent=st, alignment=TA_CENTER)
                fila.append(Paragraph(t, st))
            datos.append(fila)
            if cuerpo % 2 == 1:
                estilos.append(("BACKGROUND", (0, i), (-1, i), CELESTE))
            cuerpo += 1
        t = Table(datos, colWidths=anchos, repeatRows=1, splitByRow=1)
        t.setStyle(TableStyle(estilos))
        # un título seguido de tabla no arrastra la tabla entera a la hoja siguiente:
        # basta con que entren el título y las primeras filas (la tabla se parte por filas)
        titulos = []
        while self.story and getattr(self.story[-1], "style", None) is not None \
                and self.story[-1].style.name.startswith("h"):
            titulos.insert(0, self.story.pop())
        if titulos:
            self.story.append(CondPageBreak(4 * cm))
            for h in titulos:
                h.keepWithNext = 0
            self.story.extend(titulos)
        self.story.append(t)
        self.story.append(Spacer(1, 10))

    def imagen(self, ruta):
        img = Image(str(ruta))
        escala = min(ANCHO * 0.98 / img.imageWidth, 20.5 * cm / img.imageHeight)
        img.drawWidth, img.drawHeight = img.imageWidth * escala, img.imageHeight * escala
        img.hAlign = "CENTER"
        if self.figura:
            self.figura[1] = img
        else:
            self.story.append(img)


# --- plantilla de página: encabezado y pie del TP3 ----------------------------
class Plantilla(BaseDocTemplate):
    def __init__(self, ruta, **kw):
        super().__init__(ruta, pagesize=A4, leftMargin=MARGEN_IZQ, rightMargin=MARGEN_DER,
                         topMargin=2.4 * cm, bottomMargin=2.1 * cm, **kw)
        marco = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="tp", frames=[marco], onPage=self.decorar)])

    def decorar(self, c, doc):
        n = c.getPageNumber()
        if n == 1:
            return  # la carátula no lleva encabezado ni pie
        ancho, alto = A4
        c.saveState()
        c.setFont("Calibri", 7.5)
        c.setFillColor(GRIS)
        y = alto - 1.45 * cm
        c.drawString(MARGEN_IZQ, y, ENC_IZQ)
        c.drawRightString(ancho - MARGEN_DER, y, ENC_DER)
        c.setStrokeColor(AZUL)
        c.setLineWidth(0.8)
        c.line(MARGEN_IZQ, y - 5, ancho - MARGEN_DER, y - 5)
        c.drawString(MARGEN_IZQ, 1.2 * cm, PIE_IZQ)
        c.restoreState()

    def afterFlowable(self, f):
        nivel = getattr(f, "_indice", None)
        if nivel is not None:
            self.notify("TOCEntry", (nivel, f.getPlainText(), self.page))


class CanvasNumerado(rl_canvas.Canvas):
    """Guarda las páginas y, al cerrar, escribe "Página X de N" (N = total real)."""

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._paginas = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            if self._pageNumber > 1:
                self.setFont("Calibri", 7.5)
                self.setFillColor(GRIS)
                self.drawRightString(A4[0] - MARGEN_DER, 1.2 * cm, f"Página {self._pageNumber} de {total}")
            super().showPage()
        super().save()


# --- partes fijas -----------------------------------------------------------
def logo_utn():
    datos = (Path(__file__).resolve().parent / "logo_utn.png").read_bytes()
    img = Image(BytesIO(datos))
    escala = 2.6 * cm / img.imageWidth
    img.drawWidth, img.drawHeight = img.imageWidth * escala, img.imageHeight * escala
    return img


def caratula():
    c = lambda t, tam, esp=6: Paragraph(t, estilo("car", fontName="Calibri-Bold", fontSize=tam, leading=tam * 1.25,
                                                   alignment=TA_CENTER, spaceAfter=esp))
    lista = estilo("car_lista", fontName="Helvetica", fontSize=9.5, leading=13, alignment=TA_LEFT, spaceAfter=0)
    etiqueta = estilo("car_et", fontName="Helvetica-Bold", fontSize=10.5, alignment=TA_LEFT, spaceBefore=16, spaceAfter=8)
    integrantes = [("Jimenez, Gustavo Martín", "94662", "martinjimenez696@gmail.com"),
                   ("Martos, Leonel Agustín", "94297", "leonelmartos04@gmail.com"),
                   ("Romero, Gastón Alejandro", "75076", "gastiromero@hotmail.com"),
                   ("Scrimaglia, Edgardo", "11077", "edgardo.scrimaglia@gmail.com")]
    viñetas = lambda items: ListFlowable([ListItem(Paragraph(t, lista), leftIndent=12) for t in items],
                                         bulletType="bullet", start="●", bulletFontSize=6, leftIndent=26)
    return [
        Spacer(1, 1.2 * cm),
        c("Universidad Tecnológica Nacional", 16, 8),
        c("Facultad Regional Córdoba", 11, 8),
        c("Ingeniería en Sistemas de Información", 12.5, 14),
        logo_utn(), Spacer(1, 14),
        c("Desarrollo con Tecnologías Blockchain - 5K3", 14, 10),
        c("2026", 12, 14),
        c("Actividad 4: Modelado de un Contrato Inteligente", 16, 4),
        c("«Canje protegido» – contrato e-CanjeProtegido", 12, 30),
        Paragraph("Docentes:", etiqueta),
        viñetas(["Oscar Carlos Medina", "Rubén Aníbal Romero"]),
        Paragraph("Integrantes:", etiqueta),
        viñetas([f'{n} - {l} - <font color="#1155CC"><u><a href="mailto:{m}">{m}</a></u></font>' for n, l, m in integrantes]),
        Paragraph("Fecha de entrega:", etiqueta),
        viñetas(["05/11/2026"]),
    ]


def indice():
    toc = TableOfContents(dotsMinLevel=0)
    toc.levelStyles = [
        estilo("toc0", fontName="Calibri-Bold", fontSize=10, leading=13.5, alignment=TA_LEFT, spaceAfter=1),
        estilo("toc1", fontSize=9.5, leading=12.2, leftIndent=16, alignment=TA_LEFT, spaceAfter=0),
        estilo("toc2", fontSize=8.8, leading=11.5, leftIndent=32, textColor=GRIS, alignment=TA_LEFT, spaceAfter=0),
    ]
    return [PageBreak(), Paragraph("Índice", E["h1"]), toc]


def armar():
    doc = PdfDoc()
    arm = bd.Armador(doc)
    num_desarrollo = arm.numerar(bd.DESARROLLO)
    num_anexo = arm.numerar(bd.ANEXO, prefijo="A.")
    leer = lambda r: (bd.RAIZ / r).read_text(encoding="utf-8").splitlines()

    doc.titulo(1, "Consigna", salto=True)
    arm.markdown(leer("entrega/consigna.md"), "consigna", 1, "", [0])
    doc.titulo(1, "Glosario", salto=True)
    arm.markdown(leer("entrega/glosario.md"), "glosario", 1, "", [0])
    doc.titulo(1, "Desarrollo", salto=True)
    arm.seccion(bd.DESARROLLO, num_desarrollo)
    doc.titulo(1, "Fuentes - Bibliografía", salto=True)
    bd.referencias(doc)
    doc.titulo(1, "Declaración de uso de inteligencia artificial", salto=True)
    bd.declaracion_ia(doc, arm)
    doc.titulo(1, "Anexo: prototipo del contrato en Solidity", salto=True)
    arm.seccion(bd.ANEXO, num_anexo)
    return doc.story


def construir():
    registrar_fuentes()
    crear_estilos()
    story = caratula() + indice() + armar()
    pdf = Plantilla(str(SALIDA), title="Actividad 4: Modelado de un contrato inteligente – Canje protegido",
                    author="Jimenez, Martos, Romero, Scrimaglia",
                    subject="Contrato inteligente e-CanjeProtegido: canje de insumos con seguro paramétrico de sequía")
    pdf.multiBuild(story, canvasmaker=CanvasNumerado)  # varias pasadas internas para el índice
    print(f"OK: {SALIDA.relative_to(bd.RAIZ)} ({pdf.page} páginas)")


if __name__ == "__main__":
    construir()
