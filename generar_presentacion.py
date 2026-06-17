"""
Genera una presentacion PowerPoint profesional (.pptx) sobre el desarrollo
del Asistente IA de Corus. Ejecuta: python generar_presentacion.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# ---------- Paleta (estilo de la app) ----------
AZUL = RGBColor(0x8A, 0xB4, 0xF8)       # azul Gemini (acento)
MORADO = RGBColor(0x76, 0x4B, 0xA2)
MORADO2 = RGBColor(0x66, 0x7E, 0xEA)
FONDO = RGBColor(0x21, 0x21, 0x21)      # gris ChatGPT
FONDO2 = RGBColor(0x17, 0x17, 0x17)     # sidebar
TARJETA = RGBColor(0x2F, 0x2F, 0x2F)
TEXTO = RGBColor(0xEC, 0xEC, 0xF1)
TEXTO_TENUE = RGBColor(0x9A, 0x9A, 0xA8)
VERDE = RGBColor(0x6C, 0xC0, 0x4A)      # verde del logo Corus
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)

ANCHO = Inches(13.333)
ALTO = Inches(7.5)

prs = Presentation()
prs.slide_width = ANCHO
prs.slide_height = ALTO
BLANK = prs.slide_layouts[6]


def fondo(slide, color=FONDO):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def caja(slide, x, y, w, h, color, linea=None, linea_w=1.0):
    shp = slide.shapes.add_shape(1, x, y, w, h)  # 1 = rectangle
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    if linea is not None:
        shp.line.color.rgb = linea
        shp.line.width = Pt(linea_w)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def barra_lateral(slide):
    """Franja de acento a la izquierda."""
    caja(slide, 0, 0, Inches(0.18), ALTO, AZUL)


def texto(slide, x, y, w, h, contenido, size=18, color=TEXTO, bold=False,
          align=PP_ALIGN.LEFT, font="Calibri", italic=False, anchor=MSO_ANCHOR.TOP,
          line_spacing=1.0):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lineas = contenido if isinstance(contenido, list) else [contenido]
    for i, ln in enumerate(lineas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        if isinstance(ln, tuple):
            txt, opts = ln
        else:
            txt, opts = ln, {}
        run = p.add_run()
        run.text = txt
        run.font.size = Pt(opts.get("size", size))
        run.font.bold = opts.get("bold", bold)
        run.font.italic = opts.get("italic", italic)
        run.font.color.rgb = opts.get("color", color)
        run.font.name = font
    return tb


def vinetas(slide, x, y, w, h, items, size=16, color=TEXTO, gap=6):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.05
        nivel = 0
        if isinstance(it, tuple):
            txt, nivel = it
        else:
            txt = it
        p.level = nivel
        run = p.add_run()
        run.text = ("•  " if nivel == 0 else "–  ") + txt
        run.font.size = Pt(size if nivel == 0 else size - 2)
        run.font.color.rgb = color if nivel == 0 else TEXTO_TENUE
        run.font.name = "Calibri"
    return tb


def titulo(slide, txt, sub=None):
    barra_lateral(slide)
    texto(slide, Inches(0.55), Inches(0.35), Inches(12.2), Inches(0.9),
          txt, size=30, color=BLANCO, bold=True)
    caja(slide, Inches(0.6), Inches(1.15), Inches(2.2), Pt(3), AZUL)
    if sub:
        texto(slide, Inches(0.6), Inches(1.25), Inches(12), Inches(0.5),
              sub, size=14, color=TEXTO_TENUE, italic=True)


def numero(slide, n):
    texto(slide, Inches(12.3), Inches(6.9), Inches(0.9), Inches(0.4),
          f"{n}", size=12, color=TEXTO_TENUE, align=PP_ALIGN.RIGHT)


# ============================================================
# SLIDE 1 - PORTADA
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s, FONDO2)
caja(s, 0, Inches(3.05), ANCHO, Inches(1.4), FONDO)
texto(s, Inches(0.8), Inches(2.0), Inches(11.7), Inches(1.0),
      "Asistente IA Corporativo", size=46, color=BLANCO, bold=True)
texto(s, Inches(0.8), Inches(3.15), Inches(11.7), Inches(0.8),
      "CorusIntranetEngine v2.0  ·  Consulta inteligente de procesos", size=22, color=AZUL)
texto(s, Inches(0.8), Inches(4.3), Inches(11.7), Inches(0.6),
      "Chatbot con IA (RAG) sobre los manuales de Parafiscales y Pensiones", size=16, color=TEXTO_TENUE)
texto(s, Inches(0.8), Inches(6.5), Inches(11.7), Inches(0.5),
      "Presentación técnica  ·  15 minutos", size=14, color=TEXTO_TENUE)
caja(s, Inches(0.8), Inches(5.2), Inches(0.5), Inches(0.5), VERDE)
caja(s, Inches(1.0), Inches(5.2), Inches(0.5), Inches(0.5), AZUL)
caja(s, Inches(1.2), Inches(5.2), Inches(0.5), Inches(0.5), MORADO)

# ============================================================
# SLIDE 2 - AGENDA
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "Agenda", "Lo que veremos en los próximos 15 minutos")
vinetas(s, Inches(0.8), Inches(1.7), Inches(11.5), Inches(5),
        [
            "1. ¿Qué problema resuelve?  (1 min)",
            "2. ¿Qué hace la aplicación?  (2 min)",
            "3. Arquitectura general  (3 min)",
            "4. Tecnologías utilizadas  (2 min)",
            "5. Cómo funciona la IA por dentro (RAG)  (3 min)",
            "6. Seguridad y control  (2 min)",
            "7. Despliegue y mantenimiento  (1 min)",
            "8. Resultados y próximos pasos  (1 min)",
        ], size=20, gap=10)
numero(s, 2)

# ============================================================
# SLIDE 3 - PROBLEMA
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "1. El problema", "¿Por qué construimos esto?")
vinetas(s, Inches(0.8), Inches(1.7), Inches(11.5), Inches(4.5),
        [
            "Los procedimientos de Parafiscales y Pensiones están en muchos PDFs.",
            "Buscar 'cómo se hace un caso' es lento y manual.",
            "El conocimiento depende de la experiencia de cada analista.",
            ("Objetivo: un asistente que responda al instante, basándose SOLO en la documentación oficial.", 1),
            ("Resultado esperado: respuestas consistentes, rápidas y trazables.", 1),
        ], size=19, gap=12)
numero(s, 3)

# ============================================================
# SLIDE 4 - QUE HACE
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "2. ¿Qué hace la aplicación?")
items = [
    ("💬 Chat", "El usuario pregunta en lenguaje natural y la IA responde con los pasos del caso."),
    ("📚 Fuentes", "Muestra el documento de origen como 'ventana de comandos' para verificar."),
    ("🔐 Acceso por roles", "Login con usuarios (Administrador / Analista), cada uno con su sesión."),
    ("🗂️ Gestión de PDFs", "El admin sube carpetas a GitHub y se indexan solas."),
    ("🖥️ Control del servidor", "Modo mantenimiento (cerrar/activar) desde el panel o desde el PC."),
    ("📊 Estadísticas y accesos", "Registro de consultas y conexiones."),
]
x0, y0, w, h, gx, gy = Inches(0.7), Inches(1.7), Inches(5.9), Inches(1.45), Inches(0.3), Inches(0.25)
for i, (t, d) in enumerate(items):
    cx = x0 + (i % 2) * (w + gx)
    cy = y0 + (i // 2) * (h + gy)
    caja(s, cx, cy, w, h, TARJETA, linea=AZUL, linea_w=1.0)
    texto(s, cx + Inches(0.2), cy + Inches(0.12), w - Inches(0.4), Inches(0.5),
          t, size=18, color=AZUL, bold=True)
    texto(s, cx + Inches(0.2), cy + Inches(0.6), w - Inches(0.4), Inches(0.8),
          d, size=12.5, color=TEXTO)
numero(s, 4)

# ============================================================
# SLIDE 5 - ARQUITECTURA (diagrama)
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "3. Arquitectura general", "De la pregunta del usuario a la respuesta")

def bloque(x, y, w, h, titulo_b, detalle, color_borde=AZUL, color_fondo=TARJETA):
    caja(s, x, y, w, h, color_fondo, linea=color_borde, linea_w=1.5)
    texto(s, x + Inches(0.12), y + Inches(0.1), w - Inches(0.24), Inches(0.5),
          titulo_b, size=14, color=BLANCO, bold=True, align=PP_ALIGN.CENTER)
    texto(s, x + Inches(0.12), y + Inches(0.62), w - Inches(0.24), Inches(0.7),
          detalle, size=10.5, color=TEXTO_TENUE, align=PP_ALIGN.CENTER)

def flecha(x, y, w):
    a = s.shapes.add_shape(13, x, y, w, Inches(0.4))  # 13 = right arrow
    a.fill.solid(); a.fill.fore_color.rgb = AZUL; a.line.fill.background()
    a.shadow.inherit = False

fila_y = Inches(2.2)
bw, bh = Inches(2.5), Inches(1.5)
bloque(Inches(0.6), fila_y, bw, bh, "👤 Usuario", "Navegador web\n(Streamlit)")
flecha(Inches(3.15), fila_y + Inches(0.55), Inches(0.55))
bloque(Inches(3.75), fila_y, bw, bh, "🖥️ App Streamlit", "Login, chat, panel admin")
flecha(Inches(6.3), fila_y + Inches(0.55), Inches(0.55))
bloque(Inches(6.9), fila_y, bw, bh, "🧠 Motor IA (RAG)", "Busca + arma respuesta")
flecha(Inches(9.45), fila_y + Inches(0.55), Inches(0.55))
bloque(Inches(10.05), fila_y, Inches(2.6), bh, "🤖 OpenAI GPT-3.5", "Genera la respuesta")

# Segunda fila: datos
bloque(Inches(3.75), Inches(4.4), bw, bh, "📂 PDFs (GitHub)", "Manuales por carpeta")
flecha(Inches(6.3), Inches(4.95), Inches(0.55))
bloque(Inches(6.9), Inches(4.4), bw, bh, "🗃️ ChromaDB", "Base vectorial (búsqueda)")
texto(s, Inches(0.6), Inches(6.4), Inches(12), Inches(0.6),
      "Los PDFs se convierten en 'vectores' y se guardan en ChromaDB; el Motor IA busca ahí el documento correcto y se lo pasa a GPT.",
      size=12.5, color=TEXTO_TENUE, italic=True)
numero(s, 5)

# ============================================================
# SLIDE 6 - TECNOLOGIAS
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "4. Tecnologías utilizadas")
tech = [
    ("Frontend / App", "Streamlit 1.28 (Python)"),
    ("Lenguaje", "Python 3.11"),
    ("IA / LLM", "OpenAI GPT-3.5-turbo"),
    ("Framework IA", "LangChain"),
    ("Base vectorial", "ChromaDB"),
    ("Embeddings", "OpenAI (text-embedding-ada-002)"),
    ("Lectura de PDF", "pypdf"),
    ("Seguridad", "bcrypt (hash de contraseñas)"),
    ("Repositorio / CI", "GitHub"),
    ("Hosting", "Streamlit Community Cloud"),
]
x0, y0, w, h, gx, gy = Inches(0.7), Inches(1.7), Inches(5.9), Inches(0.72), Inches(0.3), Inches(0.18)
for i, (t, d) in enumerate(tech):
    cx = x0 + (i % 2) * (w + gx)
    cy = y0 + (i // 2) * (h + gy)
    caja(s, cx, cy, w, h, TARJETA, linea=MORADO2, linea_w=1.0)
    texto(s, cx + Inches(0.18), cy + Inches(0.08), Inches(2.4), Inches(0.55),
          t, size=13, color=AZUL, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    texto(s, cx + Inches(2.55), cy + Inches(0.08), Inches(3.2), Inches(0.55),
          d, size=12.5, color=TEXTO, anchor=MSO_ANCHOR.MIDDLE)
numero(s, 6)

# ============================================================
# SLIDE 7 - COMO FUNCIONA LA IA (RAG)
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "5. Cómo funciona la IA por dentro", "RAG = Recuperación + Generación")
pasos = [
    "1. Indexación: cada PDF se divide en fragmentos y se convierte en vectores (ChromaDB).",
    "2. Pregunta: el usuario escribe su consulta.",
    "3. Búsqueda: se buscan los fragmentos más parecidos a la pregunta.",
    "4. Selección de caso: se elige UN solo documento (no mezcla casos) usando título + semántica.",
    "5. Generación: GPT-3.5 redacta la respuesta usando SOLO ese documento.",
    "6. Continuidad: recuerda el caso para preguntas de seguimiento ('paso a paso').",
]
vinetas(s, Inches(0.8), Inches(1.7), Inches(11.6), Inches(4.2), pasos, size=17, gap=11)
caja(s, Inches(0.8), Inches(6.3), Inches(11.6), Inches(0.7), TARJETA, linea=VERDE, linea_w=1.2)
texto(s, Inches(1.0), Inches(6.42), Inches(11.2), Inches(0.5),
      "Clave: la IA NO inventa. Responde únicamente con la documentación oficial de Corus.",
      size=13.5, color=VERDE, bold=True)
numero(s, 7)

# ============================================================
# SLIDE 8 - SEGURIDAD
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "6. Seguridad y control")
vinetas(s, Inches(0.8), Inches(1.7), Inches(11.6), Inches(4.6),
        [
            "Acceso por usuario y contraseña, una cuenta por persona (sin mezcla de información).",
            "Contraseñas cifradas con bcrypt (hash), gestionadas en Streamlit Secrets.",
            "Bloqueo temporal tras 5 intentos fallidos (anti fuerza bruta).",
            "Cierre de sesión automático por inactividad (15 minutos).",
            "Modo mantenimiento: cerrar/activar el servidor (panel admin o script desde el PC).",
            "Repositorio privado, HTTPS y protección XSRF (a nivel de plataforma).",
            ("Nota: firewall / anti-DDoS los gestiona la plataforma (Streamlit/Cloudflare).", 1),
        ], size=17, gap=10)
numero(s, 8)

# ============================================================
# SLIDE 9 - DESPLIEGUE
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "7. Despliegue y mantenimiento")
vinetas(s, Inches(0.8), Inches(1.7), Inches(11.6), Inches(4.6),
        [
            "Código versionado en GitHub (rama main).",
            "Despliegue continuo: cada cambio en GitHub redespliega la app automáticamente.",
            "Auto-indexado: al iniciar, la app reconstruye la base de documentos desde los PDFs del repo.",
            "Carpetas dinámicas: subir una carpeta nueva de PDFs la agrega e indexa sola.",
            "Secrets para credenciales (API key de OpenAI y usuarios), nunca en el código.",
            ("Streamlit Cloud borra el disco al redesplegar -> por eso se reindexa solo.", 1),
        ], size=17, gap=10)
numero(s, 9)

# ============================================================
# SLIDE 10 - ESTRUCTURA DE ARCHIVOS
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "Estructura del proyecto", "Los archivos clave detrás de la app")
archivos = [
    ("app_corus.py", "Interfaz: login, chat, panel admin, seguridad, control de servidor."),
    ("ia_motor.py", "Motor IA (RAG): búsqueda, selección de caso y generación."),
    ("procesar_datos.py", "Lectura de PDFs y creación de la base vectorial."),
    ("chat_procesos.py", "Gestión de la conversación y memoria por usuario."),
    ("requirements.txt / packages.txt", "Dependencias del proyecto."),
    (".streamlit/config.toml", "Tema oscuro y configuración del servidor."),
    ("estado_app.json", "Interruptor de mantenimiento (encendido/apagado)."),
    ("Manual *.../", "Carpetas con los PDFs de los procesos."),
]
tb = s.shapes.add_textbox(Inches(0.8), Inches(1.7), Inches(11.7), Inches(5))
tf = tb.text_frame; tf.word_wrap = True
for i, (f, d) in enumerate(archivos):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.space_after = Pt(9)
    r1 = p.add_run(); r1.text = f + "   "
    r1.font.size = Pt(15); r1.font.bold = True; r1.font.color.rgb = AZUL
    r1.font.name = "Consolas"
    r2 = p.add_run(); r2.text = "→ " + d
    r2.font.size = Pt(14); r2.font.color.rgb = TEXTO; r2.font.name = "Calibri"
numero(s, 10)

# ============================================================
# SLIDE 11 - RECORRIDO DE UNA PREGUNTA (ejemplo)
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "Ejemplo real", "“¿Cómo cambio la información en el expediente?”")
flujo = [
    "El usuario escribe la pregunta en el chat.",
    "El motor busca en ChromaDB los fragmentos más parecidos.",
    "Detecta que el caso correcto es 'cambio de información doc' (no lo confunde con otros).",
    "Toma TODO ese documento y se lo pasa a GPT-3.5.",
    "GPT redacta los pasos + las consultas SQL exactas del manual.",
    "Se muestran las fuentes en estilo terminal para verificar.",
]
vinetas(s, Inches(0.8), Inches(1.7), Inches(11.6), Inches(4.5), flujo, size=17, gap=11)
numero(s, 11)

# ============================================================
# SLIDE 12 - RESULTADOS Y PROXIMOS PASOS
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s)
titulo(s, "8. Resultados y próximos pasos")
texto(s, Inches(0.8), Inches(1.6), Inches(5.6), Inches(0.5), "✅ Logrado", size=20, color=VERDE, bold=True)
vinetas(s, Inches(0.8), Inches(2.1), Inches(5.7), Inches(4),
        [
            "Asistente funcional desplegado en la nube.",
            "Respuestas completas y por caso (sin mezclar).",
            "Interfaz moderna estilo ChatGPT/Gemini.",
            "Multiusuario seguro y control de mantenimiento.",
            "Indexado automático de documentos.",
        ], size=15, gap=8)
texto(s, Inches(6.9), Inches(1.6), Inches(5.6), Inches(0.5), "🚀 Próximos pasos", size=20, color=AZUL, bold=True)
vinetas(s, Inches(6.9), Inches(2.1), Inches(5.7), Inches(4),
        [
            "Migrar a un modelo más potente (GPT-4) si se requiere.",
            "Base de datos persistente para historial.",
            "Métricas de uso y satisfacción.",
            "Más manuales y áreas de la empresa.",
            "Hash en todas las cuentas del equipo.",
        ], size=15, gap=8)
numero(s, 12)

# ============================================================
# SLIDE 13 - CIERRE
# ============================================================
s = prs.slides.add_slide(BLANK)
fondo(s, FONDO2)
texto(s, Inches(0.8), Inches(2.6), Inches(11.7), Inches(1.2),
      "¿Preguntas?", size=44, color=BLANCO, bold=True, align=PP_ALIGN.CENTER)
texto(s, Inches(0.8), Inches(3.9), Inches(11.7), Inches(0.6),
      "Asistente IA Corporativo · CorusIntranetEngine v2.0", size=18, color=AZUL, align=PP_ALIGN.CENTER)
texto(s, Inches(0.8), Inches(4.6), Inches(11.7), Inches(0.5),
      "Gracias por su atención", size=15, color=TEXTO_TENUE, align=PP_ALIGN.CENTER)

prs.save("Presentacion_IA_Corus.pptx")
print("OK: Presentacion_IA_Corus.pptx generada")
