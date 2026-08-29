import os
import json
import hashlib
import hmac
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

try:
    import streamlit as st
except ImportError:
    st = None

SECURITY_QUESTIONS = [
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What was your first school name?",
    "What is your favorite book or movie?",
    "In what city were you born?",
]

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DEFAULT_USERS_FILE = os.environ.get("USERS_FILE_PATH", os.path.join(DEFAULT_DATA_DIR, "users.json"))


def hash_password(password: str, salt: Optional[str] = None, iterations: int = 100_000) -> Tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256.
    Returns (hex_hash, hex_salt).
    """
    if salt is None:
        salt_bytes = os.urandom(16)
    else:
        salt_bytes = bytes.fromhex(salt)
    
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt_bytes,
        iterations
    )
    return dk.hex(), salt_bytes.hex()


def verify_password(password: str, stored_hash: str, stored_salt: str, iterations: int = 100_000) -> bool:
    """Verify password against stored PBKDF2-HMAC-SHA256 hash and salt."""
    try:
        salt_bytes = bytes.fromhex(stored_salt)
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt_bytes,
            iterations
        )
        return hmac.compare_digest(dk.hex(), stored_hash)
    except Exception:
        return False


def hash_security_answer(answer: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Normalized security answer hash (case-insensitive, trimmed)."""
    normalized = answer.strip().lower()
    return hash_password(normalized, salt=salt)


def verify_security_answer(answer: str, stored_hash: str, stored_salt: str) -> bool:
    """Verify normalized security answer."""
    normalized = answer.strip().lower()
    return verify_password(normalized, stored_hash, stored_salt)


class AuthManager:
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or DEFAULT_USERS_FILE
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage directory and user file exist."""
        dirname = os.path.dirname(os.path.abspath(self.storage_path))
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def load_users(self) -> Dict[str, Any]:
        """Load users from storage file."""
        self._ensure_storage()
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_users(self, users: Dict[str, Any]) -> None:
        """Save users dictionary to storage file."""
        self._ensure_storage()
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)

    def user_exists(self, username: str) -> bool:
        """Check if username already exists."""
        users = self.load_users()
        return username.strip().lower() in [u.lower() for u in users.keys()]

    def signup(
        self,
        username: str,
        password: str,
        security_question: str = "",
        security_answer: str = ""
    ) -> Tuple[bool, str]:
        """
        Register a new user.
        """
        username = username.strip()
        if not username:
            return False, "Username cannot be empty."
        if len(username) < 3:
            return False, "Username must be at least 3 characters long."
        if not password:
            return False, "Password cannot be empty."
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        if self.user_exists(username):
            return False, f"Username '{username}' already exists."

        pwd_hash, pwd_salt = hash_password(password)
        
        user_record = {
            "username": username,
            "password_hash": pwd_hash,
            "salt": pwd_salt,
            "created_at": datetime.utcnow().isoformat(),
        }

        if security_question and security_answer.strip():
            ans_hash, ans_salt = hash_security_answer(security_answer)
            user_record["security_question"] = security_question.strip()
            user_record["security_answer_hash"] = ans_hash
            user_record["security_answer_salt"] = ans_salt

        users = self.load_users()
        users[username] = user_record
        self.save_users(users)
        return True, "User registered successfully."

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """Authenticate user credentials."""
        username = username.strip()
        if not username or not password:
            return False, "Please enter both username and password."

        users = self.load_users()
        user_data = None
        for u, data in users.items():
            if u.lower() == username.lower():
                user_data = data
                break

        if not user_data:
            return False, "Invalid username or password."

        if verify_password(password, user_data.get("password_hash", ""), user_data.get("salt", "")):
            return True, "Login successful."
        return False, "Invalid username or password."

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change password for an authenticated user."""
        username = username.strip()
        users = self.load_users()
        user_key = None
        for u in users:
            if u.lower() == username.lower():
                user_key = u
                break

        if not user_key:
            return False, "User not found."

        user_data = users[user_key]
        if not verify_password(old_password, user_data.get("password_hash", ""), user_data.get("salt", "")):
            return False, "Current password is incorrect."

        if not new_password:
            return False, "New password cannot be empty."
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters long."
        if old_password == new_password:
            return False, "New password cannot be the same as old password."

        pwd_hash, pwd_salt = hash_password(new_password)
        user_data["password_hash"] = pwd_hash
        user_data["salt"] = pwd_salt
        user_data["updated_at"] = datetime.utcnow().isoformat()
        users[user_key] = user_data
        self.save_users(users)
        return True, "Password changed successfully."

    def get_security_question(self, username: str) -> Optional[str]:
        """Get the configured security question for a user."""
        users = self.load_users()
        for u, data in users.items():
            if u.lower() == username.strip().lower():
                return data.get("security_question")
        return None

    def reset_password(self, username: str, security_answer: str, new_password: str) -> Tuple[bool, str]:
        """Reset password using security question verification."""
        username = username.strip()
        users = self.load_users()
        user_key = None
        for u in users:
            if u.lower() == username.lower():
                user_key = u
                break

        if not user_key:
            return False, "User not found."

        user_data = users[user_key]
        ans_hash = user_data.get("security_answer_hash")
        ans_salt = user_data.get("security_answer_salt")

        if not ans_hash or not ans_salt:
            return False, "No security question configured for this account. Cannot recover password."

        if not verify_security_answer(security_answer, ans_hash, ans_salt):
            return False, "Incorrect security answer."

        if not new_password:
            return False, "New password cannot be empty."
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters long."

        pwd_hash, pwd_salt = hash_password(new_password)
        user_data["password_hash"] = pwd_hash
        user_data["salt"] = pwd_salt
        user_data["updated_at"] = datetime.utcnow().isoformat()
        users[user_key] = user_data
        self.save_users(users)
        return True, "Password reset successfully."


