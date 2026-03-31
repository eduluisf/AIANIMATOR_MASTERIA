# AI Animator - Blender Add-on

Add-on para Blender que genera animaciones 3D a partir de instrucciones en lenguaje natural.

## Instalación

### 1. Instalar el add-on

- Clonar o descargar este repositorio
- Copiar la carpeta `ai_animator` en la carpeta de addons de Blender:
  - **Mac:** `~/Library/Application Support/Blender/<version>/scripts/addons/`
  - **Windows:** `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\`
  - **Linux:** `~/.config/blender/<version>/scripts/addons/`
- En Blender: `Edit` → `Preferences` → `Add-ons` → Buscar "AI Animator" y activarlo

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

## Mixing de animaciones

Cuando el prompt combina una acción con una emoción, el sistema mezcla dos animaciones:

```
happy walk       → mezcla "walk" (70%) + "happy" (30%)
sad idle         → mezcla "idle" (70%) + "sad" (30%)
```

Los modificadores de velocidad e intensidad se aplican sobre el resultado:

```
clap fast        → animación de clap a 1.5x velocidad
jump slow        → animación de jump a 0.6x velocidad
big wave         → wave con amplitud aumentada
subtle dance     → dance con amplitud reducida
```

---

## Auto-loop

El auto-loop convierte cualquier animación en cíclica usando cross-fade sobre toda la duración de la animación. Se activa/desactiva desde el panel con el checkbox "Auto Loop".

---

## Opciones

| Opción | Descripción |
|--------|-------------|
| **Auto-loop** | Hace la animación cíclica usando toda la animación |
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

## Logs y depuración

Para ver los logs del addon en tiempo real, abrir Blender desde la terminal:

```bash
# Mac
/Applications/Blender.app/Contents/MacOS/Blender

# Windows
"C:\Program Files\Blender Foundation\Blender <version>\blender.exe"

# Linux
blender
```

Los logs muestran qué animaciones se importan, mezclan y procesan en cada generación.

---

## Estructura de archivos

```
ai_animator/
├── __init__.py
├── config.py
├── core/
│   ├── matcher.py      # Búsqueda semántica
│   ├── blender.py      # Motion blending (mixing de animaciones)
│   ├── sequence.py     # Concatenación de secuencias
│   ├── loop.py         # Auto-loop (full animation cross-fade)
│   ├── retarget.py     # Mapeo de huesos
│   ├── parser.py       # Parser de prompts
│   └── transform.py    # Transformaciones semánticas
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

