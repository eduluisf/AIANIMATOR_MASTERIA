"""
AI Animator - Utility Operators
"""

import bpy
import sys
import subprocess


def get_python_executable():
    return sys.executable


def install_dependencies():
    python_exe = get_python_executable()
    
    print("\n" + "="*60)
    print("Installing AI dependencies...")
    print("="*60)
    
    try:
        subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
        subprocess.check_call([python_exe, "-m", "pip", "install", "sentence-transformers"])
        
        print("="*60)
        print("✓ Installation successful! Please restart Blender")
        print("="*60 + "\n")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Installation failed: {e}")
        return False


class AI_OT_RefreshAnimations(bpy.types.Operator):
    bl_idname = "ai_animator.refresh"
    bl_label = "Refresh Animations"
    bl_description = "Rescan animation folder"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from .generate import refresh_matcher
        
        matcher = refresh_matcher()
        matcher.clear_cache()
        
        self.report({'INFO'}, f"Found {len(matcher.animations)} animations")
        return {'FINISHED'}


class AI_OT_InstallDependencies(bpy.types.Operator):
    bl_idname = "ai_animator.install_deps"
    bl_label = "Install AI Features"
    bl_description = "Install sentence-transformers"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        success = install_dependencies()
        
        if success:
            self.report({'WARNING'}, "Installation complete! Please RESTART Blender")
        else:
            self.report({'ERROR'}, "Installation failed")
        
        return {'FINISHED'}


class AI_OT_AnalyzeLoop(bpy.types.Operator):
    bl_idname = "ai_animator.analyze_loop"
    bl_label = "Analyze Loop"
    bl_description = "Check loop quality"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from ..core import AutoLoop
        
        obj = context.object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature")
            return {'CANCELLED'}
        
        if not obj.animation_data or not obj.animation_data.action:
            self.report({'ERROR'}, "No animation")
            return {'CANCELLED'}
        
        action = obj.animation_data.action
        analysis = AutoLoop.analyze_loop_quality(action)
        
        msg = f"Loop: {analysis['quality'].upper()} ({analysis['combined_score']:.0%})"
        self.report({'INFO'}, msg)
        
        return {'FINISHED'}


class AI_OT_AnalyzeRig(bpy.types.Operator):
    bl_idname = "ai_animator.analyze_rig"
    bl_label = "Analyze Rig"
    bl_description = "Check rig compatibility"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        from ..core import get_retargeter
        
        obj = context.object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature")
            return {'CANCELLED'}
        
        retargeter = get_retargeter()
        analysis = retargeter.analyze_rig(obj)
        
        if 'error' in analysis:
            self.report({'ERROR'}, analysis['error'])
            return {'CANCELLED'}
        
        msg = f"Rig: {len(analysis['recognized'])}/{analysis['total_bones']} bones recognized"
        self.report({'INFO'}, msg)
        
        return {'FINISHED'}
