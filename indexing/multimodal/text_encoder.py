import numpy as np
from typing import Union, List
from sentence_transformers import SentenceTransformer
from .base_encoder import BaseEncoder

class TextEncoder(BaseEncoder):
    """
    Implementation of the Multimodal BaseEncoder specifically for bilingual text.
    Uses Sentence Transformers to generate embeddings.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, inputs: Union[str, List[str]]) -> np.ndarray:
        """
        Encodes one or multiple text strings into dense embeddings.
        Returns shape (batch_size, embedding_dim).
        """
        if isinstance(inputs, str):
            inputs = [inputs]
            
        embeddings = self.model.encode(
            inputs, 
            convert_to_numpy=True,
            show_progress_bar=False,
            device='cpu'  # Defaulting to CPU for general execution, can be changed to 'cuda'
        )
        return embeddings
