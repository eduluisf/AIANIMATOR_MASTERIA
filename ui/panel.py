"""
AI Animator - UI Panel
Detección de secuencias + Búsqueda semántica + Control de transiciones
"""
import bpy

TRANSITION_PRESETS = {
    'SMOOTH': {'frames': 25, 'curve': 'EASE_IN_OUT', 'label': 'Smooth'},
    'NORMAL': {'frames': 15, 'curve': 'EASE_OUT', 'label': 'Normal'},
    'SHARP': {'frames': 6, 'curve': 'LINEAR', 'label': 'Sharp'},
    'SNAP': {'frames': 2, 'curve': 'LINEAR', 'label': 'Snap'},
}

SMOOTH_EXAMPLES = ["smoothly", "gently", "flowing", "gradual", "soft", "suave", "fluido"]
SHARP_EXAMPLES = ["abruptly", "sharp", "quickly", "sudden", "fast", "rápido", "brusco"]
SNAP_EXAMPLES = ["snap", "cut", "instant", "direct", "corte", "directo"]

CONNECTORS = [
    ' then ', ' after ', ' and then ', ' followed by ',
    ' luego ', ' después ', ' y luego ', ' y después ',
    ' seguido de ', ', then ', ', after ', ', luego ',
    ' -> ', ' → ', ' next ', ' antes de ',
]


def detect_transition_style(text: str, model=None) -> str:
    if not model:
        return 'NORMAL'
    
    try:
        import numpy as np
        text_emb = model.encode(text.lower())
        
        def max_sim(examples):
            embs = model.encode(examples)
            sims = np.dot(embs, text_emb) / (np.linalg.norm(embs, axis=1) * np.linalg.norm(text_emb) + 1e-8)
            return float(np.max(sims))
        
        scores = {'SMOOTH': max_sim(SMOOTH_EXAMPLES), 'SHARP': max_sim(SHARP_EXAMPLES), 'SNAP': max_sim(SNAP_EXAMPLES)}
        best = max(scores, key=scores.get)
        
        print(f"[TRANSITION] {text[:30]}... -> {best} ({scores[best]:.2f})")
        
        if scores[best] > 0.45:
            return best
    except:
        pass
    return 'NORMAL'


def split_into_sequence_with_transitions(prompt: str, model=None):
    prompt_lower = prompt.lower()
    
    # Encontrar conectores
    connector_positions = []
    for conn in CONNECTORS:
        idx = 0
        while True:
            pos = prompt_lower.find(conn, idx)
            if pos == -1:
                break
            connector_positions.append({
                'pos': pos, 'end': pos + len(conn),
                'context': prompt_lower[max(0, pos-15):pos+len(conn)+15]
            })
            idx = pos + 1
    
    if not connector_positions:
        return False, [prompt], []
    
    connector_positions.sort(key=lambda x: x['pos'])
    
    parts = []
    transitions = []
    last_end = 0
    
    for conn_info in connector_positions:
        part = prompt_lower[last_end:conn_info['pos']].strip()
        if part and len(part) > 1:
            parts.append(part)
        transitions.append(detect_transition_style(conn_info['context'], model))
        last_end = conn_info['end']
    
    last_part = prompt_lower[last_end:].strip()
    if last_part and len(last_part) > 1:
        parts.append(last_part)
    
    if len(transitions) >= len(parts):
        transitions = transitions[:len(parts)-1]
    
    if len(parts) > 1:
        return True, parts, transitions
    return False, [prompt], []


class AI_TransitionProperty(bpy.types.PropertyGroup):
    style: bpy.props.EnumProperty(
        name="Style",
        items=[
            ('SMOOTH', 'Smooth', '25 frames, ease-in-out'),
            ('NORMAL', 'Normal', '15 frames, ease-out'),
            ('SHARP', 'Sharp', '6 frames, linear'),
            ('SNAP', 'Snap', '2 frames, instant'),
        ],
        default='NORMAL'
    )
    frames: bpy.props.IntProperty(name="Frames", default=15, min=1, max=60)
    use_custom_frames: bpy.props.BoolProperty(name="Custom", default=False)


