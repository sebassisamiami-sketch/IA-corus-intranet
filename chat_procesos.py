# chat_procesos.py - Procesamiento de Chat
"""
Módulo de procesamiento de conversaciones y mensajes
Gestiona la interacción del usuario con el motor IA
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Importar motor IA
try:
    from ia_motor import CorusIntranetEngine
except ImportError:
    raise ImportError("❌ Error: ia_motor.py no encontrado. Verifica la estructura de archivos.")

# Configurar logging
logger = logging.getLogger(__name__)

class ChatProcessor:
    """
    Procesador de conversaciones y mensajes
    Gestiona la comunicación entre usuario y motor IA
    """
    
    def __init__(self, usuario: Optional[str] = None, rol: Optional[str] = None):
        """
        Inicializar procesador de chat
        
        Args:
            usuario: Nombre del usuario (opcional)
            rol: Rol del usuario - 'Analista' o 'Administrador' (opcional)
        
        Raises:
            RuntimeError: Si el motor IA no puede inicializarse
        """
        try:
            self.motor_ia = CorusIntranetEngine()
            self.usuario = usuario
            self.rol = rol
            self.historial_local: List[Dict[str, Any]] = []
            self.archivo_memoria = self._obtener_ruta_memoria()
            
            logger.info(f"✅ ChatProcessor inicializado para {usuario} ({rol})")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando ChatProcessor: {e}")
            raise RuntimeError(f"No se pudo inicializar el procesador: {e}")
    
    def _obtener_ruta_memoria(self) -> str:
        """Obtener ruta del archivo de memoria para este usuario"""
        memoria_dir = Path("data/sessions")
        memoria_dir.mkdir(parents=True, exist_ok=True)
        
        if self.usuario and self.rol:
            return str(memoria_dir / f"{self.usuario}_{self.rol}_memoria.json")
        return str(memoria_dir / "memoria_temporal.json")
    
    def _cargar_memoria_usuario(self) -> List[Dict[str, Any]]:
        """Cargar historial previo del usuario desde disco"""
        try:
            if os.path.exists(self.archivo_memoria):
                with open(self.archivo_memoria, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    self.historial_local = datos.get('historial', [])
                    logger.info(f"✅ Memoria cargada: {len(self.historial_local)} mensajes")
                    return self.historial_local
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar memoria: {e}")
        
        return []
    
    def _guardar_memoria_usuario(self):
        """Guardar historial actual del usuario en disco"""
        try:
            datos = {
                'usuario': self.usuario,
                'rol': self.rol,
                'última_actualización': datetime.now().isoformat(),
                'historial': self.historial_local[-50:]  # Guardar últimos 50 mensajes
            }
            
            with open(self.archivo_memoria, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"💾 Memoria guardada para {self.usuario}")
        except Exception as e:
            logger.error(f"❌ Error guardando memoria: {e}")
    
    def procesar_mensaje(
        self, 
        mensaje: str, 
        contexto: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Procesar mensaje del usuario y obtener respuesta IA
        
        Args:
            mensaje: Texto del mensaje del usuario
            contexto: Contexto adicional (opcional)
        
        Returns:
            Dict con respuesta, metadata y estado
        """
        try:
            timestamp = datetime.now().isoformat()
            
            logger.info(f"📨 [{self.usuario}] Procesando: {mensaje[:50]}...")
            
            # Validar mensaje
            if not mensaje or not isinstance(mensaje, str):
                raise ValueError("Mensaje inválido")
            
            mensaje = mensaje.strip()
            if len(mensaje) > 5000:
                raise ValueError("Mensaje demasiado largo (máx 5000 caracteres)")
            
            # Enriquecer prompt con contexto
            prompt_enriquecido = self._enriquecer_prompt(mensaje, contexto)
            
            # Consultar motor IA
            resultado = self.motor_ia.query(prompt_enriquecido)
            
            # Construir respuesta
            respuesta_dict = {
                'timestamp': timestamp,
                'usuario': self.usuario,
                'rol': self.rol,
                'mensaje_original': mensaje,
                'mensaje_procesado': prompt_enriquecido,
                'respuesta': resultado['respuesta'],
                'sources': self._procesar_sources(resultado.get('sources', [])),
                'exitoso': True,
                'error': None
            }
            
            # Guardar en historial local
            self.historial_local.append(respuesta_dict)
            self._guardar_memoria_usuario()
            
            logger.info(f"✅ Respuesta generada: {len(resultado['respuesta'])} caracteres")
            
            return respuesta_dict
        
        except ValueError as e:
            return self._crear_respuesta_error(mensaje, str(e), "ValidationError")
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}")
            return self._crear_respuesta_error(mensaje, str(e), "ProcessingError")
    
    def _enriquecer_prompt(
        self, 
        mensaje: str, 
        contexto: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Enriquecer el prompt del usuario con contexto
        
        Args:
            mensaje: Mensaje original
            contexto: Contexto adicional
        
        Returns:
            Prompt enriquecido
        """
        prompt = mensaje
        
        if contexto:
            if contexto.get('departamento'):
                prompt += f"\n[Contexto: Departamento {contexto['departamento']}]"
            if contexto.get('proyecto'):
                prompt += f"\n[Proyecto: {contexto['proyecto']}]"
        
        # Agregar información del rol en el prompt
        if self.rol == "Administrador":
            prompt += "\n[Nota: Responder con información administrativa/técnica]"
        elif self.rol == "Analista":
            prompt += "\n[Nota: Responder con información analítica/operativa]"
        
        return prompt
    
    def _procesar_sources(self, sources: List[Any]) -> List[Dict[str, Any]]:
        """
        Procesar y estructurar las fuentes de los documentos
        
        Args:
            sources: Lista de documentos fuente
        
        Returns:
            Lista estructurada de fuentes
        """
        sources_procesadas = []
        
        try:
            for source in sources:
                if hasattr(source, 'metadata'):
                    sources_procesadas.append({
                        'source': source.metadata.get('source', 'Desconocida'),
                        'página': source.metadata.get('page', 'N/A'),
                        'contenido_preview': source.page_content[:200]
                    })
        except Exception as e:
            logger.warning(f"⚠️ Error procesando sources: {e}")
        
        return sources_procesadas
    
    def _crear_respuesta_error(
        self, 
        mensaje: str, 
        error: str, 
        tipo_error: str = "Error"
    ) -> Dict[str, Any]:
        """
        Crear respuesta de error estructurada
        
        Args:
            mensaje: Mensaje que causó error
            error: Descripción del error
            tipo_error: Tipo de error
        
        Returns:
            Dict con información del error
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'usuario': self.usuario,
            'rol': self.rol,
            'mensaje_original': mensaje,
            'respuesta': f"❌ {tipo_error}: {error}",
            'sources': [],
            'exitoso': False,
            'error': {
                'tipo': tipo_error,
                'mensaje': error
            }
        }
    
    def obtener_historial(
        self, 
        limit: int = 50, 
        solo_exitosos: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obtener historial de conversación
        
        Args:
            limit: Número máximo de mensajes
            solo_exitosos: Filtrar solo mensajes exitosos
        
        Returns:
            Lista de mensajes del historial
        """
        historial = self.historial_local[-limit:]
        
        if solo_exitosos:
            historial = [m for m in historial if m.get('exitoso', True)]
        
        return historial
    
    def obtener_historial_formateado(self, limit: int = 20) -> str:
        """
        Obtener historial formateado para mostrar en UI
        
        Args:
            limit: Número de mensajes
        
        Returns:
            String formateado
        """
        historial = self.obtener_historial(limit=limit)
        
        if not historial:
            return "📭 Sin historial de conversación"
        
        texto = "📜 **Historial Reciente:**\n\n"
        
        for msg in historial:
            timestamp = msg['timestamp'][:16]  # HH:MM
            usuario = msg['usuario']
            
            if msg['exitoso']:
                texto += f"**[{timestamp}] {usuario}:** {msg['mensaje_original']}\n"
                texto += f"*IA:* {msg['respuesta'][:100]}...\n\n"
            else:
                texto += f"**[{timestamp}] {usuario}:** ❌ Error\n\n"
        
        return texto
    
    def limpiar_historial(self, confirmacion: bool = True) -> bool:
        """
        Limpiar historial de conversación
        
        Args:
            confirmacion: Requerir confirmación
        
        Returns:
            True si se limpió, False si no
        """
        try:
            if confirmacion and not self.historial_local:
                logger.info("⚠️ Historial ya está vacío")
                return False
            
            self.historial_local = []
            self._guardar_memoria_usuario()
            
            logger.info(f"🗑️ Historial limpiado para {self.usuario}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Error limpiando historial: {e}")
            return False
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del uso
        
        Returns:
            Dict con estadísticas
        """
        total_mensajes = len(self.historial_local)
        exitosos = sum(1 for m in self.historial_local if m.get('exitoso', True))
        fallidos = total_mensajes - exitosos
        
        promedio_respuesta = 0
        if exitosos > 0:
            respuestas = [len(m['respuesta']) for m in self.historial_local if m.get('exitoso')]
            promedio_respuesta = sum(respuestas) // len(respuestas)
        
        return {
            'total_mensajes': total_mensajes,
            'exitosos': exitosos,
            'fallidos': fallidos,
            'tasa_exito': f"{(exitosos/total_mensajes*100):.1f}%" if total_mensajes > 0 else "N/A",
            'promedio_respuesta_caracteres': promedio_respuesta,
            'usuario': self.usuario,
            'rol': self.rol
        }
    
    def exportar_historial(self, formato: str = "json") -> Optional[str]:
        """
        Exportar historial en diferentes formatos
        
        Args:
            formato: 'json' o 'txt'
        
        Returns:
            Contenido exportado o None si falla
        """
        try:
            if formato == "json":
                return json.dumps(self.historial_local, ensure_ascii=False, indent=2)
            
            elif formato == "txt":
                texto = f"=== HISTORIAL DE {self.usuario} ({self.rol}) ===\n\n"
                for msg in self.historial_local:
                    timestamp = msg['timestamp']
                    texto += f"[{timestamp}]\n"
                    texto += f"Usuario: {msg['mensaje_original']}\n"
                    texto += f"IA: {msg['respuesta']}\n"
                    texto += "---\n\n"
                return texto
        
        except Exception as e:
            logger.error(f"❌ Error exportando: {e}")
        
        return None
