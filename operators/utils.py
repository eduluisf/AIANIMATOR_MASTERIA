"""
AI Animator - Utility Operators
"""

import bpy
import os
import sys
import site
import subprocess


def get_python_executable():
    return sys.executable


def _blender_site_packages():
    """Returns the site-packages dir bundled with Blender's Python."""
    py_dir = os.path.dirname(sys.executable)
    candidates = [
        os.path.normpath(os.path.join(py_dir, "..", "lib", "site-packages")),
        os.path.normpath(os.path.join(py_dir, "..", "Lib", "site-packages")),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]


def _is_writable(path):
    try:
        test = os.path.join(path, ".ai_animator_write_test")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        return True
    except Exception:
        return False


def _detect_blender_numpy():
    """Returns (version, install_path) of the numpy bundled with Blender, or (None, None)."""
    try:
        import numpy
        return numpy.__version__, os.path.dirname(numpy.__file__)
    except Exception:
        return None, None


def _user_site_shadow_paths():
    """Return user-site folders that would shadow Blender's site-packages."""
    shadows = []
    try:
        user_site = site.getusersitepackages()
        if user_site and os.path.isdir(user_site):
            shadows.append(user_site)
    except Exception:
        pass
    appdata = os.environ.get("APPDATA")
    if appdata:
        roaming = os.path.join(appdata, "Python")
        if os.path.isdir(roaming):
            shadows.append(roaming)
    return shadows


def _has_conflicting_numpy_in_user_site():
    """Check if there is a top-level numpy package in user-site that would shadow Blender's.

    Only flags `<...>/site-packages/numpy/` — not nested submodules like
    `scipy/_lib/array_api_compat/numpy`, which are vendored helpers and harmless.
    """
    for shadow in _user_site_shadow_paths():
        for root, dirs, _ in os.walk(shadow):
            if os.path.basename(root) != "site-packages":
                continue
            if "numpy" in dirs:
                candidate = os.path.join(root, "numpy")
                # Must look like a real numpy install, not a stub.
                if os.path.exists(os.path.join(candidate, "__init__.py")) or \
                   os.path.exists(os.path.join(candidate, "_core")) or \
                   os.path.exists(os.path.join(candidate, "core")):
                    return candidate
    return None


def install_dependencies():
    python_exe = get_python_executable()
    target = _blender_site_packages()

    print("\n" + "="*60)
    print("Installing AI dependencies...")
    print(f"Blender Python:  {python_exe}")
    print(f"Target folder:   {target}")

    numpy_ver, numpy_path = _detect_blender_numpy()
    if numpy_ver:
        print(f"Blender NumPy:   {numpy_ver}  ({numpy_path})")
        print(f"  → will pin numpy=={numpy_ver} so the install can't break it")
    else:
        print("Blender NumPy:   NOT FOUND (something is already broken)")
    print("="*60)

    shadow = _has_conflicting_numpy_in_user_site()
    if shadow:
        print("="*60)
        print("✗ A user-site numpy was found that will shadow Blender's numpy:")
        print(f"   {shadow}")
        print()
        print("  This breaks Blender on import (numpy 'multiarray' error).")
        print("  Delete the parent folder before continuing, e.g.:")
        for s in _user_site_shadow_paths():
            print(f"     rmdir /S /Q \"{s}\"")
        print("="*60 + "\n")
        return False, "user_site_shadow"

    if not _is_writable(target):
        print("="*60)
        print("✗ Blender's site-packages is NOT writable:")
        print(f"  {target}")
        print()
        print("  pip would install into your user AppData folder instead,")
        print("  which Blender does NOT load. The AI module will stay disabled.")
        print()
        print("  Fix: close Blender and re-open it as Administrator,")
        print("  then click 'Install AI Dependencies' again.")
        print("  (Or install Blender outside 'Program Files'.)")
        print("="*60 + "\n")
        return False, "not_writable"

    # Force pip to ignore the user's AppData site-packages so it neither reads
    # "already satisfied" from there nor accidentally installs there.
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"

    pip_args = [
        python_exe, "-m", "pip", "install",
        "--target", target,
        "--upgrade-strategy", "only-if-needed",
        "--no-user",
        "sentence-transformers",
    ]
    if numpy_ver:
        # Pin to whatever numpy Blender already ships with so pip will pick a
        # sentence-transformers / torch combo that's compatible, instead of
        # bumping numpy to 2.x and breaking every other addon.
        pip_args.append(f"numpy=={numpy_ver}")

    try:
        subprocess.check_call(pip_args, env=env)
    except subprocess.CalledProcessError as e:
        print(f"✗ pip failed: {e}")
        return False, "pip_failed"

    if target not in sys.path:
        sys.path.insert(0, target)
    site.addsitedir(target)

    try:
        import importlib
        import sentence_transformers  # noqa: F401
        importlib.invalidate_caches()
        loaded_from = sentence_transformers.__file__
    except Exception as e:
        print("="*60)
        print(f"✗ Install reported success but import still fails: {e}")
        print("  Most likely the package landed in your user AppData folder")
        print("  (run Blender as Administrator and try again).")
        print("="*60 + "\n")
        return False, "import_failed"

    if not loaded_from.startswith(target):
        print("="*60)
        print("⚠ sentence_transformers imported, but from the WRONG location:")
        print(f"  {loaded_from}")
        print(f"  Expected under: {target}")
        print("  Run Blender as Administrator and reinstall.")
        print("="*60 + "\n")
        return False, "wrong_location"

    # Sanity-check numpy is still fine after the install.
    try:
        import importlib
        import numpy
        importlib.reload(numpy)
        new_ver = numpy.__version__
        if numpy_ver and new_ver != numpy_ver:
            print(f"⚠ numpy changed: {numpy_ver} → {new_ver}")
    except Exception as e:
        print("="*60)
        print(f"✗ NumPy is broken after install: {e}")
        print(f"  Reinstall Blender's numpy with:")
        print(f'    "{python_exe}" -m pip install --target "{target}" '
              f'--force-reinstall numpy=={numpy_ver or "1.26.4"}')
        print("="*60 + "\n")
        return False, "numpy_broken"

    print("="*60)
    print(f"✓ Installed into Blender Python: {loaded_from}")
    print("✓ Please restart Blender")
    print("="*60 + "\n")
    return True, "ok"


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
        success, reason = install_dependencies()

        if success:
            self.report({'WARNING'}, "Installation complete! Please RESTART Blender")
            return {'FINISHED'}

        messages = {
            "not_writable": "Blender folder is read-only. Re-open Blender as Administrator and try again (see console).",
            "pip_failed": "pip failed to download packages. See console for details.",
            "import_failed": "Install ran but Blender can't import it. Run Blender as Administrator (see console).",
            "wrong_location": "Installed to user AppData, not Blender. Run Blender as Administrator (see console).",
            "user_site_shadow": "Conflicting numpy in user AppData. Delete it first (see console).",
            "numpy_broken": "Install broke NumPy. See console for the recovery command.",
        }
        self.report({'ERROR'}, messages.get(reason, "Installation failed (see console)"))
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