def safe_rerun():
    """Trigger a Streamlit rerun safely across versions."""
    if st is None:
        return
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def init_auth_session_state():
    """Initialize authentication session state variables."""
    if st is None:
        return
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = AuthManager()


def logout():
    """Log out the current user and reset session state."""
    if st is None:
        return
    st.session_state.authenticated = False
    st.session_state.username = None
    safe_rerun()


def render_auth_ui(auth_manager: Optional[AuthManager] = None) -> bool:
    """
    Renders authentication UI (Login, Sign Up, Forgot Password).
    Returns True if the user is authenticated, False otherwise.
    """
    if st is None:
        return False

    init_auth_session_state()

    if st.session_state.get("authenticated", False):
        return True

    manager = auth_manager or st.session_state.get("auth_manager", AuthManager())

    st.title("🛡️ CareConnect Authentication")
    st.write("Please log in or create an account to access CareConnect.")

    tab_login, tab_signup, tab_forgot = st.tabs(["🔐 Login", "📝 Sign Up", "❓ Forgot Password"])

    with tab_login:
        st.subheader("Login to your account")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submit_login = st.form_submit_button("Log In", use_container_width=True)

            if submit_login:
                success, msg = manager.login(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = username.strip()
                    st.success(msg)
                    safe_rerun()
                else:
                    st.error(msg)

    with tab_signup:
        st.subheader("Create a new account")
        with st.form("signup_form", clear_on_submit=False):
            new_username = st.text_input("Username", key="signup_username")
            new_password = st.text_input("Password (min 6 characters)", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
            
            security_q = st.selectbox(
                "Security Question (for password recovery)",
                options=SECURITY_QUESTIONS,
                key="signup_security_q"
            )
            security_a = st.text_input("Security Answer", type="password", key="signup_security_a")
            submit_signup = st.form_submit_button("Sign Up", use_container_width=True)

            if submit_signup:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif not security_a.strip():
                    st.error("Please provide a security answer for password recovery.")
                else:
                    success, msg = manager.signup(
                        username=new_username,
                        password=new_password,
                        security_question=security_q,
                        security_answer=security_a
                    )
                    if success:
                        st.success("Account created successfully! You can now log in.")
                    else:
                        st.error(msg)

    with tab_forgot:
        st.subheader("Reset your password")
        forgot_username = st.text_input("Enter your Username", key="forgot_username_input")
        if forgot_username.strip():
            question = manager.get_security_question(forgot_username)
            if question:
                st.info(f"**Security Question:** {question}")
            elif manager.user_exists(forgot_username):
                st.warning("No security question was configured for this user.")
            else:
                st.warning("Username not found.")

        with st.form("forgot_password_form", clear_on_submit=False):
            recovery_username = st.text_input("Username", value=forgot_username, key="forgot_form_username")
            security_ans = st.text_input("Security Answer", type="password", key="forgot_security_ans")
            new_pwd = st.text_input("New Password (min 6 characters)", type="password", key="forgot_new_pwd")
            confirm_new_pwd = st.text_input("Confirm New Password", type="password", key="forgot_confirm_new_pwd")
            submit_reset = st.form_submit_button("Reset Password", use_container_width=True)

            if submit_reset:
                if new_pwd != confirm_new_pwd:
                    st.error("New passwords do not match.")
                else:
                    success, msg = manager.reset_password(recovery_username, security_ans, new_pwd)
                    if success:
                        st.success("Password reset successfully! Please log in with your new password.")
                    else:
                        st.error(msg)

    return False


def render_user_menu(auth_manager: Optional[AuthManager] = None):
    """
    Renders user profile, change password option, and logout in the sidebar.
    """
    if st is None or not st.session_state.get("authenticated", False):
        return

    manager = auth_manager or st.session_state.get("auth_manager", AuthManager())
    username = st.session_state.get("username", "User")

    st.sidebar.markdown(f"### 👤 Logged in as **{username}**")
    if st.sidebar.button("🚪 Log Out", key="logout_btn", use_container_width=True):
        logout()

    with st.sidebar.expander("🔑 Change Password"):
        with st.form("change_password_form", clear_on_submit=True):
            current_pwd = st.text_input("Current Password", type="password", key="change_curr_pwd")
            new_pwd = st.text_input("New Password", type="password", key="change_new_pwd")
            confirm_pwd = st.text_input("Confirm New Password", type="password", key="change_conf_pwd")
            submit_change = st.form_submit_button("Update Password", use_container_width=True)

            if submit_change:
                if new_pwd != confirm_pwd:
                    st.error("New passwords do not match.")
                else:
                    success, msg = manager.change_password(username, current_pwd, new_pwd)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
