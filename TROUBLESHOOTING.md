# 🔧 Guía de Solución de Problemas

## ❌ Error: "installer returned a non-zero exit code"

### Causa
Conflicto de versiones de dependencias durante la instalación en Streamlit Cloud.

### Solución

**1. Verificar requirements.txt**
```bash
# Debe contener versiones compatibles y estables
cat requirements.txt
```

**2. Limpiar caché de Streamlit Cloud**
1. Ve a tu app en Streamlit Cloud
2. Click en **⚙️ Settings**
3. Selecciona **Clear cache**
4. Click en **Clear cache** nuevamente
5. Click en **Reboot app**

**3. Verificar que las carpetas existan**
El código creará automáticamente estas carpetas:
- `Manual Paraficales/` - PDFs de parafiscales
- `Manual Pensiones/` - PDFs de pensiones
- `data/` - Datos y base de datos
- `logs/` - Archivos de log

---

## ❌ Error: "OPENAI_API_KEY not found"

### Causa
La variable de entorno `OPENAI_API_KEY` no está configurada.

### Solución

**En Streamlit Cloud:**
1. Ve a tu app → **Settings** → **Secrets**
2. Agrega:
```toml
OPENAI_API_KEY = "sk-tu-key-aqui"
```
3. Click en **Save**
4. La app se reiniciará automáticamente

**Localmente (.env):**
```bash
# Crear archivo .env en la raíz del proyecto
echo 'OPENAI_API_KEY="sk-tu-key-aqui"' > .env
```

⚠️ **NUNCA** subas tu `.env` a GitHub

---

## ❌ Error: "Module not found" o "Import error"

### Causa
Falta una dependencia en `requirements.txt`.

### Solución

**1. Verificar que el módulo esté en requirements.txt**
```bash
cat requirements.txt | grep nombre_modulo
```

**2. Si falta, agregarlo:**
```bash
echo "nombre_modulo==version" >> requirements.txt
```

**3. Push cambios:**
```bash
git add requirements.txt
git commit -m "Add missing dependency"
git push
```

Streamlit Cloud redeployará automáticamente.

---

## ⏸️ App se queda en "Installing dependencies"

### Causa
- Versiones incompatibles
- Dependencias muy pesadas
- Timeout del servidor

### Solución

**1. Usar versiones estables (ya implementado)**
```txt
# ✅ Versiones optimizadas en requirements.txt
streamlit==1.38.0
langchain==0.2.16
chromadb==0.5.5
```

**2. Si el problema persiste:**
- Espera 5-10 minutos (chromadb puede tardar)
- Si pasa de 10 min, reinicia desde Settings

**3. Optimizaciones ya aplicadas:**
- ✅ Lazy loading con `@st.cache_resource`
- ✅ Imports solo cuando son necesarios
- ✅ Verificación de API key al inicio

---

## 🐌 App muy lenta al iniciar

### Causa
Carga de modelos pesados (embeddings, ChromaDB).

### Solución

**Ya optimizado en el código:**
```python
@st.cache_resource
def cargar_motor_ia():
    """Motor se carga una sola vez"""
    ...
```

Esto hace que el motor IA se cargue una sola vez y se reutilice.

**Primera carga:** ~30-60 segundos  
**Siguientes:** Instantáneo ⚡

---

## 🔐 Error: "Authentication failed"

### Causa
Problemas con la API key de OpenAI.

### Solución

**1. Verificar que la key sea válida:**
```python
import openai
openai.api_key = "sk-tu-key"
# Si es válida, no dará error
```

**2. Verificar que tenga créditos:**
- Ve a https://platform.openai.com/account/billing
- Verifica que tengas balance

**3. Verificar formato en Secrets:**
```toml
# ✅ Correcto (sin comillas)
OPENAI_API_KEY = sk-proj-abc123...

# ❌ Incorrecto
OPENAI_API_KEY = "sk-proj-abc123..."
```

---

## 📊 Base de datos vacía / No encuentra documentos

### Causa
Los PDFs no han sido procesados.

### Solución

**1. Subir PDFs a las carpetas:**
```
Manual Paraficales/
  ├── documento1.pdf
  └── documento2.pdf

Manual Pensiones/
  ├── documento1.pdf
  └── documento2.pdf
```

**2. Procesar desde Panel Admin:**
1. Login como **admin**
2. Sidebar → **Panel Administrativo**
3. Selecciona **Procesar PDFs**
4. Click en **🔄 Procesar carpeta parafiscales**
5. Click en **🔄 Procesar carpeta pensiones**

**3. Verificar estado:**
- Panel Admin → **Estado de BD**
- Debe mostrar documentos > 0

---

## 💾 Error: "ChromaDB initialization failed"

### Causa
Problemas con la base de datos vectorial.

### Solución

**1. Limpiar base de datos:**
- Panel Admin → **Estado de BD**
- Click en **🗑️ Limpiar base de datos**
- Confirmar

**2. Reprocesar PDFs:**
- Panel Admin → **Procesar PDFs**
- Procesar ambas carpetas

**3. Si persiste:**
```bash
# Eliminar carpeta data/db/ y reiniciar
rm -rf data/db/
```

---

## 🔄 App no se actualiza después de hacer cambios

### Causa
Caché de Streamlit activo.

### Solución

**En la app:**
1. Presiona `C` en el teclado
2. O ve a ☰ (menú) → **Clear cache**

**En Streamlit Cloud:**
1. Settings → **Clear cache** → **Reboot**

---

## 📝 Logs para debugging

### Ver logs en Streamlit Cloud:
1. Ve a tu app
2. Click en **Settings**
3. Selecciona **Logs**
4. Verás el output en tiempo real

### Ver logs localmente:
```bash
# Logs de aplicación
tail -f logs/app.log

# Logs de conexiones
cat logs/registro_conexiones.csv
```

---

## 🧪 Testing Local Antes de Deploy

**Ejecuta el script de verificación:**
```bash
python test_imports.py
```

Esto verificará:
- ✅ Todas las dependencias
- ✅ Módulos propios
- ✅ Variables de entorno
- ✅ Carpetas necesarias

---

## 🆘 Recursos Adicionales

- [Documentación Streamlit Cloud](https://docs.streamlit.io/streamlit-community-cloud)
- [Forum Streamlit](https://discuss.streamlit.io/)
- [LangChain Docs](https://python.langchain.com/docs/get_started/introduction)
- [ChromaDB Docs](https://docs.trychroma.com/)

---

## 📞 Contacto

Si el problema persiste:
1. Copia el error completo de los logs
2. Ejecuta `python test_imports.py` y copia el output
3. Incluye la versión de Python y sistema operativo
4. Contacta al equipo de soporte

---

**Última actualización:** 2026-06-16  
**Versión:** 2.0
