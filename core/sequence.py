"""
AI Animator - Sequence Module
Sistema para encadenar múltiples animaciones en secuencia
y detectar modificadores como "in place"
"""

import bpy
import re
from typing import List, Tuple, Optional


# =============================================================================
# LOGGING
# =============================================================================

class SequenceLogger:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def log(self, message: str, level: str = "INFO"):
        if not self.enabled:
            return
        prefix = {
            "INFO": "  ", "SUCCESS": "  ✓", "WARNING": "  ⚠",
            "ERROR": "  ✗", "DEBUG": "    →", "BLEND": "  🔀",
            "SEQUENCE": "  📋", "INPLACE": "  📍"
        }.get(level, "  ")
        print(f"{prefix} {message}")
    
    def header(self, title: str):
        if self.enabled:
            print(f"\n{'='*50}")
            print(f" {title}")
            print(f"{'='*50}")
    
    def section(self, title: str):
        if self.enabled:
            print(f"\n--- {title} ---")


logger = SequenceLogger(enabled=True)


# =============================================================================
# IN PLACE KEYWORDS
# =============================================================================

IN_PLACE_KEYWORDS = [
    'in place', 'inplace', 'in-place', 'stationary', 'static',
    'no movement', 'no move', 'staying', 'stay', 'still',
    'on spot', 'on the spot', 'fixed', 'root motion off',
    'en el lugar', 'en sitio', 'quieto', 'estático', 'sin moverse',
    'sin movimiento', 'fijo', 'en su lugar', 'parado',
]

ROOT_MOTION_KEYWORDS = [
    'moving', 'forward', 'traveling', 'travel', 'root motion',
    'with movement', 'displacement',
    'avanzando', 'con movimiento', 'desplazamiento',
]


# =============================================================================
# IN PLACE PROCESSOR
# =============================================================================

