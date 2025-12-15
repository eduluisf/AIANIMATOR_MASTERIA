"""
AI Animator - Prompt Parser
Extrae componentes semánticos del lenguaje natural
"""

from ..config import (
    SPEED_MODIFIERS,
    INTENSITY_MODIFIERS,
    EMOTIONS,
    ACTIONS
)


class PromptParser:
    """
    Parsea prompts en lenguaje natural para extraer:
    - Acciones (walk, run, jump, etc.)
    - Emociones (happy, sad, tired, etc.)
    - Modificadores de velocidad (fast, slow)
    - Modificadores de intensidad (big, subtle)
    """
    
    def __init__(self):
        self.speed_modifiers = SPEED_MODIFIERS
        self.intensity_modifiers = INTENSITY_MODIFIERS
        self.emotions = EMOTIONS
        self.actions = ACTIONS
    
    def parse(self, prompt: str) -> dict:
        """
        Parsea el prompt y devuelve componentes estructurados.
        
        Args:
            prompt: Descripción en lenguaje natural (ej: "happy jump fast")
            
        Returns:
            dict con:
                - original: str - Prompt original
                - actions: list[str] - Acciones detectadas
                - emotions: list[str] - Emociones detectadas
                - speed: float - Multiplicador de velocidad (default 1.0)
                - intensity: float - Multiplicador de amplitud (default 1.0)
                - is_compound: bool - Si requiere blending de múltiples anims
                - clean_terms: list[str] - Términos limpios para búsqueda
        """
        prompt_lower = prompt.lower().strip()
        working_prompt = prompt_lower
        
        result = {
            'original': prompt,
            'actions': [],
            'emotions': [],
            'speed': 1.0,
            'intensity': 1.0,
            'is_compound': False,
            'clean_terms': []
        }
        
        # Detectar modificadores de velocidad (primero los más largos)
        sorted_speed = sorted(self.speed_modifiers.keys(), key=len, reverse=True)
        for mod in sorted_speed:
            if mod in working_prompt:
                result['speed'] = self.speed_modifiers[mod]
                working_prompt = working_prompt.replace(mod, ' ')
                break  # Solo aplicar un modificador de velocidad
        
        # Detectar modificadores de intensidad
        sorted_intensity = sorted(self.intensity_modifiers.keys(), key=len, reverse=True)
        for mod in sorted_intensity:
            if mod in working_prompt:
                result['intensity'] = self.intensity_modifiers[mod]
                working_prompt = working_prompt.replace(mod, ' ')
                break
        
        # Detectar emociones
        for emotion in self.emotions:
            if emotion in prompt_lower:
                result['emotions'].append(emotion)
        
        # Detectar acciones
        for action in self.actions:
            if action in prompt_lower:
                result['actions'].append(action)
        
        # Determinar si es compuesto
        result['is_compound'] = self._is_compound(result)
        
        # Generar términos limpios para búsqueda semántica
        clean_words = working_prompt.split()
        result['clean_terms'] = [w for w in clean_words if len(w) > 2]
        
        return result
    
    def _is_compound(self, parsed: dict) -> bool:
        """Determina si el prompt requiere blending de múltiples animaciones"""
        # Emoción + Acción = compuesto
        if parsed['emotions'] and parsed['actions']:
            return True
        # Múltiples acciones = compuesto
        if len(parsed['actions']) > 1:
            return True
        # Múltiples emociones = compuesto
        if len(parsed['emotions']) > 1:
            return True
        return False
    
    def get_search_queries(self, parsed: dict) -> list:
        """
        Genera queries de búsqueda optimizadas basadas en el prompt parseado.
        
        Returns:
            Lista de (query, weight) para búsqueda semántica
        """
        queries = []
        
        if parsed['is_compound']:
            # Para prompts compuestos, buscar componentes por separado
            if parsed['actions']:
                action_query = ' '.join(parsed['actions'])
                queries.append((action_query, 0.7))
            
            if parsed['emotions']:
                emotion_query = ' '.join(parsed['emotions'])
                queries.append((emotion_query, 0.3))
        else:
            # Para prompts simples, usar el original
            queries.append((parsed['original'], 1.0))
        
        return queries
