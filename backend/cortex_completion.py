import json
from typing import Tuple, List, Dict, Any
#  add historcial chat data
from conversation_handler import ConversationHandler

class CortexCompletion:
    # Initialize the Cortex completion service and search configuration
    def __init__(self, session, root):
        self.session = session
        self.root = root
        self.NUM_CHUNKS = 3
        self.CORTEX_SEARCH_DATABASE = "MEDICAL_CORTEX_SEARCH_APP"
        self.CORTEX_SEARCH_SCHEMA = "DATA"
        self.CORTEX_SEARCH_SERVICE = "CC_SEARCH_SERVICE_CS"
        self.COLUMNS = ["chunk", "relative_path", "category"]
        
        self.search_service = self.root.databases[self.CORTEX_SEARCH_DATABASE].schemas[
            self.CORTEX_SEARCH_SCHEMA
        ].cortex_search_services[self.CORTEX_SEARCH_SERVICE]

    def get_similar_chunks(self, query: str, category: str = "ALL") -> Dict[str, Any]:
        """Get similar chunks from the search service"""
        try:
            if category == "ALL":
                response = self.search_service.search(query, self.COLUMNS, limit=self.NUM_CHUNKS)
            else:
                filter_obj = {"@eq": {"category": category}}
                response = self.search_service.search(
                    query, self.COLUMNS, filter=filter_obj, limit=self.NUM_CHUNKS
                )
            
            # Convert response to dictionary if it's not already
            if not isinstance(response, dict):
                response_data = response.json()
            else:
                response_data = response
                
            return response_data
        except Exception as e:
            print(f"Error getting similar chunks: {str(e)}")
            return {"results": []}

    def create_prompt(self, question: str, use_rag: bool, prescription_text,category: str = "ALL") -> Tuple[str, set]:
        """Create prompt for completion"""
        if use_rag:
            # preprocess the prescription text  remove the special characters and unnecessary spaces
            # prescription_text = " ".join(prescription_text) if prescription_text else ""
            question_enriched = question + " \n this prescription \n " + prescription_text
            prompt_context = self.get_similar_chunks(question_enriched, category)
            print("PROMPT CONTEXT:----",prompt_context)
            # Extract context information from chunks
            context_info = []
            relative_paths = set()
            # print("debug create prompt")
            json_data = json.loads(prompt_context)
            relative_paths = set(item['relative_path'] for item in json_data['results'])
            # if "results" in prompt_context and isinstance(prompt_context["results"], list):
            #     for result in prompt_context["results"]:
            #         # Validate that result is a dictionary
            #         if isinstance(result, dict):
            #             # chunk = result.get("chunk", "")
            #             relative_path = result["relative_path"]

            #             # Append the chunk if available
            #             # if chunk:
            #             #     context_info.append(chunk)

            #             # Add the relative path if available
            #             if relative_path:
            #                 relative_paths.add(relative_path)
            #         else:
            #             print(f"Debug - Invalid result format: {result}")
            
            context_text = "\n".join(context_info)
            # print(prescription_text)
            combined_text=prompt_context+prescription_text
            # print("Debug - Context text: ", context_text)
            chat_history = ConversationHandler.fetch_history()
            prompt = f"""
                You are an expert chat assistance that extracts information from the CONTEXT provided
                between <context> and </context> tags.
                When answering the question contained between <question> and </question> tags
                be concise and do not hallucinate. 
                If you don't have the information just say i do not know.
                Only answer the question if you can extract it from the CONTEXT provided.
                
                Do not mention the CONTEXT used in your answer.
                <chat_history>
                {chat_history}
                </chat_history>
                <context>          
                {combined_text}
                </context>
                

                <question>  
                {question}
                </question>
                Answer: 
                """
        else:     
            prompt = f"Question: {question}\nAnswer:"
            relative_paths = set()
                
        return prompt, relative_paths

    def complete(self, question: str, model_name: str, use_rag: bool, prescription_text:str, category: str = "ALL") -> Tuple[str, set]:
        """Complete the prompt using Snowflake Cortex"""
        # print("Debug - Completing prompt")
        prompt, relative_paths = self.create_prompt(question, use_rag,prescription_text, category)
        # print(f"Debug - Prompt: {prompt}")
        cmd = "select snowflake.cortex.complete(?, ?) as response"
        
        # Execute the completion
        df_response = self.session.sql(cmd, params=[model_name, prompt]).collect()
        # print(f"Debug - df_response type: {type(df_response)}")
        # print(f"Debug - df_response content: {df_response}")
        # Safely access the response
        if len(df_response) > 0:
            # print(f"Debug - df_response type: {type(df_response)}")
            # print(f"Debug - df_response content: {df_response}")

            response_text = str(df_response[0].RESPONSE)
        else:
            response_text = "Sorry, I couldn't generate a response."
        # print(f"Debug - Response type: {type(df_response)}")
        # print(f"Debug - Response content: {df_response}")
        
        return response_text, relative_paths

    # def complete(self, 
    #             question: str, 
    #             model_name: str, 
    #             use_rag: bool, 
    #             chat_history: List[Dict[str, str]], 
    #             category: str = "ALL") -> Tuple[str, set]:
    #     """Complete the prompt using Snowflake Cortex with memory"""
    #     try:
    #         prompt, relative_paths = self.create_prompt(question, use_rag, chat_history, category)
    #         cmd = "select snowflake.cortex.complete(?, ?) as response"
            
    #         df_response = self.session.sql(cmd, params=[model_name, prompt]).collect()
    #         response_text = df_response[0].RESPONSE
            
    #         # Update memory with the new interaction
    #         self.update_memory(question, response_text)
            
    #         return response_text, relative_paths
    #     except Exception as e:
    #         print(f"Error in completion: {str(e)}")
    #         return "Sorry, I encountered an error processing your request.", set()    

    def get_document_url(self, path: str) -> str:
        """Get presigned URL for a document"""
        try:
            cmd = f"select GET_PRESIGNED_URL(@docs, '{path}', 360) as URL_LINK from directory(@docs)"
            df_url_link = self.session.sql(cmd).to_pandas()
            return df_url_link._get_value(0, 'URL_LINK')
        except Exception as e:
            print(f"Error getting document URL: {str(e)}")
            return ""