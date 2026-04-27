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

- Click en **Install AI Dependencies**
- Esperar 1-4 minutos
- Reiniciar Blender

Sin las dependencias, el add-on funciona en modo básico (búsqueda por palabras clave).

#### Detalles del instalador

El botón ahora hace varias cosas para evitar romper Blender en Windows:

- Detecta la versión de **numpy** que ya trae Blender y la pinea (`numpy==X.Y.Z`) para que pip no la actualice y rompa otros add-ons (auto_rig_pro, etc.).
- Verifica que la carpeta `site-packages` de Blender sea escribible. Si no lo es (Blender en `Program Files`), aborta con un mensaje pidiéndote abrir Blender como Administrador.
- Detecta si hay paquetes "fantasma" en `%APPDATA%\Python\PythonXY\site-packages` que vayan a tapar a los de Blender, y avisa.
- Fuerza `--target` a la carpeta correcta y `PYTHONNOUSERSITE=1` para que pip no instale en `AppData`.
- Verifica el import después de instalar y, si torch falla con `c10.dll`, te indica que falta el **Microsoft Visual C++ Redistributable**.

**Si en Windows ves "Defaulting to user installation":** cerrá Blender, abrílo como Administrador y volvé a darle al botón.

---

## Uso básico

1. Seleccionar un armature (rig Mixamo o compatible)
2. Escribir descripción en el campo de texto
3. Click en **Search** (lupa)
4. Seleccionar animación de los resultados
5. Click en **Generate**

El botón final cambia de label según el tipo de prompt detectado:

- **Generate** → animación única
- **Generate Sequence** → secuencia (con `then`, `luego`, etc.)
- **Generate Overlay** → overlay simultáneo (con `while`, `mientras`, etc.)

También existe **Quick Generate** que hace todo el flujo automático sin pasar por el picker (elige el primer match de cada parte).

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

## Overlay (acciones simultáneas)

Para combinar dos animaciones que ocurren al mismo tiempo —brazos haciendo una cosa mientras las piernas hacen otra— usa los conectores de **simultaneidad**:

```
clap while walk          → camina + aplaude
wave mientras correr     → corre + saluda con la mano
shoot while sprint       → sprint + apuntar/disparar
bow while idle           → idle + reverencia con torso
```

**Conectores soportados:** `while`, `mientras`, `al mismo tiempo que`, `a la vez que`, `y al mismo tiempo`, `at the same time as`.

### Cómo funciona

A diferencia del blend (promedio ponderado en todo el cuerpo), el overlay reemplaza solo las **fcurves de los huesos pertinentes** y deja el resto intactas. El sistema decide qué huesos toca el overlay a partir de `ACTION_BONE_MAPPING` (clap → ARMS, bow → SPINE, nod → HEAD, etc.).

### Asignación inteligente del root

Cuando una de las dos partes es **locomoción** (walk, run, jog, sprint, jump, etc.), automáticamente se vuelve la **base** —sin importar el orden del `while`— para que el root/hips siempre venga del lado que de verdad mueve al personaje.

```
clap while walk   ↔   walk while clap     # mismo resultado: camina y aplaude
wave while run    ↔   run while wave      # mismo resultado: corre y saluda
```

Si BERT está activo, también detecta sinónimos:

```
clap while strolling     → strolling es la base
wave mientras marchando  → marchando es la base
```

### UI

Cuando detecta `while`/`mientras`, el panel muestra dos grupos:

```
► OVERLAY: CLAP
  [✓] Hand Clap
  [ ] Standing Clap
  🔗 while
► BASE: WALK
  [✓] Walking Forward
  [ ] Walk Cycle
  [ Generate Overlay ]
```

Podés tildar manualmente qué animación querés de cada lado, igual que en el modo secuencia.

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
│   ├── matcher.py      # Búsqueda semántica (sentence-BERT)
│   ├── blender.py      # Motion blending + overlay por hueso
│   ├── sequence.py     # Secuencias + detección de overlay (while/mientras)
│   ├── loop.py         # Auto-loop (full animation cross-fade)
│   ├── retarget.py     # Mapeo de huesos
│   ├── parser.py       # Parser de prompts
│   └── transform.py    # Modificadores semánticos + locomotion scoring
├── operators/
│   ├── generate.py     # Quick Generate (auto)
│   └── utils.py        # Install AI Dependencies (numpy-safe)
└── ui/
    └── panel.py        # Panel + picker (Search → Generate / Sequence / Overlay)
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

**Overlay con footskate (los pies patinan)**
- Indicar bien la locomoción: `clap while walk` (no `clap while standing`).
- Si BERT está activo, también detecta sinónimos como `strolling`, `jogging`, etc.

**Windows: "Defaulting to user installation because normal site-packages is not writeable"**
- Cerrar Blender → abrirlo como Administrador → Install AI Dependencies de nuevo.

**Windows: "Error loading c10.dll" (torch no carga)**
- Falta el Microsoft Visual C++ Redistributable. Instalarlo desde:
  https://aka.ms/vs/17/release/vc_redist.x64.exe → reiniciar Windows.

**Windows: numpy "multiarray" import failed**
- Hay un numpy "fantasma" en `%APPDATA%\Python\PythonXY\site-packages` que tapa al de Blender. Borrar esa carpeta y reinstalar como Administrador.

---

## Requisitos

- Blender 4.0+
- Python 3.10+
- Biblioteca de animaciones FBX (Mixamo)

## Dependencias (instalación automática)

- sentence-transformers
- torch
- numpy

