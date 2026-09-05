import os
import sys
from unittest.mock import MagicMock, patch

# Add repo root and backend to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.join(repo_root, "backend"))

# Mock snowflake modules if not installed
for mod in [
    "snowflake",
    "snowflake.connector",
    "snowflake.snowpark",
    "snowflake.snowpark.context",
    "snowflake.core",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from frontend.app import check_credentials, initialize_session_state, login_page, main


class MockSessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


def test_check_credentials_default():
    with patch.dict(os.environ, {}, clear=True):
        assert check_credentials("admin", "admin") is True
        assert check_credentials("admin", "wrongpassword") is False
        assert check_credentials("wronguser", "admin") is False
        assert check_credentials("", "") is False


def test_check_credentials_custom_env():
    with patch.dict(os.environ, {"APP_USERNAME": "custom_user", "APP_PASSWORD": "secret_password"}):
        assert check_credentials("custom_user", "secret_password") is True
        assert check_credentials("admin", "admin") is False
        assert check_credentials("custom_user", "wrong") is False


def test_initialize_session_state():
    mock_session_state = MockSessionState()
    with patch("streamlit.session_state", mock_session_state):
        initialize_session_state()
        assert mock_session_state.authenticated is False
        assert mock_session_state.model_name == "mixtral-8x7b"
        assert mock_session_state.category_value == "ALL"
        assert mock_session_state.rag is True


def test_initialize_session_state_preserves_existing():
    mock_session_state = MockSessionState({
        "authenticated": True,
        "model_name": "custom-model",
        "category_value": "CARDS",
        "rag": False,
    })
    with patch("streamlit.session_state", mock_session_state):
        initialize_session_state()
        assert mock_session_state.authenticated is True
        assert mock_session_state.model_name == "custom-model"
        assert mock_session_state.category_value == "CARDS"
        assert mock_session_state.rag is False


def test_login_page_success():
    mock_session_state = MockSessionState({"authenticated": False})
    with patch("streamlit.session_state", mock_session_state), \
         patch("streamlit.title"), \
         patch("streamlit.form"), \
         patch("streamlit.text_input", side_effect=["admin", "admin"]), \
         patch("streamlit.form_submit_button", return_value=True), \
         patch("streamlit.rerun") as mock_rerun, \
         patch("streamlit.error") as mock_error:

        login_page()

        assert mock_session_state.authenticated is True
        mock_rerun.assert_called_once()
        mock_error.assert_not_called()


def test_login_page_failure():
    mock_session_state = MockSessionState({"authenticated": False})
    with patch("streamlit.session_state", mock_session_state), \
         patch("streamlit.title"), \
         patch("streamlit.form"), \
         patch("streamlit.text_input", side_effect=["admin", "wrongpass"]), \
         patch("streamlit.form_submit_button", return_value=True), \
         patch("streamlit.rerun") as mock_rerun, \
         patch("streamlit.error") as mock_error:

        login_page()

        assert mock_session_state.authenticated is False
        mock_rerun.assert_not_called()
        mock_error.assert_called_once_with("Invalid username or password")


def test_main_unauthenticated_shows_login_and_stops():
    mock_session_state = MockSessionState({"authenticated": False})
    with patch("streamlit.session_state", mock_session_state), \
         patch("frontend.app.login_page") as mock_login_page, \
         patch("frontend.app.SnowflakeConnection") as mock_conn:

        main()

        mock_login_page.assert_called_once()
        mock_conn.assert_not_called()


def test_main_authenticated_shows_app():
    mock_session_state = MockSessionState({
        "authenticated": True,
        "model_name": "mixtral-8x7b",
        "category_value": "ALL",
        "rag": True,
    })

    mock_conn_instance = MagicMock()
    mock_conn_instance.connect.return_value = True
    mock_session = MagicMock()
    mock_conn_instance.get_session.return_value = mock_session
    mock_conn_instance.get_root.return_value = MagicMock()

    mock_handler_instance = MagicMock()
    mock_handler_instance.available_models = ["mixtral-8x7b"]
    mock_handler_instance.get_available_categories.return_value = ["ALL"]
    mock_handler_instance.get_available_documents.return_value = MagicMock()

    with patch("streamlit.session_state", mock_session_state), \
         patch("frontend.app.login_page") as mock_login_page, \
         patch("frontend.app.SnowflakeConnection", return_value=mock_conn_instance), \
         patch("frontend.app.ConversationHandler", return_value=mock_handler_instance), \
         patch("frontend.app.CortexCompletion"), \
         patch("streamlit.title"), \
         patch("streamlit.write"), \
         patch("streamlit.dataframe"), \
         patch("streamlit.text_input", return_value=None), \
         patch("streamlit.sidebar"):

        main()

        mock_login_page.assert_not_called()
        mock_conn_instance.connect.assert_called_once()