class AI_SearchResultGroup(bpy.types.PropertyGroup):
    query: bpy.props.StringProperty()
    name: bpy.props.StringProperty()
    filename: bpy.props.StringProperty()
    path: bpy.props.StringProperty()
    score: bpy.props.FloatProperty()
    selected: bpy.props.BoolProperty(default=False)
    group_index: bpy.props.IntProperty()


class AI_OT_Search(bpy.types.Operator):
    bl_idname = "ai_animator.search"
    bl_label = "Search"

    def execute(self, context):
        from ..operators.generate import get_matcher
        from ..core import process_prompt_for_overlay

        prompt = context.scene.ai_animator_prompt.strip()
        if not prompt:
            self.report({'ERROR'}, "Enter search term")
            return {'CANCELLED'}

        matcher = get_matcher()
        model = matcher.model if matcher.semantic_available else None

        is_overlay, overlay_part, base_part = process_prompt_for_overlay(prompt)

        context.scene.ai_search_results.clear()
        context.scene.ai_transitions.clear()
        context.scene.ai_search_mode = 'SINGLE'

        # OVERLAY: A while B → 2 grupos sin transición entre ellos.
        if is_overlay and overlay_part and base_part:
            print(f"\n{'='*50}")
            print(f"[SEARCH OVERLAY] '{overlay_part}' WHILE '{base_part}'")
            print(f"{'='*50}")

            context.scene.ai_search_mode = 'OVERLAY'
            for group_idx, part in enumerate([overlay_part, base_part]):
                results = matcher.search_top(part, top_k=3)
                for i, (anim, score) in enumerate(results):
                    item = context.scene.ai_search_results.add()
                    item.query = part
                    item.name = anim['name']
                    item.filename = anim['filename']
                    item.path = anim['path']
                    item.score = score
                    item.group_index = group_idx
                    item.selected = (i == 0)
            return {'FINISHED'}

        is_seq, parts, transitions = split_into_sequence_with_transitions(prompt, model)

        print(f"\n{'='*50}")
        print(f"[SEARCH] '{prompt}'")
        print(f"[SEARCH] Parts: {parts}, Transitions: {transitions}")
        print(f"{'='*50}")

        if is_seq and len(parts) > 1:
            context.scene.ai_search_mode = 'SEQUENCE'
            for group_idx, part in enumerate(parts):
                results = matcher.search_top(part, top_k=3)
                for i, (anim, score) in enumerate(results):
                    item = context.scene.ai_search_results.add()
                    item.query = part
                    item.name = anim['name']
                    item.filename = anim['filename']
                    item.path = anim['path']
                    item.score = score
                    item.group_index = group_idx
                    item.selected = (i == 0)

                if group_idx < len(parts) - 1:
                    trans = context.scene.ai_transitions.add()
                    trans.style = transitions[group_idx] if group_idx < len(transitions) else 'NORMAL'
                    trans.frames = TRANSITION_PRESETS[trans.style]['frames']
        else:
            results = matcher.search_top(prompt, top_k=5)
            for i, (anim, score) in enumerate(results):
                item = context.scene.ai_search_results.add()
                item.query = prompt
                item.name = anim['name']
                item.filename = anim['filename']
                item.path = anim['path']
                item.score = score
                item.group_index = 0
                item.selected = (i == 0)

        return {'FINISHED'}


