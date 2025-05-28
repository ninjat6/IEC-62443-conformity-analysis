import unittest
from pathlib import Path
import sys

# Add the project root to the Python path
# This assumes 'tests' is a top-level directory in the project
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from conformity_analysis_module.core.file_processor import FileProcessor
from conformity_analysis_module.utils.logger import logger # For checking logs if needed, though direct log assertion is optional

# Define the path to the fixtures directory
# Assumes this test file is in tests/core/ and fixtures are in tests/fixtures/
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

class TestFileProcessor(unittest.TestCase):

    def test_extract_text_from_valid_docx(self):
        """Test extracting text from a valid DOCX file."""
        file_path = FIXTURES_DIR / "dummy.docx"
        self.assertTrue(file_path.exists(), f"Fixture file not found: {file_path}")
        snippets = FileProcessor.extract_text_snippets(file_path)
        self.assertEqual(snippets, ["Hello DOCX"])

    def test_extract_text_from_empty_docx(self):
        """Test extracting text from an empty DOCX file."""
        file_path = FIXTURES_DIR / "empty.docx"
        self.assertTrue(file_path.exists(), f"Fixture file not found: {file_path}")
        snippets = FileProcessor.extract_text_snippets(file_path)
        self.assertEqual(snippets, [])

    def test_extract_text_from_valid_xlsx(self):
        """Test extracting text from a valid XLSX file."""
        file_path = FIXTURES_DIR / "dummy.xlsx"
        self.assertTrue(file_path.exists(), f"Fixture file not found: {file_path}")
        snippets = FileProcessor.extract_text_snippets(file_path)
        self.assertEqual(snippets, ["Hello XLSX"])

    def test_extract_text_from_valid_pdf(self):
        """Test extracting text from a valid PDF file."""
        file_path = FIXTURES_DIR / "dummy.pdf"
        self.assertTrue(file_path.exists(), f"Fixture file not found: {file_path}")
        snippets = FileProcessor.extract_text_snippets(file_path)
        # PyPDF2 might extract text with extra newlines depending on PDF structure
        # For "Hello PDF" written simply, it should be straightforward.
        # If it includes line breaks, adjust assertion. Example: ["Hello PDF", ""]
        self.assertEqual(snippets, ["Hello PDF"])


    def test_extract_text_from_unsupported_file_type(self):
        """Test extracting text from an unsupported file type (TXT)."""
        file_path = FIXTURES_DIR / "dummy.txt"
        self.assertTrue(file_path.exists(), f"Fixture file not found: {file_path}")
        snippets = FileProcessor.extract_text_snippets(file_path)
        self.assertEqual(snippets, [])
        # Optionally, check logs for warning if logger is accessible and mockable
        # For now, focusing on return value as per instructions.

    def test_extract_text_from_non_existent_file(self):
        """Test extracting text from a non-existent file."""
        file_path = FIXTURES_DIR / "non_existent_file.docx"
        # Ensure it doesn't exist, though it shouldn't by name
        self.assertFalse(file_path.exists(), f"File unexpectedly found: {file_path}")
        
        # We need to test the specific extractor if we want to check its error handling,
        # or FileProcessor.extract_text_snippets if we expect it to handle it.
        # FileProcessor.extract_text_snippets itself doesn't directly open the file
        # before passing to specific extractors. The specific extractors (e.g., extract_text_from_docx)
        # are responsible for handling file open errors.
        
        # Test case for DOCX:
        snippets_docx = FileProcessor.extract_text_from_docx(file_path)
        self.assertEqual(snippets_docx, [])
        
        # Test case for XLSX:
        snippets_xlsx = FileProcessor.extract_text_from_xlsx(file_path)
        self.assertEqual(snippets_xlsx, [])
        
        # Test case for PDF:
        snippets_pdf = FileProcessor.extract_text_from_pdf(file_path)
        self.assertEqual(snippets_pdf, [])

    def test_extract_text_snippets_non_existent_file(self):
        """Test extract_text_snippets with a non-existent file."""
        file_path = FIXTURES_DIR / "non_existent_file.pdf" # Using .pdf to pass extension check
        self.assertFalse(file_path.exists(), f"File unexpectedly found: {file_path}")
        snippets = FileProcessor.extract_text_snippets(file_path)
        self.assertEqual(snippets, [])


if __name__ == '__main__':
    # This allows running the tests directly from the command line
    # Add project root to sys.path to allow imports if run directly
    # Note: The sys.path modification at the top should handle module discovery for FileProcessor
    unittest.main()
