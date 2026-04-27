"""
AI Animator - Generate Operator
Operador principal que orquesta la generación de animaciones
"""

import bpy
from ..core import (
    PromptParser,
    AnimationMatcher,
    MotionBlender,
    AutoLoop,
    get_retargeter,
    get_sequence_detector,
    get_sequence_builder,
    get_in_place_processor,
    process_prompt_for_sequence,
    process_prompt_for_overlay,
)
from ..core.transform import (
    get_transformer,
    MIXAMO_BONE_GROUPS,
    BoneGroup,
    ACTION_BONE_MAPPING,
    assign_overlay_roles,
)


# Instancias globales (se inicializan una vez)
_parser = None
_matcher = None
_transformer_initialized = False


def get_parser():
    global _parser
    if _parser is None:
        _parser = PromptParser()
    return _parser


def get_matcher():
    global _matcher
    if _matcher is None:
        _matcher = AnimationMatcher()
    return _matcher


def refresh_matcher():
    """Refresca el matcher (usado por el operador de refresh)"""
    global _matcher
    _matcher = AnimationMatcher()
    return _matcher


def ensure_transformer_initialized():
    """Inicializa el transformer semántico con el modelo del matcher."""
    global _transformer_initialized
    if _transformer_initialized:
        return
    matcher = get_matcher()
    if matcher.semantic_available and matcher.model:
        transformer = get_transformer()
        transformer.initialize(matcher.model)
        parser = get_parser()
        parser.enable_semantic_detection(transformer)
        _transformer_initialized = True


