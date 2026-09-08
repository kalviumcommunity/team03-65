"""HTML utility functions for Streamlit rendering.

Ensures that multi-line HTML strings never have leading indentation or blank lines
that could be misinterpreted by Python-Markdown / CommonMark as indented code blocks.
"""

def clean_html(raw_html: str) -> str:
    """Normalize HTML string by stripping indentation and whitespace from each line."""
    if not raw_html:
        return ""
    return " ".join(line.strip() for line in raw_html.splitlines() if line.strip())
