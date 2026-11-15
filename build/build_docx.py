"""Arma el documento de entrega del TP4 (.docx) con la estética del TP3.

Usa el paquete .docx del TP2 solo como base técnica (estilos, logo de la UTN) y genera el cuerpo
a partir de los capítulos en Markdown de desarrollo/ y entrega/. La estética (carátula, encabezado
y pie, títulos, tablas, epígrafes) es la del TP3, igual que el PDF que genera build_pdf.py.

Uso:
    python3 entrega/build_docx.py                      # primera pasada (índice sin páginas)
    python3 entrega/build_docx.py --paginas paginas.json  # segunda pasada (índice con páginas)
"""
import argparse
import json
import re
import struct
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parent.parent  # carpeta TP5 (copia adaptada del generador del TP4)
BASE_TP2 = RAIZ.parent / "TP2" / "TP2_Entrega.docx"
SALIDA = RAIZ / "entrega" / "TP4_Entrega.docx"

# Estética del TP3
ENC_IZQ = "Cátedra: Desarrollo con Tecnologías Blockchain"
ENC_DER = "2026 · 5K3 · Actividad 4"
PIE_IZQ = "Actividad 4: Modelado de un contrato inteligente · Canje protegido"
AZUL = "2F5496"
AZUL_OSCURO = "1F3864"
CELESTE = "EEF3F8"
GRUPO = "D9E2F3"
GRIS = "5F6B7A"
LINEA = "C9D3E0"
MARGEN_LAT = 1247                 # 2,2 cm
ANCHO_TEXTO = 11906 - 2 * MARGEN_LAT   # dxa: A4 vertical (todas las hojas son A4 vertical)
EMU_POR_DXA = 635
INTEGRANTES = [("Jimenez, Gustavo Martín", "94662", "martinjimenez696@gmail.com"),
               ("Martos, Leonel Agustín", "94297", "leonelmartos04@gmail.com"),
               ("Romero, Gastón Alejandro", "75076", "gastiromero@hotmail.com"),
               ("Scrimaglia, Edgardo", "11077", "edgardo.scrimaglia@gmail.com")]
NUM_VIÑETA, NUM_CARATULA = 80, 81  # numIds propios (viñeta azul y viñeta de la carátula)

# ---------------------------------------------------------------------------
# Estructura del documento (orden de la consigna, diap. 34 de CONT 3)
# Cada entrada: (nivel, título o None para usar el original, fuente)
# fuente = ("01", "3") → sección 3 de desarrollo/01_proceso.md (con sus subsecciones)
# ---------------------------------------------------------------------------
CAPITULOS = {}  # en el TP5 no hay capítulos del TP4

DESARROLLO = [
    (2, "Nombre del proceso", ("01", "1")),
    (3, None, ("01", "2")),
    (3, None, ("01", "3")),
    (3, None, ("01", "4")),
    (3, None, ("01", "5")),
    (3, None, ("01", "6")),
    (3, None, ("01", "7")),
    (2, "Contrato inteligente", None),
    (3, None, ("02", "1")),
    (3, None, ("02", "2")),
    (3, None, ("02", "3")),
    (3, None, ("02", "4")),
    (3, None, ("02", "5")),
    (3, None, ("02", "6")),
    (3, None, ("02", "7")),
    (3, None, ("02", "8")),
    (3, "Innovación respecto al proceso actual", ("03", "1")),
    (3, "Consideraciones de tecnología: red Blockchain y lenguaje de desarrollo", None),
    (4, "Red Blockchain: requisitos, alternativas y red elegida", ("03", "2.1")),
    (4, "Lenguaje de desarrollo y características técnicas", ("03", "3")),
    (3, None, ("02", "9")),
    (2, "Beneficios", ("04", "1")),
    (2, "Desafíos e inhibidores para la implementación", ("04", "2")),
    (2, "Actividad opcional: taxonomía del modelo de negocio Blockchain", "INTRO_TAXONOMIA"),
    (3, None, ("05", "1")),
    (3, None, ("05", "2")),
    (3, None, ("05", "3")),
]

ANEXO = [(2, None, ("06", "1"))]

