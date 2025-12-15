"""
AI Animator - Retargeting System
Sistema de mapeo semántico de huesos para transferir animaciones
entre diferentes rigs (Mixamo → Rigify, Custom, etc.)
"""

import bpy
import re
from typing import Dict, List, Tuple, Optional


# =============================================================================
# VOCABULARIO DE HUESOS - Incluye Mixamo, Rigify, y variantes comunes
# =============================================================================

BONE_VOCABULARY = {
    # =========================================================================
    # RAÍZ Y CADERA
    # =========================================================================
    'hips': [
        # Mixamo
        'mixamorig:hips',
        # Rigify
        'torso', 'spine', 'DEF-spine', 'ORG-spine',
        # Común
        'hips', 'hip', 'pelvis', 'root', 'cog', 'center_of_gravity',
        'cadera', 'caderas', 'raiz',
        'def_pelvis', 'bn_pelvis', 'bip01_pelvis',
    ],
    
    # =========================================================================
    # COLUMNA
    # =========================================================================
    'spine': [
        # Mixamo
        'mixamorig:spine',
        # Rigify
        'DEF-spine.001', 'ORG-spine.001', 'spine.001',
        # Común
        'spine', 'spine1', 'spine01', 'spine_01',
        'columna', 'espina',
        'def_spine', 'bn_spine', 'bip01_spine', 
        'abdomen', 'stomach',
    ],
    'spine1': [
        # Mixamo
        'mixamorig:spine1',
        # Rigify
        'DEF-spine.002', 'ORG-spine.002', 'spine.002',
        # Común
        'spine1', 'spine2', 'spine02', 'spine_02',
        'chest_lower', 'lower_chest',
        'def_spine1', 'bn_spine1',
    ],
    'spine2': [
        # Mixamo
        'mixamorig:spine2',
        # Rigify
        'DEF-spine.003', 'ORG-spine.003', 'spine.003', 'chest',
        # Común
        'spine2', 'spine3', 'spine03', 'spine_03',
        'upper_chest', 'ribcage',
        'def_spine2', 'bn_spine2',
    ],
    
    # =========================================================================
    # CUELLO Y CABEZA
    # =========================================================================
    'neck': [
        # Mixamo
        'mixamorig:neck',
        # Rigify
        'DEF-spine.004', 'ORG-spine.004', 'spine.004',
        'DEF-neck', 'ORG-neck', 'neck',
        # Común
        'neck1', 'neck01', 'cuello',
        'def_neck', 'bn_neck', 'bip01_neck', 'cervical',
    ],
    'head': [
        # Mixamo
        'mixamorig:head',
        # Rigify
        'DEF-spine.006', 'ORG-spine.006', 'spine.006',
        'DEF-head', 'ORG-head',
        # Común
        'head', 'cabeza', 'skull', 'craneo',
        'def_head', 'bn_head', 'bip01_head',
    ],
    
    # =========================================================================
    # HOMBROS / CLAVÍCULAS
    # =========================================================================
    'shoulder_l': [
        # Mixamo
        'mixamorig:leftshoulder',
        # Rigify
        'DEF-shoulder.L', 'ORG-shoulder.L', 'shoulder.L',
        # Común
        'leftshoulder', 'shoulder_l', 'shoulder.l', 'l_shoulder',
        'l.shoulder', 'hombro_izq', 'hombro.l', 'clavicle_l',
        'def_shoulder_l', 'bn_shoulder_l',
        'bip01_l_clavicle', 'left_collar', 'l_clavicle',
    ],
    'shoulder_r': [
        # Mixamo
        'mixamorig:rightshoulder',
        # Rigify
        'DEF-shoulder.R', 'ORG-shoulder.R', 'shoulder.R',
        # Común
        'rightshoulder', 'shoulder_r', 'shoulder.r', 'r_shoulder',
        'r.shoulder', 'hombro_der', 'hombro.r', 'clavicle_r',
        'def_shoulder_r', 'bn_shoulder_r',
        'bip01_r_clavicle', 'right_collar', 'r_clavicle',
    ],
    
    # =========================================================================
    # BRAZOS IZQUIERDO
    # =========================================================================
    'arm_l': [
        # Mixamo
        'mixamorig:leftarm',
        # Rigify
        'DEF-upper_arm.L', 'DEF-upper_arm.L.001', 'ORG-upper_arm.L', 
        'upper_arm.L', 'upper_arm.L.001',
        # Común
        'leftarm', 'arm_l', 'arm.l', 'l_arm', 'l.arm',
        'brazo_izq', 'brazo.l', 'upper_arm_l', 'upperarm_l',
        'def_arm_l', 'bn_arm_l',
        'bip01_l_upperarm', 'left_upper_arm', 'l_upperarm',
    ],
    'forearm_l': [
        # Mixamo
        'mixamorig:leftforearm',
        # Rigify
        'DEF-forearm.L', 'DEF-forearm.L.001', 'ORG-forearm.L',
        'forearm.L', 'forearm.L.001',
        # Común
        'leftforearm', 'forearm_l', 'forearm.l', 'l_forearm',
        'l.forearm', 'antebrazo_izq', 'antebrazo.l', 'lower_arm_l',
        'def_forearm_l', 'bn_forearm_l',
        'bip01_l_forearm', 'left_lower_arm', 'l_lowerarm',
    ],
    'hand_l': [
        # Mixamo
        'mixamorig:lefthand',
        # Rigify
        'DEF-hand.L', 'ORG-hand.L', 'hand.L',
        # Común
        'lefthand', 'hand_l', 'hand.l', 'l_hand', 'l.hand',
        'mano_izq', 'mano.l', 'wrist_l',
        'def_hand_l', 'bn_hand_l',
        'bip01_l_hand', 'left_hand', 'l_wrist',
    ],
    
    # =========================================================================
    # BRAZOS DERECHO
    # =========================================================================
    'arm_r': [
        # Mixamo
        'mixamorig:rightarm',
        # Rigify
        'DEF-upper_arm.R', 'DEF-upper_arm.R.001', 'ORG-upper_arm.R',
        'upper_arm.R', 'upper_arm.R.001',
        # Común
        'rightarm', 'arm_r', 'arm.r', 'r_arm', 'r.arm',
        'brazo_der', 'brazo.r', 'upper_arm_r', 'upperarm_r',
        'def_arm_r', 'bn_arm_r',
        'bip01_r_upperarm', 'right_upper_arm', 'r_upperarm',
    ],
    'forearm_r': [
        # Mixamo
        'mixamorig:rightforearm',
        # Rigify
        'DEF-forearm.R', 'DEF-forearm.R.001', 'ORG-forearm.R',
        'forearm.R', 'forearm.R.001',
        # Común
        'rightforearm', 'forearm_r', 'forearm.r', 'r_forearm',
        'r.forearm', 'antebrazo_der', 'antebrazo.r', 'lower_arm_r',
        'def_forearm_r', 'bn_forearm_r',
        'bip01_r_forearm', 'right_lower_arm', 'r_lowerarm',
    ],
    'hand_r': [
        # Mixamo
        'mixamorig:righthand',
        # Rigify
        'DEF-hand.R', 'ORG-hand.R', 'hand.R',
        # Común
        'righthand', 'hand_r', 'hand.r', 'r_hand', 'r.hand',
        'mano_der', 'mano.r', 'wrist_r',
        'def_hand_r', 'bn_hand_r',
        'bip01_r_hand', 'right_hand', 'r_wrist',
    ],
    
    # =========================================================================
    # PIERNAS IZQUIERDA
    # =========================================================================
    'leg_l': [
        # Mixamo
        'mixamorig:leftupleg',
        # Rigify
        'DEF-thigh.L', 'DEF-thigh.L.001', 'ORG-thigh.L',
        'thigh.L', 'thigh.L.001',
        # Común
        'leftupleg', 'leg_l', 'leg.l', 'l_leg', 'l.leg',
        'thigh_l', 'upper_leg_l', 'upperleg_l', 'pierna_izq',
        'def_leg_l', 'bn_leg_l',
        'bip01_l_thigh', 'left_upper_leg', 'l_thigh',
    ],
    'shin_l': [
        # Mixamo
        'mixamorig:leftleg',
        # Rigify
        'DEF-shin.L', 'DEF-shin.L.001', 'ORG-shin.L',
        'shin.L', 'shin.L.001',
        # Común
        'leftleg', 'shin_l', 'shin.l', 'l_shin', 'calf_l',
        'lower_leg_l', 'lowerleg_l', 'pantorrilla_izq',
        'def_shin_l', 'bn_shin_l',
        'bip01_l_calf', 'left_lower_leg', 'l_calf',
    ],
    'foot_l': [
        # Mixamo
        'mixamorig:leftfoot',
        # Rigify
        'DEF-foot.L', 'ORG-foot.L', 'foot.L',
        # Común
        'leftfoot', 'foot_l', 'foot.l', 'l_foot', 'l.foot',
        'pie_izq', 'pie.l', 'ankle_l',
        'def_foot_l', 'bn_foot_l',
        'bip01_l_foot', 'left_foot', 'l_ankle',
    ],
    'toe_l': [
        # Mixamo
        'mixamorig:lefttoebase',
        # Rigify
        'DEF-toe.L', 'ORG-toe.L', 'toe.L',
        # Común
        'lefttoebase', 'toe_l', 'toe.l', 'l_toe', 'toes_l',
        'dedos_pie_izq', 'ball_l',
        'def_toe_l', 'bn_toe_l',
        'bip01_l_toe0', 'left_toe', 'l_ball',
    ],
    
    # =========================================================================
    # PIERNAS DERECHA
    # =========================================================================
    'leg_r': [
        # Mixamo
        'mixamorig:rightupleg',
        # Rigify
        'DEF-thigh.R', 'DEF-thigh.R.001', 'ORG-thigh.R',
        'thigh.R', 'thigh.R.001',
        # Común
        'rightupleg', 'leg_r', 'leg.r', 'r_leg', 'r.leg',
        'thigh_r', 'upper_leg_r', 'upperleg_r', 'pierna_der',
        'def_leg_r', 'bn_leg_r',
        'bip01_r_thigh', 'right_upper_leg', 'r_thigh',
    ],
    'shin_r': [
        # Mixamo
        'mixamorig:rightleg',
        # Rigify
        'DEF-shin.R', 'DEF-shin.R.001', 'ORG-shin.R',
        'shin.R', 'shin.R.001',
        # Común
        'rightleg', 'shin_r', 'shin.r', 'r_shin', 'calf_r',
        'lower_leg_r', 'lowerleg_r', 'pantorrilla_der',
        'def_shin_r', 'bn_shin_r',
        'bip01_r_calf', 'right_lower_leg', 'r_calf',
    ],
    'foot_r': [
        # Mixamo
        'mixamorig:rightfoot',
        # Rigify
        'DEF-foot.R', 'ORG-foot.R', 'foot.R',
        # Común
        'rightfoot', 'foot_r', 'foot.r', 'r_foot', 'r.foot',
        'pie_der', 'pie.r', 'ankle_r',
        'def_foot_r', 'bn_foot_r',
        'bip01_r_foot', 'right_foot', 'r_ankle',
    ],
    'toe_r': [
        # Mixamo
        'mixamorig:righttoebase',
        # Rigify
        'DEF-toe.R', 'ORG-toe.R', 'toe.R',
        # Común
        'righttoebase', 'toe_r', 'toe.r', 'r_toe', 'toes_r',
        'dedos_pie_der', 'ball_r',
        'def_toe_r', 'bn_toe_r',
        'bip01_r_toe0', 'right_toe', 'r_ball',
    ],
    
    # =========================================================================
    # DEDOS MANO IZQUIERDA
    # =========================================================================
    # Pulgar
    'thumb_01_l': [
        'mixamorig:lefthandthumb1',
        'DEF-thumb.01.L', 'ORG-thumb.01.L', 'thumb.01.L',
        'thumb_01_l', 'thumb1_l', 'l_thumb1',
    ],
    'thumb_02_l': [
        'mixamorig:lefthandthumb2',
        'DEF-thumb.02.L', 'ORG-thumb.02.L', 'thumb.02.L',
        'thumb_02_l', 'thumb2_l', 'l_thumb2',
    ],
    'thumb_03_l': [
        'mixamorig:lefthandthumb3',
        'DEF-thumb.03.L', 'ORG-thumb.03.L', 'thumb.03.L',
        'thumb_03_l', 'thumb3_l', 'l_thumb3',
    ],
    # Índice
    'index_01_l': [
        'mixamorig:lefthandindex1',
        'DEF-f_index.01.L', 'ORG-f_index.01.L', 'f_index.01.L',
        'index_01_l', 'index1_l', 'l_index1',
    ],
    'index_02_l': [
        'mixamorig:lefthandindex2',
        'DEF-f_index.02.L', 'ORG-f_index.02.L', 'f_index.02.L',
        'index_02_l', 'index2_l', 'l_index2',
    ],
    'index_03_l': [
        'mixamorig:lefthandindex3',
        'DEF-f_index.03.L', 'ORG-f_index.03.L', 'f_index.03.L',
        'index_03_l', 'index3_l', 'l_index3',
    ],
    # Medio
    'middle_01_l': [
        'mixamorig:lefthandmiddle1',
        'DEF-f_middle.01.L', 'ORG-f_middle.01.L', 'f_middle.01.L',
        'middle_01_l', 'middle1_l', 'l_middle1',
    ],
    'middle_02_l': [
        'mixamorig:lefthandmiddle2',
        'DEF-f_middle.02.L', 'ORG-f_middle.02.L', 'f_middle.02.L',
        'middle_02_l', 'middle2_l', 'l_middle2',
    ],
    'middle_03_l': [
        'mixamorig:lefthandmiddle3',
        'DEF-f_middle.03.L', 'ORG-f_middle.03.L', 'f_middle.03.L',
        'middle_03_l', 'middle3_l', 'l_middle3',
    ],
    # Anular
    'ring_01_l': [
        'mixamorig:lefthandring1',
        'DEF-f_ring.01.L', 'ORG-f_ring.01.L', 'f_ring.01.L',
        'ring_01_l', 'ring1_l', 'l_ring1',
    ],
    'ring_02_l': [
        'mixamorig:lefthandring2',
        'DEF-f_ring.02.L', 'ORG-f_ring.02.L', 'f_ring.02.L',
        'ring_02_l', 'ring2_l', 'l_ring2',
    ],
    'ring_03_l': [
        'mixamorig:lefthandring3',
        'DEF-f_ring.03.L', 'ORG-f_ring.03.L', 'f_ring.03.L',
        'ring_03_l', 'ring3_l', 'l_ring3',
    ],
    # Meñique
    'pinky_01_l': [
        'mixamorig:lefthandpinky1',
        'DEF-f_pinky.01.L', 'ORG-f_pinky.01.L', 'f_pinky.01.L',
        'pinky_01_l', 'pinky1_l', 'l_pinky1',
    ],
    'pinky_02_l': [
        'mixamorig:lefthandpinky2',
        'DEF-f_pinky.02.L', 'ORG-f_pinky.02.L', 'f_pinky.02.L',
        'pinky_02_l', 'pinky2_l', 'l_pinky2',
    ],
    'pinky_03_l': [
        'mixamorig:lefthandpinky3',
        'DEF-f_pinky.03.L', 'ORG-f_pinky.03.L', 'f_pinky.03.L',
        'pinky_03_l', 'pinky3_l', 'l_pinky3',
    ],
    
    # =========================================================================
    # DEDOS MANO DERECHA
    # =========================================================================
    # Pulgar
    'thumb_01_r': [
        'mixamorig:righthandthumb1',
        'DEF-thumb.01.R', 'ORG-thumb.01.R', 'thumb.01.R',
        'thumb_01_r', 'thumb1_r', 'r_thumb1',
    ],
    'thumb_02_r': [
        'mixamorig:righthandthumb2',
        'DEF-thumb.02.R', 'ORG-thumb.02.R', 'thumb.02.R',
        'thumb_02_r', 'thumb2_r', 'r_thumb2',
    ],
    'thumb_03_r': [
        'mixamorig:righthandthumb3',
        'DEF-thumb.03.R', 'ORG-thumb.03.R', 'thumb.03.R',
        'thumb_03_r', 'thumb3_r', 'r_thumb3',
    ],
    # Índice
    'index_01_r': [
        'mixamorig:righthandindex1',
        'DEF-f_index.01.R', 'ORG-f_index.01.R', 'f_index.01.R',
        'index_01_r', 'index1_r', 'r_index1',
    ],
    'index_02_r': [
        'mixamorig:righthandindex2',
        'DEF-f_index.02.R', 'ORG-f_index.02.R', 'f_index.02.R',
        'index_02_r', 'index2_r', 'r_index2',
    ],
    'index_03_r': [
        'mixamorig:righthandindex3',
        'DEF-f_index.03.R', 'ORG-f_index.03.R', 'f_index.03.R',
        'index_03_r', 'index3_r', 'r_index3',
    ],
    # Medio
    'middle_01_r': [
        'mixamorig:righthandmiddle1',
        'DEF-f_middle.01.R', 'ORG-f_middle.01.R', 'f_middle.01.R',
        'middle_01_r', 'middle1_r', 'r_middle1',
    ],
    'middle_02_r': [
        'mixamorig:righthandmiddle2',
        'DEF-f_middle.02.R', 'ORG-f_middle.02.R', 'f_middle.02.R',
        'middle_02_r', 'middle2_r', 'r_middle2',
    ],
    'middle_03_r': [
        'mixamorig:righthandmiddle3',
        'DEF-f_middle.03.R', 'ORG-f_middle.03.R', 'f_middle.03.R',
        'middle_03_r', 'middle3_r', 'r_middle3',
    ],
    # Anular
    'ring_01_r': [
        'mixamorig:righthandring1',
        'DEF-f_ring.01.R', 'ORG-f_ring.01.R', 'f_ring.01.R',
        'ring_01_r', 'ring1_r', 'r_ring1',
    ],
    'ring_02_r': [
        'mixamorig:righthandring2',
        'DEF-f_ring.02.R', 'ORG-f_ring.02.R', 'f_ring.02.R',
        'ring_02_r', 'ring2_r', 'r_ring2',
    ],
    'ring_03_r': [
        'mixamorig:righthandring3',
        'DEF-f_ring.03.R', 'ORG-f_ring.03.R', 'f_ring.03.R',
        'ring_03_r', 'ring3_r', 'r_ring3',
    ],
    # Meñique
    'pinky_01_r': [
        'mixamorig:righthandpinky1',
        'DEF-f_pinky.01.R', 'ORG-f_pinky.01.R', 'f_pinky.01.R',
        'pinky_01_r', 'pinky1_r', 'r_pinky1',
    ],
    'pinky_02_r': [
        'mixamorig:righthandpinky2',
        'DEF-f_pinky.02.R', 'ORG-f_pinky.02.R', 'f_pinky.02.R',
        'pinky_02_r', 'pinky2_r', 'r_pinky2',
    ],
    'pinky_03_r': [
        'mixamorig:righthandpinky3',
        'DEF-f_pinky.03.R', 'ORG-f_pinky.03.R', 'f_pinky.03.R',
        'pinky_03_r', 'pinky3_r', 'r_pinky3',
    ],
}

