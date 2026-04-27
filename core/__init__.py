"""
AI Animator - Core Module
"""

from .parser import PromptParser
from .matcher import AnimationMatcher
from .blender import MotionBlender
from .loop import AutoLoop
from .retarget import BoneMapper, Retargeter, get_retargeter, auto_detect_source_rig
from .sequence import (
    SequenceDetector,
    SequenceBuilder,
    InPlaceProcessor,
    OverlayDetector,
    get_sequence_detector,
    get_sequence_builder,
    get_in_place_processor,
    get_overlay_detector,
    process_prompt_for_sequence,
    process_prompt_for_overlay,
)
from .transform import (
    AnimationTransformer,
    SemanticModifierDetector,
    ActionBoneGroupResolver,
    TransformConfig,
    ModifierType,
    BoneGroup,
    get_transformer,
    initialize_transformer,
    locomotion_score,
    assign_overlay_roles,
)

__all__ = [
    'PromptParser',
    'AnimationMatcher',
    'MotionBlender',
    'AutoLoop',
    'BoneMapper',
    'Retargeter',
    'get_retargeter',
    'auto_detect_source_rig',
    'SequenceDetector',
    'SequenceBuilder',
    'InPlaceProcessor',
    'OverlayDetector',
    'get_sequence_detector',
    'get_sequence_builder',
    'get_in_place_processor',
    'get_overlay_detector',
    'process_prompt_for_sequence',
    'process_prompt_for_overlay',
    'AnimationTransformer',
    'SemanticModifierDetector',
    'ActionBoneGroupResolver',
    'TransformConfig',
    'ModifierType',
    'BoneGroup',
    'get_transformer',
    'initialize_transformer',
]
