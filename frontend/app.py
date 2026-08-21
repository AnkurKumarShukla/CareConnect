import streamlit as st
import os
import hashlib
from backend.connection import SnowflakeConnection
from backend.conversation_handler import ConversationHandler
from backend.cortex_completion import CortexCompletion

HASH_FILE = ".password_hash"
DEFAULT_PASSWORD = "changeme"

def _hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password: str) -> bool:
    if not os.path.exists(HASH_FILE):
        return password == DEFAULT_PASSWORD
    try:
        with open(HASH_FILE, "r") as f:
            stored = f.read().strip()
        if ":" not in stored:
            return False
        salt, expected_hash = stored.split(":", 1)
        actual_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return actual_hash == expected_hash
    except Exception:
        return False

def save_password(password: str) -> None:
    hashed_entry = _hash_password(password)
    with open(HASH_FILE, "w") as f:
        f.write(hashed_entry)

def login_screen():
    st.title(":lock: CareConnect Login")
    with st.form("login_form"):
        password_input = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if verify_password(password_input):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

def render_auth_sidebar():
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    with st.sidebar.expander("Change Password"):
        with st.form("change_password_form"):
            current_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            submit_change = st.form_submit_button("Change Password")
            if submit_change:
                if not verify_password(current_pw):
                    st.error("Current password is incorrect.")
                elif not new_pw:
                    st.error("New password cannot be empty.")
                elif new_pw != confirm_pw:
                    st.error("New passwords do not match.")
                else:
                    save_password(new_pw)
                    st.success("Password changed successfully!")

def initialize_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'model_name' not in st.session_state:
        st.session_state.model_name = 'mixtral-8x7b'
    if 'category_value' not in st.session_state:
        st.session_state.category_value = 'ALL'
    if 'rag' not in st.session_state:
        st.session_state.rag = True

def config_sidebar(conversation_handler):
    """Configure sidebar options"""
    st.sidebar.selectbox(
        'Select your model:',
        conversation_handler.available_models,
        key="model_name"
    )
    
    st.sidebar.selectbox(
        'Select what products you are looking for',
        conversation_handler.get_available_categories(),
        key="category_value"
    )
    
    st.session_state.rag = st.sidebar.checkbox('Use your own documents as context?', value=True)
    
    with st.sidebar.expander("Session State"):
        st.write(st.session_state)

def main():
    # Initialize session state
    initialize_session_state()

    if not st.session_state.authenticated:
        login_screen()
        return

    st.title(":speech_balloon: Cha Document Assistant with Snowflake Cortex")
    
    render_auth_sidebar()

    # Initialize connections and handlers
    connection = SnowflakeConnection()
    if not connection.connect():
        st.error("Failed to connect to Snowflake. Please check your credentials.")
        return
    
    session = connection.get_session()
    conversation_handler = ConversationHandler(session)
    cortex_completion = CortexCompletion(session, connection.get_root())
    
    # Initialize session state
    initialize_session_state()
    
    # Configure sidebar
    config_sidebar(conversation_handler)
    
    # Display available documents
    st.write("This is the list of documents you already have and that will be used to answer your questions:")
    docs_df = conversation_handler.get_available_documents()
    st.dataframe(docs_df)
    
    # Chat interface
    question = st.text_input(
        "Enter question",
        placeholder="Is there any special lubricant to be used with the premium bike?",
        label_visibility="collapsed"
    )
    
    if question:
        # Add user question to conversation history
        conversation_handler.add_message("user", question)
        
        # Get response
        response_text, relative_paths = cortex_completion.complete(
            question,
            st.session_state.model_name,
            st.session_state.rag,
            st.session_state.category_value
        )
        
        # Add assistant response to conversation history
        conversation_handler.add_message("assistant", response_text)
        
        # Display response
        st.markdown(response_text)
        
        # Display related documents
        if relative_paths:
            with st.sidebar.expander("Related Documents"):
                for path in relative_paths:
                    url_link = cortex_completion.get_document_url(path)
                    if url_link:
                        display_url = f"Doc: [{path}]({url_link})"
                        st.sidebar.markdown(display_url)

if __name__ == "__main__":
    main()