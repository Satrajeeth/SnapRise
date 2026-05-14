import logging
import aiohttp
import json
from typing import Any, Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.default_llm_provider
        self.openai_key = settings.openai_api_key
        self.local_url = settings.local_llm_url

    async def chat_completion(
            self,
            messages: List[Dict[str, str]],
            model: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 500,
            api_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Generic chat completion that routes to either OpenAI or a local LLM.
        Supports passing an override API key (e.g. from user settings).
        """
        provider = self.provider
        key = api_key or self.openai_key

        # If no key but provider is openai , fallback to local or error
        if provider == "openai" and not key:
            logger.warning("OpenAI provider selected but no API key found. Falling back to local LLM.")
            provider = "local"  

        if provider == "openai":
            return await self._openai_chat(messages, model, temperature, max_tokens, key)
        else:
            return await self._local_chat(messages, model, temperature, max_tokens)

    async def _openai_chat(self, messages, model, temp, tokens, key) -> Optional[str]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or settings.default_model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": tokens
        }
        return await self._make_request(url, headers, payload)
    
async def _local_chat(self, messages , model, temp , tokens) -> Optional[str]:
    url = self.local_url + "/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "model": model or "local-model",
        "messages": messages,
        "temperature": temp,
        "max_tokens": tokens
    }
    return await self._make_request(url, headers, payload)

async def _make_request(self, url, headers, payload) -> Optional[str]:
    try: 
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                if response.status == 200:
                    error_text = await response.text()
                    logger.error(f"AI API error({response.status}): {error_text}")
                    return None
                
                data = await response.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI service request failed: {str(e)}")
        return None
    
async def summarize_task(self, title: str, content: Optional[str]) -> Optional[str]:
    """Generate a concise summary of a task."""
    if not content:
        return "No content to summarize."
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes project tasks. Be concise (max 2 sentences)."},
        {"role": "user", "content": f"Title: {title}\nDescription: {content}\n\nSummarize this task:"}
    ]
    return await self.chat_completion(messages, max_tokens=100)

async def detect_blockers(self, title: str, content: Optional[str], subtasks: List[str]) -> Optional[str]:
    """Detect potential blockers or risks for a task."""
    subtasks_str = "\n".join([f"- {s}" for s in subtasks]) if subtasks else "No subtasks."
    prompt = (
        f"Title: {title}\n"
        f"Description: {content or 'No description.'}\n"
        f"Subtasks:\n{subtasks_str}\n\n"
        "Analyze this task for potential blockers, dependencies, or risks. "
        "If none found, say 'None detected'. Otherwise, list them concisely."
    )

    messages = [
        {"role": "system", "content": "You are a project management expert. Analyze tasks for risks and blockers."},
        {"role": "user", "content": prompt}
    ]
    return await self.chat_completion(messages, max_tokens=200)

async def suggest_task_classification(self, title: str, content: Optional[str], columns: List[str]) -> Optional[str]:
    """Suggest the most appropriate column for a task."""
    columns_str = ", ".join(columns)
    prompt = (
            f"Task Title: {title}\n"
            f"Task Description: {content or 'No description.'}\n"
            f"Available Columns: {columns_str}\n\n"
            "Based on the task content, which column is the most appropriate? "
            "Respond ONLY with the column name."
        )
    messages = [
            {"role": "system", "content": "You are an expert project manager. Classify tasks into columns accurately."},
            {"role": "user", "content": prompt}
        ]
    return await self.chat_completion(messages, max_tokens=50)

def get_ai_service() -> AIService:
    return AIService()
