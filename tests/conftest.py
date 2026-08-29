import sys
from unittest.mock import MagicMock
import types

mock_modules = [
    "streamlit",
    "dotenv",
    "snowflake",
    "snowflake.connector",
    "snowflake.snowpark",
    "snowflake.snowpark.context",
    "snowflake.core",
    "pandas",
    "docx",
    "fitz",
    "pypdf",
    "striprtf",
    "langchain",
    "langchain.text_splitter",
    "langchain_community",
    "langchain_community.document_loaders",
    "upload_prescription",
    "backend.upload_prescription",
]

for mod in mock_modules:
    if mod not in sys.modules:
        m = MagicMock()
        m.__path__ = []
        m.__file__ = f"/mock/{mod}.py"
        sys.modules[mod] = m
