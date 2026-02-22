from nanobot.agent.memory import MemoryStore
from supermemory import Supermemory
from nanobot.config.loader import load_config
from loguru import logger
from pathlib import Path
from typing import List
import requests
from nanobot.session import Session, SessionManager
from nanobot.utils.helpers import ensure_dir
import json
import asyncio

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
        self.base_url = "https://api.supermemory.ai/v4"
        self.sessions_dir = ensure_dir(Path.home() / ".nanobot" / "failed_sessions")
        self.session_manager = SessionManager(workspace)


    async def clear_failed_sessions(self):
        """Clear all failed sessions from the failed_sessions directory."""

        i = 0

        for session_file in self.sessions_dir.glob("*.jsonl"):
            try:
                # parse session file and extract messages 
                with session_file.open("r") as file:
                    messages = [json.loads(line) for line in file]
                
                if i % 3 == 0:
                    await asyncio.sleep(2)  # Sleep to avoid hitting rate limits
                
                await self.update_conversation(messages, None)  # Pass None for session since we're not saving failed sessions here

                logger.info(f"Parsed messages from failed session file: {session_file}")
                
                session_file.unlink()
        
                logger.info(f"Deleted failed session file: {session_file}")
                
                i += 1
        
            except Exception as e:
                logger.error(f"Error deleting failed session file {session_file}: {e}")
        
    
    async def update_conversation(self, messages : List[dict], session : Session | None) -> bool:
        try:
            url = self.base_url + "/conversations"
            
            payload = {
                        "conversationId": f"session_{self.container_tag}",
                        "messages": messages,
                    }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
                    }

            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to update conversation in Supermemory: {response.text}")
                raise Exception(f"Supermemory API error: {response.status_code} - {response.text}")

            return True
        
        except Exception as e:
            logger.exception(f"Error while updating conversation in Supermemory: {e}")
            if session is not None:
                session_path = self.sessions_dir / f"{session.key.replace(':', '_')}.jsonl"
                self.session_manager.save(session, session_path)  # Save the session to failed_sessions for later retry
            else:
                logger.error("No session provided to save failed conversation.")
            
            return False
        
    
    def add_memory(self, content: str):
        try:
            """Add a new memory entry."""
                
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
                q=query, 
                threshold=0.6,
            )

            # Extract profile fields
            static_context = response.profile.static or []
            dynamic_context = response.profile.dynamic or []

            # Search results - access via attributes, not dict methods
            results = response.search_results.results if response.search_results else []
            relevant_chunks, relevant_memories = [], []
            
            for res in results:
                relevant_memories += res.get("memory", [])
                relevant_chunks += res.get("chunks", [])

            context = f"""
                User Background:
                {chr(10).join(static_context) if static_context else 'No profile yet.'}

                Current Context:
                {chr(10).join(dynamic_context) if dynamic_context else 'No recent activity.'}

                # Relevant Memories & Info:
                {chr(10).join(relevant_memories) if relevant_memories else 'None found.'}
                {chr(10).join(relevant_chunks) if relevant_chunks else 'None found.'}
                """
            return context
        
        except Exception as e:
            logger.error(f"Failed to get memory context from Supermemory: {e}")
            return self.alternative_memory.get_memory_context()  # Fallback to local memory context

