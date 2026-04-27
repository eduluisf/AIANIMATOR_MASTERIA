"""
AI Animator - Semantic Transform Module
Detección semántica de modificadores y transformación selectiva por grupo de huesos.
"""

import re
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# =============================================================================
# ENUMS Y DATACLASSES
# =============================================================================

class ModifierType(Enum):
    SPEED_FAST = "speed_fast"
    SPEED_SLOW = "speed_slow"
    INTENSITY_STRONG = "intensity_strong"
    INTENSITY_WEAK = "intensity_weak"


class BoneGroup(Enum):
    ARMS = "arms"
    LEGS = "legs"
    SPINE = "spine"
    HEAD = "head"
    FULL_BODY = "full_body"


@dataclass
class SemanticModifier:
    modifier_type: ModifierType
    factor: float
    confidence: float
    matched_concept: str


@dataclass
class TransformConfig:
    speed_factor: float = 1.0
    intensity_factor: float = 1.0
    target_bone_groups: List[BoneGroup] = field(default_factory=lambda: [BoneGroup.FULL_BODY])
    speed_confidence: float = 0.0
    intensity_confidence: float = 0.0


# =============================================================================
# CONCEPTOS SEMÁNTICOS
# =============================================================================

SEMANTIC_CONCEPTS = {
    ModifierType.SPEED_FAST: {
        'phrases': [
            "fast", "quick", "rapid", "speedy", "swift",
            "hurry", "rushed", "brisk", "snappy",
            # Español
            "rápido", "veloz", "acelerado", "apresurado",
        ],
        'factor': 1.5,
    },
    ModifierType.SPEED_SLOW: {
        'phrases': [
            "slow", "leisurely", "unhurried", "gradual",
            "calm", "measured", "deliberate",
            # Español
            "lento", "pausado", "calmado", "despacio",
        ],
        'factor': 0.6,
    },
    ModifierType.INTENSITY_STRONG: {
        'phrases': [
            "strong", "hard", "powerful", "forceful", "vigorous",
            "intense", "aggressive", "heavy", "emphatic", "energetic",
            # Español
            "fuerte", "potente", "vigoroso", "intenso", "agresivo",
        ],
        'factor': 1.4,
    },
    ModifierType.INTENSITY_WEAK: {
        'phrases': [
            "soft", "gentle", "subtle", "light", "delicate",
            "weak", "mild", "tender", "faint",
            # Español
            "suave", "ligero", "delicado", "débil", "tenue",
        ],
        'factor': 0.7,
    },
}

INTENSIFIERS = {
    'very': 1.33,
    'extremely': 1.5,
    'super': 1.4,
    'really': 1.25,
    'quite': 1.15,
    'slightly': 0.5,
    'somewhat': 0.6,
    'a bit': 0.7,
    # Español
    'muy': 1.33,
    'extremadamente': 1.5,
    'bastante': 1.15,
    'un poco': 0.7,
    'ligeramente': 0.5,
}

# =============================================================================
# MAPEO ACCIÓN → GRUPO DE HUESOS
# =============================================================================

