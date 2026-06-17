"""
video_a_manual.py
=================
Convierte un video (o audio) en el contenido de un MANUAL y lo entrega como PDF.

Flujo:
  1) Extrae el audio del video con ffmpeg (si está disponible).
  2) Transcribe con Whisper (OpenAI). Si el audio es muy grande, lo divide.
  3) Resume la transcripción en formato de manual con GPT (map-reduce si es largo).
  4) Genera un PDF descargable.

Usa la librería estándar + openai (0.28.x) + fpdf2.
"""

import os
import glob
import shutil
import tempfile
import subprocess
import logging

import openai

logger = logging.getLogger(__name__)

MAX_BYTES = 24 * 1024 * 1024  # límite práctico de Whisper (25MB)


def _api_key():
    try:
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "")


def extraer_audio(video_path: str):
    """Extrae audio comprimido (mp3 mono) con ffmpeg. Devuelve (ruta, ok)."""
    if not shutil.which("ffmpeg"):
        return video_path, False
    salida = video_path + ".mp3"
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1",
           "-ar", "16000", "-b:a", "64k", salida]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return salida, True
    except Exception as e:
        logger.warning(f"ffmpeg falló: {e}")
        return video_path, False


def _segmentar(audio_path: str):
    """Divide el audio en trozos de ~10 minutos (para audios largos)."""
    carpeta = tempfile.mkdtemp()
    patron = os.path.join(carpeta, "part%03d.mp3")
    cmd = ["ffmpeg", "-y", "-i", audio_path, "-f", "segment",
           "-segment_time", "600", "-c", "copy", patron]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        partes = sorted(glob.glob(os.path.join(carpeta, "part*.mp3")))
        return partes or [audio_path]
    except Exception as e:
        logger.warning(f"No se pudo segmentar: {e}")
        return [audio_path]


def transcribir(path: str) -> str:
    """Transcribe un archivo de audio/video con Whisper."""
    openai.api_key = _api_key()
    partes = [path]
    try:
        if os.path.getsize(path) > MAX_BYTES and shutil.which("ffmpeg"):
            partes = _segmentar(path)
    except Exception:
        pass

    textos = []
    for p in partes:
        try:
            with open(p, "rb") as f:
                tr = openai.Audio.transcribe("whisper-1", f)
            textos.append(tr["text"] if isinstance(tr, dict) else getattr(tr, "text", ""))
        except Exception as e:
            logger.error(f"Error transcribiendo {p}: {e}")
            textos.append(f"[Error transcribiendo un segmento: {e}]")
    return "\n".join(textos).strip()


def _gpt(mensajes, max_tokens=1500, temp=0.2):
    openai.api_key = _api_key()
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        temperature=temp,
        max_tokens=max_tokens,
        messages=mensajes,
    )
    return resp["choices"][0]["message"]["content"].strip()


def _resumen_parcial(texto: str) -> str:
    return _gpt([
        {"role": "system", "content": "Extrae de esta parte de la transcripción TODOS los "
         "pasos, acciones, nombres de pantallas/botones/campos, datos y consultas que se "
         "mencionen. Mantén el ORDEN. No resumas en exceso: conserva el detalle operativo. "
         "Devuelve viñetas concretas."},
        {"role": "user", "content": texto},
    ], max_tokens=1000)


