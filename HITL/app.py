"""
Streamlit HITL Application for Hotel Summary Review
CMSC 691 - Assignment #2
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime
from pipeline import HotelSummaryPipeline, extract_style_patterns

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="HITL Hotel Summary System",
    page_icon="🏨",
    layout="wide"
)

# Constants
HOTELS_CSV = "hotels.csv"
REVIEWED_CSV = "hotels_reviewed.csv"
CHECKPOINT_DIR = "checkpoints"
LEARNING_THRESHOLD = 5  # Learn from feedback after every 5 reviews

# Initialize session state
def init_session_state():
    """Initialize Streamlit session state"""
    if "pipeline" not in st.session_state:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("❌ OPENAI_API_KEY not found in environment variables!")
            st.info("Please create a .env file with: OPENAI_API_KEY=your-key-here")
            st.stop()
        st.session_state.pipeline = HotelSummaryPipeline(api_key)
    
    if "hotels_df" not in st.session_state:
        if not os.path.exists(HOTELS_CSV):
            st.error(f"❌ {HOTELS_CSV} not found!")
            st.stop()
        st.session_state.hotels_df = pd.read_csv(HOTELS_CSV)
    
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    
    if "reviewed_data" not in st.session_state:
        st.session_state.reviewed_data = load_reviewed_data()
    
    if "current_state" not in st.session_state:
        st.session_state.current_state = None
    
    if "style_guide" not in st.session_state:
        st.session_state.style_guide = ""
    
    if "few_shot_examples" not in st.session_state:
        st.session_state.few_shot_examples = []
    
    if "error_patterns" not in st.session_state:
        st.session_state.error_patterns = []
    
    if "learning_active" not in st.session_state:
        st.session_state.learning_active = False


def load_reviewed_data() -> dict:
    """Load existing reviewed data"""
    if os.path.exists(REVIEWED_CSV):
        df = pd.read_csv(REVIEWED_CSV)
        return {row['hotel_id']: row.to_dict() for _, row in df.iterrows()}
    return {}


def save_review(state: dict):
    """Save review to CSV"""
    review_entry = {
        "hotel_id": state["hotel_id"],
        "hotel_name": state["hotel_data"]["name"],
        "draft_summary": state["draft_summary"],
        "final_summary": state["final_summary"],
        "status": state["human_action"],
        "review_timestamp": state["review_timestamp"],
        "critique_flags": json.dumps(state["critique_results"]["issues"])
    }
    
    st.session_state.reviewed_data[state["hotel_id"]] = review_entry
    
    # Save to CSV
    df = pd.DataFrame(list(st.session_state.reviewed_data.values()))
    df.to_csv(REVIEWED_CSV, index=False)
    
    # Update learning if threshold reached
    update_learning_models()


def update_learning_models():
    """Update style guide and few-shot examples from reviews (BONUS)"""
    reviews = list(st.session_state.reviewed_data.values())
    
    if len(reviews) % LEARNING_THRESHOLD == 0 and len(reviews) > 0:
        # Extract accepted and edited summaries
        accepted = [r["final_summary"] for r in reviews if r["status"] == "accept"]
        edited_pairs = [(r["draft_summary"], r["final_summary"]) 
                       for r in reviews if r["status"] == "edit"]
        
        # Update style guide
        st.session_state.style_guide = extract_style_patterns(accepted, edited_pairs)
        
        # Update few-shot examples (top 3 accepted)
        if accepted:
            st.session_state.few_shot_examples = [
                {"summary": s} for s in accepted[-3:]
            ]
        
        # Track rejection patterns
        rejected = [r for r in reviews if r["status"] == "reject"]
        if rejected:
            st.session_state.error_patterns = [
                "Users rejected summaries with poor structure",
                "Focus on concrete data points"
            ]
        
        st.session_state.learning_active = True


def generate_summary_for_current():
    """Generate summary for current hotel"""
    hotel_idx = st.session_state.current_index
    hotel_row = st.session_state.hotels_df.iloc[hotel_idx]
    hotel_id = int(hotel_row["hotel_id"])
    
    # Check if already reviewed
    if hotel_id in st.session_state.reviewed_data:
        st.session_state.current_state = st.session_state.reviewed_data[hotel_id]
        return
    
    # Generate new summary
    hotel_data = hotel_row.to_dict()
    
    state = st.session_state.pipeline.run_until_human(
        hotel_id=hotel_id,
        hotel_data=hotel_data,
        style_guide=st.session_state.style_guide,
        few_shot_examples=st.session_state.few_shot_examples,
        error_patterns=st.session_state.error_patterns
    )
    
    st.session_state.current_state = state


def render_header():
    """Render application header"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("🏨 HITL Hotel Summary System")
        st.caption("Human-in-the-Loop Data Curation for Hotel Summaries")
    
    with col2:
        total = len(st.session_state.hotels_df)
        reviewed = len(st.session_state.reviewed_data)
        st.metric("Progress", f"{reviewed}/{total}", 
                 f"{(reviewed/total*100):.0f}% Complete")
    
    with col3:
        if st.session_state.learning_active:
            st.success("✨ Learning Active")
            st.caption(f"Updated after {len(st.session_state.reviewed_data)} reviews")
        else:
            st.info("🎯 Initial Mode")


