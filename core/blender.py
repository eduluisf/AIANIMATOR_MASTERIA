"""
AI Animator - Motion Blender
Combina F-curves de múltiples acciones para crear animaciones híbridas
"""

import bpy


# =============================================================================
# LOGGING
# =============================================================================

class BlendLogger:
    """Logger para operaciones de blending"""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def log(self, message: str, level: str = "INFO"):
        if not self.enabled:
            return
        prefix = {
            "INFO": "  ", "SUCCESS": "  ✓", "WARNING": "  ⚠",
            "ERROR": "  ✗", "DEBUG": "    →", "BLEND": "  🔀",
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


logger = BlendLogger(enabled=True)


# =============================================================================
# MOTION BLENDER
# =============================================================================

class MotionBlender:
    """
    Sistema para combinar múltiples animaciones en una nueva.
    Trabaja a nivel de F-curves de Blender, interpolando valores
    entre diferentes acciones con pesos configurables.
    """
    
    @staticmethod
    def blend_actions(action1, action2, weight1: float = 0.5, 
                      weight2: float = 0.5, name: str = "Blended") -> bpy.types.Action:
        """
        Combina dos acciones con pesos específicos.
        """
        if not action1 and not action2:
            return None
        
        if not action1:
            return action2.copy()
        if not action2:
            return action1.copy()
        
        # LOG: Inicio de blending
        logger.header("Motion Blending")
        logger.log(f"Action 1: {action1.name}", "BLEND")
        logger.log(f"  Weight: {weight1:.0%}")
        logger.log(f"  Frames: {action1.frame_range[0]:.0f} - {action1.frame_range[1]:.0f}")
        logger.log(f"  F-curves: {len(action1.fcurves)}")
        logger.log(f"Action 2: {action2.name}", "BLEND")
        logger.log(f"  Weight: {weight2:.0%}")
        logger.log(f"  Frames: {action2.frame_range[0]:.0f} - {action2.frame_range[1]:.0f}")
        logger.log(f"  F-curves: {len(action2.fcurves)}")
        
        # Crear nueva acción
        blended = bpy.data.actions.new(name=f"{name}_blended")
        
        # Obtener frame range combinado
        frame_start = min(action1.frame_range[0], action2.frame_range[0])
        frame_end = max(action1.frame_range[1], action2.frame_range[1])
        
        logger.section("Blending Process")
        logger.log(f"Output frame range: {frame_start:.0f} - {frame_end:.0f}")
        
        # Recopilar F-curves de ambas acciones
        fcurve_data = {}
        
        for action, weight in [(action1, weight1), (action2, weight2)]:
            if not action:
                continue
            for fc in action.fcurves:
                key = (fc.data_path, fc.array_index)
                
                if key not in fcurve_data:
                    fcurve_data[key] = []
                fcurve_data[key].append((fc, weight))
        
        # Contar curves compartidas vs únicas
        shared_curves = sum(1 for v in fcurve_data.values() if len(v) > 1)
        unique_curves = sum(1 for v in fcurve_data.values() if len(v) == 1)
        logger.log(f"Shared F-curves (blended): {shared_curves}")
        logger.log(f"Unique F-curves (copied): {unique_curves}")
        
        # Crear F-curves combinadas
        for (data_path, array_index), curves_weights in fcurve_data.items():
            new_fc = blended.fcurves.new(data_path=data_path, index=array_index)
            
            # Samplear cada frame y combinar valores
            for frame in range(int(frame_start), int(frame_end) + 1):
                combined_value = 0.0
                total_weight = 0.0
                
                for fc, weight in curves_weights:
                    value = fc.evaluate(frame)
                    combined_value += value * weight
                    total_weight += weight
                
                if total_weight > 0:
                    combined_value /= total_weight
                
                new_fc.keyframe_points.insert(frame, combined_value)
            
            # Suavizar interpolación
            for kp in new_fc.keyframe_points:
                kp.interpolation = 'BEZIER'
        
        # LOG: Resultado
        logger.section("Blend Result")
        logger.log(f"Output action: {blended.name}", "SUCCESS")
        logger.log(f"Total F-curves: {len(blended.fcurves)}")
        logger.log(f"Total keyframes: {sum(len(fc.keyframe_points) for fc in blended.fcurves)}")
        
        return blended
    
    @staticmethod
    def apply_speed_modifier(action, speed_factor: float):
        """
        Modifica la velocidad de una acción escalando temporalmente sus keyframes.
        """
        if not action or speed_factor == 1.0:
            return
        
        logger.section("Speed Modifier")
        logger.log(f"Factor: {speed_factor:.2f}x")
        logger.log(f"Original duration: {action.frame_range[1] - action.frame_range[0]:.0f} frames")
        
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.co[0] = kp.co[0] / speed_factor
                kp.handle_left[0] = kp.handle_left[0] / speed_factor
                kp.handle_right[0] = kp.handle_right[0] / speed_factor
        
        old_start, old_end = action.frame_range
        new_duration = (old_end - old_start) / speed_factor
        
        logger.log(f"New duration: {new_duration:.0f} frames", "SUCCESS")
    
    @staticmethod
    def apply_intensity_modifier(action, intensity_factor: float, 
                                  bone_filter: list = None,
                                  affect_location: bool = True,
                                  affect_rotation: bool = True):
        """
        Modifica la intensidad/amplitud de los movimientos.
        """
        if not action or intensity_factor == 1.0:
            return
        
        logger.section("Intensity Modifier")
        logger.log(f"Factor: {intensity_factor:.2f}x")
        if bone_filter:
            logger.log(f"Bone filter: {bone_filter}")
        
        curves_modified = 0
        
        for fc in action.fcurves:
            is_location = 'location' in fc.data_path
            is_rotation = 'rotation' in fc.data_path
            
            if is_location and not affect_location:
                continue
            if is_rotation and not affect_rotation:
                continue
            if not is_location and not is_rotation:
                continue
            
            if bone_filter:
                bone_match = False
                for bone_name in bone_filter:
                    if bone_name in fc.data_path:
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
                kp.co[1] = base_value + (deviation * intensity_factor)
                
                handle_left_dev = kp.handle_left[1] - base_value
                handle_right_dev = kp.handle_right[1] - base_value
                kp.handle_left[1] = base_value + (handle_left_dev * intensity_factor)
                kp.handle_right[1] = base_value + (handle_right_dev * intensity_factor)
            
            curves_modified += 1
        
        logger.log(f"F-curves modified: {curves_modified}", "SUCCESS")
    
    @staticmethod
    def apply_intensity_modifier_selective(action, intensity_factor: float,
                                           bone_filter: list = None):
        """
        Aplica intensidad solo a huesos específicos con matching case-insensitive.
        Diseñado para trabajar con grupos de huesos del módulo transform.

        Args:
            action: bpy.types.Action
            intensity_factor: Factor de escala de amplitud
            bone_filter: Lista de nombres de huesos (case-insensitive), o None para todos
        """
        if not action or intensity_factor == 1.0:
            return

        logger.section("Selective Intensity Modifier")
        logger.log(f"Factor: {intensity_factor:.2f}x")

        if bone_filter:
            bone_filter_lower = [b.lower() for b in bone_filter]
            logger.log(f"Targeting {len(bone_filter)} specific bones")
        else:
            bone_filter_lower = None
            logger.log("Targeting ALL bones")

        curves_modified = 0

        for fc in action.fcurves:
            is_location = 'location' in fc.data_path
            is_rotation = 'rotation' in fc.data_path

            if not (is_location or is_rotation):
                continue

            # Filtro de huesos case-insensitive
            if bone_filter_lower is not None:
                data_path_lower = fc.data_path.lower()
                bone_match = any(bone in data_path_lower for bone in bone_filter_lower)
                if not bone_match:
                    continue

            values = [kp.co[1] for kp in fc.keyframe_points]
            if not values:
                continue

            base_value = sum(values) / len(values)

            for kp in fc.keyframe_points:
                deviation = kp.co[1] - base_value
                kp.co[1] = base_value + (deviation * intensity_factor)

                handle_left_dev = kp.handle_left[1] - base_value
                handle_right_dev = kp.handle_right[1] - base_value
                kp.handle_left[1] = base_value + (handle_left_dev * intensity_factor)
                kp.handle_right[1] = base_value + (handle_right_dev * intensity_factor)

            curves_modified += 1

        bone_info = f"{len(bone_filter)} bones" if bone_filter else "ALL bones"
        logger.log(f"F-curves modified: {curves_modified} ({bone_info})", "SUCCESS")

    @staticmethod
    def blend_multiple(actions_weights: list, name: str = "MultiBlend") -> bpy.types.Action:
        """
        Combina múltiples acciones con sus respectivos pesos.
        """
        if not actions_weights:
            return None
        
        if len(actions_weights) == 1:
            return actions_weights[0][0].copy()
        
        logger.header(f"Multi-Action Blend ({len(actions_weights)} actions)")
        for i, (action, weight) in enumerate(actions_weights):
            logger.log(f"{i+1}. {action.name} (weight: {weight:.0%})", "BLEND")
        
        # Combinar de forma iterativa
        result = actions_weights[0][0]
        result_weight = actions_weights[0][1]
        
        for action, weight in actions_weights[1:]:
            total = result_weight + weight
            w1 = result_weight / total
            w2 = weight / total
            
            logger.log(f"Blending step: {w1:.0%} + {w2:.0%}", "DEBUG")
            result = MotionBlender.blend_actions(result, action, w1, w2, name)
            result_weight = total
        
        return result


def set_blend_logger_enabled(enabled: bool):
    """Activa/desactiva logging de blending"""
    logger.enabled = enabled