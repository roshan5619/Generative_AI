"""
LangGraph Pipeline for HITL Hotel Summary Generation
Implements: Ingest → Draft → Self-Critique → Human Review → Store
"""

from typing import TypedDict, Literal, Optional, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json
import os
from datetime import datetime
from operator import add

# State definition
class HotelState(TypedDict):
    hotel_id: int
    hotel_data: dict
    draft_summary: Optional[str]
    critique_results: Optional[dict]
    final_summary: Optional[str]
    human_action: Optional[Literal["accept", "reject", "edit"]]
    review_timestamp: Optional[str]
    style_guide: Optional[str]
    few_shot_examples: Optional[List[dict]]
    error_patterns: Optional[List[str]]


class HotelSummaryPipeline:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            openai_api_key=api_key
        )
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph pipeline"""
        workflow = StateGraph(HotelState)
        
        # Add nodes
        workflow.add_node("ingest", self.ingest_node)
        workflow.add_node("draft", self.draft_generation_node)
        workflow.add_node("critique", self.self_critique_node)
        workflow.add_node("human_review", self.human_review_node)
        workflow.add_node("store", self.store_node)
        
        # Define edges
        workflow.set_entry_point("ingest")
        workflow.add_edge("ingest", "draft")
        workflow.add_edge("draft", "critique")
        workflow.add_edge("critique", "human_review")
        
        # Conditional edge from human_review
        workflow.add_conditional_edges(
            "human_review",
            self.should_store,
            {
                "store": "store",
                "end": END
            }
        )
        workflow.add_edge("store", END)
        
        return workflow.compile()
    
    def ingest_node(self, state: HotelState) -> HotelState:
        """Normalize and prepare hotel data"""
        hotel_data = state["hotel_data"]
        
        # Normalize attribute names and extract key info
        normalized = {
            "name": hotel_data.get("hotel_name", "Unknown"),
            "city": hotel_data.get("city", "Unknown"),
            "country": hotel_data.get("country", "Unknown"),
            "star_rating": hotel_data.get("star_rating", 0),
            "location": f"{hotel_data.get('city', 'Unknown')}, {hotel_data.get('country', 'Unknown')}",
            "coordinates": f"{hotel_data.get('lat', 0)}, {hotel_data.get('lon', 0)}",
            "scores": {
                "cleanliness": hotel_data.get("cleanliness_base", 0),
                "comfort": hotel_data.get("comfort_base", 0),
                "facilities": hotel_data.get("facilities_base", 0),
                "location": hotel_data.get("location_base", 0),
                "staff": hotel_data.get("staff_base", 0),
                "value": hotel_data.get("value_for_money_base", 0)
            }
        }
        
        state["hotel_data"] = normalized
        return state
    
    def draft_generation_node(self, state: HotelState) -> HotelState:
        """Generate initial summary draft using LLM"""
        hotel = state["hotel_data"]
        style_guide = state.get("style_guide", "")
        few_shot = state.get("few_shot_examples", [])
        
        # Build prompt with style guide and examples if available
        base_prompt = """You are writing concise, factual hotel summaries based on structured data.

STYLE REQUIREMENTS:
- Length: 60-100 words, single paragraph
- Include: location (city, country), star rating, 2-4 notable scores/amenities
- Use concrete, data-grounded statements
- NO vague superlatives or marketing copy
- NO hallucinated facts
- Focus on factual attributes from the data

{style_guide}

{few_shot_examples}

HOTEL DATA:
Name: {name}
Location: {location}
Star Rating: {star_rating}
Top Scores: Cleanliness {cleanliness}, Comfort {comfort}, Facilities {facilities}, Location {location_score}

