import google.generativeai as genai
import os
from typing import Dict, List
import json

class GeminiAssistant:
    """
    AI Assistant powered by Gemini for explaining validation results.
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash-lite"):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)
        
    def generate_summary(self, validation_results: Dict, root_causes: List[Dict], fixes: List[Dict]) -> str:
        """
        Generate a comprehensive summary of the validation analysis.
        """
        prompt = self._build_summary_prompt(validation_results, root_causes, fixes)
        
        response = self.model.generate_content(prompt)
        return response.text
    
    def answer_question(self, question: str, context: Dict) -> str:
        """
        Answer user questions about validation results interactively.
        """
        prompt = f"""You are Nyx, an expert data validation assistant. 
        
Context (validation data):
{json.dumps(context, indent=2)}

User Question: {question}

Provide a clear, concise answer based on the validation data above. If the question asks about specific metrics or campaigns, reference the exact numbers from the context."""

        response = self.model.generate_content(prompt)
        return response.text
    
    def _build_summary_prompt(self, validation_results: Dict, root_causes: List[Dict], fixes: List[Dict]) -> str:
        """Build the prompt for summary generation."""
        
        # Extract key metrics
        overall_match_rate = validation_results.get('summary', {}).get('overall_match_rate', 0)
        total_segments = validation_results.get('summary', {}).get('total_segments', 0)
        passing_segments = validation_results.get('summary', {}).get('passing_segments', 0)
        
        prompt = f"""You are Nyx, an AI-powered data validation assistant. Analyze this validation report and provide a professional, actionable summary.

VALIDATION RESULTS:
- Overall Match Rate: {overall_match_rate}%
- Segments Passing: {passing_segments}/{total_segments}

ROOT CAUSES IDENTIFIED:
{json.dumps(root_causes, indent=2)}

SUGGESTED FIXES:
{json.dumps([f['pandas_fix'] for f in fixes], indent=2)}

Generate a summary that:
1. Starts with an EXECUTIVE SUMMARY (2-3 sentences on data health)
2. Lists KEY FINDINGS (bullet points for each root cause with confidence)
3. RECOMMENDED ACTIONS (which fixes to apply first, in priority order)
4. NEXT STEPS (what the user should investigate further)

Keep it professional but conversational. Use emojis sparingly (1-2 max). Be specific with numbers."""

        return prompt
    
    def stream_response(self, prompt: str):
        """
        Stream responses for real-time chat experience.
        Yields chunks of text as they're generated.
        """
        response = self.model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
