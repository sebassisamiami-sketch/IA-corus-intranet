# chat_procesos.py - Procesador de Chat
"""
Gestor de procesamiento de mensajes de chat
Incluye enriquecimiento de prompts por rol y persistencia
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from ia_motor import obtener_motor

logger = logging.getLogger(__name__)

class ChatProcessor:
    """
    Procesa mensajes de chat con contexto de rol
    Gestiona historial local y persistencia
    """
    
    def __init__(self, usuario: str, rol: str):
        """
        Inicializar processor
        
        Args:
            usuario: Nombre del usuario
            rol: Rol del usuario (Analista/Administrador)
        """
        self.usuario = usuario
        self.rol = rol
        self.motor_ia = obtener_motor()
        self.historial_local = []
        self.archivo_sesion = f"data/sessions/{usuario}_{rol}.json"
        
        Path("data/sessions").mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ChatProcessor iniciado para {usuario} ({rol})")
    
    def _cargar_memoria_usuario(self):
        """Cargar historial previo del usuario"""
        try:
            if Path(self.archivo_sesion).exists():
                with open(self.archivo_sesion, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.historial_local = data.get('historial', [])
                    logger.info(f"✅ Sesión anterior cargada ({len(self.historial_local)} mensajes)")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar sesión anterior: {e}")
    
    def _enriquecer_prompt(self, mensaje: str) -> str:
        """Enriquecer prompt según rol"""
        
        prompts_rol = {
            "Administrador": f"""
            Eres un asistente administrativo corporativo de CORUS.
            Usuario: {self.usuario} (Administrador)
            
            Tienes acceso completo a:
            - Documentos parafiscales
            - Documentos de pensiones
            - Políticas administrativas
            - Información de usuarios y accesos
            
            Proporciona respuestas detalladas y precisas.
            """,
            "Analista": f"""
            Eres un asistente analista de CORUS.
            Usuario: {self.usuario} (Analista)
            
            Tienes acceso a:
            - Documentos parafiscales
            - Documentos de pensiones
            - Reportes analíticos
            
            Proporciona análisis precisos y detallados.
            """
        }
        
        return prompts_rol.get(self.rol, "") + f"\n\nPregunta: {mensaje}"
    
    def procesar_mensaje(
        self,
        mensaje: str,
        contexto: Dict = None
    ) -> Dict[str, Any]:
        """
        Procesar mensaje del usuario
        
        Args:
            mensaje: Mensaje del usuario
            contexto: Contexto adicional (rol, etc)
        
        Returns:
            Dict con respuesta y metadata
        """
        try:
            # Validaciones
            if not mensaje or len(mensaje.strip()) < 1:
                return {
                    'exitoso': False,
                    'mensaje': mensaje,
                    'respuesta': "❌ Mensaje vacío",
                    'timestamp': datetime.now().isoformat(),
                    'usuario': self.usuario,
                    'rol': self.rol
                }
            
            if len(mensaje) > 5000:
                return {
                    'exitoso': False,
                    'mensaje': mensaje[:100] + "...",
                    'respuesta': "❌ Mensaje muy largo (máximo 5000 caracteres)",
                    'timestamp': datetime.now().isoformat(),
                    'usuario': self.usuario,
                    'rol': self.rol
                }
            
            logger.info(f"📨 Procesando mensaje de {self.usuario}: {mensaje[:50]}...")
            
            # Enriquecer prompt
            prompt_enriquecido = self._enriquecer_prompt(mensaje)
            
            # Obtener respuesta del motor
            resultado_motor = self.motor_ia.query(
                pregunta=prompt_enriquecido,
                contexto=contexto or {'rol': self.rol}
            )
            
            # Construir respuesta
            respuesta = {
                'exitoso': resultado_motor.get('exito', False),
                'mensaje_original': mensaje,
                'respuesta': resultado_motor.get('respuesta', ''),
                'sources': resultado_motor.get('sources', []),
                'timestamp': datetime.now().isoformat(),
                'usuario': self.usuario,
                'rol': self.rol,
                'modo': resultado_motor.get('modo', 'desconocido')
            }
            
            if not respuesta['exitoso']:
                respuesta['error'] = {
                    'mensaje': resultado_motor.get('error', 'Error desconocido'),
                    'detalles': resultado_motor.get('respuesta', '')
                }
            
            # Guardar en historial local
            self.historial_local.append(respuesta)
            
            # Persistir sesión
            self._guardar_sesion()
            
            logger.info(f"✅ Mensaje procesado exitosamente")
            
            return respuesta
        
        except Exception as e:
            logger.error(f"❌ Error procesando mensaje: {e}", exc_info=True)
            
            return {
                'exitoso': False,
                'mensaje': mensaje,
                'respuesta': f"❌ Error: {str(e)}",
                'timestamp': datetime.now().isoformat(),
                'usuario': self.usuario,
                'rol': self.rol,
                'error': {
                    'mensaje': 'Error interno',
                    'detalles': str(e)
                }
            }
    
    def _guardar_sesion(self):
        """Guardar sesión en JSON"""
        try:
            data = {
                'usuario': self.usuario,
                'rol': self.rol,
                'historial': self.historial_local,
                'ultima_actualizacion': datetime.now().isoformat()
            }
            
            with open(self.archivo_sesion, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"✅ Sesión guardada")
        
        except Exception as e:
            logger.warning(f"⚠️ No se pudo guardar sesión: {e}")
    
    def obtener_historial(self, ultimos: int = 50) -> List[Dict]:
        """Obtener últimos mensajes del historial"""
        return self.historial_local[-ultimos:] if self.historial_local else []
    
    def limpiar_historial(self) -> bool:
        """Limpiar historial de la sesión"""
        try:
            self.historial_local = []
            self._guardar_sesion()
            logger.info(f"✅ Historial limpiado para {self.usuario}")
            return True
        except Exception as e:
            logger.error(f"❌ Error limpiando historial: {e}")
            return False
    
    def exportar_historial(self, formato: str = 'json') -> str:
        """
        Exportar historial
        
        Args:
            formato: 'json' o 'txt'
        
        Returns:
            Contenido del archivo
        """
        try:
            if formato == 'json':
                return json.dumps(self.historial_local, ensure_ascii=False, indent=2)
            
            elif formato == 'txt':
                lineas = [f"Historial de chat - {self.usuario} ({self.rol})"]
                lineas.append("=" * 60)
                
                for msg in self.historial_local:
                    lineas.append(f"\n👤 Usuario: {msg['mensaje_original']}")
                    lineas.append(f"🤖 IA: {msg['respuesta']}")
                    lineas.append(f"⏱️  {msg['timestamp']}")
                    lineas.append("-" * 40)
                
                return "\n".join(lineas)
        
        except Exception as e:
            logger.error(f"❌ Error exportando historial: {e}")
            return ""
