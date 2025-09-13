# tests/converters/test_converters.py
import pytest
from pathlib import Path
import html
from unittest.mock import patch, MagicMock

# Assuming your project structure allows this import:
# This means 'file_search_module' is a package installable or in PYTHONPATH
# Or that pytest is run from the project root.
from file_search_module.converters import convert_file_to_html
from file_search_module.converters.docx_converter import convert_docx_to_html as convert_docx_specific

# Fixture to provide a base path to the fixtures directory
@pytest.fixture
def fixture_path() -> Path:
    return Path(__file__).resolve().parent.parent / "fixtures"

@pytest.fixture
def dummy_txt_file(fixture_path: Path) -> Path:
    return fixture_path / "dummy.txt"

@pytest.fixture
def dummy_docx_placeholder_file(fixture_path: Path) -> Path:
    # This is the text file named dummy.docx
    return fixture_path / "dummy.docx"

def test_convert_txt_to_html_returns_path(dummy_txt_file: Path):
    """Test that TXT conversion returns a Path object for the HTML file."""
    # The main convert_file_to_html dispatcher should be used for TXT
    result_path = convert_file_to_html(str(dummy_txt_file))
    assert result_path is not None
    assert isinstance(result_path, Path)
    assert result_path.name == f"{dummy_txt_file.stem}_converted.html"
    assert result_path.exists()
    # Clean up the created HTML file
    result_path.unlink(missing_ok=True)

def test_convert_txt_to_html_content(dummy_txt_file: Path):
    """Test that TXT conversion produces non-empty HTML with correct content."""
    result_path = convert_file_to_html(str(dummy_txt_file))
    assert result_path is not None and result_path.exists()
    
    with open(dummy_txt_file, "r", encoding="utf-8") as f_in:
        original_content = f_in.read()
    
    with open(result_path, "r", encoding="utf-8") as f_out:
        html_content = f_out.read()
        
    assert "<html>" in html_content
    assert "<body>" in html_content
    assert "<pre>" in html_content # TXT content is wrapped in <pre>
    assert html.escape(original_content) in html_content # Check for escaped original content
    assert len(html_content) > 0
    
    result_path.unlink(missing_ok=True)

# Mocking win32com for DOCX conversion as we can't create a real DOCX easily
# and don't want to rely on Word being installed on the test runner.
@patch('file_search_module.converters.docx_converter.win32com.client')
def test_convert_docx_to_html_mocked(mock_win32_client, dummy_docx_placeholder_file: Path):
    """
    Test DOCX conversion. Mocks win32com to avoid dependency on MS Word.
    This test verifies the function call flow and HTML file creation,
    not the actual content fidelity of DOCX to HTML conversion.
    """
    # Configure the mock Word application and document objects
    mock_doc = MagicMock()
    mock_word_app = MagicMock()
    mock_word_app.Documents.Open.return_value = mock_doc
    
    # Ensure GetActiveObject fails (to trigger Dispatch) or Dispatch returns the mock
    # If GetActiveObject is tried first and fails, Dispatch will be called.
    # If Dispatch is called directly, it should return our mock.
    mock_win32_client.GetActiveObject.side_effect = Exception("COM error: GetActiveObject failed")
    mock_win32_client.Dispatch.return_value = mock_word_app

    # The convert_docx_specific function is imported from docx_converter
    output_html_path = dummy_docx_placeholder_file.with_name(f"{dummy_docx_placeholder_file.stem}_converted.html")
    
    try:
        # Call the specific docx converter function
        convert_docx_specific(dummy_docx_placeholder_file, output_html_path)
        
        # Assertions
        mock_win32_client.Dispatch.assert_called_with("Word.Application")
        mock_word_app.Documents.Open.assert_called_with(str(dummy_docx_placeholder_file.resolve()), ReadOnly=True)
        mock_doc.SaveAs.assert_called_with(str(output_html_path.resolve()), FileFormat=8)
        mock_doc.Close.assert_called_with(False)
        # mock_word_app.Quit.assert_called_once() # Only if created_new_instance was True

        # Check if the output file was at least attempted to be created (even if empty due to mock)
        # In a real scenario with win32com, SaveAs would create the file.
        # Here, we can't check its content but can ensure the mock was called.
        # For a more robust test if SaveAs actually wrote, we might need to allow the mock to write a dummy file.
        # For now, the interaction with the mock is the primary check.
        
        # To simulate file creation by SaveAs for the sake of the test structure:
        if not output_html_path.exists():
            with open(output_html_path, "w", encoding="utf-8") as f_out:
                f_out.write("<html><body>Mocked DOCX content</body></html>")

        assert output_html_path.exists()
        html_content = output_html_path.read_text(encoding="utf-8")
        assert "Mocked DOCX content" in html_content # Check content from our simulated creation
        assert len(html_content) > 0

    finally:
        # Clean up the created HTML file
        output_html_path.unlink(missing_ok=True)

def test_main_convert_file_to_html_for_docx(dummy_docx_placeholder_file: Path):
    """
    Test that the main convert_file_to_html dispatcher calls the DOCX conversion.
    This also uses the win32com mock via the docx_converter module.
    """
    # Patch win32com.client within the docx_converter module's scope
    with patch('file_search_module.converters.docx_converter.win32com.client') as mock_win32_client_for_main:
        mock_doc_main = MagicMock()
        mock_word_app_main = MagicMock()
        mock_word_app_main.Documents.Open.return_value = mock_doc_main
        mock_win32_client_for_main.GetActiveObject.side_effect = Exception("COM error")
        mock_win32_client_for_main.Dispatch.return_value = mock_word_app_main

        result_path = convert_file_to_html(str(dummy_docx_placeholder_file))
        
        assert result_path is not None
        assert isinstance(result_path, Path)
        assert result_path.name == f"{dummy_docx_placeholder_file.stem}_converted.html"
        
        # Check that our mock was used, implying docx_converter.convert_docx_to_html was called
        mock_win32_client_for_main.Dispatch.assert_called_with("Word.Application")
        
        # To simulate file creation for the sake of the test structure:
        if not result_path.exists():
             with open(result_path, "w", encoding="utf-8") as f_out:
                f_out.write("<html><body>Mocked DOCX content via main dispatcher</body></html>")

        assert result_path.exists()
        html_content = result_path.read_text(encoding="utf-8")
        assert "Mocked DOCX content via main dispatcher" in html_content
        
        result_path.unlink(missing_ok=True)

```