class InPlaceProcessor:
    def __init__(self):
        self.keywords_inplace = IN_PLACE_KEYWORDS
        self.keywords_root = ROOT_MOTION_KEYWORDS
    
    def detect_in_place(self, prompt: str) -> Tuple[bool, str]:
        prompt_lower = prompt.lower()
        
        for keyword in self.keywords_inplace:
            if keyword in prompt_lower:
                cleaned = prompt_lower.replace(keyword, '').strip()
                cleaned = re.sub(r'\s+', ' ', cleaned)
                logger.log(f"Detected 'in place' from: '{keyword}'", "INPLACE")
                return (True, cleaned)
        
        for keyword in self.keywords_root:
            if keyword in prompt_lower:
                return (False, prompt)
        
        return (False, prompt)
    
    def remove_root_motion(self, action: bpy.types.Action, 
                           axes: str = 'Z',
                           root_bones: List[str] = None) -> bpy.types.Action:
        """
        Elimina el movimiento del root/hips en los ejes especificados.
        """
        logger.header("REMOVING ROOT MOTION (In-Place)")
        
        if not action:
            logger.log("No action provided!", "ERROR")
            return None
        
        logger.log(f"Action: {action.name}")
        logger.log(f"Total F-curves: {len(action.fcurves)}")
        
        # Listar TODAS las fcurves de location para debug
        logger.section("All location F-curves found")
        location_curves = []
        for fc in action.fcurves:
            if 'location' in fc.data_path:
                location_curves.append(fc)
                axis_name = ['X', 'Y', 'Z'][fc.array_index] if fc.array_index < 3 else '?'
                logger.log(f"{fc.data_path} [{axis_name}]", "DEBUG")
        
        logger.log(f"Total location curves: {len(location_curves)}")
        
        # Detectar huesos root
        if root_bones is None:
            root_bones = self._detect_root_bones(action)
        
        logger.section("Root bone detection")
        if not root_bones:
            logger.log("No root bones auto-detected, using fallback search...", "WARNING")
            root_bones = self._fallback_root_detection(action)
        
        if not root_bones:
            logger.log("FAILED: Could not find any root bones!", "ERROR")
            return action
        
        logger.log(f"Root bones to process: {root_bones}", "SUCCESS")
        logger.log(f"Axes to zero: {axes}")
        
        # Mapear ejes
        axis_indices = []
        if 'X' in axes.upper():
            axis_indices.append(0)
        if 'Y' in axes.upper():
            axis_indices.append(1)
        if 'Z' in axes.upper():
            axis_indices.append(2)
        
        logger.log(f"Axis indices: {axis_indices} (0=X, 1=Y, 2=Z)")
        
        # Procesar
        logger.section("Processing F-curves")
        curves_modified = 0
        
        for fc in action.fcurves:
            if 'location' not in fc.data_path:
                continue
            
            # Verificar si es root
            is_root = False
            matched_bone = None
            for root_bone in root_bones:
                # Buscar el nombre exacto en el data_path
                if f'"{root_bone}"' in fc.data_path or root_bone.lower() in fc.data_path.lower():
                    is_root = True
                    matched_bone = root_bone
                    break
            
            if not is_root:
                continue
            
            # Verificar eje
            if fc.array_index not in axis_indices:
                continue
            
            axis_name = ['X', 'Y', 'Z'][fc.array_index]
            
            if not fc.keyframe_points:
                logger.log(f"No keyframes in {matched_bone}.location.{axis_name}", "WARNING")
                continue
            
            # Obtener primer valor
            first_value = fc.keyframe_points[0].co[1]
            last_value = fc.keyframe_points[-1].co[1]
            movement_range = last_value - first_value
            
            logger.log(f"Found: {matched_bone} location.{axis_name}", "DEBUG")
            logger.log(f"  First: {first_value:.4f}, Last: {last_value:.4f}", "DEBUG")
            logger.log(f"  Movement: {movement_range:.4f}", "DEBUG")
            logger.log(f"  Keyframes: {len(fc.keyframe_points)}", "DEBUG")
            
            # FIJAR todos los keyframes al primer valor
            for kp in fc.keyframe_points:
                kp.co[1] = first_value
                kp.handle_left[1] = first_value
                kp.handle_right[1] = first_value
            
            curves_modified += 1
            logger.log(f"ZEROED: {matched_bone}.location.{axis_name}", "SUCCESS")
        
        logger.section("Result")
        logger.log(f"F-curves modified: {curves_modified}")
        
        if curves_modified == 0:
            logger.log("WARNING: No curves were modified!", "ERROR")
            logger.log("This means no root bone location curves matched.", "ERROR")
            logger.log("Check bone names in your rig vs detected roots.", "ERROR")
        else:
            logger.log(f"Successfully applied in-place to {curves_modified} curves", "SUCCESS")
        
        return action
    
    def _detect_root_bones(self, action: bpy.types.Action) -> List[str]:
        """Auto-detecta huesos root"""
        root_keywords = [
            'hips', 'pelvis', 'root', 'torso', 'cog', 'hip',
            'mixamorig:hips', 'DEF-spine', 'spine'
        ]
        
        found = []
        for fc in action.fcurves:
            match = re.search(r'pose\.bones\["([^"]+)"\]', fc.data_path)
            if match:
                bone_name = match.group(1)
                bone_lower = bone_name.lower()
                
                for keyword in root_keywords:
                    if keyword.lower() in bone_lower:
                        if bone_name not in found:
                            found.append(bone_name)
                            logger.log(f"Found root candidate: {bone_name}", "DEBUG")
                        break
        
        return found
    
    def _fallback_root_detection(self, action: bpy.types.Action) -> List[str]:
        """Fallback: encuentra el hueso con más movimiento en location"""
        bone_movement = {}
        
        for fc in action.fcurves:
            if 'location' not in fc.data_path:
                continue
            
            match = re.search(r'pose\.bones\["([^"]+)"\]', fc.data_path)
            if not match:
                continue
            
            bone_name = match.group(1)
            
            if fc.keyframe_points:
                values = [kp.co[1] for kp in fc.keyframe_points]
                movement = abs(max(values) - min(values))
                
                if bone_name not in bone_movement:
                    bone_movement[bone_name] = 0
                bone_movement[bone_name] += movement
        
        if bone_movement:
            sorted_bones = sorted(bone_movement.items(), key=lambda x: x[1], reverse=True)
            logger.log(f"Bones by total movement:", "DEBUG")
            for bone, mov in sorted_bones[:5]:
                logger.log(f"  {bone}: {mov:.4f}", "DEBUG")
            
            if sorted_bones:
                return [sorted_bones[0][0]]
        
        return []


