# Desplegar Corus IA en Render (sin marca de Streamlit)

Al alojar la app **fuera de Streamlit Community Cloud**, desaparece el badge
"Hosted/Built with Streamlit". Esta guía usa **Render** con Docker.

## Requisitos
- Cuenta en https://render.com (puedes entrar con tu GitHub).
- El repositorio `IA-corus-intranet` en GitHub (ya lo tienes).
- Tu `OPENAI_API_KEY`.

## Pasos

1. **Entra a Render** y haz clic en **New +** → **Blueprint**
   (o **Web Service** si prefieres configurarlo a mano).

2. **Conecta tu repositorio** `sebassisamiami-sketch/IA-corus-intranet`.
   - Render detectará el archivo `render.yaml` y el `Dockerfile` automáticamente.

3. **Configura las variables de entorno** (en el panel del servicio → *Environment*):
   - `OPENAI_API_KEY` = tu clave de OpenAI (obligatoria).
   - `INVITE_SEED` = una cadena larga y secreta (opcional, para los enlaces de invitación).

4. **Crea el servicio** y espera a que termine el *build* (primera vez: varios minutos,
   porque instala ffmpeg y las dependencias).

5. **Listo.** Render te dará una URL del tipo `https://corus-ia.onrender.com`.
   - Ahí la app se ve **sin ninguna marca de Streamlit**.
   - Pon esa URL en el panel **Enlaces de acceso** para generar los enlaces de invitados.

## Notas importantes

- **Plan free**: el servicio se "duerme" tras ~15 min sin uso y tarda ~50s en despertar
  en la primera visita. Si quieres que esté siempre activo, sube al plan *Starter*.
- **Memoria**: el plan free tiene 512 MB de RAM. Si la app se reinicia por memoria,
  sube a *Starter* (cambia `plan: free` por `plan: starter` en `render.yaml`).
- **Usuarios**: por defecto existen `admin/admin123` y `analista/analista123`.
  Cámbialos cuanto antes (Gestionar Usuarios o variables/secret file).
- **Datos**: el índice de los PDFs se reconstruye solo al arrancar (igual que en Streamlit Cloud).

## Alternativas equivalentes
- **Railway** (https://railway.app): igual de simple con este mismo `Dockerfile`.
- **Hugging Face Spaces** (Docker): también sirve.
- **VPS propio** (Docker): `docker build -t corus-ia . && docker run -p 8501:8501 -e OPENAI_API_KEY=... corus-ia`.