class AI_OT_GenerateFromMixer(bpy.types.Operator):
    bl_idname = "ai_animator.generate_mix"
    bl_label = "Generate"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from ..core import AutoLoop, get_in_place_processor, MotionBlender
        from ..core.sequence import SequenceBuilder
        from ..core.transform import MIXAMO_BONE_GROUPS, BoneGroup, ACTION_BONE_MAPPING

        results = context.scene.ai_search_results
        if not results:
            self.report({'ERROR'}, "Search first")
            return {'CANCELLED'}

        obj = context.object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select armature")
            return {'CANCELLED'}

        groups = {}
        for r in results:
            if r.group_index not in groups:
                groups[r.group_index] = []
            groups[r.group_index].append(r)

        to_import = []
        for idx in sorted(groups.keys()):
            selected = [r for r in groups[idx] if r.selected]
            to_import.append(selected[0] if selected else groups[idx][0])

        # ---------- OVERLAY MODE ----------
        if context.scene.ai_search_mode == 'OVERLAY' and len(to_import) >= 2:
            return self._execute_overlay(
                context, obj, to_import,
                MotionBlender, AutoLoop, get_in_place_processor,
                MIXAMO_BONE_GROUPS, BoneGroup, ACTION_BONE_MAPPING,
            )
        
        transition_configs = []
        for trans in context.scene.ai_transitions:
            frames = trans.frames if trans.use_custom_frames else TRANSITION_PRESETS[trans.style]['frames']
            transition_configs.append({
                'style': trans.style,
                'frames': frames,
                'curve': TRANSITION_PRESETS[trans.style]['curve']
            })
        
        print(f"\n{'='*50}")
        print(f"  GENERATING: {len(to_import)} animations")
        for i, item in enumerate(to_import):
            print(f"    {i+1}. {item.name}")
            if i < len(transition_configs):
                tc = transition_configs[i]
                print(f"        ↓ {tc['style']} ({tc['frames']}f)")
        print(f"{'='*50}")
        
        actions = []
        for item in to_import:
            print(f"\n  📦 Importing: {item.name} (score: {item.score:.0%})")
            print(f"      File: {item.path}")
            before = set(bpy.data.objects.keys())
            try:
                bpy.ops.import_scene.fbx(filepath=item.path)
            except Exception as e:
                print(f"      ✗ Import failed: {e}")
                continue
            after = set(bpy.data.objects.keys())

            for n in (after - before):
                o = bpy.data.objects.get(n)
                if o and o.type == 'ARMATURE' and o.animation_data and o.animation_data.action:
                    action_copy = o.animation_data.action.copy()
                    actions.append(action_copy)
                    frames = action_copy.frame_range[1] - action_copy.frame_range[0]
                    print(f"      ✓ Loaded: {action_copy.name} ({frames:.0f} frames)")
                    break

            for n in (after - before):
                if n in bpy.data.objects:
                    bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
        
        if not actions:
            self.report({'ERROR'}, "No animations")
            return {'CANCELLED'}
        
        print(f"\n{'='*50}")
        print(f" BUILDING FINAL ANIMATION")
        print(f"{'='*50}")
        if len(actions) == 1:
            print(f"  Using single animation: {actions[0].name}")
            final = actions[0]
        else:
            print(f"  Chaining {len(actions)} animations:")
            for i, a in enumerate(actions):
                frames = a.frame_range[1] - a.frame_range[0]
                print(f"    {i+1}. {a.name} ({frames:.0f} frames)")
                if i < len(transition_configs):
                    tc = transition_configs[i]
                    print(f"       ↓ transition: {tc['style']} ({tc['frames']} frames)")
            builder = SequenceBuilder()
            # Intentar con transiciones custom
            if hasattr(builder, 'build_sequence_with_transitions'):
                final = builder.build_sequence_with_transitions(actions, transition_configs, "Sequence")
            else:
                # Fallback - usar frames promedio
                avg_frames = sum(tc['frames'] for tc in transition_configs) // len(transition_configs) if transition_configs else 15
                final = builder.build_sequence(actions, avg_frames, "Sequence")
        
        prompt_lower = context.scene.ai_animator_prompt.lower()
        if any(kw in prompt_lower for kw in ['in place', 'in-place', 'sin moverse']):
            processor = get_in_place_processor()
            final = processor.remove_root_motion(final, axes='XY')
        
        if context.scene.ai_animator_auto_loop:
            print(f"\n  🔄 Applying auto-loop to: {final.name}")
            AutoLoop.make_loopable(final)
        
        if context.scene.ai_animator_mode == 'EDIT' and obj.animation_data and obj.animation_data.action:
            bpy.data.actions.remove(obj.animation_data.action)
        
        obj.animation_data_create()
        obj.animation_data.action = final

        # Mostrar qué animaciones se usaron
        anim_names = [item.name for item in to_import]
        if len(anim_names) == 1:
            self.report({'INFO'}, f"Generated: {anim_names[0]}")
        else:
            chain = " → ".join(anim_names)
            self.report({'INFO'}, f"Generated sequence: {chain}")
        return {'FINISHED'}


    def _import_one(self, item):
        """Import an FBX picked from the search list and return its action copy."""
        before = set(bpy.data.objects.keys())
        try:
            bpy.ops.import_scene.fbx(filepath=item.path)
        except Exception as e:
            print(f"      ✗ Import failed: {e}")
            return None
        after = set(bpy.data.objects.keys())
        action = None
        for n in (after - before):
            o = bpy.data.objects.get(n)
            if o and o.type == 'ARMATURE' and o.animation_data and o.animation_data.action:
                action = o.animation_data.action.copy()
                break
        for n in (after - before):
            if n in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
        return action

    def _execute_overlay(self, context, obj, to_import,
                         MotionBlender, AutoLoop, get_in_place_processor,
                         MIXAMO_BONE_GROUPS, BoneGroup, ACTION_BONE_MAPPING):
        """Combine the user's two picks (overlay + base) into a per-bone overlay.

        Auto-detects which query is locomotion (BERT + keywords) and uses that
        animation as the BASE so the root/hips comes from the actual movement.
        """
        from ..operators.generate import get_matcher
        from ..core import assign_overlay_roles

        overlay_item = to_import[0]
        base_item = to_import[1]

        matcher = get_matcher()
        model = matcher.model if matcher.semantic_available else None
        base_is_left, base_score, ovl_score = assign_overlay_roles(
            overlay_item.query, base_item.query, model=model,
        )
        if base_is_left:
            print(f"  ↻ Auto-swap: '{overlay_item.query}' is locomotion → it becomes BASE")
            overlay_item, base_item = base_item, overlay_item

        print(f"\n{'='*50}")
        print(f"  GENERATING OVERLAY")
        print(f"  Base (root/hips):  {base_item.name}  on '{base_item.query}' "
              f"(loc={max(base_score, ovl_score):.2f})")
        print(f"  Overlay (gesture): {overlay_item.name}  on '{overlay_item.query}'")
        print(f"{'='*50}")

        overlay_action = self._import_one(overlay_item)
        base_action = self._import_one(base_item)

        if not base_action:
            self.report({'ERROR'}, "Could not load base animation")
            return {'CANCELLED'}
        if not overlay_action:
            self.report({'ERROR'}, "Could not load overlay animation")
            return {'CANCELLED'}

        # Resolver qué huesos toma el overlay (a partir de las palabras del query).
        groups = set()
        for word in overlay_item.query.lower().split():
            mapped = ACTION_BONE_MAPPING.get(word)
            if not mapped:
                continue
            for bg in mapped:
                if bg != BoneGroup.FULL_BODY:
                    groups.add(bg)
        if not groups:
            groups.add(BoneGroup.ARMS)

        bones = []
        for bg in groups:
            bones.extend(MIXAMO_BONE_GROUPS.get(bg) or [])
        bones = list(set(bones))

        print(f"  Overlay bone groups: {[bg.value for bg in groups]} ({len(bones)} bones)")

        final = MotionBlender.overlay_actions(
            base_action, overlay_action,
            overlay_bones=bones,
            name=f"{overlay_item.query[:10]}_while_{base_item.query[:10]}",
        )

        prompt_lower = context.scene.ai_animator_prompt.lower()
        if any(kw in prompt_lower for kw in ['in place', 'in-place', 'sin moverse']):
            processor = get_in_place_processor()
            final = processor.remove_root_motion(final, axes='XY')

        if context.scene.ai_animator_auto_loop:
            print(f"\n  🔄 Applying auto-loop to: {final.name}")
            AutoLoop.make_loopable(final)

        if context.scene.ai_animator_mode == 'EDIT' and obj.animation_data and obj.animation_data.action:
            bpy.data.actions.remove(obj.animation_data.action)

        obj.animation_data_create()
        obj.animation_data.action = final

        self.report(
            {'INFO'},
            f"Overlay: {overlay_item.name} on top of {base_item.name}",
        )
        return {'FINISHED'}


