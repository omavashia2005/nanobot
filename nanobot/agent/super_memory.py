"""
Intelligent memory system using https://supermemory.ai
"""

from supermemory import Supermemory
from pathlib import Path
from nanobot.config.loader import load_config

class SupermemoryStore:
    """
    Agent memory using Supermemory for persistent, searchable, and structured memory.
    """

    def __init__(self):
        config = load_config()
        self.api_key = config.supermemory.api_key
        self.container_tag = config.supermemory.container_tag or "nanobot_memory"
        self.supermemory_client = Supermemory(api_key=self.api_key)

    def add_memory(self, content: str) -> None:
        """Add a new memory entry."""
        if content == "New session started. Memory consolidation in progress. ":
            return
            
        self.supermemory_client.add(
            content=content,
            container_tag=self.container_tag,
            custom_id=f"session_{self.container_tag}",  
        )


    def get_user_long_term_memory(self) -> str:
        result = self.supermemory_client.profile(container_tag=self.container_tag)
        static_memory = result.profile.static or []
        dynamic_memory = result.profile.dynamic or []
        long_term_memory =  "Long term facts: \n " +  "\n".join(static_memory) + "\n --- \n"  + "Recent context: \n" +  "\n".join(dynamic_memory)

        return long_term_memory

    def get_memory_context(self, query: str) -> str:
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
