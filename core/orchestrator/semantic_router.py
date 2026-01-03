
import os
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

logger = logging.getLogger("athena.router")

class SemanticRouter:
    """
    The Traffic Controller.
    Decides USER INTENT based on conversation history.
    """
    
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.model_name = model_name
        self.api_key = os.getenv("GEMINI_API_KEY")
        
    def route(self, user_text: str, context_history: List[Dict], active_task: Optional[Dict] = None, active_reference: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Determine the intent and extract slots.
        
        Returns:
            Dict: {
                "intent": "schedule_event" | "research_topic" | "capture_note" | "finance_query" | "general_chat",
                "confidence": float,
                "slots": { ... },
                "reasoning": "User mentioned 'tomorrow'..."
            }
        """
        if not self.api_key:
            return {"intent": "general_chat", "confidence": 0.0, "slots": {}, "error": "No API Key"}

        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.api_key)
            
            # Format context for LLM
            history_str = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in context_history[-5:]])
            
            current_task_str = "None"
            if active_task:
                current_task_str = f"{active_task.get('intent')} (Status: {active_task.get('status')})"
            
            reference_str = "None"
            if active_reference:
                reference_str = f"User is referring to: {json.dumps(active_reference)[:500]}"

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get Context Tags for situational awareness
            context_tags_str = ""
            try:
                from core.context.context_tags import get_context_tagger
                tagger = get_context_tagger()
                tags = tagger.get_current_tags()
                context_tags_str = tags.to_prompt_string()
                context_hint = tagger._generate_context_hint(tags)
            except Exception:
                context_tags_str = "[No context tags]"
                context_hint = ""

            prompt = f"""
            You are the Router for Athena, an advanced AI assistant.
            Current Time: {now}
            CONTEXT: {context_tags_str}
            HINT: {context_hint}
            
            ACTIVE TASK: {current_task_str}
            ACTIVE REFERENCE: {reference_str} (Use this if user says 'that', '#5', 'it')
            
            RECENT HISTORY:
            {history_str}
            
            USER INPUT: "{user_text}"
            
            YOUR JOB:
            1. Classify intent into ONE of: 
               - [schedule_event] (meetings, reminders, calendar)
               - [research_topic] (look up info, summaries, deep dives)
               - [capture_note] (save thought, log generic info)
               - [finance_query] (money, budget, spending)
               - [email_search] (find email, check inbox)
               - [general_chat] (greetings, philosophy, basic Q&A)
               
            2. Extract SLOTS (parameters) for that intent.
               - schedule_event: title, start_time, duration_minutes, location
               - research_topic: query, depth (quick/deep)
               - email_search: query, sender, days_back
               
            3. RESOLVE PRONOUNS based on history (e.g., "it", "that", "there").
            
            Output JSON only:
            {{
                "intent": "string",
                "confidence": float (0.0-1.0),
                "slots": {{ key: value }},
                "reasoning": "brief explanation"
            }}
            """
            
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"Router failed: {e}")
            return {"intent": "general_chat", "confidence": 0.0, "slots": {}, "error": str(e)}
