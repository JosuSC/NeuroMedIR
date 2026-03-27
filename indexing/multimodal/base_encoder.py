from abc import ABC, abstractmethod
import numpy as np
from typing import Union, List

class BaseEncoder(ABC):
    """
    Abstract Base Class for Multimodal Encoders.
    Forces all future encoders (Audio, Image, Video) to implement the 'encode' method
    to guarantee a uniform embedding pipeline.
    """
    
    @abstractmethod
    def encode(self, inputs: Union[str, List[str], bytes, List[bytes]]) -> np.ndarray:
        """
        Receives input data and returns a numpy array representing the dense vectors.
        Output shape should be (num_inputs, embedding_dimension).
        """
        pass
