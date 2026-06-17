# invite_links.py - Enlaces de invitación con token firmado
"""
Genera y valida ENLACES DE INVITACIÓN para que personas externas puedan
entrar a la IA SIN usuario/contraseña, usando únicamente un enlace que:

- Va cambiando: cada vez que se genera, el token es distinto (incluye un nonce).
- Caduca: por defecto dura 7 días (1 semana) desde que se genera.
- Es exclusivo: solo funcionan los enlaces firmados con la semilla del servidor;
  no se puede entrar "de otra manera" (sin enlace válido no hay acceso de invitado).

Diseño SIN estado (no necesita base de datos ni archivos):
el token lleva su propia fecha de caducidad y una firma HMAC. La validez se
comprueba recalculando la firma con la semilla secreta. Por eso los enlaces
siguen funcionando aunque Streamlit Cloud reinicie/redespliegue la app.

Seguridad de la semilla:
- Producción: define la semilla en Streamlit Secrets como  invite_seed = "algo-largo-y-secreto"
  (o en la variable de entorno INVITE_SEED). Así puedes invalidar TODOS los
  enlaces existentes con solo cambiar la semilla.
- Si no hay semilla configurada, se usa una por defecto (menos segura) para
  que la función no deje de operar.
"""

import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime

# Semilla por defecto (se recomienda sobreescribir con Secrets/env en producción)
_SEMILLA_DEFECTO = b"corus-intranet-invite-seed-cambia-esto-en-secrets-v1"


def _semilla() -> bytes:
    """Obtiene la semilla secreta para firmar/validar tokens."""
    # 1) Streamlit Secrets
    try:
        import streamlit as st  # import local para no exigir streamlit en tests
        valor = st.secrets.get("invite_seed", None)
        if valor:
            return str(valor).encode("utf-8")
    except Exception:
        pass
    # 2) Variable de entorno
    valor = os.getenv("INVITE_SEED")
    if valor:
        return valor.encode("utf-8")
    # 3) Por defecto
    return _SEMILLA_DEFECTO


def _firmar(payload: str) -> str:
    """Firma el payload con HMAC-SHA256 y devuelve una firma url-safe corta."""
    firma = hmac.new(_semilla(), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(firma).decode("utf-8").rstrip("=")[:32]


def generar_token(dias: int = 7) -> str:
    """Genera un token de invitación nuevo, válido durante `dias` (por defecto 7).

    Formato: "<nonce>.<exp>.<firma>"  (sin puntos dentro de cada parte).
    """
    nonce = secrets.token_urlsafe(8)
    exp = int(time.time()) + int(dias) * 86400
    payload = f"{nonce}.{exp}"
    return f"{payload}.{_firmar(payload)}"


def validar_token(token: str):
    """Valida un token de invitación.

    Devuelve una tupla (valido: bool, expira_en: int|None) donde `expira_en`
    es el timestamp UNIX de caducidad (si se pudo leer).
    """
    try:
        partes = str(token).split(".")
        if len(partes) != 3:
            return (False, None)
        nonce, exp_str, firma = partes
        payload = f"{nonce}.{exp_str}"
        # Comparación segura contra ataques de tiempo
        if not hmac.compare_digest(firma, _firmar(payload)):
            return (False, None)
        exp = int(exp_str)
        if time.time() > exp:
            return (False, exp)  # firma válida pero caducado
        return (True, exp)
    except Exception:
        return (False, None)


def expira_legible(exp: int) -> str:
    """Convierte el timestamp de caducidad a texto legible (local)."""
    try:
        return datetime.fromtimestamp(int(exp)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "—"


def construir_enlace(base_url: str, token: str) -> str:
    """Construye el enlace completo a partir de la URL base y el token."""
    base = (base_url or "").strip().rstrip("/")
    sep = "&" if ("?" in base) else "?"
    return f"{base}{sep}invite={token}"
