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
    get_sequence_detector,
    get_sequence_builder,
    get_in_place_processor,
    process_prompt_for_sequence
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
    'get_sequence_detector',
    'get_sequence_builder',
    'get_in_place_processor',
    'process_prompt_for_sequence',
]
