# learning_system.py
import pandas as pd
import json
from typing import List, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

class FeedbackLearner:
    def __init__(self):
        self.feedback_history = []
        self.style_guide_updates = []
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.1,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    
    def add_feedback(self, hotel_id: str, action: str, original_draft: str, final_text: str):
        """Add new feedback to learning system"""
        feedback_record = {
            "hotel_id": hotel_id,
            "action": action,
            "original_draft": original_draft,
            "final_text": final_text
        }
        self.feedback_history.append(feedback_record)
    
    def analyze_feedback_patterns(self):
        """Analyze feedback to identify common correction patterns using Gemini"""
        edits = [f for f in self.feedback_history if f["action"] == "edit"]
        
        if not edits:
            return "No edit patterns detected yet."
        
        # Use Gemini to analyze patterns
        analysis_prompt = f"""
        Analyze these hotel summary edits to identify common patterns in human corrections:
        
        EDIT EXAMPLES:
        {json.dumps(edits[:5], indent=2)}
        
        Identify:
        1. Common types of factual errors in original drafts
        2. Frequent style improvements made by humans
        3. Missing elements that humans consistently add
        4. Length adjustment patterns
        
        Provide a concise analysis of improvement patterns.
        """
        
        try:
            messages = [
                SystemMessage(content="You are an analyst that identifies patterns in text edits."),
                HumanMessage(content=analysis_prompt)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"Pattern analysis failed: {e}"
    
    def get_improved_style_guide(self, base_style_guide: str) -> str:
        """Generate improved style guide based on feedback using Gemini"""
        patterns = self.analyze_feedback_patterns()
        
        if "No edit patterns" in patterns or "failed" in patterns:
            return base_style_guide
        
        improvement_prompt = f"""
        Based on this pattern analysis of human edits:
        
        {patterns}
        
        Generate specific improvements to add to the hotel summary style guide. Focus on concrete, actionable improvements.
        """
        
        try:
            messages = [
                SystemMessage(content="You improve style guides based on human feedback patterns."),
                HumanMessage(content=improvement_prompt)
            ]
            response = self.llm.invoke(messages)
            
            improved_guide = base_style_guide + "\n\nFEEDBACK-BASED IMPROVEMENTS:\n" + response.content
            return improved_guide
        except Exception as e:
            return base_style_guide  # Fixed variable name
    
    def get_few_shot_examples(self, count: int = 3) -> List[Dict]:
        """Get few-shot examples from accepted summaries for future generations"""
        accepted = [f for f in self.feedback_history if f["action"] in ["accept", "edit"]]
        
        if not accepted:
            return []
        
        examples = []
        for feedback in accepted[:count]:
            examples.append({
                "hotel_data": "Previous accepted summary",
                "summary": feedback["final_text"]
            })
        
        return examples
    
    def get_normalization_rules(self) -> Dict:
        """Generate normalization rules based on common edits"""
        edits = [f for f in self.feedback_history if f["action"] == "edit"]
        
        if not edits:
            return {}
        
        # Simple pattern: track common word replacements
        normalization_rules = {}
        
        for edit in edits:
            original_words = set(edit["original_draft"].lower().split())
            final_words = set(edit["final_text"].lower().split())
            
            # Find words that were removed (potentially problematic)
            removed_words = original_words - final_words
            for word in removed_words:
                if len(word) > 4:  # Only consider meaningful words
                    normalization_rules[word] = "REMOVE"
            
            # Find words that were added (potentially important)
            added_words = final_words - original_words
            for word in added_words:
                if len(word) > 4:
                    normalization_rules[word] = "PRIORITIZE"
        
        return normalization_rules