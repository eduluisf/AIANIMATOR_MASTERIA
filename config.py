"""
AI Animator - Configuration
Constantes, paths y configuración global
"""

import os

# Paths
ADDON_DIR = os.path.dirname(os.path.realpath(__file__))
ANIM_FOLDER = os.path.join(ADDON_DIR, "anims")
CACHE_FILE = os.path.join(ADDON_DIR, "embeddings_cache.json")

# Modelo de embeddings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Umbrales de confianza
MIN_CONFIDENCE_SEMANTIC = 0.3
LOW_CONFIDENCE_THRESHOLD = 0.6

# Configuración de blending por defecto
DEFAULT_ACTION_WEIGHT = 0.7
DEFAULT_EMOTION_WEIGHT = 0.3

# Auto-loop defaults
DEFAULT_LOOP_BLEND_FRAMES = 10
LOOP_SEARCH_WINDOW = 30

# Modificadores de velocidad (palabra: factor)
SPEED_MODIFIERS = {
    # Inglés
    'fast': 1.5,
    'quick': 1.4,
    'rapid': 1.5,
    'slow': 0.6,
    'slowly': 0.6,
    'very fast': 2.0,
    'very slow': 0.4,
    # Español
    'rápido': 1.5,
    'rápida': 1.5,
    'lento': 0.6,
    'lenta': 0.6,
    'muy rápido': 2.0,
    'muy lento': 0.4,
}

# Modificadores de intensidad/amplitud
INTENSITY_MODIFIERS = {
    # Inglés
    'big': 1.3,
    'large': 1.3,
    'exaggerated': 1.5,
    'small': 0.7,
    'subtle': 0.6,
    'tiny': 0.5,
    'intense': 1.4,
    # Español
    'grande': 1.3,
    'pequeño': 0.7,
    'suave': 0.7,
    'intenso': 1.4,
    'exagerado': 1.5,
}

# Emociones reconocidas
EMOTIONS = [
    # Inglés
    'happy', 'sad', 'angry', 'tired', 'excited', 'scared', 'nervous',
    'confident', 'shy', 'proud', 'defeated', 'relaxed', 'tense',
    'bored', 'surprised', 'confused', 'determined', 'playful',
    # Español
    'feliz', 'triste', 'enojado', 'cansado', 'emocionado', 'asustado',
    'nervioso', 'confiado', 'tímido', 'orgulloso', 'derrotado',
    'relajado', 'tenso', 'aburrido', 'sorprendido', 'confundido',
]

# Acciones base reconocidas
ACTIONS = [
    # Inglés - Locomoción
    'walk', 'run', 'jog', 'sprint', 'jump', 'hop', 'skip', 'crawl',
    'crouch', 'sneak', 'strafe', 'climb', 'fall', 'land', 'roll',
    # Inglés - Estados
    'idle', 'stand', 'sit', 'lie', 'kneel', 'lean',
    # Inglés - Acciones
    'wave', 'point', 'grab', 'throw', 'catch', 'push', 'pull',
    'dance', 'clap', 'bow', 'nod', 'shake',
    # Inglés - Combate
    'fight', 'attack', 'punch', 'kick', 'block', 'dodge',
    'slash', 'stab', 'shoot', 'aim', 'reload',
    # Inglés - Otros
    'talk', 'laugh', 'cry', 'yawn', 'stretch', 'drink', 'eat',
    # Español
    'caminar', 'correr', 'saltar', 'sentarse', 'pararse', 'bailar',
    'pelear', 'atacar', 'patear', 'golpear', 'agacharse', 'rodar',
    'saludar', 'aplaudir', 'reír', 'llorar', 'hablar',
]