TEXTOS = {
    "INTRO_TAXONOMIA": (
        "Aplicamos al mismo caso de uso la taxonomía de modelos de negocio Blockchain de Weking et al. (2020), "
        "presentada en clase (Medina y Romero, 2026c, diap. 17 a 21). Siguiendo el ejemplo de la cátedra, "
        "cada dimensión se justificó dentro de la actividad de la metodología a la que pertenece; esta sección "
        "completa la actividad 4 (creación de valor y flujo de ingresos) y reúne las 22 dimensiones en una sola tabla."
    ),
    "INTRO_IA": (
        "Usamos herramientas de inteligencia artificial (Claude; Anthropic, 2026) como apoyo para investigar fuentes, organizar el trabajo, "
        "redactar borradores, dibujar los diagramas y programar el prototipo. En ningún caso usamos una respuesta "
        "tal cual: cada dato se verificó en su fuente original (que es la que se cita, no la IA), la notación de cada "
        "diagrama se contrastó con el material de la cátedra y el texto se revisó y reescribió por el grupo. "
        "Cuando una respuesta de la IA no pudo verificarse, no se usó. La tabla resume cada uso, con el prompt "
        "y la forma en que se validó el resultado."
    ),
}

# ---------------------------------------------------------------------------
# Lectura de los capítulos en Markdown
# ---------------------------------------------------------------------------
RE_H = re.compile(r"^(#{2,3}) (?:(\d+(?:\.\d+)?)\.?\s+)?(.*)$")


def leer_capitulo(ruta):
    """Devuelve {clave: (titulo, lineas)} para cada sección numerada ('3' y '3.1').
    La sección '3' incluye sus subsecciones como líneas '###'."""
    secciones, actual, sub = {}, None, None
    for linea in (RAIZ / ruta).read_text(encoding="utf-8").splitlines():
        m = RE_H.match(linea)
        if m and m.group(1) == "##":
            sub = None
            actual = m.group(2)  # None para secciones sin número (por ejemplo, Pendientes)
            if actual:
                secciones[actual] = (m.group(3), [])
            continue
        if m and m.group(1) == "###" and actual:
            sub = m.group(2)
            if sub:
                secciones[sub] = (m.group(3), [])
            secciones[actual][1].append(linea)
            continue
        if actual:
            secciones[actual][1].append(linea)
            if sub:
                secciones[sub][1].append(linea)
    return secciones


