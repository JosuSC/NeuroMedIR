"""
test_crawler.py — Pruebas unitarias para el módulo de crawling y scraping.

Tests de funcionalidad verificada:
1. Validación de URLs
2. Extracción de enlaces
3. Parsing de contenido
4. Sanitización de texto
5. Clasificación y validación de documentos
6. Manejo de errores en scraper
"""

import unittest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

from crawler.utils import is_valid_url, clean_text, normalize_url
from crawler.scraper import Scraper
from crawler.document_classifier import DocumentClassifier
from crawler.storage import Storage
from crawler.crawler import Crawler


class TestURLValidation(unittest.TestCase):
    """Tests para validación de URLs."""

    def test_valid_url_https(self):
        """Debe aceptar URLs HTTPS válidas."""
        self.assertTrue(is_valid_url("https://medlineplus.gov/healthtopics.html"))

    def test_valid_url_http(self):
        """Debe aceptar URLs HTTP válidas."""
        self.assertTrue(is_valid_url("http://example.com"))

    def test_invalid_url_no_scheme(self):
        """Debe rechazar URLs sin scheme."""
        self.assertFalse(is_valid_url("medlineplus.gov"))

    def test_invalid_url_no_netloc(self):
        """Debe rechazar URLs sin netloc."""
        self.assertFalse(is_valid_url("http://"))

    def test_invalid_url_empty(self):
        """Debe rechazar strings vacíos."""
        self.assertFalse(is_valid_url(""))

    def test_invalid_url_special_chars(self):
        """Debe rechazar URLs malformadas."""
        self.assertFalse(is_valid_url("not a url at all"))
        self.assertFalse(is_valid_url("://broken.com"))


class TestTextCleaning(unittest.TestCase):
    """Tests para limpieza de texto."""

    def test_clean_single_space(self):
        """Debe normalizar espacios múltiples."""
        result = clean_text("hello    world")
        self.assertEqual(result, "hello world")

    def test_clean_newlines(self):
        """Debe normalizar saltos de línea."""
        result = clean_text("hello\n\nworld")
        self.assertEqual(result, "hello world")

    def test_clean_tabs(self):
        """Debe normalizar tabulaciones."""
        result = clean_text("hello\t\tworld")
        self.assertEqual(result, "hello world")

    def test_clean_empty_string(self):
        """Debe manejar strings vacíos."""
        result = clean_text("")
        self.assertEqual(result, "")

    def test_clean_strip_whitespace(self):
        """Debe remover espacios al inicio y fin."""
        result = clean_text("  hello world  ")
        self.assertEqual(result, "hello world")


class TestURLNormalization(unittest.TestCase):
    """Tests para normalización de URLs."""

    def test_normalize_trailing_slash(self):
        """Debe unificar URL con/sin slash final."""
        self.assertEqual(
            normalize_url("https://site.com/page/"),
            normalize_url("https://site.com/page")
        )

    def test_normalize_lowercase_scheme_host(self):
        """Debe normalizar scheme y host a minúsculas."""
        self.assertEqual(
            normalize_url("HTTPS://SITE.COM/Page/"),
            "https://site.com/Page"
        )


class TestDocumentClassifier(unittest.TestCase):
    """Tests para clasificación y validación de documentos."""

    def test_validate_valid_document(self):
        """Debe aceptar documento con estructura válida."""
        doc = {
            "title": "Test Title",
            "content": "This is a test content with more than 100 characters to meet minimum length requirements for medical documents and health information which needs to be substantial nope",
            "source": "example.com",
            "url": "https://example.com/test"
        }
        is_valid, error = DocumentClassifier.validate_document_schema(doc)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_missing_title(self):
        """Debe rechazar documento sin título."""
        doc = {
            "content": "Test content with enough length to pass minimum requirement",
            "source": "example.com",
            "url": "https://example.com/test"
        }
        is_valid, error = DocumentClassifier.validate_document_schema(doc)
        self.assertFalse(is_valid)
        self.assertIn("title", error.lower())

    def test_validate_empty_content(self):
        """Debe rechazar documento con contenido vacío."""
        doc = {
            "title": "Test",
            "content": "",
            "source": "example.com",
            "url": "https://example.com/test"
        }
        is_valid, error = DocumentClassifier.validate_document_schema(doc)
        self.assertFalse(is_valid)

    def test_validate_content_too_short(self):
        """Debe rechazar contenido muy corto."""
        doc = {
            "title": "Test",
            "content": "Short",
            "source": "example.com",
            "url": "https://example.com/test"
        }
        is_valid, error = DocumentClassifier.validate_document_schema(doc)
        self.assertFalse(is_valid)
        self.assertIn("too short", error.lower())

    def test_infer_category_medlineplus(self):
        """Debe clasificar MedlinePlus como health_topic."""
        category = DocumentClassifier.infer_category(
            "medlineplus.gov",
            "This is a health topic about diabetes"
        )
        self.assertEqual(category, "health_topic")

    def test_infer_category_pubmed(self):
        """Debe clasificar PubMed como research_article."""
        category = DocumentClassifier.infer_category(
            "pubmed.ncbi.nlm.nih.gov",
            "This is a research article with an abstract"
        )
        self.assertEqual(category, "research_article")

    def test_infer_category_by_keywords(self):
        """Debe clasificar por palabras clave en contenido."""
        category = DocumentClassifier.infer_category(
            "unknown.com",
            "This article includes an abstract and authors"
        )
        self.assertEqual(category, "research_article")

    def test_enrich_document_valid(self):
        """Debe enriquecer documento válido con categoría."""
        doc = {
            "title": "Health Topic",
            "content": "Long enough content about medical topics and treatments for patients with various health conditions that need comprehensive medical information and support",
            "source": "medlineplus.gov",
            "url": "https://medlineplus.gov/health"
        }
        enriched = DocumentClassifier.enrich_document(doc)
        self.assertTrue(enriched["is_valid"])
        self.assertEqual(enriched["category"], "health_topic")
        self.assertIsNone(enriched["validation_error"])

    def test_enrich_document_invalid(self):
        """Debe marcar documento inválido con error."""
        doc = {
            "title": "Test",
            "content": "Short",
            "source": "example.com",
            "url": "https://example.com/test"
        }
        enriched = DocumentClassifier.enrich_document(doc)
        self.assertFalse(enriched["is_valid"])
        self.assertIsNotNone(enriched["validation_error"])


