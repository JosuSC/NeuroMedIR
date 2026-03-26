import json
import os
from typing import Dict, Any

class Storage:
    # Por defecto, guarda en una carpeta "data" en la raíz (ej. desde donde se ejecuta main.py)
    def __init__(self, base_dir: str = "data"):
        self.raw_dir = os.path.join(base_dir, "raw")
        self.processed_dir = os.path.join(base_dir, "processed")
        
        # Asegura que los directorios existan
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
    def save_raw(self, doc_id: int, data: Dict[str, Any]):
        """Guarda los datos en crudo (ej. HTML original) si fuese necesario."""
        filepath = os.path.join(self.raw_dir, f"doc_{doc_id}.json")
        self._save_json(filepath, data)
        
    def save_processed(self, doc_id: int, data: Dict[str, Any]):
        """Guarda la información extraída y limpia."""
        filepath = os.path.join(self.processed_dir, f"doc_{doc_id}.json")
        self._save_json(filepath, data)
        
    def _save_json(self, filepath: str, data: Dict[str, Any]):
        """Helper interno para guardar diccionarios como JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            # ensure_ascii=False permite guardar acentos y caracteres UTF-8 correctamente
            json.dump(data, f, ensure_ascii=False, indent=2)