# ---------------------------------------------------------------------------
# Generación de WordprocessingML
# ---------------------------------------------------------------------------
class Doc:
    def __init__(self):
        self.cuerpo = []
        self.imagenes = []          # (rId, nombre, bytes)
        self.nums = []              # numIds nuevos para listas numeradas
        self.indice = []            # (nivel, texto)
        self.id_dibujo = 100
        self.figura = None          # título de la figura a la espera de la imagen y la nota

    # --- texto en línea ---------------------------------------------------
    def runs(self, texto, base=""):
        """Convierte **negrita**, *cursiva*, `código` y [VERIFICAR] en runs."""
        partes = re.split(r"(\*\*.+?\*\*|`[^`]+`|\*[^*]+\*|\[VERIFICAR[^\]]*\])", texto)
        xml = []
        for p in partes:
            if not p:
                continue
            rpr = base
            if p.startswith("**") and p.endswith("**"):
                interior = p[2:-2]
                if "*" in interior or "`" in interior:
                    xml.append(self.runs(interior, base + "<w:b/><w:bCs/>"))
                    continue
                p, rpr = interior, rpr + "<w:b/><w:bCs/>"
            elif p.startswith("`"):
                p = p[1:-1]
                rpr += f'<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:color w:val="{AZUL_OSCURO}"/><w:sz w:val="17"/>'
            elif p.startswith("*") and p.endswith("*") and len(p) > 2:
                p, rpr = p[1:-1], rpr + "<w:i/><w:iCs/>"
            elif p.startswith("[VERIFICAR"):
                rpr += '<w:highlight w:val="yellow"/>'
            xml.append(f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(p)}</w:t></w:r>')
        return "".join(xml)

    # --- bloques -----------------------------------------------------------
    def parrafo(self, texto, ppr="", rpr=""):
        ppr = ppr or '<w:spacing w:after="120" w:line="276" w:lineRule="auto"/><w:jc w:val="both"/>'
        self.cuerpo.append(f"<w:p><w:pPr>{ppr}</w:pPr>{self.runs(texto, rpr)}</w:p>")

    def subtitulo(self, texto):
        self.parrafo(texto, '<w:spacing w:after="160"/>', f'<w:color w:val="{GRIS}"/>')

    def biblio(self, texto):
        self.parrafo(texto, '<w:spacing w:after="140" w:line="264" w:lineRule="auto"/><w:ind w:left="440" w:hanging="440"/>')

    def titulo(self, nivel, texto, salto=False, indice=True):
        estilos = {
            1: ("Ttulo1", '<w:spacing w:before="80" w:after="240"/>', f'<w:b/><w:bCs/><w:color w:val="{AZUL}"/><w:sz w:val="38"/><w:szCs w:val="38"/>'),
            2: ("Ttulo2", '<w:spacing w:before="240" w:after="120"/>', f'<w:b/><w:bCs/><w:color w:val="{AZUL}"/><w:sz w:val="27"/><w:szCs w:val="27"/>'),
            3: ("Ttulo3", '<w:spacing w:before="180" w:after="80"/>', '<w:b/><w:bCs/><w:color w:val="1A1A1A"/><w:sz w:val="23"/><w:szCs w:val="23"/>'),
            4: ("Ttulo4", '<w:spacing w:before="140" w:after="60"/>', f'<w:b/><w:bCs/><w:i/><w:color w:val="{AZUL}"/><w:sz w:val="21"/><w:szCs w:val="21"/>'),
        }
        estilo, esp, rpr = estilos[nivel]
        pb = "<w:pageBreakBefore/>" if salto else ""
        self.cuerpo.append(f'<w:p><w:pPr><w:pStyle w:val="{estilo}"/><w:keepNext/>{pb}{esp}</w:pPr>'
                           f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>')
        if indice and nivel <= 3:
            self.indice.append((nivel, texto))

    def lista(self, items, numerada):
        if numerada:
            num_id = 50 + len(self.nums)
            self.nums.append(num_id)
        else:
            num_id = NUM_VIÑETA
        for nivel, texto in items:
            self.cuerpo.append(
                f'<w:p><w:pPr><w:pStyle w:val="Prrafodelista"/><w:numPr><w:ilvl w:val="{nivel}"/><w:numId w:val="{num_id}"/></w:numPr>'
                f'<w:spacing w:after="50" w:line="264" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr>{self.runs(texto)}</w:p>')
        self.cuerpo.append('<w:p><w:pPr><w:spacing w:after="40"/></w:pPr></w:p>')

    def codigo(self, lineas):
        borde = f'<w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="{AZUL}"/></w:pBdr>'
        for k, l in enumerate(lineas):
            esp = f'<w:spacing w:before="{100 if k == 0 else 0}" w:after="{100 if k == len(lineas) - 1 else 0}" w:line="230" w:lineRule="auto"/>'
            self.cuerpo.append(
                f'<w:p><w:pPr><w:keepLines/>{borde}<w:shd w:val="clear" w:color="auto" w:fill="F4F6F8"/>{esp}<w:ind w:left="200" w:right="80"/></w:pPr>'
                f'<w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="15"/><w:szCs w:val="15"/></w:rPr>'
                f'<w:t xml:space="preserve">{escape(l) or " "}</w:t></w:r></w:p>')
        self.cuerpo.append('<w:p><w:pPr><w:spacing w:after="120"/></w:pPr></w:p>')

    def tabla(self, filas, primera_negrita=False, ancho=ANCHO_TEXTO):
        ncol = max(len(f) for f in filas)
        tam = 18
        limpio = lambda t: re.sub(r"[*`]", "", t)
        es_grupo = lambda f: f[0].strip() and all(not x.strip() for x in f[1:])
        celdas_col = [[limpio(f[c]) for f in filas if c < len(f) and not es_grupo(f)] for c in range(ncol)]
        largos = [max([min(len(t), 70) for t in col] or [1]) for col in celdas_col]
        palabra = [max([len(w) for t in col for w in t.split()] or [1]) for col in celdas_col]
        # primero el mínimo para que la palabra más larga no se corte (tope de 14 caracteres:
        # los identificadores muy largos se parten igual); después se reparte el sobrante
        minimos = [min(palabra[c], 14) * (5.6 * tam) + 240 for c in range(ncol)]
        if sum(minimos) > ancho:
            minimos = [m * ancho / sum(minimos) for m in minimos]
        sobrante = ancho - sum(minimos)
        pesos = [max(l, 3) ** 0.85 for l in largos]
        anchos = [int(minimos[c] + sobrante * pesos[c] / sum(pesos)) for c in range(ncol)]
        anchos[-1] = ancho - sum(anchos[:-1])
        bordes = (f'<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="{LINEA}"/>'
                  f'<w:right w:val="nil"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="{LINEA}"/><w:insideV w:val="nil"/></w:tblBorders>')
        xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{ancho}" w:type="dxa"/>{bordes}<w:tblLayout w:type="fixed"/>'
               '<w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar><w:tblLook w:val="0000"/></w:tblPr>'
               '<w:tblGrid>' + "".join(f'<w:gridCol w:w="{a}"/>' for a in anchos) + "</w:tblGrid>"]
        mar = '<w:tcMar><w:top w:w="60" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:bottom w:w="60" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tcMar>'
        fila_cuerpo = 0
        for i, fila in enumerate(filas):
            encabezado = i == 0
            grupo = not encabezado and es_grupo(fila)
            trpr = "<w:cantSplit/>" + ("<w:tblHeader/>" if encabezado else "")
            if encabezado:
                fondo = AZUL_OSCURO
            elif grupo:
                fondo = GRUPO
            else:
                fondo = CELESTE if fila_cuerpo % 2 == 1 else None
                fila_cuerpo += 1
            celdas = []
            columnas = [(fila[0], ancho, ncol)] if grupo else [(fila[c] if c < len(fila) else "", anchos[c], 1) for c in range(ncol)]
            for c, (texto, w, span) in enumerate(columnas):
                fill = f'<w:shd w:val="clear" w:color="auto" w:fill="{fondo}"/>' if fondo else ""
                gs = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ""
                negrita = "<w:b/><w:bCs/>" if (encabezado or grupo or (primera_negrita and c == 0)) else ""
                color = '<w:color w:val="FFFFFF"/>' if encabezado else ""
                centrar = '<w:jc w:val="center"/>' if (len(texto.strip()) <= 2 and not encabezado) else ""
                rpr = f'{negrita}{color}<w:sz w:val="{tam}"/><w:szCs w:val="{tam}"/>'
                kn = "<w:keepNext/>" if (encabezado or grupo) else ""
                celdas.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{gs}{fill}{mar}</w:tcPr>'
                              f'<w:p><w:pPr>{kn}<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>{centrar}</w:pPr>{self.runs(texto.strip(), rpr)}</w:p></w:tc>')
            xml.append(f"<w:tr><w:trPr>{trpr}</w:trPr>{''.join(celdas)}</w:tr>")
        xml.append("</w:tbl>")
        self.cuerpo.append("".join(xml))
        self.cuerpo.append('<w:p><w:pPr><w:spacing w:after="160"/></w:pPr></w:p>')

    # --- figuras: imagen y, debajo, epígrafe en cursiva gris (como el TP3) ---
    def figura_titulo(self, texto):
        m = re.match(r"\*\*(Figura \d+\.)\*\*\s*\*(.+)\*$", texto)
        self.figura = f"{m.group(1)} {m.group(2)}" if m else texto

    def figura_nota(self, texto):
        nota = texto.replace("*Nota.*", "").strip()
        epigrafe = f"{(self.figura or '').rstrip('.')}. {nota}" if self.figura else nota
        self.parrafo(epigrafe, '<w:spacing w:before="60" w:after="240"/><w:jc w:val="center"/>',
                     f'<w:i/><w:iCs/><w:color w:val="{GRIS}"/><w:sz w:val="18"/><w:szCs w:val="18"/>')
        self.figura = None

    def imagen(self, ruta):
        datos = ruta.read_bytes()
        w_px, h_px = struct.unpack(">II", datos[16:24])
        max_w = int(ANCHO_TEXTO * 0.98) * EMU_POR_DXA
        max_h = int(8.1 * 914400)  # deja lugar al título de la sección y al epígrafe
        escala = min(max_w / w_px, max_h / h_px)
        cx, cy = int(w_px * escala), int(h_px * escala)
        rid = f"rIdFig{len(self.imagenes) + 1}"
        nombre = ruta.name
        self.imagenes.append((rid, nombre, datos))
        self.id_dibujo += 1
        n = self.id_dibujo
        self.cuerpo.append(
            f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="{nombre}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{n}" name="{nombre}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


# ---------------------------------------------------------------------------
# Conversión de Markdown a bloques
# ---------------------------------------------------------------------------
class Armador:
    def __init__(self, doc):
        self.doc = doc
        self.capitulos = {k: leer_capitulo(v) for k, v in CAPITULOS.items()}
        self.mapa = {}  # (capitulo, clave) → número final

    def resolver_referencias(self, texto, cap):
        def parte(m):
            c = f"0{m.group(1)}"
            return f"sección {self.mapa.get((c, m.group(2) or m.group(3)), '?')}"
        # "Parte 2, §7" / "Parte 2 §7" / "Parte 1 (§7)": el ")" solo se consume si abrió "(§"
        texto = re.sub(r"Parte (\d)(?:,? §([\d.]+)| \(§([\d.]+)\))", parte, texto)
        texto = re.sub(r"(?<=la )sección (\d+(?:\.\d+)?)(?!\.\d)", lambda m: f"sección {self.mapa.get((cap, m.group(1)), m.group(1))}", texto)
        texto = re.sub(r"0(\d)_[a-z_]+\.md §([\d.]+)", lambda m: f"sección {self.mapa.get((f'0{m.group(1)}', m.group(2)), '?')}", texto)
        partes_gral = {"1": "la sección 1", "2": "la sección 2", "3": "las secciones 2.9 y 2.10", "4": "las secciones 3 y 4"}
        texto = re.sub(r"la Parte (\d)\b", lambda m: partes_gral.get(m.group(1), m.group(0)), texto)
        texto = re.sub(r"^§(\d+)$", lambda m: self.mapa.get((cap, m.group(1)), m.group(0)), texto)
        return texto

    def markdown(self, lineas, cap, nivel_base, numero_padre, contador):
        """Convierte líneas de Markdown. '###' pasa a título de nivel nivel_base+1 numerado."""
        d = self.doc
        i, n = 0, len(lineas)
        while i < n:
            l = lineas[i]
            s = l.strip()
            if not s or s.startswith("> "):
                i += 1
                continue
            m = RE_H.match(l)
            if m and m.group(1) == "###":
                if not numero_padre:  # secciones sin numerar (consigna)
                    d.titulo(nivel_base + 1, m.group(3))
                    i += 1
                    continue
                contador[0] += 1
                num = f"{numero_padre}.{contador[0]}"
                if m.group(2):
                    self.mapa[(cap, m.group(2))] = num
                d.titulo(nivel_base + 1, f"{num} {m.group(3)}")
                i += 1
                continue
            if s.startswith("```"):
                bloque = []
                i += 1
                while i < n and not lineas[i].strip().startswith("```"):
                    bloque.append(lineas[i])
                    i += 1
                d.codigo(bloque)
                i += 1
                continue
            if s.startswith("|"):
                filas = []
                while i < n and lineas[i].strip().startswith("|"):
                    celdas = [c for c in lineas[i].strip().strip("|").split("|")]
                    if not all(re.fullmatch(r"\s*:?-+:?\s*", c) for c in celdas):
                        filas.append([self.resolver_referencias(c.strip(), cap) for c in celdas])
                    i += 1
                d.tabla(filas, primera_negrita=(cap == "glosario"))
                continue
            if re.match(r"^\s*(- |\d+\. )", l):
                numerada = bool(re.match(r"^\s*\d+\. ", l))
                items = []
                while i < n and re.match(r"^\s*(- |\d+\. )", lineas[i]):
                    sangria = len(lineas[i]) - len(lineas[i].lstrip())
                    texto = re.sub(r"^\s*(- |\d+\. )", "", lineas[i])
                    i += 1
                    while i < n and lineas[i].startswith("   ") and lineas[i].strip() and not re.match(r"^\s*(- |\d+\. )", lineas[i]):
                        texto += " " + lineas[i].strip()
                        i += 1
                    items.append((1 if sangria >= 2 else 0, self.resolver_referencias(texto, cap)))
                d.lista(items, numerada)
                continue
            mfig = re.match(r"^\*\*Figura \d+\.\*\*", s)
            if mfig:
                d.figura_titulo(s)
                i += 1
                continue
            if s.startswith("!["):
                ruta = (RAIZ / "docs" / re.search(r"\(([^)]+)\)", s).group(1)).resolve()
                d.imagen(ruta)
                i += 1
                continue
            if s.startswith("*Nota.*"):
                d.figura_nota(s)
                i += 1
                continue
            # párrafo: une líneas consecutivas
            texto = s
            i += 1
            while i < n and lineas[i].strip() and not re.match(r"^\s*(- |\d+\. |\||#|```|!\[|> )", lineas[i]):
                texto += " " + lineas[i].strip()
                i += 1
            d.parrafo(self.resolver_referencias(texto, cap))

    def numerar(self, estructura, prefijo=""):
        """Asigna números a las entradas de la estructura y registra el mapa de referencias."""
        contadores = {2: 0, 3: 0, 4: 0}
        numeros = []
        for nivel, _, fuente in estructura:
            contadores[nivel] += 1
            for k in contadores:
                if k > nivel:
                    contadores[k] = 0
            num = prefijo + ".".join(str(contadores[k]) for k in range(2, nivel + 1))
            numeros.append(num)
            if isinstance(fuente, tuple):
                self.mapa[fuente] = num
        return numeros

    def seccion(self, estructura, numeros):
        for (nivel, titulo, fuente), num in zip(estructura, numeros):
            if isinstance(fuente, tuple):
                cap, clave = fuente
                titulo_orig, lineas = self.capitulos[cap][clave]
                titulo = titulo or titulo_orig
                self.doc.titulo(nivel, f"{num}. {titulo}" if nivel == 2 else f"{num} {titulo}")
                self.markdown(lineas, cap, nivel, num, [0])
            else:
                self.doc.titulo(nivel, f"{num}. {titulo}" if nivel == 2 else f"{num} {titulo}")
                if fuente in TEXTOS:
                    self.doc.parrafo(TEXTOS[fuente])


# ---------------------------------------------------------------------------
# Partes fijas: carátula, índice, referencias, declaración de IA
# ---------------------------------------------------------------------------
def caratula(xml_tp2):
    """Carátula con el diseño del TP3. Del TP2 solo se reutiliza el párrafo con el logo de la UTN."""
    logo = re.findall(r"<w:p[ >].*?</w:p>", xml_tp2, flags=re.S)[4]
    assert "<w:drawing" in logo, "No se encontró el logo de la UTN en el TP2"

    def linea(texto, tam, antes=0, despues=120):
        return (f'<w:p><w:pPr><w:spacing w:before="{antes}" w:after="{despues}"/><w:jc w:val="center"/></w:pPr>'
                f'<w:r><w:rPr><w:b/><w:bCs/><w:sz w:val="{tam}"/><w:szCs w:val="{tam}"/></w:rPr>'
                f'<w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>')

    arial = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'

    def etiqueta(texto):
        return (f'<w:p><w:pPr><w:spacing w:before="320" w:after="160"/></w:pPr><w:r><w:rPr>{arial}<w:b/><w:bCs/>'
                f'<w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr><w:t>{escape(texto)}</w:t></w:r></w:p>')

    def item(runs):
        return (f'<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{NUM_CARATULA}"/></w:numPr>'
                f'<w:spacing w:after="20"/></w:pPr>{runs}</w:p>')

    run = lambda t, extra="": f'<w:r><w:rPr>{arial}{extra}<w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr><w:t xml:space="preserve">{escape(t)}</w:t></w:r>'
    xml = [linea("Universidad Tecnológica Nacional", 32, antes=700),
           linea("Facultad Regional Córdoba", 22),
           linea("Ingeniería en Sistemas de Información", 25, despues=240),
           logo,
           linea("Desarrollo con Tecnologías Blockchain - 5K3", 28, antes=240),
           linea("2026", 24, despues=240),
           linea("Actividad 4: Modelado de un Contrato Inteligente", 32, despues=60),
           linea("«Canje protegido» – contrato e-CanjeProtegido", 24, despues=600),
           etiqueta("Docentes:"),
           item(run("Oscar Carlos Medina")), item(run("Rubén Aníbal Romero")),
           etiqueta("Integrantes:")]
    for k, (nombre, legajo, mail) in enumerate(INTEGRANTES, 1):
        enlace = (f'<w:hyperlink r:id="rIdMail{k}" w:history="1">'
                  + run(mail, '<w:color w:val="1155CC"/><w:u w:val="single"/>') + "</w:hyperlink>")
        xml.append(item(run(f"{nombre} - {legajo} - ") + enlace))
    return "".join(xml)


def indice(entradas, paginas):
    tab = f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{ANCHO_TEXTO}"/></w:tabs>'
    xml = [f'<w:p><w:pPr><w:pageBreakBefore/><w:spacing w:before="80" w:after="240"/></w:pPr><w:r><w:rPr><w:b/><w:bCs/>'
           f'<w:color w:val="{AZUL}"/><w:sz w:val="38"/><w:szCs w:val="38"/></w:rPr><w:t>Índice</w:t></w:r></w:p>']
    formato = {1: ("0", "<w:b/><w:bCs/>", 20, 80), 2: ("320", "", 19, 30), 3: ("640", f'<w:color w:val="{GRIS}"/>', 17, 20)}
    for nivel, texto in entradas:
        sangria, rpr, tam, despues = formato[nivel]
        rpr += f'<w:sz w:val="{tam}"/><w:szCs w:val="{tam}"/>'
        pag = str(paginas.get(texto, ""))
        xml.append(f'<w:p><w:pPr>{tab}<w:spacing w:before="{40 if nivel == 1 else 0}" w:after="{despues}" w:line="250" w:lineRule="auto"/>'
                   f'<w:ind w:left="{sangria}"/></w:pPr><w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{escape(texto)}</w:t></w:r>'
                   f'<w:r><w:rPr>{rpr}</w:rPr><w:tab/><w:t>{pag}</w:t></w:r></w:p>')
    return "".join(xml)


def encabezado_y_pie(archivos):
    """Encabezado y pie del TP3: textos en gris a izquierda y derecha, línea azul bajo el encabezado."""
    gris = f'<w:rPr><w:color w:val="{GRIS}"/><w:sz w:val="15"/><w:szCs w:val="15"/></w:rPr>'
    tab = f'<w:tabs><w:tab w:val="right" w:pos="{ANCHO_TEXTO}"/></w:tabs>'
    h = archivos["word/header1.xml"].decode("utf-8")
    raiz = re.match(r".*?<w:hdr[^>]*>", h, re.S).group(0)
    archivos["word/header1.xml"] = (raiz +
        f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="4" w:color="{AZUL}"/></w:pBdr>{tab}<w:spacing w:after="0"/></w:pPr>'
        f'<w:r>{gris}<w:t>{escape(ENC_IZQ)}</w:t></w:r><w:r>{gris}<w:tab/><w:t>{escape(ENC_DER)}</w:t></w:r></w:p></w:hdr>').encode("utf-8")
    f = archivos["word/footer1.xml"].decode("utf-8")
    raiz = re.match(r".*?<w:ftr[^>]*>", f, re.S).group(0)
    # campo completo (no fldSimple) para que Word conserve el formato gris al actualizar el número
    campo = lambda instr, v: (f'<w:r>{gris}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{gris}<w:instrText xml:space="preserve"> {instr} </w:instrText></w:r>'
                              f'<w:r>{gris}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{gris}<w:t>{v}</w:t></w:r><w:r>{gris}<w:fldChar w:fldCharType="end"/></w:r>')
    archivos["word/footer1.xml"] = (raiz +
        f'<w:p><w:pPr>{tab}<w:spacing w:after="0"/></w:pPr><w:r>{gris}<w:t xml:space="preserve">{escape(PIE_IZQ)}</w:t></w:r>'
        f'<w:r>{gris}<w:tab/><w:t xml:space="preserve">Página </w:t></w:r>{campo("PAGE", 1)}'
        f'<w:r>{gris}<w:t xml:space="preserve"> de </w:t></w:r>{campo("NUMPAGES", 1)}</w:p></w:ftr>').encode("utf-8")


def numeracion(archivos, nums):
    """Viñetas azules, numeración azul en negrita y viñeta de la carátula (como el TP3)."""
    abstractos = (
        '<w:abstractNum w:abstractNumId="90"><w:multiLevelType w:val="hybridMultilevel"/>'
        f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>'
        f'<w:pPr><w:ind w:left="360" w:hanging="220"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:color w:val="{AZUL}"/></w:rPr></w:lvl>'
        f'<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="◦"/><w:lvlJc w:val="left"/>'
        f'<w:pPr><w:ind w:left="720" w:hanging="220"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:color w:val="{AZUL}"/></w:rPr></w:lvl>'
        '</w:abstractNum>'
        '<w:abstractNum w:abstractNumId="91"><w:multiLevelType w:val="hybridMultilevel"/>'
        f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/>'
        f'<w:pPr><w:ind w:left="400" w:hanging="280"/></w:pPr><w:rPr><w:b/><w:bCs/><w:color w:val="{AZUL}"/></w:rPr></w:lvl>'
        f'<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="◦"/><w:lvlJc w:val="left"/>'
        f'<w:pPr><w:ind w:left="760" w:hanging="220"/></w:pPr><w:rPr><w:color w:val="{AZUL}"/></w:rPr></w:lvl>'
        '</w:abstractNum>'
        '<w:abstractNum w:abstractNumId="92"><w:multiLevelType w:val="hybridMultilevel"/>'
        '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="●"/><w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="740" w:hanging="300"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="12"/></w:rPr></w:lvl>'
        '</w:abstractNum>')
    num = archivos["word/numbering.xml"].decode("utf-8")
    k = num.index("<w:num ")
    num = num[:k] + abstractos + num[k:]
    instancias = (f'<w:num w:numId="{NUM_VIÑETA}"><w:abstractNumId w:val="90"/></w:num>'
                  f'<w:num w:numId="{NUM_CARATULA}"><w:abstractNumId w:val="92"/></w:num>'
                  + "".join(f'<w:num w:numId="{i}"><w:abstractNumId w:val="91"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'
                            for i in nums))
    archivos["word/numbering.xml"] = num.replace("</w:numbering>", instancias + "</w:numbering>").encode("utf-8")


def referencias(doc):
    texto = (RAIZ / "fuentes" / "referencias.md").read_text(encoding="utf-8")
    entradas = [e.strip() for e in texto.split("\n\n")[2:] if e.strip()]
    doc.subtitulo("Referencias según normas APA, 7.ª edición.")
    for e in entradas:
        doc.biblio(e)


def declaracion_ia(doc, arm):
    doc.parrafo(TEXTOS["INTRO_IA"])
    filas = []
    for l in (RAIZ / "ia" / "registro_uso_ia.md").read_text(encoding="utf-8").splitlines():
        if l.startswith("|") and not re.fullmatch(r"\|[-| ]+\|", l.strip()):
            filas.append([arm.resolver_referencias(c.strip(), "ia") for c in l.strip().strip("|").split("|")])
    doc.tabla(filas)


# ---------------------------------------------------------------------------
# Ensamblado del paquete
# ---------------------------------------------------------------------------
def construir(paginas):
    with zipfile.ZipFile(BASE_TP2) as z:
        archivos = {n: z.read(n) for n in z.namelist()}
    doc_tp2 = archivos["word/document.xml"].decode("utf-8")

    doc = Doc()
    arm = Armador(doc)
    arm.capitulos["glosario"] = None

    # numerar todo antes de escribir, para resolver referencias hacia adelante
    num_desarrollo = arm.numerar(DESARROLLO)
    num_anexo = arm.numerar(ANEXO, prefijo="A.")

    doc.titulo(1, "Glosario", salto=True)
    arm.markdown((RAIZ / "entrega" / "glosario.md").read_text(encoding="utf-8").splitlines(), "glosario", 1, "", [0])
    doc.titulo(1, "Desarrollo", salto=True)
    arm.seccion(DESARROLLO, num_desarrollo)
    doc.titulo(1, "Fuentes - Bibliografía", salto=True)
    referencias(doc)
    doc.titulo(1, "Declaración de uso de inteligencia artificial", salto=True)
    declaracion_ia(doc, arm)
    doc.titulo(1, "Anexo: prototipo del contrato en Solidity", salto=True)
    arm.seccion(ANEXO, num_anexo)

    cuerpo = caratula(doc_tp2) + indice(doc.indice, paginas) + "".join(doc.cuerpo)
    sect_final = re.search(r"<w:sectPr[ >].*?</w:sectPr>(?=</w:body>)", doc_tp2, re.S).group(0)
    sect_final = re.sub(r"<w:pgMar [^>]*/>", f'<w:pgMar w:top="1361" w:right="{MARGEN_LAT}" w:bottom="1191" w:left="{MARGEN_LAT}" '
                        'w:header="822" w:footer="680" w:gutter="0"/>', sect_final)
    inicio = doc_tp2[:doc_tp2.index("<w:body>") + len("<w:body>")]
    archivos["word/document.xml"] = (inicio + cuerpo + sect_final + "</w:body></w:document>").encode("utf-8")

    encabezado_y_pie(archivos)
    estilos = archivos["word/styles.xml"].decode("utf-8")
    defaults = re.search(r"<w:docDefaults>.*?</w:docDefaults>", estilos, re.S).group(0)
    estilos = estilos.replace(defaults, defaults.replace('<w:sz w:val="22"/><w:szCs w:val="22"/>', '<w:sz w:val="21"/><w:szCs w:val="21"/>'))
    archivos["word/styles.xml"] = estilos.encode("utf-8")

    # imágenes y relaciones (se quita la imagen del TP2 que no se usa)
    rels = archivos["word/_rels/document.xml.rels"].decode("utf-8")
    rels = re.sub(r'<Relationship Id="rId8"[^>]*/>', "", rels)
    archivos.pop("word/media/image2.png", None)
    nuevas = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{nombre}"/>'
                     for rid, nombre, _ in doc.imagenes)
    nuevas += "".join(f'<Relationship Id="rIdMail{k}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
                      f'Target="mailto:{mail}" TargetMode="External"/>' for k, (_, _, mail) in enumerate(INTEGRANTES, 1))
    archivos["word/_rels/document.xml.rels"] = rels.replace("</Relationships>", nuevas + "</Relationships>").encode("utf-8")
    for _, nombre, datos in doc.imagenes:
        archivos[f"word/media/{nombre}"] = datos

    numeracion(archivos, doc.nums)  # cada lista numerada reinicia en 1

    # propiedades del documento
    core = archivos["docProps/core.xml"].decode("utf-8")
    core = re.sub(r"<dc:title>.*?</dc:title>", "<dc:title>TP4 – Modelado de un contrato inteligente: Canje protegido</dc:title>", core)
    core = re.sub(r"<dc:creator>.*?</dc:creator>", "<dc:creator>" + ", ".join(n.split(",")[0] for n, _, _ in INTEGRANTES) + "</dc:creator>", core)
    core = re.sub(r"<dc:description>.*?</dc:description>", "<dc:description>Contrato inteligente e-CanjeProtegido: "
                  "canje de insumos con seguro paramétrico de sequía</dc:description>", core)
    archivos["docProps/core.xml"] = core.encode("utf-8")

    with zipfile.ZipFile(SALIDA, "w", zipfile.ZIP_DEFLATED) as z:
        orden = ["[Content_Types].xml"] + [n for n in archivos if n != "[Content_Types].xml"]
        for n in orden:
            z.writestr(n, archivos[n])
    return doc.indice


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paginas", help="JSON {título: página} para completar el índice")
    args = ap.parse_args()
    paginas = json.loads(Path(args.paginas).read_text(encoding="utf-8")) if args.paginas else {}
    entradas = construir(paginas)
    (RAIZ / "entrega" / "indice.json").write_text(json.dumps([t for _, t in entradas], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {SALIDA.relative_to(RAIZ)} ({len(entradas)} entradas de índice)")
