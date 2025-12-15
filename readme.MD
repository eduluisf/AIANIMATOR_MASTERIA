# AI Animator - Blender Add-on

Add-on para Blender que genera animaciones 3D a partir de instrucciones en lenguaje natural.

## Instalación

### 1. Descargar e instalar el add-on

- Descargar `ai_animator.zip` desde [Releases](https://github.com/eduluisf/Ai_animator/releases)
- En Blender: `Edit` → `Preferences` → `Add-ons` → `Install...`
- Seleccionar el `.zip` y activar "AI Animator"

### 2. Configurar biblioteca de animaciones

- Abrir panel lateral: `N` → `AI Animator`
- En "Animation Library" establecer la ruta a tu carpeta con archivos FBX
- Se recomienda usar animaciones de [Mixamo](https://www.mixamo.com/)

### 3. Instalar dependencias de IA (opcional)

- Click en "Install AI Dependencies" 
- Esperar 1-4 minutos
- Reiniciar Blender

Sin las dependencias, el add-on funciona en modo básico (búsqueda por palabras clave).

---

## Uso básico

1. Seleccionar un armature (rig Mixamo o compatible)
2. Escribir descripción en el campo de texto
3. Click en **Search**
4. Seleccionar animación de los resultados
5. Click en **Generate**

### Ejemplos de búsqueda

```
happy jump
walk with gun
scared running
kick like a ninja
```

---

## Secuencias

Usa conectores para encadenar animaciones:

```
walk then jump then idle
run then stop
punch after kick
caminar luego saltar
```

**Conectores:** `then`, `after`, `→`, `luego`, `después`, `y luego`

### Transiciones

Añade modificadores para controlar la transición:

```
walk smoothly then jump      → transición suave (25 frames)
run then stop sharp          → transición rápida (6 frames)
```

También puedes ajustar manualmente en el Animation Mixer.

---

## Opciones

| Opción | Descripción |
|--------|-------------|
| **Auto-loop** | Hace la animación cíclica (seam blending) |
| **In-place** | Elimina desplazamiento del root |
| **New/Edit** | Crear nueva Action o reemplazar existente |

---

## Presets de transición

| Preset | Frames | Uso |
|--------|--------|-----|
| Smooth | 25 | Locomotion, movimientos continuos |
| Normal | 15 | Uso general |
| Sharp | 6 | Acciones rápidas, combate |
| Snap | 2 | Cortes directos |

---

## Estructura de archivos

```
ai_animator/
├── __init__.py
├── config.py
├── core/
│   ├── matcher.py      # Búsqueda semántica
│   ├── sequence.py     # Concatenación
│   ├── loop.py         # Auto-loop
│   ├── retarget.py     # Mapeo de huesos
│   └── blender.py      # Utilidades
├── operators/
│   └── generate.py
└── ui/
    └── panel.py
```

---

## Problemas comunes

**"No animations found"**
- Verificar ruta de biblioteca en configuración

**"Basic Search Mode"**
- Instalar dependencias de IA y reiniciar Blender

**Animación no se aplica**
- Verificar que hay un armature seleccionado

**Transiciones con saltos**
- Aumentar frames de transición o usar preset Smooth

---

## Requisitos

- Blender 4.0+
- Python 3.10+
- Biblioteca de animaciones FBX (Mixamo)

## Dependencias (instalación automática)

- sentence-transformers
- torch
- numpy

