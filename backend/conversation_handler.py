from dataclasses import dataclass
from typing import List, Optional
import pandas as pd

@dataclass
class Message:
    role: str
    content: str

history = []

class ConversationHandler:
    def __init__(self, session):
        self.session = session
        self.history: List[Message] = []
        self.available_models = [
            'mistral-large2',
            'mixtral-8x7b',
            'snowflake-arctic',           
            'llama3-8b',
            'llama3-70b',
            'reka-flash',
            'mistral-7b',
            'llama2-70b-chat',
            'gemma-7b'
        ]

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history"""
        self.history.append(Message(role=role, content=content))
        history.append(Message(role=role, content=content))

    def get_history(self) -> List[Message]:
        """Get conversation history"""
        return self.history
    
    def fetch_history():
        return history

    def clear_history(self):
        """Clear conversation history"""
        self.history = []

    @property
    def last_message(self) -> Optional[Message]:
        """Get the last message in the conversation"""
        return self.history[-1] if self.history else None

    def get_available_categories(self) -> List[str]:
        """Get available document categories with caching"""
        try:
            categories = self.session.sql(
                "select category from data.docs_chunks_table group by category"
            ).collect()
            
            cat_list = ['ALL']
            for cat in categories:
                cat_list.append(cat.CATEGORY)
            return cat_list
        except Exception as e:
            print(f"Error getting categories: {str(e)}")
            return ['ALL']

    def get_available_documents(self) -> pd.DataFrame:
        """Get list of available documents"""
        try:
            docs_available = self.session.sql("ls @data.docs").collect()
            return pd.DataFrame([{"name": doc["name"]} for doc in docs_available])
        except Exception as e:
            print(f"Error getting documents: {str(e)}")
            return pd.DataFrame(columns=["name"])