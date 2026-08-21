import streamlit as st
from backend.connection import SnowflakeConnection
from backend.conversation_handler import ConversationHandler
from backend.cortex_completion import CortexCompletion
try:
    from backend.auth import (
        init_auth_session,
        is_authenticated,
        render_login_screen,
        render_auth_controls,
    )
except ImportError:
    from auth import (
        init_auth_session,
        is_authenticated,
        render_login_screen,
        render_auth_controls,
    )

def initialize_session_state():
    """Initialize session state variables"""
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
    
    render_auth_controls()

    with st.sidebar.expander("Session State"):
        st.write(st.session_state)

def main():
    init_auth_session()
    if not is_authenticated():
        render_login_screen()
        return

    st.title(":speech_balloon: Cha Document Assistant with Snowflake Cortex")
    
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