class TestScraper(unittest.TestCase):
    """Tests para scraping de contenido."""

    def setUp(self):
        self.scraper = Scraper(max_retries=2, backoff_base=1.5)

    def test_extract_links_simple(self):
        """Debe extraer enlaces simples de HTML."""
        html = """
        <html>
            <a href="https://example.com/page1">Link 1</a>
            <a href="/page2">Link 2</a>
        </html>
        """
        links = self.scraper.extract_links(html, "https://example.com")
        self.assertGreaterEqual(len(links), 1)
        self.assertIn("https://example.com/page2", links)

    def test_extract_links_no_links(self):
        """Debe retornar lista vacía si no hay enlaces."""
        html = "<html><body>No links here</body></html>"
        links = self.scraper.extract_links(html, "https://example.com")
        self.assertEqual(links, [])

    def test_extract_links_removes_fragments(self):
        """Debe remover fragmentos de URL."""
        html = '<html><a href="https://example.com/page#section">Link</a></html>'
        links = self.scraper.extract_links(html, "https://example.com")
        self.assertIn("https://example.com/page", links)
        self.assertNotIn("#", links[0] if links else "")

    def test_parse_content_valid(self):
        """Debe parsear contenido HTML válido."""
        html = """
        <html>
            <title>Test Page</title>
            <main>
                <p>This is test content with sufficient length to pass validation checks.</p>
            </main>
        </html>
        """
        result = self.scraper.parse_content(html, "https://example.com")
        self.assertIn("title", result)
        self.assertIn("content", result)
        self.assertIn("source", result)
        self.assertIn("url", result)

    def test_parse_content_removes_boilerplate(self):
        """Debe remover elementos de navegación y scripts."""
        html = """
        <html>
            <title>Test</title>
            <nav>Navigation</nav>
            <script>alert('test');</script>
            <main>Important content with enough length to be valid</main>
            <footer>Footer</footer>
        </html>
        """
        result = self.scraper.parse_content(html, "https://example.com")
        content = result["content"].lower()
        self.assertNotIn("script", content)
        self.assertNotIn("navigation", content)
        self.assertNotIn("footer", content)

    @patch('requests.get')
    def test_fetch_page_success(self, mock_get):
        """Debe retornar Response en caso de éxito."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test</html>"
        mock_get.return_value = mock_response

        result = self.scraper.fetch_page(
            "https://example.com",
            {"User-Agent": "Test"}
        )
        self.assertIsNotNone(result)

    @patch('requests.get')
    def test_fetch_page_timeout_retries(self, mock_get):
        """Debe reintentar en timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()

        result = self.scraper.fetch_page(
            "https://example.com",
            {"User-Agent": "Test"}
        )
        # Debe intentar max_retries veces
        self.assertEqual(mock_get.call_count, self.scraper.max_retries)
        self.assertIsNone(result)

    @patch('requests.get')
    def test_fetch_page_http_500_retries(self, mock_get):
        """Debe reintentar en errores 5xx."""
        import requests
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_get.return_value = mock_response

        result = self.scraper.fetch_page(
            "https://example.com",
            {"User-Agent": "Test"}
        )
        self.assertIsNone(result)