# =============================================================================
# SEQUENCE DETECTOR
# =============================================================================

SEQUENCE_SEPARATORS = [
    ', then ', ' then ', ', después ', ' después ',
    ', luego ', ' luego ', ' -> ', ' → ', ', and then ',
    ' seguido de ', ', followed by ', ' y luego ', ' y después ',
]

SEQUENCE_INDICATORS = [
    'first', 'then', 'after', 'next', 'finally',
    'primero', 'después', 'luego', 'siguiente', 'finalmente',
    'start with', 'end with', 'comenzar con', 'terminar con',
]


class SequenceDetector:
    def __init__(self):
        self.separators = SEQUENCE_SEPARATORS
        self.indicators = SEQUENCE_INDICATORS
    
    def is_sequence(self, prompt: str) -> bool:
        prompt_lower = prompt.lower()
        
        for sep in self.separators:
            if sep in prompt_lower:
                return True
        
        indicator_count = sum(1 for ind in self.indicators if ind in prompt_lower)
        return indicator_count >= 2
    
    def parse_sequence(self, prompt: str) -> List[str]:
        prompt_lower = prompt.lower()
        
        normalized = prompt_lower
        for sep in self.separators:
            normalized = normalized.replace(sep, '|||')
        
        if any(ind in prompt_lower for ind in self.indicators):
            normalized = normalized.replace(',', '|||')
        
        parts = normalized.split('|||')
        
        cleaned_parts = []
        for part in parts:
            clean = part.strip()
            for ind in self.indicators:
                clean = clean.replace(ind, '').strip()
            clean = re.sub(r'\s+', ' ', clean).strip()
            
            if clean and len(clean) > 1:
                cleaned_parts.append(clean)
        
        return cleaned_parts


# =============================================================================
# SEQUENCE BUILDER
# =============================================================================