# Mapeo directo Mixamo → Canónico
MIXAMO_TO_CANONICAL = {
    'mixamorig:hips': 'hips',
    'mixamorig:spine': 'spine',
    'mixamorig:spine1': 'spine1',
    'mixamorig:spine2': 'spine2',
    'mixamorig:neck': 'neck',
    'mixamorig:head': 'head',
    'mixamorig:leftshoulder': 'shoulder_l',
    'mixamorig:leftarm': 'arm_l',
    'mixamorig:leftforearm': 'forearm_l',
    'mixamorig:lefthand': 'hand_l',
    'mixamorig:rightshoulder': 'shoulder_r',
    'mixamorig:rightarm': 'arm_r',
    'mixamorig:rightforearm': 'forearm_r',
    'mixamorig:righthand': 'hand_r',
    'mixamorig:leftupleg': 'leg_l',
    'mixamorig:leftleg': 'shin_l',
    'mixamorig:leftfoot': 'foot_l',
    'mixamorig:lefttoebase': 'toe_l',
    'mixamorig:rightupleg': 'leg_r',
    'mixamorig:rightleg': 'shin_r',
    'mixamorig:rightfoot': 'foot_r',
    'mixamorig:righttoebase': 'toe_r',
    # Dedos izquierda
    'mixamorig:lefthandthumb1': 'thumb_01_l',
    'mixamorig:lefthandthumb2': 'thumb_02_l',
    'mixamorig:lefthandthumb3': 'thumb_03_l',
    'mixamorig:lefthandindex1': 'index_01_l',
    'mixamorig:lefthandindex2': 'index_02_l',
    'mixamorig:lefthandindex3': 'index_03_l',
    'mixamorig:lefthandmiddle1': 'middle_01_l',
    'mixamorig:lefthandmiddle2': 'middle_02_l',
    'mixamorig:lefthandmiddle3': 'middle_03_l',
    'mixamorig:lefthandring1': 'ring_01_l',
    'mixamorig:lefthandring2': 'ring_02_l',
    'mixamorig:lefthandring3': 'ring_03_l',
    'mixamorig:lefthandpinky1': 'pinky_01_l',
    'mixamorig:lefthandpinky2': 'pinky_02_l',
    'mixamorig:lefthandpinky3': 'pinky_03_l',
    # Dedos derecha
    'mixamorig:righthandthumb1': 'thumb_01_r',
    'mixamorig:righthandthumb2': 'thumb_02_r',
    'mixamorig:righthandthumb3': 'thumb_03_r',
    'mixamorig:righthandindex1': 'index_01_r',
    'mixamorig:righthandindex2': 'index_02_r',
    'mixamorig:righthandindex3': 'index_03_r',
    'mixamorig:righthandmiddle1': 'middle_01_r',
    'mixamorig:righthandmiddle2': 'middle_02_r',
    'mixamorig:righthandmiddle3': 'middle_03_r',
    'mixamorig:righthandring1': 'ring_01_r',
    'mixamorig:righthandring2': 'ring_02_r',
    'mixamorig:righthandring3': 'ring_03_r',
    'mixamorig:righthandpinky1': 'pinky_01_r',
    'mixamorig:righthandpinky2': 'pinky_02_r',
    'mixamorig:righthandpinky3': 'pinky_03_r',
}


