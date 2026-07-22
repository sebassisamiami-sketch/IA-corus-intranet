# -*- coding: utf-8 -*-
"""Genera un PDF con el resumen completo del proyecto IA-corus-intranet."""
from fpdf import FPDF

FONT_DIR = "/usr/share/fonts/google-noto"

# Paleta de colores (corporativo azul/gris)
AZUL = (30, 64, 122)
AZUL_CLARO = (232, 240, 254)
GRIS = (90, 90, 90)
GRIS_CLARO = (240, 240, 240)
BLANCO = (255, 255, 255)
NEGRO = (33, 33, 33)


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Noto", "", 8)
        self.set_text_color(*GRIS)
        self.cell(0, 8, "IA-corus-intranet  |  Resumen del proyecto", align="L")
        self.cell(0, 8, "CorusIntranetEngine v2.0", align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Noto", "", 8)
        self.set_text_color(*GRIS)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")


def setup_fonts(pdf):
    pdf.add_font("Noto", "", f"{FONT_DIR}/NotoSans-Regular.ttf")
    pdf.add_font("Noto", "B", f"{FONT_DIR}/NotoSans-Bold.ttf")
    pdf.add_font("Noto", "I", f"{FONT_DIR}/NotoSans-Italic.ttf")


def h1(pdf, text):
    pdf.ln(2)
    pdf.set_font("Noto", "B", 15)
    pdf.set_text_color(*AZUL)
    pdf.multi_cell(0, 8, text)
    # linea inferior
    y = pdf.get_y() + 1
    pdf.set_draw_color(*AZUL)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(4)


def h2(pdf, text):
    pdf.ln(2)
    pdf.set_font("Noto", "B", 12)
    pdf.set_text_color(*AZUL)
    pdf.multi_cell(0, 7, text)
    pdf.ln(1)


def paragraph(pdf, text):
    pdf.set_font("Noto", "", 10.5)
    pdf.set_text_color(*NEGRO)
    pdf.multi_cell(0, 6, text)
    pdf.ln(1.5)


def bullet(pdf, title, text):
    pdf.set_x(pdf.l_margin)
    start_y = pdf.get_y()
    # vineta
    pdf.set_font("Noto", "B", 10.5)
    pdf.set_text_color(*AZUL)
    pdf.cell(6, 6, "•")
    # contenido
    pdf.set_x(pdf.l_margin + 6)
    if title:
        pdf.set_font("Noto", "B", 10.5)
        pdf.set_text_color(*NEGRO)
        pdf.write(6, f"{title}: ")
        pdf.set_font("Noto", "", 10.5)
        pdf.set_text_color(*NEGRO)
        pdf.write(6, text)
    else:
        pdf.set_font("Noto", "", 10.5)
        pdf.set_text_color(*NEGRO)
        pdf.write(6, text)
    pdf.ln(6)
    pdf.set_x(pdf.l_margin)


def key_value_table(pdf, rows, col1_w=55):
    pdf.set_font("Noto", "", 10)
    page_w = pdf.w - pdf.l_margin - pdf.r_margin
    col2_w = page_w - col1_w
    fill = False
    for k, v in rows:
        # calcular altura necesaria
        pdf.set_font("Noto", "B", 9.5)
        lines1 = pdf.multi_cell(col1_w, 6, k, dry_run=True, output="LINES")
        pdf.set_font("Noto", "", 9.5)
        lines2 = pdf.multi_cell(col2_w, 6, v, dry_run=True, output="LINES")
        h = max(len(lines1), len(lines2)) * 6
        # salto de pagina si no cabe
        if pdf.get_y() + h > pdf.h - pdf.b_margin - 15:
            pdf.add_page()
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        bg = AZUL_CLARO if fill else BLANCO
        pdf.set_fill_color(*bg)
        pdf.set_draw_color(215, 215, 215)
        # celda 1
        pdf.set_font("Noto", "B", 9.5)
        pdf.set_text_color(*AZUL)
        pdf.multi_cell(col1_w, 6, k, border=1, fill=True, max_line_height=6)
        pdf.set_xy(x0 + col1_w, y0)
        # celda 2
        pdf.set_font("Noto", "", 9.5)
        pdf.set_text_color(*NEGRO)
        pdf.multi_cell(col2_w, 6, v, border=1, fill=True, max_line_height=6)
        # normalizar y
        end_y = max(pdf.get_y(), y0 + h)
        pdf.set_xy(x0, end_y)
        fill = not fill
    pdf.ln(3)


pdf = PDF(orientation="P", unit="mm", format="A4")
setup_fonts(pdf)
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(20, 18, 20)
pdf.add_page()

# ---------- PORTADA ----------
pdf.set_fill_color(*AZUL)
pdf.rect(0, 0, pdf.w, 90, style="F")
pdf.set_xy(pdf.l_margin, 28)
pdf.set_font("Noto", "B", 26)
pdf.set_text_color(*BLANCO)
pdf.multi_cell(0, 12, "IA-corus-intranet", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_x(pdf.l_margin)
pdf.set_font("Noto", "", 14)
pdf.multi_cell(0, 9, "CorusIntranetEngine v2.0", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(2)
pdf.set_x(pdf.l_margin)
pdf.set_font("Noto", "I", 12)
pdf.multi_cell(0, 8, "Resumen del proyecto y stack tecnológico", align="C", new_x="LMARGIN", new_y="NEXT")

pdf.set_xy(pdf.l_margin, 110)
pdf.set_font("Noto", "", 10.5)
pdf.set_text_color(*NEGRO)
pdf.multi_cell(
    0, 6,
    "Asistente de IA corporativo interno para la empresa Corus. Chatbot basado en "
    "RAG (Retrieval-Augmented Generation) que responde preguntas en lenguaje natural "
    "sobre los procedimientos internos de Parafiscales y Pensiones, apoyándose "
    "exclusivamente en los manuales oficiales de la empresa.",
    align="C", new_x="LMARGIN", new_y="NEXT",
)
pdf.ln(6)
pdf.set_x(pdf.l_margin)
pdf.set_font("Noto", "", 9)
pdf.set_text_color(*GRIS)
pdf.multi_cell(0, 5, "Repositorio: sebassisamiami-sketch/IA-corus-intranet", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_x(pdf.l_margin)
pdf.multi_cell(0, 5, "Documento generado automáticamente", align="C", new_x="LMARGIN", new_y="NEXT")

# ---------- DESCRIPCION ----------
pdf.add_page()
h1(pdf, "1. Descripción del proyecto")
paragraph(
    pdf,
    "CorusIntranetEngine v2.0 es un asistente de IA corporativo interno (una intranet "
    "inteligente) para la empresa Corus. Es un chatbot que responde preguntas en lenguaje "
    "natural sobre los procedimientos internos de Parafiscales y Pensiones, basándose "
    "exclusivamente en los manuales oficiales de la empresa (archivos PDF).",
)
paragraph(
    pdf,
    "Utiliza la técnica RAG (Retrieval-Augmented Generation): en lugar de \"inventar\" "
    "respuestas, la IA busca el documento correcto entre los manuales y genera la respuesta "
    "únicamente con esa información, mostrando además las fuentes para que puedan verificarse.",
)
paragraph(
    pdf,
    "El dominio de negocio gira en torno a herramientas como webMethods (Software AG / BPM), "
    "Service Manager (gestión de radicados / tickets) y DBeaver (consultas SQL).",
)

# ---------- TECNOLOGIAS ----------
h1(pdf, "2. Tecnologías (stack técnico)")
tech_rows = [
    ("Lenguaje", "Python 3.11"),
    ("Frontend / App web", "Streamlit"),
    ("Framework de IA", "LangChain"),
    ("LLM (modelo de lenguaje)", "OpenAI GPT-3.5-turbo (chat), GPT-4o / GPT-4o-mini (visión)"),
    ("Embeddings", "OpenAI (text-embedding-ada-002)"),
    ("Base de datos vectorial", "ChromaDB"),
    ("Transcripción audio/video", "OpenAI Whisper (whisper-1)"),
    ("Procesamiento de PDF", "pypdf"),
    ("Generación de PDF", "fpdf2"),
    ("Generación de PowerPoint", "python-pptx"),
    ("Datos", "pandas, tiktoken"),
    ("Seguridad", "bcrypt (hash de contraseñas), tokens HMAC-SHA256 firmados"),
    ("Audio/Video (sistema)", "ffmpeg"),
    ("Grabación de micrófono", "streamlit-mic-recorder"),
    ("Contenedores", "Docker (Python 3.11-slim)"),
    ("Hosting", "Streamlit Community Cloud y/o Render (con Docker)"),
    ("Repositorio / CI", "GitHub (auto-deploy en main)"),
]
key_value_table(pdf, tech_rows)

# ---------- ARQUITECTURA ----------
pdf.add_page()
h1(pdf, "3. Arquitectura y módulos principales")
paragraph(
    pdf,
    "El flujo general es: Usuario (navegador) -> App Streamlit -> Motor IA (RAG) -> OpenAI. "
    "Los PDFs se almacenan en GitHub y se indexan como vectores en ChromaDB.",
)
h2(pdf, "Archivos clave")
modulos = [
    ("app_corus.py", "Aplicación principal Streamlit. Login, chat estilo ChatGPT/Gemini, panel de administración, seguridad y control del servidor. Es el archivo central."),
    ("ia_motor.py", "Motor de IA (patrón Singleton). Implementa el RAG: búsqueda vectorial, selección inteligente de un único documento, continuidad de conversación y modo experto."),
    ("procesar_datos.py", "Lee los PDFs, los divide en fragmentos (chunks) y crea/actualiza la base vectorial ChromaDB."),
    ("chat_procesos.py", "Gestiona la conversación por usuario: memoria, historial persistente y filtros de saludos/cierres para ahorrar tokens."),
    ("vision_chat.py", "Análisis de imágenes (capturas de BPM / Service Manager) usando modelos de visión GPT-4o."),
    ("video_a_manual.py", "Convierte un video/audio en un manual PDF: extrae audio con ffmpeg, transcribe con Whisper, resume con GPT y genera el PDF."),
    ("invite_links.py", "Genera enlaces de invitación temporales (tokens firmados con HMAC) y tokens de sesión para acceso sin login."),
    ("copiloto_reunion.py", "App separada: copiloto de reuniones que graba el micrófono, transcribe y responde preguntas del proyecto en vivo."),
    ("control_servidor.py", "Script CLI para poner la app en modo mantenimiento remotamente vía la API de GitHub."),
    ("generar_presentacion.py", "Genera una presentación PowerPoint profesional del proyecto."),
    ("consultar_datos.py", "Herramienta de depuración (comentada, no se usa en producción)."),
]
for nombre, desc in modulos:
    bullet(pdf, nombre, desc)

# ---------- FUNCIONALIDADES ----------
pdf.add_page()
h1(pdf, "4. Funcionalidades destacadas")
funcs = [
    ("Chat con IA (RAG)", "Responde sobre procesos con fuentes verificables, sin inventar."),
    ("Roles y acceso", "Administrador, Analista e Invitado (por enlace), cada uno con permisos y vistas distintas."),
    ("Panel de administración", "Gestión de usuarios, procesamiento de PDFs, estado de la BD, registros de acceso, estadísticas de IA y control del servidor."),
    ("Auto-indexado dinámico", "Detecta e indexa sola cualquier carpeta nueva de PDFs subida a GitHub al arrancar (necesario porque Streamlit Cloud borra el disco en cada redespliegue)."),
    ("Análisis de imágenes", "Sube una captura de pantalla y la IA ayuda con el caso (visión)."),
    ("Video a Manual", "Convierte grabaciones en manuales PDF automáticamente."),
    ("Modo experto", "Alterna entre responder solo con los manuales o con conocimiento general del dominio (BPM, webMethods, etc.)."),
    ("Seguridad robusta", "bcrypt, bloqueo tras 5 intentos fallidos, auto-logout por inactividad (15 min), enlaces de invitación firmados y caducables, modo mantenimiento."),
    ("Personalización visual", "CSS elaborado que imita la interfaz de ChatGPT/Gemini y oculta la marca de Streamlit."),
]
for t, d in funcs:
    bullet(pdf, t, d)

# ---------- OBSERVACIONES ----------
h1(pdf, "5. Observaciones")
obs = [
    ("Versiones inconsistentes", "requirements.txt usa Streamlit 1.28 y LangChain 0.0.354, mientras QUICK_START.md menciona Streamlit 1.38 y LangChain 0.2.16. El archivo real de dependencias usa las versiones antiguas."),
    ("Función duplicada", "En video_a_manual.py hay una función resumir_a_manual duplicada; la segunda definición sobrescribe a la primera (probable descuido)."),
    ("Idioma", "El proyecto está orientado a hispanohablantes: código, comentarios y UI están en español."),
]
for t, d in obs:
    bullet(pdf, t, d)

pdf.output("/projects/sandbox/IA-corus-intranet/Resumen_IA_corus_intranet.pdf")
print("PDF generado correctamente.")
