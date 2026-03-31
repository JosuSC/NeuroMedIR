import json
import os
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class Storage:
    # Por defecto, guarda en una carpeta "data" en la raíz (ej. desde donde se ejecuta main.py)
    def __init__(self, base_dir: str = "data"):
        self.raw_dir = os.path.join(base_dir, "raw")
        self.processed_dir = os.path.join(base_dir, "processed")
        self.rejected_dir = os.path.join(base_dir, "rejected")
        
        # Asegura que los directorios existan
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.rejected_dir, exist_ok=True)
        
        # Crear subdirectorios por categoría para documentos válidos
        self.category_dirs = {}
        self._init_category_dirs()
        
    def _init_category_dirs(self):
        """Crea subdirectorios para cada categoría esperada."""
        categories = ["health_topic", "research_article", "health_guideline", "news", "generic_content"]
        for cat in categories:
            cat_dir = os.path.join(self.processed_dir, cat)
            os.makedirs(cat_dir, exist_ok=True)
            self.category_dirs[cat] = cat_dir
            
    def save_raw(self, doc_id: int, data: Dict[str, Any]):
        """Guarda los datos en crudo (ej. HTML original) si fuese necesario."""
        filepath = os.path.join(self.raw_dir, f"doc_{doc_id}.json")
        self._save_json(filepath, data)
        
    def save_processed(self, doc_id: int, data: Dict[str, Any]) -> bool:
        """
        Guarda la información extraída y limpia, validando previamente.
        
        Si el documento es válido: se guarda en processed/{category}/
        Si es inválido: se guarda en rejected/ con motivo del rechazo.
        
        Returns:
            True si se guardó exitosamente, False si fue rechazado.
        """
        # Verificar campos obligatorios de validación
        is_valid = data.get("is_valid", False)
        category = data.get("category", None)
        validation_error = data.get("validation_error", None)
        
        if not is_valid:
            # Guardar en rejected con el motivo
            self._save_rejected(doc_id, data, validation_error)
            logger.warning(f"Documento {doc_id} rechazado: {validation_error}")
            return False
        
        # Documento válido: guardar en carpeta de categoría
        if category and category in self.category_dirs:
            filepath = os.path.join(self.category_dirs[category], f"doc_{doc_id}.json")
        else:
            # Fallback a processed root si categoría no existe
            category = category or "unknown"
            logger.warning(f"Categoría '{category}' no reconocida para doc {doc_id}, guardando en root")
            filepath = os.path.join(self.processed_dir, f"doc_{doc_id}.json")
        
        self._save_json(filepath, data)
        logger.info(f"Documento {doc_id} guardado en categoría '{category}'")
        return True
    
    def _save_rejected(self, doc_id: int, data: Dict[str, Any], reason: str = None):
        """Guarda un documento rechazado con el motivo."""
        filepath = os.path.join(self.rejected_dir, f"rejected_doc_{doc_id}.json")
        data_with_reason = {**data, "rejection_reason": reason}
        self._save_json(filepath, data_with_reason)
        
    def _save_json(self, filepath: str, data: Dict[str, Any]):
        """Helper interno para guardar diccionarios como JSON."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # ensure_ascii=False permite guardar acentos y caracteres UTF-8 correctamente
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Error al guardar {filepath}: {e}")
            raise
