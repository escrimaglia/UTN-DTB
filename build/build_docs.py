"""Genera los PDF del TP5 con la estética del TP4 (encabezado, pie, títulos, tablas).

Usa build_pdf.py y build_docx.py de esta carpeta (copias adaptadas del generador del TP4).

Uso (desde TP5/):
  python3 build/build_docs.py docs/TP5_Desarrollo.md --caratula --indice
  python3 build/build_docs.py docs/TP5_Documento_Tecnico.md --indice
  python3 build/build_docs.py docs/TP5_Guia_Demostracion.md

Las imágenes se referencian desde el Markdown como ![x](img/archivo.png), relativas a docs/.
"""
import re
import sys
from pathlib import Path

TP5 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TP5 / "build"))  # build_pdf.py y build_docx.py: copias adaptadas del TP4

from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.platypus import ListFlowable, ListItem, PageBreak, Paragraph, Spacer  # noqa: E402

import build_docx as bd  # noqa: E402
import build_pdf as bp  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
FUENTE = Path(args[0]).resolve()
SALIDA = FUENTE.with_suffix(".pdf")
CARATULA = "--caratula" in sys.argv
INDICE = "--indice" in sys.argv
TITULO = FUENTE.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()

ENC_DER = "2026 · 5K3 · Actividad 5"
PIE = "Actividad 5: Implementación del contrato e-CanjeProtegido · " + TITULO.split("—")[0].strip()


class Plantilla(bp.Plantilla):
    def decorar(self, c, doc):
        if CARATULA and c.getPageNumber() == 1:
            return
        ancho, alto = bp.A4
        c.saveState()
        c.setFont("Calibri", 7.5)
        c.setFillColor(bp.GRIS)
        y = alto - 1.45 * bp.cm
        c.drawString(bp.MARGEN_IZQ, y, bp.ENC_IZQ)
        c.drawRightString(ancho - bp.MARGEN_DER, y, ENC_DER)
        c.setStrokeColor(bp.AZUL)
        c.setLineWidth(0.8)
        c.line(bp.MARGEN_IZQ, y - 5, ancho - bp.MARGEN_DER, y - 5)
        c.drawString(bp.MARGEN_IZQ, 1.2 * bp.cm, PIE)
        c.restoreState()


class Canvas(bp.CanvasNumerado):
    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            if not (CARATULA and self._pageNumber == 1):
                self.setFont("Calibri", 7.5)
                self.setFillColor(bp.GRIS)
                self.drawRightString(bp.A4[0] - bp.MARGEN_DER, 1.2 * bp.cm, f"Página {self._pageNumber} de {total}")
            bp.rl_canvas.Canvas.showPage(self)
        bp.rl_canvas.Canvas.save(self)


def caratula():
    c = lambda t, tam, esp=6: Paragraph(t, bp.estilo("car", fontName="Calibri-Bold", fontSize=tam, leading=tam * 1.25,
                                                      alignment=TA_CENTER, spaceAfter=esp))
    lista = bp.estilo("car_lista", fontName="Helvetica", fontSize=9.5, leading=13, alignment=TA_LEFT, spaceAfter=0)
    etiqueta = bp.estilo("car_et", fontName="Helvetica-Bold", fontSize=10.5, alignment=TA_LEFT, spaceBefore=16, spaceAfter=8)
    viñetas = lambda items: ListFlowable([ListItem(Paragraph(t, lista), leftIndent=12) for t in items],
                                         bulletType="bullet", start="●", bulletFontSize=6, leftIndent=26)
    return [
        Spacer(1, 1.2 * bp.cm),
        c("Universidad Tecnológica Nacional", 16, 8),
        c("Facultad Regional Córdoba", 11, 8),
        c("Ingeniería en Sistemas de Información", 12.5, 14),
        bp.logo_utn(), Spacer(1, 14),
        c("Desarrollo con Tecnologías Blockchain - 5K3", 14, 10),
        c("2026", 12, 14),
        c("Actividad 5: Implementación del Contrato Inteligente", 16, 4),
        c("Proyecto «Canje protegido» – contrato e-CanjeProtegido", 12, 4),
        c("Documento del desarrollo", 11, 26),
        Paragraph("Docentes:", etiqueta),
        viñetas(["Oscar Carlos Medina", "Rubén Aníbal Romero"]),
        Paragraph("Integrantes:", etiqueta),
        viñetas([f'{n} - {l} - <font color="#1155CC"><u><a href="mailto:{m}">{m}</a></u></font>' for n, l, m in bd.INTEGRANTES]),
        Paragraph("Fecha de presentación:", etiqueta),
        viñetas(["16/11/2026"]),
    ]


def armar():
    doc = bp.PdfDoc()
    arm = bd.Armador(doc)
    lineas = FUENTE.read_text(encoding="utf-8").splitlines()[1:]  # la línea 1 es el título del archivo
    bloque = []

    def volcar():
        if bloque:
            arm.markdown(bloque, "tp5", 1, "", [0])
            bloque.clear()

    primero = not (CARATULA or INDICE)  # False = el próximo capítulo empieza hoja nueva (tras el índice)
    en_codigo = False
    for linea in lineas:
        if linea.strip().startswith("```"):
            en_codigo = not en_codigo
        m = None if en_codigo else re.match(r"^(#{1,3}) (.*)", linea)
        if m:
            volcar()
            nivel = len(m.group(1))
            salto = nivel == 1 and not primero  # solo el primer capítulo, después del índice
            doc.titulo(nivel, m.group(2).strip(), salto=salto, indice=INDICE)
            if nivel == 1:
                primero = True
        elif linea.strip() == "---":
            volcar()
            doc.story.append(PageBreak())
        else:
            bloque.append(linea)
    volcar()
    while doc.story and isinstance(doc.story[-1], Spacer):
        doc.story.pop()
    return doc.story


def construir():
    bp.registrar_fuentes()
    bp.crear_estilos()
    story = []
    if not CARATULA:
        t = bp.PdfDoc()
        t.titulo(1, TITULO, indice=False)
        story += t.story
    if CARATULA:
        story += caratula()
    if INDICE:
        story += bp.indice() if CARATULA else [Paragraph("Índice", bp.E["h2"]), bp.indice()[2]]
    story += armar()
    pdf = Plantilla(str(SALIDA), title=TITULO, author=", ".join(n.split(",")[0] for n, _, _ in bd.INTEGRANTES),
                    subject="TP5 – implementación del contrato e-CanjeProtegido")
    pdf.multiBuild(story, canvasmaker=Canvas)
    print(f"OK: {SALIDA.relative_to(TP5)} ({pdf.page} páginas)")


if __name__ == "__main__":
    construir()
