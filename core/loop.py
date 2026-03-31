"""
AI Animator - Auto Loop
Sistema profesional para hacer animaciones cíclicas automáticamente

Técnica: Cross-fade simétrico
- Los primeros N frames y últimos N frames se mezclan gradualmente
- Frame 0 = 100% inicio, 0% final
- Frame N/2 = 50% inicio, 50% final  
- Frame N = 0% inicio, 100% final (que es similar al inicio)
- Esto crea un loop perfecto sin saltos
"""

import bpy
from typing import List, Tuple, Optional, Dict
from ..config import LOOP_SEARCH_WINDOW, DEFAULT_LOOP_BLEND_FRAMES


class AutoLoop:
    """
    Sistema para convertir animaciones en loops suaves.
    
    Usa cross-fade simétrico: mezcla gradual entre el inicio y final
    de la animación para crear transiciones perfectas.
    """
    
    # Huesos que típicamente tienen root motion y deben tratarse especial
    ROOT_BONE_KEYWORDS = ['hips', 'pelvis', 'root', 'cog', 'mixamorig:hips']
    
    @staticmethod
    def smoothstep(t: float) -> float:
        """Función de interpolación suave (ease-in-out)"""
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)
    
    @staticmethod
    def calculate_pose_similarity(action, frame1: int, frame2: int, 
                                   exclude_root_location: bool = True) -> float:
        """
        Calcula qué tan similares son dos poses en diferentes frames.
        
        Args:
            action: Acción a analizar
            frame1: Primer frame
            frame2: Segundo frame
            exclude_root_location: Si excluir location del root (para ignorar desplazamiento)
            
        Returns:
            Valor entre 0 (muy diferentes) y 1 (idénticas)
        """
        if not action or not action.fcurves:
            return 0.0
        
        total_diff = 0.0
        num_channels = 0
        
        for fc in action.fcurves:
            # Opcionalmente excluir root location
            if exclude_root_location:
                if 'location' in fc.data_path:
                    is_root = any(kw.lower() in fc.data_path.lower() 
                                  for kw in AutoLoop.ROOT_BONE_KEYWORDS)
                    if is_root:
                        continue
            
            val1 = fc.evaluate(frame1)
            val2 = fc.evaluate(frame2)
            
            diff = abs(val1 - val2)
            total_diff += diff
            num_channels += 1
        
        if num_channels == 0:
            return 0.0
        
        avg_diff = total_diff / num_channels
        similarity = max(0.0, 1.0 - (avg_diff / 2.0))
        return similarity
    
    @staticmethod
    def calculate_velocity_similarity(action, frame1: int, frame2: int, delta: int = 2) -> float:
        """
        Calcula qué tan similar es la velocidad/momentum en dos frames.
        Importante para que el loop no tenga cambios bruscos de velocidad.
        """
        if not action or not action.fcurves:
            return 0.0
        
        total_diff = 0.0
        num_channels = 0
        
        for fc in action.fcurves:
            # Velocidad = diferencia entre frames consecutivos
            vel1 = fc.evaluate(frame1) - fc.evaluate(frame1 - delta)
            vel2 = fc.evaluate(frame2) - fc.evaluate(frame2 - delta)
            
            diff = abs(vel1 - vel2)
            total_diff += diff
            num_channels += 1
        
        if num_channels == 0:
            return 0.0
        
        avg_diff = total_diff / num_channels
        similarity = max(0.0, 1.0 - (avg_diff / 1.0))
        return similarity
    
    @staticmethod
    def find_best_loop_point(action, search_window: int = None, 
                             consider_velocity: bool = True) -> Tuple[int, float]:
        """
        Encuentra el mejor frame para cerrar el loop.
        Considera tanto similitud de pose como de velocidad.
        
        Returns:
            Tupla (best_frame, combined_score)
        """
        if not action:
            return None, 0.0
        
        if search_window is None:
            search_window = LOOP_SEARCH_WINDOW
        
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        
        if frame_end - frame_start < 20:
            return frame_end, 0.5
        
        best_frame = frame_end
        best_score = 0.0
        
        search_start = max(frame_start + 10, frame_end - search_window)
        
        print(f"  Searching for best loop point in frames {search_start}-{frame_end}...")
        
        for test_frame in range(search_start, frame_end + 1):
            pose_sim = AutoLoop.calculate_pose_similarity(
                action, frame_start, test_frame, exclude_root_location=True
            )
            
            if consider_velocity:
                vel_sim = AutoLoop.calculate_velocity_similarity(
                    action, frame_start, test_frame
                )
                # Combinar: pose es más importante que velocidad
                score = pose_sim * 0.7 + vel_sim * 0.3
            else:
                score = pose_sim
            
            if score > best_score:
                best_score = score
                best_frame = test_frame
        
        return best_frame, best_score
    
    @staticmethod
    def make_loopable(action, blend_frames: int = None,
                      auto_find_loop_point: bool = True,
                      preserve_root_motion: bool = False) -> int:
        """
        Hace una acción loopable usando cross-fade sobre toda la animación.

        Técnica:
        - Usa toda la duración de la animación como zona de blend
        - Cada frame se interpola gradualmente entre su valor original
          y el valor correspondiente desde el extremo opuesto
        - Resultado: loop suave sin saltos usando la animación completa

        Args:
            action: Acción a modificar (se modifica in-place)
            blend_frames: No usado, se mantiene por compatibilidad
            auto_find_loop_point: Si buscar automáticamente el mejor punto
            preserve_root_motion: Si preservar el desplazamiento del root

        Returns:
            Frame final del loop
        """
        if not action:
            return 0

        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        duration = frame_end - frame_start

        if duration < 4:
            print(f"  ⚠ Animation too short for looping ({duration} frames)")
            return frame_end

        print(f"\n{'='*50}")
        print(f" AUTO-LOOP: {action.name}")
        print(f"{'='*50}")
        print(f"  Duration: {duration} frames")
        print(f"  Blend zone: FULL animation")

        # Encontrar punto óptimo de loop
        if auto_find_loop_point:
            loop_frame, score = AutoLoop.find_best_loop_point(action)
            print(f"  Best loop point: frame {loop_frame} (score: {score:.1%})")

            # Ajustar frame_end al mejor punto
            if loop_frame < frame_end:
                frame_end = loop_frame
                duration = frame_end - frame_start

        # =====================================================================
        # CROSS-FADE SOBRE TODA LA ANIMACIÓN
        # =====================================================================
        print(f"\n  Applying full-animation cross-fade...")

        for fc in action.fcurves:
            # Detectar si es root location
            is_root_location = False
            if 'location' in fc.data_path:
                is_root_location = any(kw.lower() in fc.data_path.lower()
                                       for kw in AutoLoop.ROOT_BONE_KEYWORDS)

            # Si es root location y queremos preservar motion, saltar
            if is_root_location and preserve_root_motion:
                continue

            # Guardar valores originales de toda la animación
            original_values = []
            for i in range(duration + 1):
                original_values.append(fc.evaluate(frame_start + i))

            # Aplicar cross-fade gradual sobre toda la animación
            # En la primera mitad: el valor original domina
            # En la segunda mitad: transiciona hacia el valor inicial
            for i in range(duration + 1):
                t = i / max(1, duration)
                t = AutoLoop.smoothstep(t)

                # Blend entre valor original y valor espejado desde el inicio
                original = original_values[i]
                mirror_idx = duration - i
                from_mirror = original_values[mirror_idx]
                first_value = original_values[0]

                # En la segunda mitad, mezclar hacia el primer frame
                blend_factor = t  # 0 al inicio, 1 al final
                blended = original * (1.0 - blend_factor) + first_value * blend_factor

                fc.keyframe_points.insert(frame_start + i, blended)

            # Asegurar que el último frame sea igual al primero
            first_value = original_values[0]
            fc.keyframe_points.insert(frame_end, first_value)
        
        # Suavizar todas las curvas
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
        
        # Ajustar frame range
        action.frame_range = (frame_start, frame_end)
        
        # Verificar calidad del loop resultante
        final_similarity = AutoLoop.calculate_pose_similarity(
            action, frame_start, frame_end, exclude_root_location=True
        )
        
        print(f"\n  ✓ Loop created")
        print(f"    Final duration: {frame_end - frame_start} frames")
        print(f"    Loop similarity: {final_similarity:.1%}")
        
        return frame_end
    
    @staticmethod
    def make_loopable_simple(action, blend_frames: int = None) -> int:
        """
        Versión simplificada: solo iguala el último frame al primero
        con una transición suave en los últimos N frames.
        
        Útil para animaciones que ya son casi loops.
        """
        if not action:
            return 0
        
        if blend_frames is None:
            blend_frames = DEFAULT_LOOP_BLEND_FRAMES
        
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        
        for fc in action.fcurves:
            start_value = fc.evaluate(frame_start)
            
            for i in range(blend_frames):
                frame = frame_end - blend_frames + i + 1
                if frame <= frame_start:
                    continue
                
                t = (i + 1) / blend_frames
                t = AutoLoop.smoothstep(t)
                
                current_value = fc.evaluate(frame)
                blended_value = current_value * (1.0 - t) + start_value * t
                
                fc.keyframe_points.insert(frame, blended_value)
        
        return frame_end
    
    @staticmethod
    def analyze_loop_quality(action) -> dict:
        """
        Analiza la calidad del loop de una acción.
        
        Returns:
            Dict con métricas de calidad del loop
        """
        if not action:
            return {'quality': 'none', 'message': 'No action'}
        
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        
        pose_sim = AutoLoop.calculate_pose_similarity(
            action, frame_start, frame_end, exclude_root_location=True
        )
        vel_sim = AutoLoop.calculate_velocity_similarity(
            action, frame_start, frame_end
        )
        
        # Score combinado
        combined = pose_sim * 0.7 + vel_sim * 0.3
        
        # Clasificar calidad
        if combined > 0.95:
            quality = 'excellent'
            message = 'Perfect loop - no visible seam'
        elif combined > 0.85:
            quality = 'good'
            message = 'Smooth loop - barely noticeable transition'
        elif combined > 0.7:
            quality = 'acceptable'
            message = 'Minor pop at loop point'
        elif combined > 0.5:
            quality = 'poor'
            message = 'Visible jump at loop point'
        else:
            quality = 'bad'
            message = 'Severe discontinuity - not suitable for looping'
        
        return {
            'pose_similarity': pose_sim,
            'velocity_similarity': vel_sim,
            'combined_score': combined,
            'quality': quality,
            'message': message,
            'frame_start': frame_start,
            'frame_end': frame_end,
            'duration': frame_end - frame_start
        }
    
    @staticmethod
    def detect_natural_loop_points(action, threshold: float = 0.8) -> List[int]:
        """
        Detecta frames donde la animación naturalmente vuelve a una pose similar al inicio.
        Útil para encontrar múltiples ciclos en una animación larga.
        
        Returns:
            Lista de frames donde hay poses similares al inicio
        """
        if not action:
            return []
        
        frame_start = int(action.frame_range[0])
        frame_end = int(action.frame_range[1])
        
        loop_points = []
        
        # Empezar a buscar después del 20% de la animación
        search_start = frame_start + int((frame_end - frame_start) * 0.2)
        
        for frame in range(search_start, frame_end + 1):
            similarity = AutoLoop.calculate_pose_similarity(
                action, frame_start, frame, exclude_root_location=True
            )
            
            if similarity >= threshold:
                # Evitar puntos muy cercanos entre sí
                if not loop_points or frame - loop_points[-1] > 10:
                    loop_points.append(frame)
        
        return loop_points