class AI_OT_GenerateAnimation(bpy.types.Operator):
    """Generate and apply animation using AI semantic search and motion synthesis"""
    bl_idname = "ai_animator.generate"
    bl_label = "Generate Animation"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        prompt = context.scene.ai_animator_prompt.strip()
        
        if not prompt:
            self.report({'ERROR'}, "Please enter an animation description")
            return {'CANCELLED'}
        
        # Verificar armature seleccionado
        active_obj = context.object
        if not active_obj or active_obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Please select an armature first")
            return {'CANCELLED'}
        
        # =====================================================================
        # PASO 1: Detectar overlay, secuencia e in-place
        # =====================================================================
        is_sequence, sequence_parts, is_in_place, cleaned_prompt = process_prompt_for_sequence(prompt)
        is_overlay, overlay_part, base_part = process_prompt_for_overlay(cleaned_prompt)

        print(f"\n{'='*50}")
        print(f" AI ANIMATOR - Processing Request")
        print(f"{'='*50}")
        print(f"  Original prompt: {prompt}")
        print(f"  Is overlay: {is_overlay}")
        if is_overlay:
            print(f"    Overlay part: '{overlay_part}'")
            print(f"    Base part:    '{base_part}'")
        print(f"  Is sequence: {is_sequence}")
        print(f"  Sequence parts: {sequence_parts}")
        print(f"  Is in-place: {is_in_place}")
        print(f"  Cleaned prompt: {cleaned_prompt}")

        parser = get_parser()
        matcher = get_matcher()
        ensure_transformer_initialized()

        # =====================================================================
        # PASO 2: Procesar según tipo (overlay > secuencia > blend)
        # =====================================================================

        if is_overlay and overlay_part and base_part:
            final_action = self._process_overlay(
                overlay_part, base_part, parser, matcher, active_obj, context
            )
        elif is_sequence and len(sequence_parts) > 1:
            final_action = self._process_sequence(
                sequence_parts, parser, matcher, active_obj, context
            )
        else:
            final_action = self._process_blend(
                cleaned_prompt, parser, matcher, active_obj, context
            )
        
        if not final_action:
            self.report({'ERROR'}, "Failed to generate animation")
            return {'CANCELLED'}
        
        # =====================================================================
        # PASO 3: Aplicar in-place si se detectó
        # =====================================================================
        if is_in_place:
            print(f"\n{'='*50}")
            print(f" Applying In-Place (removing root motion)")
            print(f"{'='*50}")
            in_place_processor = get_in_place_processor()
            final_action = in_place_processor.remove_root_motion(
                final_action, 
                axes='Z'  # Eliminar movimiento horizontal, mantener vertical
            )
        
        # =====================================================================
        # PASO 4: Asignar al rig
        # =====================================================================
        active_obj.animation_data_create()
        active_obj.animation_data.action = final_action
        
        # Mensaje de éxito con nombres de animaciones
        in_place_info = " [in-place]" if is_in_place else ""
        self.report({'INFO'}, f"Generated: {final_action.name}{in_place_info}")
        
        return {'FINISHED'}
    
    def _resolve_overlay_bones(self, parsed_overlay):
        """Determina qué huesos del cuerpo cubre la parte de overlay.

        Si las acciones detectadas mapean a un grupo concreto (ARMS/HEAD/SPINE)
        se usan esos huesos. Si caen en FULL_BODY o no se detecta nada se asume
        ARMS, que es el caso por defecto cuando alguien dice "X mientras camina".
        """
        groups = set()
        for action in parsed_overlay.get('actions', []):
            mapped = ACTION_BONE_MAPPING.get(action.lower())
            if not mapped:
                continue
            for bg in mapped:
                if bg != BoneGroup.FULL_BODY:
                    groups.add(bg)
        if not groups:
            groups.add(BoneGroup.ARMS)

        bones = []
        for bg in groups:
            group_bones = MIXAMO_BONE_GROUPS.get(bg) or []
            bones.extend(group_bones)
        return list(set(bones)), [bg.value for bg in groups]

    def _resolve_single_action(self, prompt, parser, matcher, target_armature):
        """Parse + search + import + (optional) blend for a single sub-prompt."""
        parsed = parser.parse(prompt)
        self._log_parsed(parsed)

        anims = matcher.find_animations_for_blend(parsed)
        if not anims:
            return None, parsed

        imported = self._import_animations(anims, target_armature)
        if not imported:
            return None, parsed

        if len(imported) > 1:
            action = MotionBlender.blend_actions(
                imported[0][0], imported[1][0],
                weight1=imported[0][1], weight2=imported[1][1],
                name=prompt[:15],
            )
        else:
            action = imported[0][0]

        if parsed['speed'] != 1.0:
            MotionBlender.apply_speed_modifier(action, parsed['speed'])
        if parsed['intensity'] != 1.0:
            MotionBlender.apply_intensity_modifier(action, parsed['intensity'])

        return action, parsed

    def _process_overlay(self, overlay_prompt, base_prompt, parser, matcher,
                         target_armature, context):
        """Combina dos animaciones por grupo de huesos (A mientras B).

        Detecta cuál lado es la locomoción y le asigna el rol de BASE (dueña
        del root/hips), sin importar el orden del 'while'. Así
        'walk while clap' y 'clap while walk' dan el mismo resultado.
        """
        print(f"\n{'='*50}")
        print(f" OVERLAY MODE")
        print(f"{'='*50}")

        # left = lo que el usuario escribió antes del 'while', right = después.
        # Por convención inicial: left=overlay, right=base. Pero si BERT detecta
        # que la locomoción está del lado del overlay, hay que invertir roles.
        model = matcher.model if matcher.semantic_available else None
        base_is_left, base_score, ovl_score = assign_overlay_roles(
            overlay_prompt, base_prompt, model=model,
        )
        if base_is_left:
            print(f"  ↻ Auto-swap: '{overlay_prompt}' is locomotion (score={base_score:.2f}) → it becomes BASE")
            base_prompt, overlay_prompt = overlay_prompt, base_prompt
        else:
            print(f"  Locomotion side: BASE='{base_prompt}' (score={base_score:.2f}) "
                  f"OVERLAY='{overlay_prompt}' (score={ovl_score:.2f})")

        print(f"\n--- Base (locomotion / root): '{base_prompt}' ---")
        base_action, _ = self._resolve_single_action(
            base_prompt, parser, matcher, target_armature
        )
        if not base_action:
            print("  ⚠ No animation for base — falling back to blend")
            return self._process_blend(
                f"{overlay_prompt} {base_prompt}", parser, matcher,
                target_armature, context,
            )

        print(f"\n--- Overlay (gesture): '{overlay_prompt}' ---")
        overlay_action, parsed_overlay = self._resolve_single_action(
            overlay_prompt, parser, matcher, target_armature
        )
        if not overlay_action:
            print("  ⚠ No animation for overlay — using base only")
            return base_action

        bones, groups = self._resolve_overlay_bones(parsed_overlay)
        print(f"\n--- Overlay target bone groups: {groups} ({len(bones)} bones) ---")
        print(f"    Root/hips → kept from BASE ('{base_prompt}')")

        final_action = MotionBlender.overlay_actions(
            base_action, overlay_action,
            overlay_bones=bones,
            name=f"{overlay_prompt[:10]}_while_{base_prompt[:10]}",
        )

        if context.scene.ai_animator_auto_loop:
            print("\n--- Making overlay loopable ---")
            AutoLoop.make_loopable(
                final_action,
                blend_frames=context.scene.ai_animator_loop_frames,
            )

        return final_action

    def _process_sequence(self, sequence_parts, parser, matcher, target_armature, context):
        """Procesa una secuencia de animaciones (encadenar)"""
        print(f"\n{'='*50}")
        print(f" SEQUENCE MODE: {len(sequence_parts)} animations")
        print(f"{'='*50}")
        
        sequence_actions = []
        
        for i, part in enumerate(sequence_parts):
            print(f"\n--- Part {i+1}: '{part}' ---")
            
            # Parsear esta parte
            parsed = parser.parse(part)
            self._log_parsed(parsed)
            
            # Buscar animación
            anims_to_blend = matcher.find_animations_for_blend(parsed)
            
            if not anims_to_blend:
                print(f"  ⚠ No animation found for '{part}', skipping")
                continue
            
            # Importar
            imported_actions = self._import_animations(anims_to_blend, target_armature)
            
            if not imported_actions:
                print(f"  ⚠ Failed to import for '{part}', skipping")
                continue
            
            # Si hay múltiples para esta parte, blendear
            if len(imported_actions) > 1:
                action = MotionBlender.blend_actions(
                    imported_actions[0][0],
                    imported_actions[1][0],
                    weight1=imported_actions[0][1],
                    weight2=imported_actions[1][1],
                    name=part[:15]
                )
            else:
                action = imported_actions[0][0]
            
            # Aplicar modificadores de velocidad/intensidad
            if parsed['speed'] != 1.0:
                MotionBlender.apply_speed_modifier(action, parsed['speed'])
            if parsed['intensity'] != 1.0:
                if parsed.get('transform_config'):
                    transformer = get_transformer()
                    bone_filter = transformer.bone_resolver.get_bones_for_groups(
                        parsed['transform_config'].target_bone_groups
                    )
                    MotionBlender.apply_intensity_modifier_selective(
                        action, parsed['intensity'], bone_filter=bone_filter
                    )
                else:
                    MotionBlender.apply_intensity_modifier(action, parsed['intensity'])
            
            sequence_actions.append(action)
            print(f"  ✓ Added to sequence: {action.name}")
        
        if not sequence_actions:
            return None
        
        # Construir secuencia
        print(f"\n--- Building Final Sequence ---")
        print(f"  Actions to chain: {len(sequence_actions)}")
        for i, act in enumerate(sequence_actions):
            print(f"    {i+1}. {act.name} ({act.frame_range[1] - act.frame_range[0]:.0f} frames)")
        
        sequence_builder = get_sequence_builder()
        final_action = sequence_builder.build_sequence(
            sequence_actions,
            transition_frames=context.scene.ai_animator_loop_frames,
            name="Sequence"
        )
        
        # Auto-loop de la secuencia completa si está habilitado
        if context.scene.ai_animator_auto_loop:
            print(f"\n--- Making sequence loopable ---")
            AutoLoop.make_loopable(
                final_action,
                blend_frames=context.scene.ai_animator_loop_frames
            )
        
        return final_action
    
    def _process_blend(self, prompt, parser, matcher, target_armature, context):
        """Procesa un blend de animaciones (comportamiento original)"""
        print(f"\n{'='*50}")
        print(f" BLEND MODE")
        print(f"{'='*50}")
        
        # Parsear prompt
        parsed = parser.parse(prompt)
        self._log_parsed(parsed)
        
        # Buscar animaciones
        anims_to_blend = matcher.find_animations_for_blend(parsed)
        
        if not anims_to_blend:
            return None
        
        # Importar animaciones
        imported_actions = self._import_animations(anims_to_blend, target_armature)
        
        if not imported_actions:
            return None
        
        # Log resumen de lo que se va a procesar
        print(f"\n{'='*50}")
        print(f" PROCESSING SUMMARY")
        print(f"{'='*50}")
        if len(imported_actions) > 1:
            print(f"  Mixing {len(imported_actions)} animations:")
            for i, (act, w) in enumerate(imported_actions):
                print(f"    {i+1}. {act.name} (weight: {w:.0%})")
        else:
            print(f"  Single animation: {imported_actions[0][0].name}")
        if parsed['speed'] != 1.0:
            print(f"  Speed modifier: {parsed['speed']}x")
        if parsed['intensity'] != 1.0:
            print(f"  Intensity modifier: {parsed['intensity']}x")
        print(f"  Auto-loop: {'ON' if context.scene.ai_animator_auto_loop else 'OFF'}")

        # Procesar: blend, speed, intensity, loop
        final_action = self._apply_processing(
            imported_actions, parsed, context, prompt
        )

        return final_action
    
    def _log_parsed(self, parsed):
        """Log del prompt parseado para debug"""
        print(f"  Parsed prompt:")
        print(f"    Original: {parsed['original']}")
        print(f"    Actions: {parsed['actions']}")
        print(f"    Emotions: {parsed['emotions']}")
        print(f"    Speed: {parsed['speed']}x")
        print(f"    Intensity: {parsed['intensity']}x")
        print(f"    Compound: {parsed['is_compound']}")
        if parsed.get('semantic_detected'):
            groups = [bg.value for bg in parsed.get('target_bone_groups', [])]
            print(f"    Semantic: YES")
            print(f"    Target bones: {groups}")
    
    def _import_animations(self, anims_to_blend, target_armature):
        """Importa las animaciones necesarias y devuelve sus actions con retargeting"""
        imported_actions = []
        retargeter = get_retargeter()
        
        for anim_result, weight in anims_to_blend:
            anim = anim_result['animation']
            confidence = anim_result['confidence']
            method = anim_result.get('method', 'unknown')
            
            print(f"\n  📦 Importing: {anim['name']} ({anim['filename']})")
            print(f"      Match confidence: {confidence:.0%} (method: {method})")
            print(f"      Blend weight: {weight:.0%}")
            print(f"      File: {anim['path']}")
            
            try:
                # Guardar objetos antes de importar
                before_import = set(bpy.data.objects.keys())
                
                # Importar FBX
                bpy.ops.import_scene.fbx(filepath=anim['path'])
                
                # Encontrar nuevos objetos
                after_import = set(bpy.data.objects.keys())
                new_objs = list(after_import - before_import)
                
                # Buscar armature importado
                imported_arm = None
                for obj_name in new_objs:
                    obj = bpy.data.objects[obj_name]
                    if obj.type == 'ARMATURE':
                        imported_arm = obj
                        break
                
                # Extraer action
                if (imported_arm and 
                    imported_arm.animation_data and 
                    imported_arm.animation_data.action):
                    
                    original_action = imported_arm.animation_data.action
                    
                    # Verificar si necesita retargeting
                    needs_retarget = self._needs_retargeting(imported_arm, target_armature)
                    
                    if needs_retarget:
                        print(f"      Retargeting to {target_armature.name}...")
                        action = retargeter.retarget_action(
                            original_action,
                            imported_arm,
                            target_armature
                        )
                        if action:
                            print(f"      ✓ Retargeted: {action.name}")
                        else:
                            print(f"      ✗ Retarget failed, using original")
                            action = original_action.copy()
                    else:
                        action = original_action.copy()
                        print(f"      ✓ Direct copy (same rig type)")
                    
                    imported_actions.append((action, weight))
                else:
                    print(f"      ✗ No animation data found")
                
                # Limpiar objetos importados
                for obj_name in new_objs:
                    if obj_name in bpy.data.objects:
                        bpy.data.objects.remove(bpy.data.objects[obj_name], do_unlink=True)
                
            except Exception as e:
                print(f"      ✗ Import error: {e}")
                continue
        
        return imported_actions
    
    def _needs_retargeting(self, source_arm, target_arm) -> bool:
        """Determina si se necesita retargeting comparando los huesos"""
        source_bones = {b.name.lower() for b in source_arm.data.bones}
        target_bones = {b.name.lower() for b in target_arm.data.bones}
        
        # Si hay alta coincidencia de nombres, no necesita retarget
        common = source_bones & target_bones
        if len(common) > len(source_bones) * 0.8:
            return False
        
        return True
    
    def _apply_processing(self, imported_actions, parsed, context, prompt):
        """Procesa las animaciones: blend, modifiers, loop"""
        
        # 1. Combinar si hay múltiples
        if len(imported_actions) > 1:
            print(f"\n--- Blending {len(imported_actions)} animations ---")
            for i, (action, weight) in enumerate(imported_actions):
                print(f"    {i+1}. {action.name} (weight: {weight:.0%})")
            
            final_action = MotionBlender.blend_actions(
                imported_actions[0][0],
                imported_actions[1][0],
                weight1=imported_actions[0][1],
                weight2=imported_actions[1][1],
                name=prompt[:20]
            )
        else:
            final_action = imported_actions[0][0]
            print(f"\n--- Single animation: {final_action.name} ---")
        
        # 2. Aplicar modificador de velocidad
        if parsed['speed'] != 1.0:
            print(f"\n--- Applying speed: {parsed['speed']}x ---")
            MotionBlender.apply_speed_modifier(final_action, parsed['speed'])
        
        # 3. Aplicar modificador de intensidad (selectivo por huesos si hay config semántica)
        if parsed['intensity'] != 1.0:
            print(f"\n--- Applying intensity: {parsed['intensity']}x ---")
            if parsed.get('transform_config'):
                transformer = get_transformer()
                bone_filter = transformer.bone_resolver.get_bones_for_groups(
                    parsed['transform_config'].target_bone_groups
                )
                MotionBlender.apply_intensity_modifier_selective(
                    final_action, parsed['intensity'], bone_filter=bone_filter
                )
            else:
                MotionBlender.apply_intensity_modifier(final_action, parsed['intensity'])
        
        # 4. Auto-loop si está habilitado
        if context.scene.ai_animator_auto_loop:
            print(f"\n--- Making loopable ---")
            AutoLoop.make_loopable(
                final_action,
                blend_frames=context.scene.ai_animator_loop_frames
            )
        
        return final_action