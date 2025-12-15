"""
AI Animator - Animation Matcher con Mixer support
"""

import os
import json
from ..config import ANIM_FOLDER, CACHE_FILE, EMBEDDING_MODEL

class AnimationMatcher:
    def __init__(self):
        self.model = None
        self.cache = {}
        self.animations = []
        self.semantic_available = False
        self._init_model()
        self._load_cache()
        self.scan_animations()
    
    def _init_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            self.semantic_available = True
            print("✓ AI Semantic Model loaded")
        except:
            self.semantic_available = False
    
    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    self.cache = json.load(f)
            except:
                self.cache = {}
    
    def _save_cache(self):
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f)
        except:
            pass
    
    def scan_animations(self):
        self.animations = []
        if not os.path.exists(ANIM_FOLDER):
            return
        for root, dirs, files in os.walk(ANIM_FOLDER):
            for f in files:
                if f.lower().endswith(".fbx"):
                    name = os.path.splitext(f)[0].replace("_", " ").replace("-", " ")
                    self.animations.append({
                        'name': name,
                        'path': os.path.join(root, f),
                        'filename': f
                    })
        print(f"✓ {len(self.animations)} animations")
    
    def clear_cache(self):
        self.cache = {}
        self._save_cache()
    
    def search_top(self, query: str, top_k: int = 5) -> list:
        """Busca y retorna top_k resultados con scores"""
        print(f"\n{'='*50}")
        print(f"  SEARCH: '{query}'")
        print(f"{'='*50}")
        
        if not self.semantic_available or not self.model:
            return self._basic_search_top(query, top_k)
        
        try:
            import numpy as np
            query_emb = self.model.encode(query.lower())
            
            anim_embs = []
            for anim in self.animations:
                key = anim['name']
                if key in self.cache:
                    anim_embs.append(self.cache[key])
                else:
                    emb = self.model.encode(anim['name']).tolist()
                    self.cache[key] = emb
                    anim_embs.append(emb)
            
            anim_embs = np.array(anim_embs)
            sims = np.dot(anim_embs, query_emb)
            norms = np.linalg.norm(anim_embs, axis=1) * np.linalg.norm(query_emb)
            sims = sims / (norms + 1e-8)
            
            indices = np.argsort(sims)[::-1][:top_k]
            
            results = []
            print(f"\n  Top {top_k}:")
            for i, idx in enumerate(indices):
                anim = self.animations[idx]
                score = float(sims[idx])
                print(f"    {i+1}. [{score:.3f}] {anim['name']}")
                results.append((anim, score))
            
            self._save_cache()
            return results
        except Exception as e:
            print(f"  Error: {e}")
            return self._basic_search_top(query, top_k)
    
    def _basic_search_top(self, query: str, top_k: int) -> list:
        words = query.lower().split()
        scored = []
        for anim in self.animations:
            score = sum(1 for w in words if w in anim['name'].lower())
            if score > 0:
                scored.append((anim, score / len(words)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    
    def find_animation(self, query: str) -> dict:
        results = self.search_top(query, top_k=1)
        if results:
            anim, score = results[0]
            return {'animation': anim, 'confidence': score, 'method': 'semantic'}
        return None
    
    def find_animations_for_blend(self, parsed_prompt: dict) -> list:
        from ..config import DEFAULT_ACTION_WEIGHT, DEFAULT_EMOTION_WEIGHT
        anims = []
        if parsed_prompt['is_compound'] and parsed_prompt['actions'] and parsed_prompt['emotions']:
            r = self.find_animation(' '.join(parsed_prompt['actions']))
            if r: anims.append((r, DEFAULT_ACTION_WEIGHT))
            r = self.find_animation(' '.join(parsed_prompt['emotions']))
            if r: anims.append((r, DEFAULT_EMOTION_WEIGHT))
        else:
            r = self.find_animation(parsed_prompt['original'])
            if r: anims.append((r, 1.0))
        return anims
    
    def get_stats(self) -> dict:
        return {
            'total_animations': len(self.animations),
            'semantic_available': self.semantic_available,
            'embedding_cache_size': len(self.cache),
        }