def render_hotel_info(state):
    """Render hotel information section"""
    hotel = state["hotel_data"]
    
    st.subheader("📋 Hotel Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"**Name:** {hotel['name']}")
        st.markdown(f"**Location:** {hotel['location']}")
        st.markdown(f"**Rating:** {'⭐' * int(hotel['star_rating'])}")
    
    with col2:
        st.markdown("**Quality Scores:**")
        scores = hotel['scores']
        st.markdown(f"🧹 Cleanliness: {scores['cleanliness']}")
        st.markdown(f"🛏️ Comfort: {scores['comfort']}")
        st.markdown(f"🏢 Facilities: {scores['facilities']}")
    
    with col3:
        st.markdown("**Service Scores:**")
        st.markdown(f"📍 Location: {scores['location']}")
        st.markdown(f"👥 Staff: {scores['staff']}")
        st.markdown(f"💰 Value: {scores['value']}")


def render_critique_warnings(critique):
    """Render self-critique warnings"""
    if critique["issues"]:
        st.warning("⚠️ **Self-Critique Warnings:**")
        for issue in critique["issues"]:
            st.markdown(f"- {issue}")
    else:
        st.success("✅ All validation checks passed!")


def render_review_interface(state):
    """Render the review interface"""
    st.subheader("📝 Generated Summary")
    
    # Show critique results
    render_critique_warnings(state["critique_results"])
    
    st.markdown("---")
    
    # Display draft in a box
    st.markdown("**Draft Summary:**")
    st.info(state["draft_summary"])
    
    word_count = len(state["draft_summary"].split())
    st.caption(f"Word count: {word_count} words")
    
    st.markdown("---")
    
    # Edit section
    st.markdown("**Review Actions:**")
    
    edited_text = st.text_area(
        "Edit summary (if needed):",
        value=state.get("final_summary") or state["draft_summary"],
        height=150,
        key="edit_box",
        help="Make any necessary corrections to the summary"
    )
    
    # Action buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    
    with col1:
        if st.button("✅ Accept", type="primary", use_container_width=True):
            handle_review_action("accept", state["draft_summary"])
    
    with col2:
        if st.button("✏️ Edit & Save", use_container_width=True):
            handle_review_action("edit", edited_text)
    
    with col3:
        if st.button("❌ Reject", use_container_width=True):
            handle_review_action("reject", None)


def handle_review_action(action, final_text):
    """Handle user review action"""
    state = st.session_state.current_state
    
    # Complete the review in pipeline
    completed_state = st.session_state.pipeline.complete_review(
        state, action, final_text
    )
    
    # Save to CSV
    save_review(completed_state)
    
    # Show success message
    if action == "accept":
        st.success("✅ Summary accepted!")
    elif action == "edit":
        st.success("✏️ Summary edited and saved!")
    elif action == "reject":
        st.warning("❌ Summary rejected.")
    
    # Auto-advance to next
    if st.session_state.current_index < len(st.session_state.hotels_df) - 1:
        st.session_state.current_index += 1
        st.session_state.current_state = None
        st.rerun()


def render_navigation():
    """Render navigation controls"""
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous", 
                    disabled=st.session_state.current_index == 0,
                    use_container_width=True):
            st.session_state.current_index -= 1
            st.session_state.current_state = None
            st.rerun()
    
    with col2:
        if st.button("➡️ Next", 
                    disabled=st.session_state.current_index >= len(st.session_state.hotels_df) - 1,
                    use_container_width=True):
            st.session_state.current_index += 1
            st.session_state.current_state = None
            st.rerun()
    
    with col3:
        current = st.session_state.current_index + 1
        total = len(st.session_state.hotels_df)
        st.markdown(f"<div style='text-align: center; padding-top: 8px;'><b>Hotel {current} of {total}</b></div>", 
                   unsafe_allow_html=True)
    
    with col4:
        # Jump to hotel dropdown
        hotel_names = st.session_state.hotels_df['hotel_name'].tolist()
        selected_idx = st.selectbox(
            "Jump to:",
            range(len(hotel_names)),
            format_func=lambda x: f"{x+1}. {hotel_names[x]}",
            key="jump_select",
            label_visibility="collapsed"
        )
        if selected_idx != st.session_state.current_index:
            st.session_state.current_index = selected_idx
            st.session_state.current_state = None
            st.rerun()