class SequenceBuilder:
    """
    Construye secuencias de animaciones con:
    - Crossfade suave entre animaciones
    - Continuidad de posición del root (motion matching)
    - Propagación de velocidad entre clips
    """
    
    # Palabras clave para identificar huesos root
    ROOT_BONE_KEYWORDS = ['hips', 'pelvis', 'root', 'cog', 'mixamorig:hips']
    
    def __init__(self):
        self.detector = SequenceDetector()
        self.in_place_processor = InPlaceProcessor()
    
    @staticmethod
    def smoothstep(t: float) -> float:
        """Interpolación suave ease-in-out"""
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)
    
    @staticmethod
    def ease_out(t: float) -> float:
        """Interpolación ease-out (desacelera al final)"""
        t = max(0.0, min(1.0, t))
        return 1.0 - (1.0 - t) ** 2
    
    @staticmethod
    def ease_in(t: float) -> float:
        """Interpolación ease-in (acelera al inicio)"""
        t = max(0.0, min(1.0, t))
        return t * t
    
    @staticmethod
    def linear(t: float) -> float:
        """Interpolación lineal"""
        return max(0.0, min(1.0, t))
    
    def get_interpolation_func(self, curve_type: str):
        """Retorna la función de interpolación según el tipo"""
        curves = {
            'EASE_IN_OUT': self.smoothstep,
            'EASE_OUT': self.ease_out,
            'EASE_IN': self.ease_in,
            'LINEAR': self.linear,
        }
        return curves.get(curve_type, self.smoothstep)
    
    def build_sequence_with_transitions(self, actions: List[bpy.types.Action],
                                        transition_configs: List[dict],
                                        name: str = "Sequence") -> bpy.types.Action:
        """
        Construye secuencia con transiciones personalizadas por conexión.
        
        transition_configs: lista de dicts con:
            - 'frames': int
            - 'curve': 'EASE_IN_OUT', 'EASE_OUT', 'LINEAR', etc.
            - 'style': 'SMOOTH', 'NORMAL', 'SHARP', 'SNAP'
        """
        if not actions:
            return None
        
        if len(actions) == 1:
            return actions[0].copy()
        
        logger.header(f"Building Sequence with Custom Transitions ({len(actions)} actions)")
        
        # Asegurar que hay suficientes configs
        while len(transition_configs) < len(actions) - 1:
            transition_configs.append({'frames': 15, 'curve': 'EASE_OUT', 'style': 'NORMAL'})
        
        for i, tc in enumerate(transition_configs[:len(actions)-1]):
            logger.log(f"Transition {i+1}→{i+2}: {tc['style']} ({tc['frames']}f, {tc['curve']})", "INFO")
        
        sequence_action = bpy.data.actions.new(name=f"{name}_sequence")
        
        # Analizar acciones y calcular offsets
        action_data = []
        cumulative_offset = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        current_frame = 0
        
        for i, action in enumerate(actions):
            start = action.frame_range[0]
            end = action.frame_range[1]
            duration = end - start
            
            root_motion = self._analyze_root_motion(action)
            
            data = {
                'action': action,
                'index': i,
                'original_start': start,
                'original_end': end,
                'new_start': current_frame,
                'new_end': current_frame + duration,
                'root_motion': root_motion,
                'position_offset': {
                    'x': cumulative_offset['x'],
                    'y': cumulative_offset['y'],
                    'z': cumulative_offset['z']
                }
            }
            action_data.append(data)
            
            cumulative_offset['x'] += root_motion['delta_x']
            cumulative_offset['y'] += root_motion['delta_y']
            cumulative_offset['z'] += root_motion['delta_z']
            
            # Siguiente acción empieza con overlap según su transición
            if i < len(actions) - 1:
                trans_frames = transition_configs[i]['frames']
                current_frame += duration - trans_frames
            else:
                current_frame += duration
        
        # Identificar zonas de transición con sus curvas
        transitions = []
        for i in range(len(action_data) - 1):
            ar_current = action_data[i]
            ar_next = action_data[i + 1]
            
            trans_config = transition_configs[i]
            
            transition_start = ar_next['new_start']
            transition_end = ar_current['new_end']
            
            if transition_end > transition_start:
                transitions.append({
                    'from_action': ar_current,
                    'to_action': ar_next,
                    'start_frame': transition_start,
                    'end_frame': transition_end,
                    'curve_func': self.get_interpolation_func(trans_config['curve']),
                    'config': trans_config
                })
        
        # Recopilar paths
        all_paths = set()
        for action in actions:
            for fc in action.fcurves:
                all_paths.add((fc.data_path, fc.array_index))
        
        # Crear F-curves
        for data_path, array_index in all_paths:
            new_fc = sequence_action.fcurves.new(data_path=data_path, index=array_index)
            is_root_location = self._is_root_location_curve(data_path)
            total_end = int(action_data[-1]['new_end'])
            
            for frame in range(0, total_end + 1):
                value = self._get_blended_value_with_curve(
                    frame, data_path, array_index,
                    action_data, transitions,
                    is_root_location
                )
                
                if value is not None:
                    new_fc.keyframe_points.insert(frame, value)
            
            self._optimize_fcurve(new_fc)
        
        total_duration = action_data[-1]['new_end'] if action_data else 0
        logger.log(f"Total duration: {total_duration:.0f} frames", "SUCCESS")
        
        return sequence_action
    
    def _get_blended_value_with_curve(self, frame: int, data_path: str, array_index: int,
                                       action_data: list, transitions: list,
                                       is_root_location: bool) -> float:
        """Obtiene valor con curva de interpolación personalizada"""
        
        # Verificar si estamos en una transición
        for trans in transitions:
            if trans['start_frame'] <= frame <= trans['end_frame']:
                # Calcular t con la curva personalizada
                t_linear = (frame - trans['start_frame']) / max(1, trans['end_frame'] - trans['start_frame'])
                t = trans['curve_func'](t_linear)
                
                from_data = trans['from_action']
                to_data = trans['to_action']
                
                # Valores de cada acción
                from_frame = from_data['original_start'] + (frame - from_data['new_start'])
                to_frame = to_data['original_start'] + (frame - to_data['new_start'])
                
                from_fc = self._find_fcurve(from_data['action'], data_path, array_index)
                to_fc = self._find_fcurve(to_data['action'], data_path, array_index)
                
                from_val = from_fc.evaluate(from_frame) if from_fc else 0.0
                to_val = to_fc.evaluate(to_frame) if to_fc else 0.0
                
                # Ajustar root location
                if is_root_location:
                    axis_idx = array_index
                    axis_map = {0: 'x', 1: 'y', 2: 'z'}
                    if axis_idx in axis_map:
                        axis = axis_map[axis_idx]
                        from_val += from_data['position_offset'].get(axis, 0.0)
                        to_val += to_data['position_offset'].get(axis, 0.0)
                
                return from_val * (1.0 - t) + to_val * t
        
        # No en transición - buscar acción activa
        for data in action_data:
            if data['new_start'] <= frame <= data['new_end']:
                original_frame = data['original_start'] + (frame - data['new_start'])
                fc = self._find_fcurve(data['action'], data_path, array_index)
                
                if fc:
                    value = fc.evaluate(original_frame)
                    if is_root_location:
                        axis_idx = array_index
                        axis_map = {0: 'x', 1: 'y', 2: 'z'}
                        if axis_idx in axis_map:
                            value += data['position_offset'].get(axis_map[axis_idx], 0.0)
                    return value
        
        return None
    
    def build_sequence(self, actions: List[bpy.types.Action], 
                       transition_frames: int = 10,
                       name: str = "Sequence") -> bpy.types.Action:
        if not actions:
            return None
        
        if len(actions) == 1:
            return actions[0].copy()
        
        logger.header(f"Building Sequence ({len(actions)} actions)")
        logger.log(f"Transition frames: {transition_frames}", "INFO")
        
        sequence_action = bpy.data.actions.new(name=f"{name}_sequence")
        
        # =====================================================================
        # PASO 1: Analizar cada acción y calcular offsets de posición
        # =====================================================================
        action_data = []
        cumulative_offset = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        current_frame = 0
        
        for i, action in enumerate(actions):
            start = action.frame_range[0]
            end = action.frame_range[1]
            duration = end - start
            
            # Analizar movimiento del root en esta acción
            root_motion = self._analyze_root_motion(action)
            
            data = {
                'action': action,
                'index': i,
                'original_start': start,
                'original_end': end,
                'new_start': current_frame,
                'new_end': current_frame + duration,
                'root_motion': root_motion,
                # Offset acumulado ANTES de esta animación
                'position_offset': {
                    'x': cumulative_offset['x'],
                    'y': cumulative_offset['y'],
                    'z': cumulative_offset['z']
                }
            }
            action_data.append(data)
            
            logger.log(f"{i+1}. {action.name}", "SEQUENCE")
            logger.log(f"    Frames: {current_frame:.0f}-{current_frame + duration:.0f}", "DEBUG")
            logger.log(f"    Root motion: X={root_motion['delta_x']:.3f}, Y={root_motion['delta_y']:.3f}, Z={root_motion['delta_z']:.3f}", "DEBUG")
            logger.log(f"    Position offset: X={data['position_offset']['x']:.3f}, Y={data['position_offset']['y']:.3f}", "DEBUG")
            
            # Acumular el movimiento de esta animación para la siguiente
            cumulative_offset['x'] += root_motion['delta_x']
            cumulative_offset['y'] += root_motion['delta_y']
            cumulative_offset['z'] += root_motion['delta_z']
            
            # Siguiente acción empieza con overlap
            if i < len(actions) - 1:
                current_frame += duration - transition_frames
            else:
                current_frame += duration
        
        # =====================================================================
        # PASO 2: Identificar zonas de transición
        # =====================================================================
        transitions = []
        for i in range(len(action_data) - 1):
            ar_current = action_data[i]
            ar_next = action_data[i + 1]
            
            transition_start = ar_next['new_start']
            transition_end = ar_current['new_end']
            
            if transition_end > transition_start:
                transitions.append({
                    'from_action': ar_current,
                    'to_action': ar_next,
                    'start_frame': transition_start,
                    'end_frame': transition_end,
                })
                logger.log(f"Transition {i+1}→{i+2}: frames {transition_start:.0f}-{transition_end:.0f}", "BLEND")
        
        # =====================================================================
        # PASO 3: Recopilar todos los data_paths
        # =====================================================================
        all_paths = set()
        for action in actions:
            for fc in action.fcurves:
                all_paths.add((fc.data_path, fc.array_index))
        
        logger.log(f"Total F-curve paths: {len(all_paths)}", "INFO")
        
        # =====================================================================
        # PASO 4: Crear F-curves con crossfade y continuidad de posición
        # =====================================================================
        for data_path, array_index in all_paths:
            new_fc = sequence_action.fcurves.new(data_path=data_path, index=array_index)
            
            # Detectar si es una curva de location del root
            is_root_location = self._is_root_location_curve(data_path)
            
            total_end = int(action_data[-1]['new_end'])
            
            for frame in range(0, total_end + 1):
                value = self._get_blended_value_at_frame(
                    frame, data_path, array_index, 
                    action_data, transitions, transition_frames,
                    is_root_location
                )
                
                if value is not None:
                    new_fc.keyframe_points.insert(frame, value)
            
            self._optimize_fcurve(new_fc)
        
        total_duration = action_data[-1]['new_end'] if action_data else 0
        logger.log(f"Total duration: {total_duration:.0f} frames", "SUCCESS")
        logger.log(f"Transitions blended: {len(transitions)}", "SUCCESS")
        
        return sequence_action
    
    def _analyze_root_motion(self, action: bpy.types.Action) -> dict:
        """
        Analiza el movimiento del root bone en una acción.
        Retorna el delta de posición entre inicio y fin.
        """
        result = {
            'delta_x': 0.0, 'delta_y': 0.0, 'delta_z': 0.0,
            'start_x': 0.0, 'start_y': 0.0, 'start_z': 0.0,
            'end_x': 0.0, 'end_y': 0.0, 'end_z': 0.0,
            'root_bone': None
        }
        
        for fc in action.fcurves:
            if 'location' not in fc.data_path:
                continue
            
            # Verificar si es root bone
            is_root = False
            for keyword in self.ROOT_BONE_KEYWORDS:
                if keyword.lower() in fc.data_path.lower():
                    is_root = True
                    # Extraer nombre del hueso
                    import re
                    match = re.search(r'pose\.bones\["([^"]+)"\]', fc.data_path)
                    if match:
                        result['root_bone'] = match.group(1)
                    break
            
            if not is_root:
                continue
            
            if not fc.keyframe_points:
                continue
            
            start_val = fc.keyframe_points[0].co[1]
            end_val = fc.keyframe_points[-1].co[1]
            
            axis = ['x', 'y', 'z'][fc.array_index] if fc.array_index < 3 else None
            if axis:
                result[f'start_{axis}'] = start_val
                result[f'end_{axis}'] = end_val
                result[f'delta_{axis}'] = end_val - start_val
        
        return result
    
    def _is_root_location_curve(self, data_path: str) -> bool:
        """Verifica si un data_path corresponde a location de un root bone"""
        if 'location' not in data_path:
            return False
        
        for keyword in self.ROOT_BONE_KEYWORDS:
            if keyword.lower() in data_path.lower():
                return True
        return False
    
    def _get_blended_value_at_frame(self, frame: int, data_path: str, array_index: int,
                                     action_data: List[dict], transitions: List[dict],
                                     transition_frames: int, is_root_location: bool) -> Optional[float]:
        """
        Obtiene el valor interpolado para un frame específico.
        Para root location, aplica offset de posición acumulado.
        """
        # Verificar si estamos en una zona de transición
        for trans in transitions:
            if trans['start_frame'] <= frame <= trans['end_frame']:
                return self._crossfade_at_frame(
                    frame, data_path, array_index, trans, 
                    transition_frames, is_root_location
                )
        
        # No estamos en transición - buscar qué acción aplica
        for ar in action_data:
            if ar['new_start'] <= frame <= ar['new_end']:
                source_fc = self._find_fcurve(ar['action'], data_path, array_index)
                if source_fc:
                    original_frame = frame - ar['new_start'] + ar['original_start']
                    value = source_fc.evaluate(original_frame)
                    
                    # Aplicar offset de posición para root location
                    if is_root_location:
                        axis = ['x', 'y', 'z'][array_index] if array_index < 3 else None
                        if axis:
                            offset = ar['position_offset'].get(axis, 0.0)
                            value += offset
                    
                    return value
        
        return None
    
    def _crossfade_at_frame(self, frame: int, data_path: str, array_index: int,
                            transition: dict, transition_frames: int,
                            is_root_location: bool) -> Optional[float]:
        """
        Calcula el valor de crossfade entre dos animaciones.
        Para root location, mantiene continuidad de posición.
        """
        ar_from = transition['from_action']
        ar_to = transition['to_action']
        
        # Factor de blend (0 = 100% from, 1 = 100% to)
        t = (frame - transition['start_frame']) / max(1, transition['end_frame'] - transition['start_frame'])
        t = self.smoothstep(t)
        
        fc_from = self._find_fcurve(ar_from['action'], data_path, array_index)
        fc_to = self._find_fcurve(ar_to['action'], data_path, array_index)
        
        value_from = None
        value_to = None
        
        if fc_from:
            original_frame_from = frame - ar_from['new_start'] + ar_from['original_start']
            value_from = fc_from.evaluate(original_frame_from)
            
            # Aplicar offset para animación "from"
            if is_root_location:
                axis = ['x', 'y', 'z'][array_index] if array_index < 3 else None
                if axis:
                    value_from += ar_from['position_offset'].get(axis, 0.0)
        
        if fc_to:
            original_frame_to = frame - ar_to['new_start'] + ar_to['original_start']
            value_to = fc_to.evaluate(original_frame_to)
            
            # Aplicar offset para animación "to"
            if is_root_location:
                axis = ['x', 'y', 'z'][array_index] if array_index < 3 else None
                if axis:
                    value_to += ar_to['position_offset'].get(axis, 0.0)
        
        # Interpolar
        if value_from is not None and value_to is not None:
            return value_from * (1.0 - t) + value_to * t
        elif value_from is not None:
            return value_from
        elif value_to is not None:
            return value_to
        
        return None
    
    def _find_fcurve(self, action: bpy.types.Action, data_path: str, 
                     array_index: int) -> Optional[bpy.types.FCurve]:
        """Encuentra una F-curve específica en una acción"""
        for fc in action.fcurves:
            if fc.data_path == data_path and fc.array_index == array_index:
                return fc
        return None
    
    def _optimize_fcurve(self, fcurve: bpy.types.FCurve, threshold: float = 0.0001):
        """Ajusta interpolación a BEZIER para suavidad"""
        if len(fcurve.keyframe_points) < 3:
            return
        
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'BEZIER'


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================

