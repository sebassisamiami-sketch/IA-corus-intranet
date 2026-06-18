---
inclusion: always
---

# Memoria del proyecto — IA Corus (CorusIntranetEngine)

> Contexto para retomar el proyecto en cualquier sesión. Responder al usuario en **español**
> (perfil no muy técnico). Hablar claro y directo.

## Qué es
App **Streamlit** (chatbot RAG) para los procesos internos de Corus (Parafiscales y Pensiones).
Responde **solo desde los manuales** (PDF) salvo el "Modo experto".

## Repo y despliegue
- Repo GitHub: `sebassisamiami-sketch/IA-corus-intranet`, rama de despliegue: **`main`**.
- Hosting: **Streamlit Community Cloud (plan gratis)**. La URL es tipo `*.streamlit.app`.
- La app debe estar **pública** en Streamlit Cloud para que funcionen los enlaces de invitado.
- Streamlit Cloud borra el disco en cada redespliegue → los PDFs se **reindexan al arrancar**.

## Stack
Streamlit 1.28.0 · Python 3.11 · openai==0.28.1 · langchain 0.0.354 · chromadb 0.4.15 ·
bcrypt · fpdf2 · ffmpeg · streamlit-mic-recorder.

## Archivos clave
- `app_corus.py` — UI principal, login, sidebar, paneles admin, chat.
- `ia_motor.py` — motor RAG (`query`, `EXPERTO_SYS`, `_unir_chunks`, re-ranking por título, continuidad).
- `chat_procesos.py` — procesa mensajes, filtros de saludo/cierre (`_normalizar_texto`), `ultima_fuente`.
- `procesar_datos.py` — indexa PDFs (chunks 1500/overlap 250).
- `vision_chat.py` — análisis de imágenes (gpt-4o-mini, respaldo gpt-4o), `DOMAIN`, `DEV_GUIA`.
- `video_a_manual.py` — video/audio → PDF de manual.
- `copiloto_reunion.py` — app aparte de copiloto de reunión.
- `invite_links.py` — tokens firmados (HMAC) de invitación y de sesión.
- `Dockerfile`, `render.yaml`, `DEPLOY_RENDER.md` — despliegue alternativo en Render (preparado, sin usar aún).

## Funcionalidades ya implementadas (todo mergeado en main)
- Login estilo Microsoft: **usuario escrito** (sin lista), enviar con **Enter** (st.form),
  casillas blancas redondeadas con **glow azul** al enfocar, ojo gris semitransparente,
  fondo con degradado suave, carga limpia "Iniciando sesión...".
- **Sesión persistente al refrescar** (token firmado en la URL `?s=`, caduca 8h). Se limpia al
  cerrar sesión (bandera `_post_logout`) o por inactividad (auto-logout 15 min). Permite cambiar de usuario.
- Seguridad: rate limit (5 intentos → bloqueo 2 min), bcrypt, generador de hash en la app.
- Multiusuario por Secrets + usuarios por defecto (admin/admin123, analista/analista123).
- **Enlaces de invitación** (menú admin "Enlaces de acceso"): token firmado, **caduca 7 días**,
  acceso **solo por enlace** como rol **Invitado** (solo ve el Chat). Pantalla "ACCESO DE INVITADO".
- Chat estilo ChatGPT oscuro, fuentes estilo terminal, respuestas completas (`_unir_chunks` muestra
  el documento completo sin solapamientos), no mezcla casos, continuidad fuerte de caso.
- **Modo experto** (toggle): conocimiento de BPM, **webMethods (Software AG)**, **DBeaver**,
  **Service Manager** (gestor de radicados), tipos de flujo BPM; orienta desarrollos/modificaciones
  sin inventar IDs/queries. Aplica en texto y en imágenes.
- Chat con **imágenes** (visión) para casos de BPM/Service Manager/webMethods.
- **Video a Manual** (PDF), **Procesar PDFs** por carpetas dinámicas, control del servidor
  (mantenimiento), presentación .pptx.
- **Indexado diferido**: el login NO espera; los PDFs se indexan perezosamente al primer uso del
  chat (`asegurar_indice`, cacheado) con mensaje "📚 Preparando la base de conocimiento...".

## Reglas de negocio / dominio
- Los tickets/radicados se **buscan y validan en flujos de BPM** y se **resuelven en Service Manager**.
- "WetMethods" = **webMethods** (plataforma BPM/integración de Software AG).
- El chat NO inventa procedimientos: los pasos salen SOLO de los manuales (RAG). El Modo experto es
  la excepción para conceptos/desarrollo, pero sin fabricar IDs/consultas exactas.

## Convenciones de trabajo (IMPORTANTE)
- Flujo Git: **push a una rama feature + crear PR a `main`**; el USUARIO mergea los PRs (yo no puedo).
  Usar las herramientas del power de GitHub (push_to_remote, create_pull_request, pull_repository),
  nunca `git push` directo.
- El usuario **mergea rápido**: avisar claramente cuál es el PR FINAL. Si un PR se mergea antes de
  un commit extra, recrear rama desde el `main` actualizado.
- Verificar SIEMPRE la sintaxis de Python con `ast.parse` antes de commitear.
- Streamlit 1.28: usar `st.experimental_get/set_query_params` (no `st.query_params`); NO existe
  `st.popover`/`st.toggle`; usar `use_column_width` en `st.image`. Cuidado: `set_query_params` justo
  antes de `st.rerun()` se pierde (hacerlo en el render ya autenticado, no antes del rerun).
- Para ocultar elementos / barras se usa CSS en `st.markdown`.

## Decisión de hosting (recordar)
- El usuario **NO financiará hosting de pago** por ahora → seguir en Streamlit gratis y asumir sus
  límites (arranque en frío lento, ~512MB–1GB RAM, badge "Hosted with Streamlit" no removible en gratis).
- Render/Docker ya está preparado en el repo. **NO** insistir con opciones de pago (Render Starter ~$7
  = 0.5 CPU/512MB; Standard ~$25 = 1 CPU/2GB). Retomar Render solo si el usuario lo pide.

## Secrets recomendados en Streamlit Cloud
`invite_seed` (firma de tokens; el usuario puso "VivaChollo"), opcional `app_url`, `OPENAI_API_KEY`,
y `[usuarios.<nombre>]` para usuarios permanentes.
