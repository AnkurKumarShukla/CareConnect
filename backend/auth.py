import hashlib
import json
import os
import streamlit as st

AUTH_FILE_PATH = os.environ.get(
    "AUTH_CREDENTIALS_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".auth_credentials.json")
)
DEFAULT_PASSWORD = os.environ.get("DEFAULT_PASSWORD", "admin123")


def hash_password(password: str, salt: bytes = None) -> tuple:
    """Hash a password using PBKDF2-HMAC-SHA256 with 100,000 iterations."""
    if salt is None:
        salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex(), hashed.hex()


def verify_password(stored_salt_hex: str, stored_hash_hex: str, provided_password: str) -> bool:
    """Verify a password against stored salt and hash."""
    try:
        salt = bytes.fromhex(stored_salt_hex)
        _, computed_hash_hex = hash_password(provided_password, salt)
        return computed_hash_hex == stored_hash_hex
    except Exception:
        return False


def load_credentials() -> dict:
    """Load credentials from file or initialize with default password."""
    if os.path.exists(AUTH_FILE_PATH):
        try:
            with open(AUTH_FILE_PATH, "r", encoding="utf-8") as f:
                creds = json.load(f)
                if "salt" in creds and "password_hash" in creds:
                    return creds
        except Exception:
            pass

    # Initialize default credentials
    salt_hex, hash_hex = hash_password(DEFAULT_PASSWORD)
    creds = {
        "username": "admin",
        "salt": salt_hex,
        "password_hash": hash_hex
    }
    save_credentials(creds)
    return creds


def save_credentials(creds: dict) -> None:
    """Save credentials securely to file."""
    with open(AUTH_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)


def authenticate(password: str) -> bool:
    """Authenticate provided password against stored hash."""
    creds = load_credentials()
    return verify_password(creds.get("salt", ""), creds.get("password_hash", ""), password)


def update_password(current_password: str, new_password: str) -> tuple:
    """Change the password after verifying current password."""
    if not authenticate(current_password):
        return False, "Current password is incorrect."
    if not new_password or len(new_password) < 4:
        return False, "New password must be at least 4 characters long."
    salt_hex, hash_hex = hash_password(new_password)
    creds = load_credentials()
    creds["salt"] = salt_hex
    creds["password_hash"] = hash_hex
    save_credentials(creds)
    return True, "Password successfully updated."


def render_login_page():
    """Render Streamlit login form."""
    st.markdown("## :lock: Login to CareConnect")
    st.info("Please enter your password to access the application.")

    with st.form("login_form"):
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Log In")

        if submitted:
            if not password:
                st.error("Please enter a password.")
            elif authenticate(password):
                st.session_state.authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid password. Please try again.")


def render_auth_sidebar():
    """Render auth controls in the sidebar (User status, Logout, Change Password)."""
    st.sidebar.markdown("### :bust_in_silhouette: User Account")
    st.sidebar.caption("Authenticated as: **Admin**")

    if st.sidebar.button("Log Out", key="auth_logout_btn"):
        st.session_state.authenticated = False
        st.rerun()

    with st.sidebar.expander("Change Password"):
        with st.form("change_password_form"):
            current_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            pw_submitted = st.form_submit_button("Update Password")

            if pw_submitted:
                if new_pw != confirm_pw:
                    st.error("New passwords do not match.")
                else:
                    success, msg = update_password(current_pw, new_pw)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)


def check_authentication() -> bool:
    """
    Check if user is authenticated.
    If not, renders login page and returns False.
    If authenticated, renders auth controls in sidebar and returns True.
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        render_login_page()
        return False

    render_auth_sidebar()
    return True