ACTION_BONE_MAPPING = {
    # Brazos
    'clap': [BoneGroup.ARMS],
    'wave': [BoneGroup.ARMS],
    'throw': [BoneGroup.ARMS],
    'catch': [BoneGroup.ARMS],
    'punch': [BoneGroup.ARMS],
    'grab': [BoneGroup.ARMS],
    'push': [BoneGroup.ARMS],
    'pull': [BoneGroup.ARMS],
    'point': [BoneGroup.ARMS],
    'shoot': [BoneGroup.ARMS],
    'aim': [BoneGroup.ARMS],
    'reload': [BoneGroup.ARMS],
    'slash': [BoneGroup.ARMS],
    'stab': [BoneGroup.ARMS],
    # Español
    'aplaudir': [BoneGroup.ARMS],
    'saludar': [BoneGroup.ARMS],
    'lanzar': [BoneGroup.ARMS],
    'golpear': [BoneGroup.ARMS],

    # Piernas
    'kick': [BoneGroup.LEGS],
    'walk': [BoneGroup.LEGS],
    'run': [BoneGroup.LEGS],
    'jog': [BoneGroup.LEGS],
    'sprint': [BoneGroup.LEGS],
    'jump': [BoneGroup.LEGS],
    'hop': [BoneGroup.LEGS],
    'crouch': [BoneGroup.LEGS],
    'kneel': [BoneGroup.LEGS],
    'sneak': [BoneGroup.LEGS],
    # Español
    'patear': [BoneGroup.LEGS],
    'caminar': [BoneGroup.LEGS],
    'correr': [BoneGroup.LEGS],
    'saltar': [BoneGroup.LEGS],
    'agacharse': [BoneGroup.LEGS],

    # Cuerpo completo
    'dance': [BoneGroup.FULL_BODY],
    'stretch': [BoneGroup.FULL_BODY],
    'fall': [BoneGroup.FULL_BODY],
    'roll': [BoneGroup.FULL_BODY],
    'dodge': [BoneGroup.FULL_BODY],
    'climb': [BoneGroup.FULL_BODY],
    'fight': [BoneGroup.FULL_BODY],
    'attack': [BoneGroup.FULL_BODY],
    # Español
    'bailar': [BoneGroup.FULL_BODY],
    'rodar': [BoneGroup.FULL_BODY],
    'pelear': [BoneGroup.FULL_BODY],
    'atacar': [BoneGroup.FULL_BODY],

    # Torso
    'bow': [BoneGroup.SPINE],
    # Español

    # Cabeza
    'nod': [BoneGroup.HEAD],
    'shake': [BoneGroup.HEAD],
}

# =============================================================================
# HUESOS MIXAMO POR GRUPO
# =============================================================================

# Acciones que mueven al personaje en el espacio: deben ser dueñas del root/hips.
LOCOMOTION_ACTIONS = {
    'walk', 'run', 'jog', 'sprint', 'jump', 'hop', 'crouch', 'sneak',
    'climb', 'roll', 'fall', 'dodge',
    # Español
    'caminar', 'correr', 'saltar', 'agacharse', 'rodar',
}

LOCOMOTION_CONCEPTS = [
    "walking", "running", "jogging", "sprinting",
    "moving forward", "stepping", "locomotion",
    "displacement", "traveling", "running across",
]


def locomotion_score(query: str, model=None) -> float:
    """0.0 si no hay locomoción detectable; 1.0 si la frase es claramente locomoción.

    Capa 1: keyword exacto contra LOCOMOTION_ACTIONS → 1.0
    Capa 2: similitud de embedding contra LOCOMOTION_CONCEPTS (si hay BERT)
    """
    if not query:
        return 0.0
    q = query.lower()
    for kw in LOCOMOTION_ACTIONS:
        if kw in q.split() or f' {kw} ' in f' {q} ':
            return 1.0
    if model is None:
        return 0.0
    try:
        qe = model.encode(q)
        ce = model.encode(LOCOMOTION_CONCEPTS)
        sims = np.dot(ce, qe) / (
            np.linalg.norm(ce, axis=1) * np.linalg.norm(qe) + 1e-8
        )
        return float(np.max(sims))
    except Exception:
        return 0.0


def assign_overlay_roles(left_query: str, right_query: str, model=None):
    """Decide qué lado del 'while' es la base (locomoción/root) y cuál el gesto.

    Returns (base_is_left: bool, base_score: float, overlay_score: float).
    Si ambos lados tienen score parecido, gana el orden natural (right=base).
    """
    left_score = locomotion_score(left_query, model)
    right_score = locomotion_score(right_query, model)

    THRESHOLD = 0.45
    DIFF = 0.08

    if max(left_score, right_score) < THRESHOLD:
        return (False, right_score, left_score)

    if left_score > right_score + DIFF:
        return (True, left_score, right_score)
    return (False, right_score, left_score)