class AI_PT_AnimatorPanel(bpy.types.Panel):
    bl_label = "AI Animator"
    bl_idname = "VIEW3D_PT_ai_animator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AI Animator'
    
    def draw(self, context):
        layout = self.layout
        from ..operators.generate import get_matcher
        matcher = get_matcher()
        stats = matcher.get_stats()
        
        box = layout.box()
        if matcher.semantic_available:
            box.label(text="✓ AI Active", icon='CHECKMARK')
        else:
            box.label(text="⚠ No AI", icon='ERROR')
            box.operator("ai_animator.install_deps")
        box.label(text=f"{stats['total_animations']} animations")
        
        layout.separator()
        layout.label(text="Describe animation:")
        row = layout.row(align=True)
        row.prop(context.scene, "ai_animator_prompt", text="")
        row.operator("ai_animator.search", text="", icon='VIEWZOOM')
        
        row = layout.row()
        row.prop(context.scene, "ai_animator_mode", expand=True)
        
        layout.separator()
        
        results = context.scene.ai_search_results
        transitions = context.scene.ai_transitions
        
        if results:
            box = layout.box()
            mode = context.scene.ai_search_mode

            groups = {}
            for r in results:
                if r.group_index not in groups:
                    groups[r.group_index] = {'query': r.query, 'items': []}
                groups[r.group_index]['items'].append(r)

            sorted_idx = sorted(groups.keys())

            overlay_labels = {0: 'OVERLAY', 1: 'BASE'}

            for i, idx in enumerate(sorted_idx):
                group = groups[idx]

                if len(groups) > 1:
                    if mode == 'OVERLAY':
                        prefix = overlay_labels.get(idx, f"#{idx+1}")
                        box.label(text=f"► {prefix}: {group['query'].upper()}", icon='FORWARD')
                    else:
                        box.label(text=f"► {idx+1}. {group['query'].upper()}", icon='FORWARD')

                for item in group['items']:
                    row = box.row(align=True)
                    row.prop(item, "selected", text="")
                    row.label(text=f"[{item.score:.0%}] {item.name}")

                # En overlay no hay transición entre grupos (son simultáneos).
                if mode != 'OVERLAY' and i < len(sorted_idx) - 1 and i < len(transitions):
                    trans = transitions[i]
                    tbox = box.box()
                    row = tbox.row(align=True)
                    row.label(text="↓", icon='ARROW_LEFTRIGHT')
                    row.prop(trans, "style", text="")
                    row.prop(trans, "use_custom_frames", text="", icon='PREFERENCES')
                    if trans.use_custom_frames:
                        row.prop(trans, "frames", text="")
                    else:
                        trans.frames = TRANSITION_PRESETS[trans.style]['frames']

                if mode == 'OVERLAY' and i < len(sorted_idx) - 1:
                    sep = box.box()
                    sep.label(text="while", icon='LINKED')

                if i < len(sorted_idx) - 1:
                    box.separator()

            row = box.row()
            row.scale_y = 1.5
            if mode == 'OVERLAY':
                btn = "Generate Overlay"
            elif len(groups) > 1:
                btn = "Generate Sequence"
            else:
                btn = "Generate"
            row.operator("ai_animator.generate_mix", text=btn, icon='PLAY')
        
        layout.separator()
        box = layout.box()
        box.prop(context.scene, "ai_animator_auto_loop")
        
        layout.separator()
        layout.operator("ai_animator.generate", text="Quick Generate", icon='AUTO')
        layout.operator("ai_animator.refresh", icon='FILE_REFRESH')


class AI_PT_ExamplesPanel(bpy.types.Panel):
    bl_label = "Examples"
    bl_idname = "VIEW3D_PT_ai_animator_examples"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AI Animator'
    bl_parent_id = "VIEW3D_PT_ai_animator"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Sequence:")
        layout.label(text="• walk smoothly then jump")
        layout.label(text="• idle sharp to punch")
        layout.label(text="• run then snap to idle")
        layout.separator()
        layout.label(text="Overlay (while / mientras):")
        layout.label(text="• clap while walk")
        layout.label(text="• wave mientras correr")
        layout.label(text="• shoot while sprint")
