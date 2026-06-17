"""
vision_chat.py
==============
Analiza una IMAGEN (captura de BPM, Service Manager o WetMethods) junto con la
consulta del usuario y, opcionalmente, la documentación relevante (RAG), usando
un modelo con visión (gpt-4o-mini, con respaldo a gpt-4o).
"""

import os
import base64
import logging

import openai

logger = logging.getLogger(__name__)

DOMAIN = (
    "El equipo trabaja con Software AG / webMethods (a veces llamado 'WetMethods') y flujos de BPM "
    "(Business Process Management). Los tickets/casos (radicados) se buscan y validan en los flujos "
    "de BPM y se RESUELVEN en Service Manager (el gestor donde se consultan los radicados).\n"
    "Herramientas de desarrollo del equipo: webMethods Designer (servicios/flow services y flujos "
    "de BPM en Integration Server), DBeaver (consultas SQL y revisión de datos en base de datos) y "
    "Service Manager (seguimiento y cierre de radicados).\n"
    "Tipos de flujo de BPM a tener en cuenta: flujo principal y subflujos, etapas/estados y sus "
    "transiciones, validaciones y puntos de decisión (gateways), reasignación de tareas y "
    "excepciones, instancias padre e hijo, y el cierre del caso integrado con Service Manager."
)

DEV_GUIA = (
    "Si la imagen o la consulta apuntan a algo que requiere DESARROLLO o MODIFICACIÓN que no está "
    "en los manuales, orienta de forma práctica: indica el enfoque recomendado, en qué herramienta "
    "hacerlo (webMethods Designer, DBeaver o Service Manager) y qué tener en cuenta del flujo de BPM "
    "(etapa, transición, validación, instancia padre/hijo, etc.). NO inventes identificadores, "
    "nombres de servicios, tablas, columnas ni consultas SQL exactas; si no se ven en la imagen, "
    "descríbelos de forma genérica e indica que se validen en el entorno real o con el responsable técnico."
)


def _key():
    try:
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY", "")


def analizar_imagen(pregunta: str, imagen_bytes: bytes,
                    mime: str = "image/png", contexto_doc: str = "") -> str:
    """Analiza la imagen + la consulta y devuelve una respuesta de ayuda."""
    openai.api_key = _key()
    b64 = base64.b64encode(imagen_bytes).decode()
    data_url = f"data:{mime or 'image/png'};base64,{b64}"

    system = (
        "Eres un analista de procesos y desarrollador de Corus. Te comparten una IMAGEN (captura de "
        "pantalla de BPM, Service Manager o webMethods) y una consulta. Analiza lo que se ve en la "
        "imagen (estado del ticket/radicado, etapa del flujo de BPM, errores, campos, botones, "
        "servicios o consultas) y ayuda con el caso de forma clara, práctica y paso a paso.\n"
        + DOMAIN + "\n" + DEV_GUIA + "\n"
        "Si se incluye DOCUMENTACIÓN relevante, básate en ella para los procedimientos. "
        "No inventes pasos que no estén ni en la documentación ni visibles en la imagen; si algo "
        "no se puede determinar desde la imagen, indícalo."
    )
    if contexto_doc:
        system += "\n\nDOCUMENTACIÓN RELEVANTE:\n" + contexto_doc[:6000]

    texto = pregunta.strip() if (pregunta and pregunta.strip()) else \
        "Ayúdame con el caso que se ve en la imagen."

    user_content = [
        {"type": "text", "text": texto},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    ultima = None
    for modelo in ("gpt-4o-mini", "gpt-4o"):
        try:
            resp = openai.ChatCompletion.create(
                model=modelo,
                temperature=0.3,
                max_tokens=900,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
            )
            return resp["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Visión con {modelo} falló: {e}")
            ultima = e
    raise RuntimeError(f"No se pudo analizar la imagen: {ultima}")