_sequence_detector = None
_sequence_builder = None
_in_place_processor = None


def get_sequence_detector() -> SequenceDetector:
    global _sequence_detector
    if _sequence_detector is None:
        _sequence_detector = SequenceDetector()
    return _sequence_detector


def get_sequence_builder() -> SequenceBuilder:
    global _sequence_builder
    if _sequence_builder is None:
        _sequence_builder = SequenceBuilder()
    return _sequence_builder


def get_in_place_processor() -> InPlaceProcessor:
    global _in_place_processor
    if _in_place_processor is None:
        _in_place_processor = InPlaceProcessor()
    return _in_place_processor


def process_prompt_for_sequence(prompt: str) -> Tuple[bool, List[str], bool, str]:
    """
    Procesa un prompt detectando secuencias e in-place.
    
    Returns:
        (is_sequence, sequence_parts, is_in_place, cleaned_prompt)
    """
    detector = get_sequence_detector()
    in_place = get_in_place_processor()
    
    # Detectar in-place primero
    is_in_place, cleaned = in_place.detect_in_place(prompt)
    
    # Detectar secuencia
    is_seq = detector.is_sequence(cleaned)
    
    if is_seq:
        parts = detector.parse_sequence(cleaned)
        return (True, parts, is_in_place, cleaned)
    else:
        return (False, [cleaned], is_in_place, cleaned)