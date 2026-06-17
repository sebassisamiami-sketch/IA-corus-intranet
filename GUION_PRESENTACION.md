# 🎤 Guion de presentación (15 minutos) — Asistente IA Corus

> Archivo de diapositivas: **Presentacion_IA_Corus.pptx**
> Consejo: habla con naturalidad, no leas la diapositiva; úsala de apoyo.

---

### Diapositiva 1 — Portada (0:00–0:30)
"Buenos días. Les voy a presentar el **Asistente IA Corporativo**, un chatbot que
responde dudas sobre los procesos de Parafiscales y Pensiones usando nuestros
propios manuales."

### Diapositiva 2 — Agenda (0:30–1:00)
"Veremos el problema, qué hace, la arquitectura, las tecnologías, cómo funciona la
IA por dentro, la seguridad, el despliegue y los resultados."

### Diapositiva 3 — El problema (1:00–2:00)
"Hoy la información está repartida en muchos PDFs y buscar un procedimiento es lento.
El objetivo: respuestas inmediatas, consistentes y basadas SOLO en la documentación oficial."

### Diapositiva 4 — ¿Qué hace? (2:00–4:00)
"La app tiene chat con IA, muestra las fuentes, acceso por roles, gestión de PDFs,
control del servidor y estadísticas." (Menciona cada tarjeta brevemente.)

### Diapositiva 5 — Arquitectura (4:00–7:00)  ⭐ clave
"Sigamos el camino de una pregunta: el usuario escribe en la app (Streamlit), el
Motor IA busca el documento correcto en la base vectorial (ChromaDB) que se creó a
partir de los PDFs, y GPT-3.5 redacta la respuesta. Es lo que se llama **RAG**."

### Diapositiva 6 — Tecnologías (7:00–9:00)
"Python con Streamlit para la interfaz; OpenAI GPT-3.5 como cerebro; LangChain para
orquestar; ChromaDB para la búsqueda; bcrypt para seguridad; y GitHub + Streamlit
Cloud para el despliegue."

### Diapositiva 7 — Cómo funciona la IA / RAG (9:00–12:00)  ⭐ clave
"Indexamos los PDFs en fragmentos, buscamos los más parecidos a la pregunta,
elegimos UN solo caso (para no mezclar procesos) y GPT redacta usando solo ese
documento. Lo importante: **la IA no inventa**."

### Diapositiva 8 — Seguridad (12:00–13:30)
"Una cuenta por persona, contraseñas cifradas, bloqueo por intentos, cierre por
inactividad y modo mantenimiento. La parte de red la cubre la plataforma."

### Diapositiva 9 — Despliegue (13:30–14:00)
"Todo está en GitHub; cada cambio se publica solo. Y los documentos se reindexan
automáticamente, incluso si subo carpetas nuevas."

### Diapositivas 10–11 — Estructura y ejemplo (apoyo)
"Estos son los archivos clave y un ejemplo real de una consulta de principio a fin."
(Úsalas si te sobra tiempo o para preguntas.)

### Diapositiva 12 — Resultados y próximos pasos (14:00–14:45)
"Logramos un asistente funcional, seguro y moderno. A futuro: GPT-4, métricas y más áreas."

### Diapositiva 13 — Cierre (14:45–15:00)
"Con esto termino. ¿Preguntas?"

---

## 💡 Consejos de exposición
- **Demo en vivo (opcional):** si puedes, abre la app y haz 1 pregunta real. Vale más que mil palabras.
- **Ten un plan B:** una captura de pantalla por si falla el internet.
- **Frases potentes:** "La IA responde solo con nuestra documentación, no inventa" y "Subir un manual nuevo es solo arrastrarlo a GitHub".
- **Si preguntan por costos:** GPT-3.5 es económico; el hosting (Streamlit Community) es gratuito.
- **Si preguntan por seguridad:** repo privado, contraseñas cifradas, control de acceso y mantenimiento.
