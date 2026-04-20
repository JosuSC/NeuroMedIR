import unittest

from crawler.language import detect_language
from crawler.quality import CorpusQualityGate


class TestLanguage(unittest.TestCase):
    def test_detect_english(self):
        text = "The patient receives treatment for chronic heart disease and health monitoring."
        self.assertEqual(detect_language(text), "en")

    def test_detect_spanish(self):
        text = "El paciente recibe tratamiento para enfermedad cronica y seguimiento de salud."
        self.assertEqual(detect_language(text), "es")


class TestQualityGate(unittest.TestCase):
    def setUp(self):
        self.gate = CorpusQualityGate(min_content_chars=50)
        self.base_doc = {
            "title": "Sample",
            "content": "This is a long enough medical content body used for tests only." * 2,
            "source": "MedlinePlus",
            "url": "https://example.org/doc-1",
            "category": "health_topic",
            "language": "en",
        }

    def test_valid_document(self):
        result = self.gate.validate(dict(self.base_doc))
        self.assertTrue(result.is_valid)

    def test_duplicate_url(self):
        self.assertTrue(self.gate.validate(dict(self.base_doc)).is_valid)
        result = self.gate.validate(dict(self.base_doc))
        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "duplicate_url")

    def test_duplicate_content(self):
        self.assertTrue(self.gate.validate(dict(self.base_doc)).is_valid)
        doc2 = dict(self.base_doc)
        doc2["url"] = "https://example.org/doc-2"
        result = self.gate.validate(doc2)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.reason, "duplicate_content")


if __name__ == "__main__":
    unittest.main()
