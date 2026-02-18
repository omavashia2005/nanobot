from nanobot.agent.memory import MemoryStore
from supermemory import Supermemory
from nanobot.config.loader import load_config
from loguru import logger
from pathlib import Path

"""
Intelligent memory system using https://supermemory.ai
"""
class SupermemoryStore():
    """
    Agent memory using Supermemory for persistent, searchable, and structured memory.
    """
    def __init__(self, workspace: Path):
        config = load_config()
        self.api_key = config.supermemory.api_key
        self.container_tag = config.supermemory.container_tag or "nanobot_memory"
        self.supermemory_client = Supermemory(api_key=self.api_key)
        self.alternative_memory = MemoryStore(workspace)  # Fallback to local file-based memory
    
    def add_memory(self, content: str) -> None:
        try:
            """Add a new memory entry."""
            """
            TODO: 
            -   Add update conversation logic instead of adding new memories 
                everytime this function is called for better memory extraction
            """
            url = "https://api.supermemory.ai/v4/conversations"
            payload = {
                        "conversationId": f"session_{self.container_tag}",
                        "messages": [
                            {
                                "role": "user",
                                "content": content,
                                "name": "<string>",
                                "tool_calls": ["<unknown>"],
                                "tool_call_id": "<string>"
                            }
                        ]
                     }
                
            self.supermemory_client.add(
                content=content,
                container_tag=self.container_tag,
                custom_id=f"session_{self.container_tag}",  
            )
        
        except Exception as e:
            logger.error(f"Failed to add memory to Supermemory: {e}")
            self.alternative_memory.append_history(content)  # Fallback to local history

    def get_user_long_term_memory(self) -> str:
        
        try:
            result = self.supermemory_client.profile(container_tag=self.container_tag)
            static_memory = result.profile.static or []
            dynamic_memory = result.profile.dynamic or []
            long_term_memory =  "Long term facts: \n " +  "\n".join(static_memory) + "\n --- \n"  + "Recent context: \n" +  "\n".join(dynamic_memory)

            return long_term_memory
        
        except Exception as e:
            logger.error(f"Failed to retrieve memory from Supermemory: {e}")
            return self.alternative_memory.read_long_term()  # Fallback to local long-term memory

    def get_context(self, query: str) -> str:
       
        try:
            """Get relevant memory context for the current conversation."""
            response = self.supermemory_client.profile(
                container_tag=self.container_tag,
                q=query
            )

            # Extract profile fields
            static_context = response.profile.static or []
            dynamic_context = response.profile.dynamic or []

            # Search results - access via attributes, not dict methods
            # results = response.search_results.results if response.search_results else []
            

            context = (
                "User Background: " + "\n".join(static_context) + "\n"
                "Current Context: " + "\n".join(dynamic_context) + "\n"
            )

            return context
        
        except Exception as e:
            logger.error(f"Failed to get memory context from Supermemory: {e}")
            return self.alternative_memory.get_memory_context()  # Fallback to local memory context

