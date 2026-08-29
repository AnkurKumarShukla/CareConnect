import pytest
from unittest.mock import MagicMock, patch
from tests.test_auth import MockSessionState
import frontend.app as frontend_app
import backend.app as backend_app


def test_frontend_initialize_session_state():
    mock_state = MockSessionState()
    with patch("streamlit.session_state", mock_state):
        frontend_app.initialize_session_state()
        assert mock_state.authenticated is False
        assert mock_state.username is None
        assert mock_state.model_name == "mixtral-8x7b"
        assert mock_state.category_value == "ALL"
        assert mock_state.rag is True


def test_backend_initialize_session_state():
    mock_state = MockSessionState()
    with patch("streamlit.session_state", mock_state):
        backend_app.initialize_session_state()
        assert mock_state.authenticated is False
        assert mock_state.username is None
        assert mock_state.model_name == "mistral-large2"
        assert mock_state.category_value == "ALL"
        assert mock_state.rag is True
        assert mock_state.show_documents is False


def test_frontend_main_unauthenticated():
    mock_state = MockSessionState()
    with patch("streamlit.session_state", mock_state), \
         patch("frontend.app.render_auth_ui", return_value=False) as mock_auth, \
         patch("frontend.app.SnowflakeConnection") as mock_conn:
        frontend_app.main()
        mock_auth.assert_called_once()
        mock_conn.assert_not_called()


def test_backend_main_unauthenticated():
    mock_state = MockSessionState()
    with patch("streamlit.session_state", mock_state), \
         patch("backend.app.render_auth_ui", return_value=False) as mock_auth, \
         patch("backend.app.initialize_handlers") as mock_handlers:
        backend_app.main()
        mock_auth.assert_called_once()
        mock_handlers.assert_not_called()