Write a summary paragraph (60-100 words):"""

        # Add learned style guide
        style_section = ""
        if style_guide:
            style_section = f"\nLEARNED STYLE PREFERENCES:\n{style_guide}\n"
        
        # Add few-shot examples
        examples_section = ""
        if few_shot:
            examples_section = "EXAMPLES OF GOOD SUMMARIES:\n"
            for ex in few_shot[:3]:  # Use top 3 examples
                examples_section += f"- {ex['summary']}\n"
            examples_section += "\n"
        
        prompt = ChatPromptTemplate.from_template(base_prompt)
        
        messages = prompt.format_messages(
            style_guide=style_section,
            few_shot_examples=examples_section,
            name=hotel["name"],
            location=hotel["location"],
            star_rating=hotel["star_rating"],
            cleanliness=hotel["scores"]["cleanliness"],
            comfort=hotel["scores"]["comfort"],
            facilities=hotel["scores"]["facilities"],
            location_score=hotel["scores"]["location"]
        )
        
        response = self.llm.invoke(messages)
        state["draft_summary"] = response.content.strip()
        
        return state
    
    def self_critique_node(self, state: HotelState) -> HotelState:
        """Validate draft against constraints"""
        draft = state["draft_summary"]
        hotel = state["hotel_data"]
        
        critique = {
            "word_count_valid": False,
            "location_mentioned": False,
            "star_rating_mentioned": False,
            "amenities_count": 0,
            "no_superlatives": True,
            "issues": []
        }
        
        # Check word count (60-100 words)
        word_count = len(draft.split())
        critique["word_count_valid"] = 60 <= word_count <= 100
        if not critique["word_count_valid"]:
            critique["issues"].append(f"Word count {word_count} (expected 60-100)")
        
        # Check location mentioned
        city = hotel["city"].lower()
        country = hotel["country"].lower()
        draft_lower = draft.lower()
        critique["location_mentioned"] = city in draft_lower or country in draft_lower
        if not critique["location_mentioned"]:
            critique["issues"].append("Location not clearly mentioned")
        
        # Check star rating
        star_rating = str(hotel["star_rating"])
        critique["star_rating_mentioned"] = star_rating in draft or "star" in draft_lower
        if not critique["star_rating_mentioned"]:
            critique["issues"].append("Star rating not mentioned")
        
        # Count amenity/score mentions (look for at least 2-4)
        score_keywords = ["cleanli", "comfort", "facilit", "staff", "value", "location score"]
        amenities_mentioned = sum(1 for kw in score_keywords if kw in draft_lower)
        critique["amenities_count"] = amenities_mentioned
        if amenities_mentioned < 2:
            critique["issues"].append(f"Only {amenities_mentioned} amenities mentioned (expected 2-4)")
        
        # Check for vague superlatives
        superlatives = ["amazing", "incredible", "stunning", "breathtaking", "perfect", "ultimate"]
        found_superlatives = [s for s in superlatives if s in draft_lower]
        if found_superlatives:
            critique["no_superlatives"] = False
            critique["issues"].append(f"Contains superlatives: {', '.join(found_superlatives)}")
        
        state["critique_results"] = critique
        return state
    
    def human_review_node(self, state: HotelState) -> HotelState:
        """Placeholder for human interaction - handled by Streamlit UI"""
        # This node is a marker for where human interaction happens
        # The actual review is done in the Streamlit interface
        # State will be updated with human_action and final_summary
        return state
    
    def store_node(self, state: HotelState) -> HotelState:
        """Store the reviewed summary"""
        state["review_timestamp"] = datetime.now().isoformat()
        return state
    
    def should_store(self, state: HotelState) -> Literal["store", "end"]:
        """Decide whether to store based on human action"""
        action = state.get("human_action")
        if action in ["accept", "edit"]:
            return "store"
        return "end"
    
    def run_until_human(self, hotel_id: int, hotel_data: dict, 
                        style_guide: str = "", 
                        few_shot_examples: List[dict] = None,
                        error_patterns: List[str] = None) -> HotelState:
        """Run pipeline until human review node"""
        initial_state = HotelState(
            hotel_id=hotel_id,
            hotel_data=hotel_data,
            draft_summary=None,
            critique_results=None,
            final_summary=None,
            human_action=None,
            review_timestamp=None,
            style_guide=style_guide,
            few_shot_examples=few_shot_examples or [],
            error_patterns=error_patterns or []
        )
        
        # Run through automated nodes
        state = initial_state
        state = self.ingest_node(state)
        state = self.draft_generation_node(state)
        state = self.self_critique_node(state)
        
        return state
    
    def complete_review(self, state: HotelState, 
                       action: Literal["accept", "reject", "edit"],
                       edited_summary: Optional[str] = None) -> HotelState:
        """Complete the review with human input"""
        state["human_action"] = action
        
        if action == "edit" and edited_summary:
            state["final_summary"] = edited_summary
        elif action == "accept":
            state["final_summary"] = state["draft_summary"]
        else:  # reject
            state["final_summary"] = None
        
        # Run store node if needed
        if action in ["accept", "edit"]:
            state = self.store_node(state)
        
        return state


def extract_style_patterns(accepted_summaries: List[str], edited_pairs: List[tuple]) -> str:
    """Extract style patterns from accepted/edited summaries"""
    patterns = []
    
    if len(accepted_summaries) >= 3:
        avg_length = sum(len(s.split()) for s in accepted_summaries) / len(accepted_summaries)
        patterns.append(f"- Preferred length: ~{int(avg_length)} words")
    
    if edited_pairs:
        # Analyze what changed in edits
        patterns.append("- Users prefer concise, direct language")
        patterns.append("- Emphasize factual scores over descriptions")
    
    return "\n".join(patterns) if patterns else ""