MIXAMO_BONE_GROUPS = {
    BoneGroup.ARMS: [
        'mixamorig:leftshoulder', 'mixamorig:rightshoulder',
        'mixamorig:leftarm', 'mixamorig:rightarm',
        'mixamorig:leftforearm', 'mixamorig:rightforearm',
        'mixamorig:lefthand', 'mixamorig:righthand',
        # Dedos izquierda
        'mixamorig:lefthandthumb1', 'mixamorig:lefthandthumb2', 'mixamorig:lefthandthumb3',
        'mixamorig:lefthandindex1', 'mixamorig:lefthandindex2', 'mixamorig:lefthandindex3',
        'mixamorig:lefthandmiddle1', 'mixamorig:lefthandmiddle2', 'mixamorig:lefthandmiddle3',
        'mixamorig:lefthandring1', 'mixamorig:lefthandring2', 'mixamorig:lefthandring3',
        'mixamorig:lefthandpinky1', 'mixamorig:lefthandpinky2', 'mixamorig:lefthandpinky3',
        # Dedos derecha
        'mixamorig:righthandthumb1', 'mixamorig:righthandthumb2', 'mixamorig:righthandthumb3',
        'mixamorig:righthandindex1', 'mixamorig:righthandindex2', 'mixamorig:righthandindex3',
        'mixamorig:righthandmiddle1', 'mixamorig:righthandmiddle2', 'mixamorig:righthandmiddle3',
        'mixamorig:righthandring1', 'mixamorig:righthandring2', 'mixamorig:righthandring3',
        'mixamorig:righthandpinky1', 'mixamorig:righthandpinky2', 'mixamorig:righthandpinky3',
    ],
    BoneGroup.LEGS: [
        'mixamorig:leftupleg', 'mixamorig:rightupleg',
        'mixamorig:leftleg', 'mixamorig:rightleg',
        'mixamorig:leftfoot', 'mixamorig:rightfoot',
        'mixamorig:lefttoebase', 'mixamorig:righttoebase',
    ],
    BoneGroup.SPINE: [
        'mixamorig:spine', 'mixamorig:spine1', 'mixamorig:spine2',
    ],
    BoneGroup.HEAD: [
        'mixamorig:neck', 'mixamorig:head',
    ],
    BoneGroup.FULL_BODY: None,  # None = todos los huesos
}


# =============================================================================
# SEMANTIC MODIFIER DETECTOR
# =============================================================================

class SemanticModifierDetector:
    """Detecta modificadores de velocidad/intensidad usando embeddings semánticos."""

    def __init__(self, model=None):
        self.model = model
        self._concept_embeddings = None

    def set_model(self, model):
        self.model = model
        self._precompute_concept_embeddings()

    def _precompute_concept_embeddings(self):
        if not self.model:
            return

        self._concept_embeddings = {}

        for modifier_type, config in SEMANTIC_CONCEPTS.items():
            embeddings = []
            for phrase in config['phrases']:
                emb = self.model.encode(phrase)
                embeddings.append(emb)

            self._concept_embeddings[modifier_type] = {
                'embeddings': np.array(embeddings),
                'centroid': np.mean(embeddings, axis=0),
                'phrases': config['phrases'],
                'factor': config['factor'],
            }

        print("  ✓ Semantic modifier embeddings pre-computed")

    def detect_modifiers(self, prompt: str,
                         threshold: float = 0.5) -> List[SemanticModifier]:
        if not self.model or not self._concept_embeddings:
            return self._fallback_keyword_detection(prompt)

        detected = []
        prompt_lower = prompt.lower()

        # Detectar intensificadores
        intensifier_multiplier = 1.0
        sorted_intensifiers = sorted(INTENSIFIERS.keys(), key=len, reverse=True)
        for intensifier in sorted_intensifiers:
            if intensifier in prompt_lower:
                intensifier_multiplier = INTENSIFIERS[intensifier]
                # Eliminar intensificador del prompt para no confundir la detección
                prompt_lower = prompt_lower.replace(intensifier, ' ').strip()
                break

        # Extraer palabras candidatas a modificador (excluir acciones conocidas)
        words = prompt_lower.split()

        # Encontrar la mejor coincidencia por categoría
        speed_best = None
        intensity_best = None

        for word in words:
            if len(word) < 3:
                continue

            word_emb = self.model.encode(word)

            for modifier_type, concept_data in self._concept_embeddings.items():
                # Calcular similitud contra cada frase del concepto
                sims = np.dot(concept_data['embeddings'], word_emb)
                norms = np.linalg.norm(concept_data['embeddings'], axis=1) * np.linalg.norm(word_emb)
                sims = sims / (norms + 1e-8)

                best_idx = np.argmax(sims)
                best_sim = float(sims[best_idx])

                if best_sim < threshold:
                    continue

                base_factor = concept_data['factor']
                adjusted_factor = self._apply_intensifier(base_factor, intensifier_multiplier)

                candidate = SemanticModifier(
                    modifier_type=modifier_type,
                    factor=adjusted_factor,
                    confidence=best_sim,
                    matched_concept=concept_data['phrases'][best_idx],
                )

                is_speed = modifier_type in (ModifierType.SPEED_FAST, ModifierType.SPEED_SLOW)
                is_intensity = modifier_type in (ModifierType.INTENSITY_STRONG, ModifierType.INTENSITY_WEAK)

                if is_speed and (speed_best is None or best_sim > speed_best.confidence):
                    speed_best = candidate
                elif is_intensity and (intensity_best is None or best_sim > intensity_best.confidence):
                    intensity_best = candidate

        if speed_best:
            detected.append(speed_best)
        if intensity_best:
            detected.append(intensity_best)

        return detected

    def _apply_intensifier(self, base_factor: float, intensifier_mult: float) -> float:
        if base_factor > 1.0:
            deviation = base_factor - 1.0
            return 1.0 + (deviation * intensifier_mult)
        else:
            deviation = 1.0 - base_factor
            return 1.0 - (deviation * intensifier_mult)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

    def _fallback_keyword_detection(self, prompt: str) -> List[SemanticModifier]:
        detected = []
        prompt_lower = prompt.lower()

        # Detectar intensificador
        intensifier_multiplier = 1.0
        sorted_intensifiers = sorted(INTENSIFIERS.keys(), key=len, reverse=True)
        for intensifier in sorted_intensifiers:
            if intensifier in prompt_lower:
                intensifier_multiplier = INTENSIFIERS[intensifier]
                break

        for modifier_type, concept_data in SEMANTIC_CONCEPTS.items():
            for phrase in concept_data['phrases']:
                if phrase in prompt_lower:
                    base_factor = concept_data['factor']
                    adjusted = self._apply_intensifier(base_factor, intensifier_multiplier)
                    detected.append(SemanticModifier(
                        modifier_type=modifier_type,
                        factor=adjusted,
                        confidence=1.0,
                        matched_concept=phrase,
                    ))
                    break
        return detected