class TestStorage(unittest.TestCase):
    """Tests para almacenamiento de documentos."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = Storage(base_dir=self.temp_dir)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_save_processed_valid_document(self):
        """Debe guardar documento válido en carpeta categorizada."""
        doc = {
            "id": 1,
            "title": "Test Topic",
            "content": "This is test content with enough length to meet minimum requirements",
            "source": "medlineplus.gov",
            "url": "https://medlineplus.gov/test",
            "is_valid": True,
            "category": "health_topic",
            "validation_error": None
        }
        result = self.storage.save_processed(1, doc)
        self.assertTrue(result)
        # Verificar que existe el archivo
        filepath = os.path.join(self.storage.processed_dir, "health_topic", "doc_1.json")
        self.assertTrue(os.path.exists(filepath))

    def test_save_processed_invalid_document(self):
        """Debe guardar documento inválido en carpeta rejected."""
        doc = {
            "id": 2,
            "title": "Test",
            "content": "Short",
            "source": "example.com",
            "url": "https://example.com/test",
            "is_valid": False,
            "category": None,
            "validation_error": "Content too short"
        }
        result = self.storage.save_processed(2, doc)
        self.assertFalse(result)
        # Verificar que existe en rejected
        filepath = os.path.join(self.storage.rejected_dir, "rejected_doc_2.json")
        self.assertTrue(os.path.exists(filepath))

    def test_directory_structure_created(self):
        """Debe crear estructura de directorios esperada."""
        categories = ["health_topic", "research_article", "health_guideline", "news", "generic_content"]
        for cat in categories:
            cat_dir = os.path.join(self.storage.processed_dir, cat)
            self.assertTrue(os.path.isdir(cat_dir))

    def test_rejected_directory_exists(self):
        """Debe crear directorio para documentos rechazados."""
        self.assertTrue(os.path.isdir(self.storage.rejected_dir))


class TestCrawlerStart(unittest.TestCase):
    """Tests end-to-end del ciclo principal Crawler.start()."""

    @patch("crawler.crawler.time.sleep", return_value=None)
    @patch.object(Crawler, "_can_fetch", return_value=True)
    def test_start_processes_valid_document(self, _, __):
        """Debe procesar una URL válida y guardar documento procesado."""
        crawler = Crawler(
            seed_urls=["https://example.com/health"],
            max_pages=1,
            max_depth=0,
            delay_seconds=0,
        )

        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_response.text = "<html><body>ok</body></html>"

        crawler.scraper = MagicMock()
        crawler.scraper.fetch_page.return_value = mock_response
        crawler.scraper.parse_content.return_value = {
            "title": "Doc",
            "content": "contenido medico suficientemente largo para pasar validacion " * 3,
            "source": "example.com",
            "url": "https://example.com/health",
            "is_valid": True,
            "validation_error": None,
            "category": "health_topic",
        }
        crawler.scraper.extract_links.return_value = []

        crawler.storage = MagicMock()
        crawler.storage.save_processed.return_value = True

        crawler.start()

        self.assertEqual(crawler.documents_valid, 1)
        self.assertEqual(crawler.documents_rejected, 0)
        self.assertEqual(crawler.documents_crawled, 1)
        crawler.storage.save_processed.assert_called_once()

    @patch("crawler.crawler.time.sleep", return_value=None)
    @patch.object(Crawler, "_can_fetch", return_value=True)
    def test_start_counts_rejected_on_parse_error(self, _, __):
        """Si parse_content falla, debe registrar rechazo y continuar sin crashear."""
        crawler = Crawler(
            seed_urls=["https://example.com/fail"],
            max_pages=1,
            max_depth=0,
            delay_seconds=0,
        )

        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "<html><body>broken</body></html>"

        crawler.scraper = MagicMock()
        crawler.scraper.fetch_page.return_value = mock_response
        crawler.scraper.parse_content.side_effect = ValueError("parser failed")
        crawler.scraper.extract_links.return_value = []

        crawler.storage = MagicMock()

        crawler.start()

        self.assertEqual(crawler.documents_valid, 0)
        self.assertEqual(crawler.documents_rejected, 1)
        self.assertEqual(crawler.documents_crawled, 0)
        crawler.storage.save_processed.assert_not_called()

    @patch("crawler.crawler.time.sleep", return_value=None)
    @patch.object(Crawler, "_can_fetch", return_value=True)
    def test_start_saves_raw_when_enabled(self, _, __):
        """Debe guardar HTML crudo cuando save_raw_html=True."""
        crawler = Crawler(
            seed_urls=["https://example.com/raw"],
            max_pages=1,
            max_depth=0,
            delay_seconds=0,
            save_raw_html=True,
        )

        mock_response = MagicMock()
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "<html><body>raw html</body></html>"

        crawler.scraper = MagicMock()
        crawler.scraper.fetch_page.return_value = mock_response
        crawler.scraper.parse_content.return_value = {
            "title": "Doc Raw",
            "content": "contenido medico suficientemente largo para pasar validacion " * 3,
            "source": "example.com",
            "url": "https://example.com/raw",
            "is_valid": True,
            "validation_error": None,
            "category": "health_topic",
        }
        crawler.scraper.extract_links.return_value = []

        crawler.storage = MagicMock()
        crawler.storage.save_processed.return_value = True

        crawler.start()

        crawler.storage.save_raw.assert_called_once()
        crawler.storage.save_processed.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
