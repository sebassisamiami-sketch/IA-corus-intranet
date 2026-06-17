"""
control_servidor.py
====================
Apaga o enciende la app Corus DE FORMA REMOTA (desde tu PC), cambiando el
archivo `estado_app.json` del repositorio en GitHub. Como Streamlit Cloud
despliega desde el repo, al cambiar este archivo la app entra/sale de
mantenimiento (tras un breve redespliegue automatico).

USO (desde la terminal / cmd):
    python control_servidor.py cerrar     # pone la app en mantenimiento
    python control_servidor.py activar    # reactiva la app

REQUISITOS:
    - Python 3 instalado.
    - Un token de GitHub (Personal Access Token) con permiso de "Contents: Read and write"
      sobre el repositorio. El script lo lee de:
         1) la variable de entorno GITHUB_TOKEN, o
         2) un archivo local llamado  github_token.txt  (en la misma carpeta)
      (NO subas el token al repositorio.)

No usa librerias externas: solo la libreria estandar de Python.
"""

import base64
import json
import os
import sys
import urllib.request
import urllib.error

# ====== CONFIGURACION (ajusta si cambia el repo) ======
OWNER = "sebassisamiami-sketch"
REPO = "IA-corus-intranet"
BRANCH = "main"
ARCHIVO = "estado_app.json"
# ======================================================

API = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{ARCHIVO}"


def _token() -> str:
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "github_token.txt")
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()
    print("❌ No encontré el token. Define GITHUB_TOKEN o crea github_token.txt")
    sys.exit(1)


def _req(method: str, url: str, token: str, data: dict = None):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "corus-control-servidor")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"❌ Error HTTP {e.code}: {e.read().decode()}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("cerrar", "activar"):
        print("Uso: python control_servidor.py [cerrar|activar]")
        sys.exit(1)

    activo = sys.argv[1] == "activar"
    token = _token()

    # 1) Obtener el SHA actual del archivo
    actual = _req("GET", f"{API}?ref={BRANCH}", token)
    sha = actual.get("sha")

    # 2) Subir el nuevo contenido
    nuevo = json.dumps({"servidor_activo": activo}, ensure_ascii=False, indent=2) + "\n"
    payload = {
        "message": f"{'Activar' if activo else 'Cerrar'} servidor (control remoto)",
        "content": base64.b64encode(nuevo.encode()).decode(),
        "branch": BRANCH,
        "sha": sha,
    }
    _req("PUT", API, token, payload)

    estado = "ACTIVADO 🟢" if activo else "CERRADO (mantenimiento) 🚧"
    print(f"✅ Servidor {estado}. La app se actualizará en 1-2 minutos.")


if __name__ == "__main__":
    main()