# =============================================================================
# ACTION BONE GROUP RESOLVER
# =============================================================================

class ActionBoneGroupResolver:
    """Determina qué grupos de huesos afectar según la acción detectada."""

    def __init__(self, model=None):
        self.model = model
        self._action_embeddings = None

    def set_model(self, model):
        self.model = model
        self._precompute_action_embeddings()

    def _precompute_action_embeddings(self):
        if not self.model:
            return
        self._action_embeddings = {}
        for action in ACTION_BONE_MAPPING.keys():
            self._action_embeddings[action] = self.model.encode(action)

    def resolve_bone_groups(self, actions: List[str]) -> List[BoneGroup]:
        groups = set()

        for action in actions:
            action_lower = action.lower()

            if action_lower in ACTION_BONE_MAPPING:
                for bg in ACTION_BONE_MAPPING[action_lower]:
                    groups.add(bg)
            elif self.model and self._action_embeddings:
                matched = self._semantic_action_match(action_lower)
                if matched:
                    for bg in ACTION_BONE_MAPPING[matched]:
                        groups.add(bg)

        if not groups:
            groups.add(BoneGroup.FULL_BODY)

        if BoneGroup.FULL_BODY in groups:
            return [BoneGroup.FULL_BODY]

        return list(groups)

    def _semantic_action_match(self, action: str, threshold: float = 0.6) -> Optional[str]:
        if not self._action_embeddings:
            return None

        action_emb = self.model.encode(action)
        best_match = None
        best_score = 0.0

        for known_action, emb in self._action_embeddings.items():
            sim = float(np.dot(action_emb, emb) / (
                np.linalg.norm(action_emb) * np.linalg.norm(emb) + 1e-8
            ))
            if sim > best_score and sim >= threshold:
                best_score = sim
                best_match = known_action

        return best_match

    def get_bones_for_groups(self, groups: List[BoneGroup]) -> Optional[List[str]]:
        if BoneGroup.FULL_BODY in groups:
            return None

        bones = []
        for group in groups:
            group_bones = MIXAMO_BONE_GROUPS.get(group)
            if group_bones:
                bones.extend(group_bones)

        return list(set(bones)) if bones else None


