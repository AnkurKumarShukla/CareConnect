import hashlib

try:
    import streamlit as st
except ImportError:
    class MockSessionState(dict):
        def __getattr__(self, key):
            try:
                return self[key]
            except KeyError:
                raise AttributeError(f"No attribute {key}")

        def __setattr__(self, key, value):
            self[key] = value

        def __delattr__(self, key):
            try:
                del self[key]
            except KeyError:
                raise AttributeError(f"No attribute {key}")

    class MockStreamlit:
        session_state = MockSessionState()

        def markdown(self, *args, **kwargs): pass
        def subheader(self, *args, **kwargs): pass
        def text_input(self, *args, **kwargs): return ""
        def selectbox(self, *args, **kwargs): return args[1][0] if len(args) > 1 and args[1] else ""
        def form_submit_button(self, *args, **kwargs): return False
        def button(self, *args, **kwargs): return False
        def success(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def rerun(self, *args, **kwargs): pass
        def divider(self): pass
        def tabs(self, tabs): return [MockStreamlit() for _ in tabs]
        def form(self, key): return self
        def expander(self, label): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass

    st = MockStreamlit()

SECURITY_QUESTIONS = [
    "What is your mother's maiden name?",
    "What was the name of your first pet?",
    "What city were you born in?",
    "What was the make of your first car?",
    "What is your favorite book or movie?",
]


class AuthManager:
    """Manages user registration, authentication, password change, and password recovery."""

    def __init__(self, users_db: dict[str, dict] | None = None):
        # Initialize user database in session state if not present
        if users_db is not None:
            self._users_db = users_db
        else:
            if not hasattr(st, "session_state"):
                st.session_state = {}
            if "users_db" not in st.session_state:
                st.session_state["users_db"] = {}
            self._users_db = None

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password securely using SHA-256."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @property
    def users(self) -> dict[str, dict]:
        """Access the user dictionary."""
        if self._users_db is not None:
            return self._users_db
        if "users_db" not in st.session_state:
            st.session_state["users_db"] = {}
        return st.session_state["users_db"]

    def user_exists(self, username: str) -> bool:
        """Check if a username exists."""
        return username.strip().lower() in self.users

    def register_user(
        self,
        username: str,
        password: str,
        security_question: str = "",
        security_answer: str = "",
    ) -> tuple[bool, str]:
        """Register a new user with credentials and optional security question."""
        cleaned_username = username.strip()
        if not cleaned_username:
            return False, "Username cannot be empty."

        if not password:
            return False, "Password cannot be empty."

        key = cleaned_username.lower()
        if key in self.users:
            return False, f"Username '{cleaned_username}' already exists. Please choose a different one or log in."

        self.users[key] = {
            "display_name": cleaned_username,
            "password_hash": self.hash_password(password),
            "security_question": security_question.strip(),
            "security_answer_hash": self.hash_password(security_answer.strip().lower()) if security_answer.strip() else "",
        }
        return True, "Account created successfully! You can now log in."

    def authenticate_user(self, username: str, password: str) -> tuple[bool, str]:
        """Verify user credentials for login."""
        cleaned_username = username.strip()
        if not cleaned_username or not password:
            return False, "Username and password are required."

        key = cleaned_username.lower()
        if key not in self.users:
            return False, "Invalid username or password."

        user_record = self.users[key]
        if user_record.get("password_hash") != self.hash_password(password):
            return False, "Invalid username or password."

        return True, f"Welcome back, {user_record.get('display_name', cleaned_username)}!"

    def change_password(
        self,
        username: str,
        current_password: str,
        new_password: str,
    ) -> tuple[bool, str]:
        """Allow a logged-in user to change their password."""
        cleaned_username = username.strip()
        key = cleaned_username.lower()

        if key not in self.users:
            return False, "User not found."

        user_record = self.users[key]
        if user_record.get("password_hash") != self.hash_password(current_password):
            return False, "Current password is incorrect."

        if not new_password:
            return False, "New password cannot be empty."

        if current_password == new_password:
            return False, "New password must be different from current password."

        user_record["password_hash"] = self.hash_password(new_password)
        return True, "Password updated successfully!"

    def get_security_question(self, username: str) -> str | None:
        """Get the security question registered for the user."""
        key = username.strip().lower()
        if key in self.users:
            return self.users[key].get("security_question", "")
        return None

    def reset_password(
        self,
        username: str,
        security_answer: str,
        new_password: str,
    ) -> tuple[bool, str]:
        """Reset forgotten password using the security answer."""
        cleaned_username = username.strip()
        key = cleaned_username.lower()

        if not cleaned_username:
            return False, "Username cannot be empty."

        if key not in self.users:
            return False, f"User '{cleaned_username}' not found."

        user_record = self.users[key]
        stored_answer_hash = user_record.get("security_answer_hash", "")

        if not stored_answer_hash:
            return False, "No security recovery information found for this user."

        if self.hash_password(security_answer.strip().lower()) != stored_answer_hash:
            return False, "Incorrect security answer."

        if not new_password:
            return False, "New password cannot be empty."

        user_record["password_hash"] = self.hash_password(new_password)
        return True, "Password reset successfully! You can now log in with your new password."


def initialize_auth_state():
    """Initialize authentication session state variables."""
    if not hasattr(st, "session_state"):
        st.session_state = {}
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "logged_in_user" not in st.session_state:
        st.session_state["logged_in_user"] = None
    if "users_db" not in st.session_state:
        st.session_state["users_db"] = {}


def render_auth_page() -> bool:
    """
    Render login, signup, and forgot password tabs.
    Returns True if user is authenticated, False otherwise.
    """
    initialize_auth_state()

    if st.session_state.get("authenticated", False):
        return True

    auth_mgr = AuthManager()

    st.markdown("## 🔐 CareConnect Portal")
    st.markdown("Please log in to your account or sign up to continue.")

    tab_login, tab_signup, tab_forgot = st.tabs(["🔑 Login", "📝 Sign Up", "🔄 Forgot Password"])

    # --- LOGIN TAB ---
    with tab_login:
        st.subheader("Login to CareConnect")
        with st.form("login_form"):
            login_username = st.text_input("Username / User ID", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_submit = st.form_submit_button("Log In", use_container_width=True)

            if login_submit:
                success, msg = auth_mgr.authenticate_user(login_username, login_password)
                if success:
                    st.session_state["authenticated"] = True
                    st.session_state["logged_in_user"] = login_username.strip()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # --- SIGN UP TAB ---
    with tab_signup:
        st.subheader("Create a New Account")
        with st.form("signup_form"):
            signup_username = st.text_input("Choose a Username / User ID", key="signup_username")
            signup_password = st.text_input("Choose a Password", type="password", key="signup_password")
            signup_confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")

            st.markdown("#### Security Question (for password recovery)")
            sec_question = st.selectbox(
                "Select a security question",
                SECURITY_QUESTIONS,
                key="signup_sec_question",
            )
            sec_answer = st.text_input("Your Answer", key="signup_sec_answer")

            signup_submit = st.form_submit_button("Sign Up", use_container_width=True)

            if signup_submit:
                if signup_password != signup_confirm_password:
                    st.error("Passwords do not match. Please try again.")
                elif not sec_answer.strip():
                    st.error("Please provide an answer to the security question for password recovery.")
                else:
                    success, msg = auth_mgr.register_user(
                        username=signup_username,
                        password=signup_password,
                        security_question=sec_question,
                        security_answer=sec_answer,
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    # --- FORGOT PASSWORD TAB ---
    with tab_forgot:
        st.subheader("Recover / Reset Password")
        with st.form("forgot_password_form"):
            forgot_username = st.text_input("Enter your Username / User ID", key="forgot_username")
            forgot_sec_answer = st.text_input("Your Security Answer", key="forgot_sec_answer")
            forgot_new_password = st.text_input("New Password", type="password", key="forgot_new_password")
            forgot_confirm_password = st.text_input("Confirm New Password", type="password", key="forgot_confirm_password")

            forgot_submit = st.form_submit_button("Reset Password", use_container_width=True)

            if forgot_submit:
                if forgot_new_password != forgot_confirm_password:
                    st.error("New passwords do not match. Please try again.")
                else:
                    success, msg = auth_mgr.reset_password(
                        username=forgot_username,
                        security_answer=forgot_sec_answer,
                        new_password=forgot_new_password,
                    )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    return False


def render_user_sidebar():
    """Render authenticated user info, change password section, and logout button in sidebar."""
    initialize_auth_state()
    if not st.session_state.get("authenticated", False):
        return

    auth_mgr = AuthManager()
    user = st.session_state.get("logged_in_user", "User")

    st.sidebar.markdown(f"### 👤 Logged in as: **{user}**")

    if st.sidebar.button("🚪 Log Out", key="logout_btn", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["logged_in_user"] = None
        st.rerun()

    st.sidebar.divider()

    with st.sidebar.expander("🔑 Change Password"), st.form("change_password_form"):
        current_pwd = st.text_input("Current Password", type="password", key="cp_current")
        new_pwd = st.text_input("New Password", type="password", key="cp_new")
        confirm_new_pwd = st.text_input("Confirm New Password", type="password", key="cp_confirm")
        cp_submit = st.form_submit_button("Update Password", use_container_width=True)

        if cp_submit:
            if new_pwd != confirm_new_pwd:
                st.error("New passwords do not match.")
            else:
                success, msg = auth_mgr.change_password(user, current_pwd, new_pwd)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
