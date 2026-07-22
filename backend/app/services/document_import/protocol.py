"""
services/document_import/protocol.py — DocumentExtractor Protocol

This is the plugin interface for the Smart Academic Import System.

EXTENDING THE SYSTEM WITH A NEW FORMAT:
  1. Create a new class that implements this Protocol.
  2. Add it to the EXTRACTORS list in pipeline.py.
  3. No other changes needed — classification, field extraction, confidence
     scoring, planner integration, and review flow are all format-agnostic.

Example for a future DOCX extractor:
  class DOCXExtractor:
      def supports(self, file_type: str) -> bool:
          return file_type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx")
      def extract_text(self, file_path: str) -> str:
          import docx
          doc = docx.Document(file_path)
          return "\\n".join(p.text for p in doc.paragraphs)
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocumentExtractor(Protocol):
    """
    Contract that every document format extractor must satisfy.
    Implement this Protocol to add support for a new file format.
    """

    def supports(self, file_type: str) -> bool:
        """
        Return True if this extractor can handle the given file type.

        Args:
            file_type: MIME type string (e.g. "application/pdf") or
                       file extension with dot (e.g. ".pdf").

        Returns:
            True if this extractor handles the format; False otherwise.
        """
        ...

    def extract_text(self, file_path: str) -> str:
        """
        Extract all readable text from the file at file_path.

        Args:
            file_path: Absolute path to the uploaded file on disk.

        Returns:
            Plain text string containing all extractable content.
            Returns empty string on extraction failure — never raises.

        Postconditions:
            - Caller must not assume any particular line structure.
            - OCR-based implementations may include noise — caller applies
              post-processing before classification.
        """
        ...