# =============================================================================
# ANIMATION TRANSFORMER
# =============================================================================

class AnimationTransformer:
    """Orquestador: detección semántica + transformación selectiva."""

    def __init__(self):
        self.modifier_detector = SemanticModifierDetector()
        self.bone_resolver = ActionBoneGroupResolver()
        self._model = None

    def initialize(self, model):
        self._model = model
        self.modifier_detector.set_model(model)
        self.bone_resolver.set_model(model)
        print("✓ Semantic Transform Module initialized")

    @property
    def is_initialized(self):
        return self._model is not None

    def analyze_prompt(self, parsed_prompt: dict) -> TransformConfig:
        config = TransformConfig()

        # Detectar modificadores semánticos
        modifiers = self.modifier_detector.detect_modifiers(
            parsed_prompt['original']
        )

        for mod in modifiers:
            if mod.modifier_type in (ModifierType.SPEED_FAST, ModifierType.SPEED_SLOW):
                config.speed_factor = mod.factor
                config.speed_confidence = mod.confidence
                print(f"  → Speed: {mod.factor:.2f}x ('{mod.matched_concept}', conf={mod.confidence:.2f})")
            elif mod.modifier_type in (ModifierType.INTENSITY_STRONG, ModifierType.INTENSITY_WEAK):
                config.intensity_factor = mod.factor
                config.intensity_confidence = mod.confidence
                print(f"  → Intensity: {mod.factor:.2f}x ('{mod.matched_concept}', conf={mod.confidence:.2f})")

        # Determinar grupos de huesos
        actions = parsed_prompt.get('actions', [])
        bone_groups = self.bone_resolver.resolve_bone_groups(actions)
        config.target_bone_groups = bone_groups
        print(f"  → Bone groups: {[bg.value for bg in bone_groups]}")

        return config

    def apply_transforms(self, action, config: TransformConfig):
        """Aplica transformaciones a una Action de Blender."""
        target_bones = self.bone_resolver.get_bones_for_groups(
            config.target_bone_groups
        )

        if config.speed_factor != 1.0:
            self._apply_speed(action, config.speed_factor)

        if config.intensity_factor != 1.0:
            self._apply_intensity(action, config.intensity_factor, target_bones)

    def _apply_speed(self, action, factor: float):
        """Escala keyframes en el tiempo (afecta toda la animación)."""
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.co[0] = kp.co[0] / factor
                kp.handle_left[0] = kp.handle_left[0] / factor
                kp.handle_right[0] = kp.handle_right[0] / factor
        print(f"  ✓ Speed applied: {factor:.2f}x")

    def _apply_intensity(self, action, factor: float,
                         target_bones: Optional[List[str]]):
        """Escala amplitud de movimiento en huesos específicos."""
        curves_modified = 0

        for fc in action.fcurves:
            is_location = 'location' in fc.data_path
            is_rotation = 'rotation' in fc.data_path

            if not (is_location or is_rotation):
                continue

            # Filtrar por hueso
            if target_bones is not None:
                bone_match = False
                for bone_name in target_bones:
                    if bone_name.lower() in fc.data_path.lower():
                        bone_match = True
                        break
                if not bone_match:
                    continue

            values = [kp.co[1] for kp in fc.keyframe_points]
            if not values:
                continue

            base_value = sum(values) / len(values)

            for kp in fc.keyframe_points:
                deviation = kp.co[1] - base_value
                kp.co[1] = base_value + (deviation * factor)

                handle_left_dev = kp.handle_left[1] - base_value
                handle_right_dev = kp.handle_right[1] - base_value
                kp.handle_left[1] = base_value + (handle_left_dev * factor)
                kp.handle_right[1] = base_value + (handle_right_dev * factor)

            curves_modified += 1

        bone_info = f"{len(target_bones)} bones" if target_bones else "ALL bones"
        print(f"  ✓ Intensity applied: {factor:.2f}x on {bone_info} ({curves_modified} curves)")


# =============================================================================
# SINGLETON
# =============================================================================

_transformer = None


def get_transformer() -> AnimationTransformer:
    global _transformer
    if _transformer is None:
        _transformer = AnimationTransformer()
    return _transformer


def initialize_transformer(model):
    transformer = get_transformer()
    transformer.initialize(model)
    return transformer
