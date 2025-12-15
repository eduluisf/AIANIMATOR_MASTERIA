bl_info = {
    "name": "AI Animator",
    "author": "Eduardo Sierra",
    "version": (3, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > AI Animator",
    "description": "AI-powered animation search, sequencing and transitions",
    "category": "Animation",
}

import bpy
from .operators import (
    AI_OT_GenerateAnimation,
    AI_OT_RefreshAnimations,
    AI_OT_InstallDependencies,
    AI_OT_AnalyzeLoop,
    AI_OT_AnalyzeRig
)
from .ui import (
    AI_TransitionProperty,
    AI_SearchResultGroup,
    AI_OT_Search,
    AI_OT_GenerateFromMixer,
    AI_PT_AnimatorPanel,
    AI_PT_ExamplesPanel,
)

classes = (
    AI_TransitionProperty,
    AI_SearchResultGroup,
    AI_OT_GenerateAnimation,
    AI_OT_RefreshAnimations,
    AI_OT_InstallDependencies,
    AI_OT_AnalyzeLoop,
    AI_OT_AnalyzeRig,
    AI_OT_Search,
    AI_OT_GenerateFromMixer,
    AI_PT_AnimatorPanel,
    AI_PT_ExamplesPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.ai_animator_prompt = bpy.props.StringProperty(name="Prompt", default="")
    bpy.types.Scene.ai_animator_mode = bpy.props.EnumProperty(
        name="Mode",
        items=[('NEW', 'New', 'Create new'), ('EDIT', 'Edit', 'Replace current')],
        default='NEW'
    )
    bpy.types.Scene.ai_animator_auto_loop = bpy.props.BoolProperty(name="Auto Loop", default=True)
    bpy.types.Scene.ai_animator_loop_frames = bpy.props.IntProperty(name="Blend Frames", default=15, min=5, max=60)
    bpy.types.Scene.ai_search_results = bpy.props.CollectionProperty(type=AI_SearchResultGroup)
    bpy.types.Scene.ai_transitions = bpy.props.CollectionProperty(type=AI_TransitionProperty)
    
    print("✓ AI Animator v3.0 loaded")

def unregister():
    del bpy.types.Scene.ai_animator_prompt
    del bpy.types.Scene.ai_animator_mode
    del bpy.types.Scene.ai_animator_auto_loop
    del bpy.types.Scene.ai_animator_loop_frames
    del bpy.types.Scene.ai_search_results
    del bpy.types.Scene.ai_transitions
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