def _manual_final(texto: str, titulo: str) -> str:
    instruccion = (
        "Eres un redactor técnico experto. A partir de la TRANSCRIPCIÓN de un video donde se "
        "explica un proceso, redacta un MANUAL DE PROCESO COMPLETO y DETALLADO en español.\n\n"
        "Estructura obligatoria (desarrolla CADA sección al máximo detalle):\n"
        "TÍTULO\n"
        "OBJETIVO: qué se logra con el proceso.\n"
        "REQUISITOS PREVIOS: accesos, datos, sistemas o herramientas mencionados.\n"
        "PASOS: enumera TODOS los pasos en orden (1, 2, 3...), de forma clara y detallada. "
        "Incluye nombres de pantallas, botones, campos, rutas, consultas o datos exactos que "
        "aparezcan. NO omitas pasos.\n"
        "NOTAS Y ADVERTENCIAS: validaciones, errores comunes o recomendaciones.\n"
        "RESUMEN: breve.\n\n"
        "Reglas:\n"
        "- Básate en la transcripción, pero ORDENA y REDACTA con claridad (puedes reformular).\n"
        "- NO dejes secciones vacías: si hay información relacionada en la transcripción, inclúyela.\n"
        "- Si algo no se menciona, escribe 'No se especifica en el video' en esa sección.\n"
        "- Sé extenso y útil; este texto será un manual oficial."
    )
    return _gpt([
        {"role": "system", "content": instruccion},
        {"role": "user", "content": f"Título sugerido: {titulo}\n\nTRANSCRIPCIÓN / CONTENIDO:\n{texto}"},
    ], max_tokens=2200, temp=0.35)


def resumir_a_manual(transcripcion: str, titulo: str) -> str:
    """Convierte la transcripción en el contenido de un manual (map-reduce si es largo)."""
    transcripcion = (transcripcion or "").strip()
    if not transcripcion:
        return "No se obtuvo transcripción del video."

    max_chars = 12000
    if len(transcripcion) <= max_chars:
        return _manual_final(transcripcion, titulo)

    # Dividir y resumir por partes, luego combinar
    trozos = [transcripcion[i:i + max_chars] for i in range(0, len(transcripcion), max_chars)]
    resumenes = []
    for t in trozos:
        try:
            resumenes.append(_resumen_parcial(t))
        except Exception as e:
            logger.error(f"Error en resumen parcial: {e}")
    combinado = "\n".join(resumenes)
    if len(combinado) > max_chars:
        combinado = combinado[:max_chars]
    return _manual_final(combinado, titulo)


def _latin(texto: str) -> str:
    """Compatibiliza con fuentes core (latin-1) y corta palabras larguísimas
    para evitar el error 'Not enough horizontal space' de FPDF."""
    t = (texto or "").encode("latin-1", "replace").decode("latin-1")
    fijas = []
    for w in t.split(" "):
        while len(w) > 70:
            fijas.append(w[:70])
            w = w[70:]
        fijas.append(w)
    return " ".join(fijas)


def generar_pdf(titulo: str, contenido: str) -> bytes:
    """Genera un PDF con el contenido del manual. Devuelve bytes."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Encabezado
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 9, _latin(titulo or "Manual"))
    pdf.ln(2)
    pdf.set_draw_color(138, 180, 248)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    for linea in (contenido or "").split("\n"):
        bruto = linea.rstrip()
        texto = _latin(bruto.replace("**", "").replace("#", "").strip())
        if not texto:
            pdf.ln(3)
            continue
        try:
            # Encabezado de sección (línea corta en mayúsculas o que empieza con #)
            es_titulo = bruto.startswith("#") or (bruto.isupper() and len(bruto) < 60)
            if es_titulo:
                pdf.ln(2)
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(30, 30, 30)
                pdf.multi_cell(0, 7, texto)
                pdf.ln(1)
            elif bruto.lstrip().startswith(("-", "*", "•")):
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 6, "  -  " + texto.lstrip("-*• ").strip())
            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(50, 50, 50)
                pdf.multi_cell(0, 6, texto)
        except Exception:
            # Si una línea no se puede renderizar, la omitimos para no romper el PDF
            continue

    salida = pdf.output(dest="S")
    if isinstance(salida, str):
        return salida.encode("latin-1")
    return bytes(salida)


def procesar_video(ruta_video: str, titulo: str):
    """Pipeline completo. Devuelve dict con transcripcion, manual y pdf (bytes)."""
    audio, _ = extraer_audio(ruta_video)
    transcripcion = transcribir(audio)
    manual = resumir_a_manual(transcripcion, titulo)
    pdf = generar_pdf(titulo, manual)
    return {"transcripcion": transcripcion, "manual": manual, "pdf": pdf}
