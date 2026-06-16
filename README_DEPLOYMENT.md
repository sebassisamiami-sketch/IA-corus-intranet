# 🚀 Guía de Deployment - Corus Intranet Engine

## 📋 Requisitos Previos

1. Cuenta en [Streamlit Cloud](https://streamlit.io/cloud)
2. API Key de OpenAI válida
3. Repositorio conectado a GitHub

## 🔧 Configuración en Streamlit Cloud

### Paso 1: Configurar Variables de Entorno

En Streamlit Cloud, ve a:
**App settings → Secrets**

Agrega tu API key de OpenAI:

```toml
OPENAI_API_KEY = "sk-tu-api-key-aqui"
```

### Paso 2: Configuración Avanzada (Opcional)

Si necesitas ajustar recursos, en **App settings → Advanced**:

- Python version: `3.11`
- Memory: `1GB` (mínimo recomendado)

### Paso 3: Deploy

1. Click en **Deploy**
2. Espera a que se instalen las dependencias (2-5 minutos)
3. La app estará disponible en tu URL de Streamlit Cloud

## 🐛 Solución de Problemas Comunes

### Error: "installer returned a non-zero exit code"

**Causa:** Conflicto de versiones de dependencias

**Solución:**
1. Verifica que `requirements.txt` esté actualizado
2. Limpia el caché en Streamlit Cloud:
   - Settings → Clear cache → Reboot

### Error: "OPENAI_API_KEY not found"

**Causa:** Variable de entorno no configurada

**Solución:**
1. Ve a App settings → Secrets
2. Agrega: `OPENAI_API_KEY = "tu-key"`
3. Reinicia la app

### Error: "Module not found"

**Causa:** Dependencia faltante

**Solución:**
1. Verifica que todas las dependencias estén en `requirements.txt`
2. Haz push de los cambios
3. Streamlit Cloud redeployará automáticamente

## 📦 Archivos Importantes

- `requirements.txt` - Dependencias de Python
- `packages.txt` - Dependencias del sistema (apt-get)
- `.streamlit/config.toml` - Configuración de Streamlit
- `.env.example` - Ejemplo de variables de entorno

## 🔒 Seguridad

⚠️ **NUNCA** subas tu archivo `.env` con la API key real a GitHub

- El archivo `.env` debe estar en `.gitignore`
- Usa siempre Streamlit Secrets para producción

## 📊 Monitoreo

Una vez deployado, puedes ver:

- Logs en tiempo real
- Uso de recursos
- Errores de runtime

En **App settings → Logs**

## 🆘 Soporte

Si el problema persiste:

1. Revisa los logs completos en Streamlit Cloud
2. Copia el error exacto
3. Busca en [Streamlit Community](https://discuss.streamlit.io/)

## ✅ Checklist Pre-Deploy

- [ ] `requirements.txt` actualizado
- [ ] `.streamlit/config.toml` creado
- [ ] API Key configurada en Secrets
- [ ] `.gitignore` incluye `.env`
- [ ] Repositorio pusheado a GitHub
- [ ] Carpetas `Manual Paraficales` y `Manual Pensiones` con PDFs

---

**Versión:** 2.0  
**Última actualización:** 2026