# =============================================================================
# BONE MAPPER
# =============================================================================

class BoneMapper:
    """
    Sistema de mapeo semántico de huesos.
    Soporta Mixamo, Rigify, y convenciones comunes.
    """
    
    def __init__(self):
        self.vocabulary = BONE_VOCABULARY
        self.mixamo_map = MIXAMO_TO_CANONICAL
        self._mapping_cache = {}
    
    def normalize_bone_name(self, name: str) -> str:
        """Normaliza nombre de hueso para comparación"""
        normalized = name.lower().strip()
        
        # Eliminar prefijos comunes
        prefixes = ['def-', 'org-', 'mch-', 'def_', 'bn_', 'bip01_', 
                    'mixamorig:', 'rig_', 'ctrl_', 'fk_', 'ik_']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        
        # Normalizar separadores
        normalized = normalized.replace('-', '_').replace('.', '_').replace(' ', '_')
        
        return normalized
    
    def find_canonical(self, bone_name: str) -> Optional[str]:
        """Encuentra el nombre canónico para un hueso"""
        bone_lower = bone_name.lower()
        
        # Buscar en mapeo directo de Mixamo
        if bone_lower in self.mixamo_map:
            return self.mixamo_map[bone_lower]
        
        # Buscar en vocabulario
        for canonical, variants in self.vocabulary.items():
            for variant in variants:
                if bone_lower == variant.lower():
                    return canonical
        
        # Búsqueda normalizada
        normalized = self.normalize_bone_name(bone_name)
        for canonical, variants in self.vocabulary.items():
            for variant in variants:
                if normalized == self.normalize_bone_name(variant):
                    return canonical
        
        return None
    
    def find_target_bone(self, canonical: str, target_bones: List[str]) -> Optional[str]:
        """Encuentra el hueso correspondiente en el rig destino"""
        if canonical not in self.vocabulary:
            return None
        
        variants = self.vocabulary[canonical]
        
        # Búsqueda exacta primero
        for target_bone in target_bones:
            target_lower = target_bone.lower()
            for variant in variants:
                if target_lower == variant.lower():
                    return target_bone
        
        # Búsqueda normalizada
        for target_bone in target_bones:
            target_normalized = self.normalize_bone_name(target_bone)
            for variant in variants:
                if target_normalized == self.normalize_bone_name(variant):
                    return target_bone
        
        return None
    
    def create_mapping(self, source_armature, target_armature) -> Dict[str, str]:
        """Crea mapeo completo entre dos armatures"""
        cache_key = f"{source_armature.name}_{target_armature.name}"
        if cache_key in self._mapping_cache:
            return self._mapping_cache[cache_key]
        
        mapping = {}
        target_bones = [b.name for b in target_armature.data.bones]
        
        for source_bone in source_armature.data.bones:
            canonical = self.find_canonical(source_bone.name)
            
            if canonical:
                target_bone = self.find_target_bone(canonical, target_bones)
                if target_bone:
                    mapping[source_bone.name] = target_bone
        
        self._mapping_cache[cache_key] = mapping
        return mapping
    
    def clear_cache(self):
        self._mapping_cache = {}


