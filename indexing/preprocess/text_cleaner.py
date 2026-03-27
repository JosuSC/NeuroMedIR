import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from bs4 import BeautifulSoup

class TextCleaner:
    def __init__(self):
        # We ensure standard components are downloaded
        self._download_nltk_data()
        
        # Load stop words for English and Spanish
        self.stop_words_en = set(stopwords.words('english'))
        self.stop_words_es = set(stopwords.words('spanish'))
        self.stop_words = self.stop_words_en.union(self.stop_words_es)

    def _download_nltk_data(self):
        """Downloads required NLTK resources silently."""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            # Support for updated punkt paths
            nltk.download('punkt_tab', quiet=True)

    def clean_html(self, raw_html: str) -> str:
        """Removes residual HTML if any."""
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text(separator=" ")

    def normalize(self, text: str) -> str:
        """Lowercases and cleans up extra whitespaces and special characters."""
        if not text:
            return ""
        text = text.lower()
        # Keep alphanumeric, some basic punctuation like dot/comma may be removed for pure lexical BM25
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def tokenize_and_remove_stopwords(self, text: str) -> list[str]:
        """Tokenizes text and removes standard stop words for EN/ES."""
        tokens = word_tokenize(text)
        cleaned_tokens = [t for t in tokens if t not in self.stop_words and len(t) > 1]
        return cleaned_tokens

    def preprocess_for_lexical(self, text: str) -> list[str]:
        """
        Complete pipeline for BM25: HTML clean -> Normalize -> Tokenize -> Remove Stopwords.
        """
        text = self.clean_html(text)
        text = self.normalize(text)
        return self.tokenize_and_remove_stopwords(text)

    def preprocess_for_semantic(self, text: str) -> str:
        """
        Complete pipeline for Encoders: HTML clean -> Normalize.
        Keeps stopwords as models like BERT need context.
        """
        text = self.clean_html(text)
        # We don't remove punctuation aggressively for BERT, but for safety we clean spaces
        text = re.sub(r'\s+', ' ', text).strip()
        return text
