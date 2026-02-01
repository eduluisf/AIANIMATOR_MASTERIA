"""
AI Animator - Prompt Parser
Extrae componentes semánticos del lenguaje natural
"""

from ..config import (
    SPEED_MODIFIERS,
    INTENSITY_MODIFIERS,
    EMOTIONS,
    ACTIONS,
    USE_SEMANTIC_MODIFIERS
)


class PromptParser:
    """
    Parsea prompts en lenguaje natural para extraer:
    - Acciones (walk, run, jump, etc.)
    - Emociones (happy, sad, tired, etc.)
    - Modificadores de velocidad (fast, slow)
    - Modificadores de intensidad (big, subtle)
    - Transformaciones semánticas (strong, powerful, vigorous, etc.)
    """

    def __init__(self):
        self.speed_modifiers = SPEED_MODIFIERS
        self.intensity_modifiers = INTENSITY_MODIFIERS
        self.emotions = EMOTIONS
        self.actions = ACTIONS
        self._transformer = None
        self._use_semantic = False

    def enable_semantic_detection(self, transformer):
        """Habilita detección semántica usando el AnimationTransformer."""
        self._transformer = transformer
        self._use_semantic = USE_SEMANTIC_MODIFIERS

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
                - transform_config: TransformConfig o None
                - target_bone_groups: list[BoneGroup]
                - semantic_detected: bool
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
            'clean_terms': [],
            'transform_config': None,
            'target_bone_groups': [],
            'semantic_detected': False,
        }

        # Detectar emociones
        for emotion in self.emotions:
            if emotion in prompt_lower:
                result['emotions'].append(emotion)

        # Detectar acciones
        for action in self.actions:
            if action in prompt_lower:
                result['actions'].append(action)

        # Usar detección semántica si está disponible
        if self._use_semantic and self._transformer and self._transformer.is_initialized:
            print("\n--- Semantic Modifier Detection ---")
            transform_config = self._transformer.analyze_prompt(result)
            result['speed'] = transform_config.speed_factor
            result['intensity'] = transform_config.intensity_factor
            result['transform_config'] = transform_config
            result['target_bone_groups'] = transform_config.target_bone_groups
            result['semantic_detected'] = True
        else:
            # Fallback: detección por keywords
            sorted_speed = sorted(self.speed_modifiers.keys(), key=len, reverse=True)
            for mod in sorted_speed:
                if mod in working_prompt:
                    result['speed'] = self.speed_modifiers[mod]
                    working_prompt = working_prompt.replace(mod, ' ')
                    break

            sorted_intensity = sorted(self.intensity_modifiers.keys(), key=len, reverse=True)
            for mod in sorted_intensity:
                if mod in working_prompt:
                    result['intensity'] = self.intensity_modifiers[mod]
                    working_prompt = working_prompt.replace(mod, ' ')
                    break

        # Determinar si es compuesto
        result['is_compound'] = self._is_compound(result)

        # Generar términos limpios para búsqueda semántica
        clean_words = working_prompt.split()
        result['clean_terms'] = [w for w in clean_words if len(w) > 2]

        return result

    def _is_compound(self, parsed: dict) -> bool:
        """Determina si el prompt requiere blending de múltiples animaciones"""
        if parsed['emotions'] and parsed['actions']:
            return True
        if len(parsed['actions']) > 1:
            return True
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
            if parsed['actions']:
                action_query = ' '.join(parsed['actions'])
                queries.append((action_query, 0.7))

            if parsed['emotions']:
                emotion_query = ' '.join(parsed['emotions'])
                queries.append((emotion_query, 0.3))
        else:
            queries.append((parsed['original'], 1.0))

        return queries