# =============================================================================
# RETARGETER
# =============================================================================

class Retargeter:
    """Transfiere animaciones entre rigs usando mapeo semántico"""
    
    def __init__(self):
        self.mapper = BoneMapper()
    
    def retarget_action(self, action: bpy.types.Action, 
                        source_armature: bpy.types.Object,
                        target_armature: bpy.types.Object,
                        new_name: str = None) -> bpy.types.Action:
        """Retargetea una acción de un armature a otro"""
        if not action or not source_armature or not target_armature:
            return None
        
        print(f"\n{'='*40}")
        print(f"Retargeting: {action.name}")
        print(f"  From: {source_armature.name}")
        print(f"  To: {target_armature.name}")
        
        mapping = self.mapper.create_mapping(source_armature, target_armature)
        
        if not mapping:
            print("  ✗ No bone mapping found!")
            return None
        
        print(f"  Mapped {len(mapping)} bones")
        
        if new_name is None:
            new_name = f"{action.name}_retargeted"
        
        new_action = bpy.data.actions.new(name=new_name)
        
        for fc in action.fcurves:
            match = re.search(r'pose\.bones\["([^"]+)"\]', fc.data_path)
            if not match:
                continue
            
            source_bone = match.group(1)
            if source_bone not in mapping:
                continue
            
            target_bone = mapping[source_bone]
            new_data_path = fc.data_path.replace(
                f'pose.bones["{source_bone}"]',
                f'pose.bones["{target_bone}"]'
            )
            
            try:
                new_fc = new_action.fcurves.new(
                    data_path=new_data_path,
                    index=fc.array_index
                )
                
                for kp in fc.keyframe_points:
                    new_kp = new_fc.keyframe_points.insert(kp.co[0], kp.co[1])
                    new_kp.interpolation = kp.interpolation
                    
            except Exception as e:
                continue
        
        print(f"  ✓ Created: {new_action.name} ({len(new_action.fcurves)} fcurves)")
        return new_action
    
    def analyze_rig(self, armature: bpy.types.Object) -> Dict:
        """Analiza un rig y devuelve info sobre compatibilidad"""
        if not armature or armature.type != 'ARMATURE':
            return {'error': 'Not an armature'}
        
        bones = [b.name for b in armature.data.bones]
        recognized = []
        unrecognized = []
        
        for bone in bones:
            canonical = self.mapper.find_canonical(bone)
            if canonical:
                recognized.append((bone, canonical))
            else:
                unrecognized.append(bone)
        
        # Detectar tipo de rig
        rig_type = 'custom'
        if any('mixamorig:' in b.lower() for b in bones):
            rig_type = 'mixamo'
        elif any('DEF-' in b for b in bones):
            rig_type = 'rigify'
        
        return {
            'name': armature.name,
            'rig_type': rig_type,
            'total_bones': len(bones),
            'recognized': recognized,
            'unrecognized': unrecognized,
            'recognition_rate': len(recognized) / len(bones) if bones else 0
        }


# =============================================================================
# UTILIDADES
# =============================================================================

_retargeter = None

def get_retargeter() -> Retargeter:
    global _retargeter
    if _retargeter is None:
        _retargeter = Retargeter()
    return _retargeter


def auto_detect_source_rig(action: bpy.types.Action) -> str:
    """Detecta tipo de rig basado en nombres de huesos en la acción"""
    if not action:
        return 'unknown'
    
    bone_names = set()
    for fc in action.fcurves:
        match = re.search(r'pose\.bones\["([^"]+)"\]', fc.data_path)
        if match:
            bone_names.add(match.group(1))
    
    if any('mixamorig:' in b.lower() for b in bone_names):
        return 'mixamo'
    if any('DEF-' in b for b in bone_names):
        return 'rigify'
    
    return 'custom'