def render_sidebar():
    """Render sidebar with statistics and controls"""
    with st.sidebar:
        st.header("📊 Statistics")
        
        total = len(st.session_state.hotels_df)
        reviewed = len(st.session_state.reviewed_data)
        
        if reviewed > 0:
            accepted = sum(1 for r in st.session_state.reviewed_data.values() 
                         if r["status"] == "accept")
            edited = sum(1 for r in st.session_state.reviewed_data.values() 
                       if r["status"] == "edit")
            rejected = sum(1 for r in st.session_state.reviewed_data.values() 
                         if r["status"] == "reject")
            
            st.metric("Total Reviewed", reviewed)
            st.metric("Accepted", accepted, f"{accepted/reviewed*100:.0f}%")
            st.metric("Edited", edited, f"{edited/reviewed*100:.0f}%")
            st.metric("Rejected", rejected, f"{rejected/reviewed*100:.0f}%")
            
            st.markdown("---")
            
            # Learning status
            st.subheader("🧠 Learning Status")
            if st.session_state.learning_active:
                st.success("Active - Using feedback")
                if st.session_state.style_guide:
                    with st.expander("View Learned Patterns"):
                        st.markdown(st.session_state.style_guide)
            else:
                remaining = LEARNING_THRESHOLD - (reviewed % LEARNING_THRESHOLD)
                if reviewed == 0:
                    remaining = LEARNING_THRESHOLD
                st.info(f"Learning in {remaining} reviews")
        else:
            st.info("No reviews completed yet")
        
        st.markdown("---")
        
        # Export button
        if st.button("📥 Export Reviews", use_container_width=True):
            if os.path.exists(REVIEWED_CSV):
                with open(REVIEWED_CSV, 'r') as f:
                    st.download_button(
                        "Download CSV",
                        f.read(),
                        file_name=REVIEWED_CSV,
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.warning("No reviews to export yet")
        
        # Reset button
        st.markdown("---")
        if st.button("🔄 Reset All", use_container_width=True):
            if st.button("⚠️ Confirm Reset", use_container_width=True):
                if os.path.exists(REVIEWED_CSV):
                    os.remove(REVIEWED_CSV)
                st.session_state.reviewed_data = {}
                st.session_state.current_index = 0
                st.session_state.current_state = None
                st.session_state.style_guide = ""
                st.session_state.few_shot_examples = []
                st.session_state.learning_active = False
                st.rerun()


def render_already_reviewed(review_data):
    """Render interface for already reviewed hotels"""
    st.subheader("✅ Previously Reviewed")
    
    status_emoji = {
        "accept": "✅",
        "edit": "✏️",
        "reject": "❌"
    }
    
    st.info(f"{status_emoji.get(review_data['status'], '❓')} Status: **{review_data['status'].upper()}**")
    
    if review_data['status'] != 'reject':
        st.markdown("**Final Summary:**")
        st.success(review_data['final_summary'])
        
        if review_data['status'] == 'edit':
            with st.expander("View Original Draft"):
                st.markdown(review_data['draft_summary'])
    
    st.caption(f"Reviewed: {review_data['review_timestamp']}")
    
    # Option to re-review
    if st.button("🔄 Re-review this hotel"):
        del st.session_state.reviewed_data[review_data['hotel_id']]
        st.session_state.current_state = None
        st.rerun()


def main():
    """Main application"""
    init_session_state()
    
    render_header()
    render_sidebar()
    
    st.markdown("---")
    
    # Generate summary if not already done
    if st.session_state.current_state is None:
        with st.spinner("Generating summary..."):
            generate_summary_for_current()
    
    state = st.session_state.current_state
    
    # Check if this is a reviewed hotel
    if "status" in state:
        render_already_reviewed(state)
    else:
        # New review
        render_hotel_info(state)
        st.markdown("---")
        render_review_interface(state)
    
    # Navigation at bottom
    render_navigation()
    
    # Instructions footer
    with st.expander("ℹ️ How to Use"):
        st.markdown("""
        ### Instructions:
        1. **Review the hotel information** at the top
        2. **Check the generated summary** and any critique warnings
        3. **Choose an action:**
           - **Accept**: Summary is good as-is
           - **Edit & Save**: Make corrections in the text box first
           - **Reject**: Summary is not usable
        4. **Navigate** using Previous/Next buttons or the dropdown
        5. **Learning**: System improves after every 5 reviews
        
        ### Tips:
        - Summaries should be 60-100 words
        - Include location, star rating, and 2-4 key scores
        - Avoid vague language - be specific and factual
        - Your edits help the system learn your style!
        """)


if __name__ == "__main__":
    main()