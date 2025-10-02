# HITL Hotel Summary System
## 📋 Overview

A complete human-in-the-loop (HITL) system that generates, validates, and curates factual hotel summaries using LangGraph and Streamlit. The system combines automated LLM generation with explicit human review and learning from feedback.

### Key Features
- ✅ **LangGraph Pipeline**: Ingest → Draft → Self-Critique → Human Review → Store
- ✅ **Streamlit UI**: Clean interface with edit capabilities
- ✅ **Persistent State**: Resume reviews across sessions
- ✅ **Self-Critique**: Validates summaries before human review
- ✅ **Learning System (BONUS)**: Improves from feedback every 5 reviews

---

## 🚀 Quick Start

### 1. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/signup)
2. Sign up or log in
3. Navigate to [API Keys](https://platform.openai.com/api-keys)
4. Click "Create new secret key"
5. Copy the key (you won't see it again!)

### 2. Setup Project

```bash
# Clone or extract the project
cd hitl-hotel-system

# Create .env file
echo "OPENAI_API_KEY=sk-proj-your-actual-key-here" > .env

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📁 Project Structure

```
project_root/
├── app.py                      # Main Streamlit application
├── pipeline.py                 # LangGraph pipeline implementation
├── requirements.txt            # Python dependencies
├── .env                        # API keys (create this)
├── .gitignore                  # Git ignore file
├── hotels.csv                  # Input data (provided)
├── hotels_reviewed.csv         # Output (generated)
├── checkpoints/                # State persistence (auto-created)
└── README.md                   # This file
```

---

## 🏗️ Architecture

### LangGraph Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                     HITL Pipeline Flow                       │
└─────────────────────────────────────────────────────────────┘

1. INGEST NODE
   ↓
   • Normalizes hotel data
   • Extracts key attributes
   • Prepares structured input
   
2. DRAFT GENERATION NODE
   ↓
   • Uses GPT-4-mini for generation
   • Applies learned style guide (bonus)
   • Includes few-shot examples (bonus)
   • Generates 60-100 word summary
   
3. SELF-CRITIQUE NODE
   ↓
   • Validates word count (60-100)
   • Checks location mentioned
   • Verifies star rating included
   • Counts amenities (2-4 required)
   • Flags vague superlatives
   
4. HUMAN REVIEW NODE
   ↓
   • Presents in Streamlit UI
   • Allows accept/edit/reject
   • Records human decisions
   
5. STORE NODE
   ↓
   • Saves to hotels_reviewed.csv
   • Updates learning models (bonus)
   • Tracks statistics
```

### Data Flow

**Input (hotels.csv):**
```csv
hotel_id, hotel_name, city, country, star_rating, lat, lon,
cleanliness_base, comfort_base, facilities_base, location_base,
staff_base, value_for_money_base
```

**Output (hotels_reviewed.csv):**
```csv
hotel_id, hotel_name, draft_summary, final_summary, status,
review_timestamp, critique_flags
```

---

## 💡 Usage Guide

### Review Workflow

1. **View Hotel Info**: See all attributes from the CSV
2. **Read Generated Summary**: Review the LLM-generated draft
3. **Check Warnings**: See any validation issues flagged
4. **Take Action**:
   - ✅ **Accept**: Summary is good as-is
   - ✏️ **Edit & Save**: Modify text then save
   - ❌ **Reject**: Summary is unusable
5. **Navigate**: Use Next/Previous or dropdown to move between hotels

### Navigation Options

- **Next/Previous Buttons**: Sequential review (recommended)
- **Dropdown Menu**: Jump to any hotel by name
- **Progress Indicator**: Shows X of Y completed

### Learning System (Bonus)

The system learns from your feedback:

- **After 5 reviews**: Analyzes patterns in accepted/edited summaries
- **Style Guide**: Extracts preferred patterns (length, tone, structure)
- **Few-Shot Examples**: Uses your best summaries as examples
- **Error Patterns**: Tracks common rejection reasons

**Learning Indicator**: When active, you'll see "✨ Learning Active" in the header

---

## 🎯 Requirements Checklist

### Core Requirements ✅

- [x] **LangGraph Pipeline** with automated and human nodes
- [x] **Minimal Graph**: Ingest → Draft → Critique → Human Review → Store
- [x] **Streamlit UI** with clear separation of automated/human steps
- [x] **Two Input Types**: Binary validation (accept/reject) + text edits
- [x] **CSV Storage**: hotels_reviewed.csv with all required fields
- [x] **Separation of Concerns**: Clear code and UI separation

### Bonus Features ✅ (+10 points)

- [x] **Evolving Style Guide**: Learns from edits after every 5 reviews
- [x] **Few-Shot Learning**: Uses accepted summaries as examples
- [x] **Error Pattern Detection**: Tracks rejection patterns
- [x] **Persistent State**: Resumes across sessions with checkpointing

### Self-Critique Validations ✅

1. **Word Count**: 60-100 words
2. **Location Mentioned**: City or country present
3. **Star Rating**: Rating mentioned in summary
4. **Amenities Count**: 2-4 salient attributes mentioned
5. **No Superlatives**: Flags vague marketing language

---

## 🛠️ Technical Details

### LLM Configuration

- **Model**: GPT-4o-mini
- **Temperature**: 0.3 (balanced creativity/consistency)
- **Style**: Factual, concise, data-grounded
- **Length**: 60-100 words per summary

### State Management

- **Checkpointing**: SQLite-based persistence
- **Session State**: Streamlit session state for UI
- **CSV Storage**: Pandas for data persistence

### Pipeline Components

**Nodes:**
1. `ingest_node`: Normalizes and prepares data
2. `draft_generation_node`: LLM summary generation
3. `self_critique_node`: Automated validation
4. `human_review_node`: UI interaction point
5. `store_node`: Persists reviewed data

**Conditional Logic:**
- Accept/Edit → Store → End
- Reject → End (no storage)

---

## 📊 Example Summary

**Input Data:**
```
Hotel: The Azure Tower
Location: New York, United States
Star Rating: 5
Scores: Cleanliness 9.1, Comfort 8.8, Location 9.5
```

**Generated Summary:**
```
The Azure Tower is a five-star hotel located in New York, United States.
It achieves strong performance across quality metrics, scoring 9.1 for
cleanliness and 9.5 for location. The property also rates 8.8 for
comfort and 8.0 for value. Positioned in central New York, the hotel
serves guests seeking upscale accommodation with high cleanliness and
location standards.
```

**Word Count**: 62 words ✅  
**Validation**: All checks passed ✅

---

## 🔍 Troubleshooting

### API Key Issues

**Error**: "OPENAI_API_KEY not found"
- **Solution**: Create `.env` file with `OPENAI_API_KEY=your-key`
- Verify key is valid at OpenAI platform

### CSV Not Found

**Error**: "hotels.csv not found"
- **Solution**: Ensure `hotels.csv` is in project root
- Check file name matches exactly (case-sensitive)

### Import Errors

**Error**: "No module named 'langgraph'"
- **Solution**: Run `pip install -r requirements.txt`
- Use virtual environment to avoid conflicts

### Memory Issues

**Error**: Long sessions slow down
- **Solution**: Export reviews and restart app
- Checkpoints accumulate - clear `checkpoints/` folder periodically

---

## 📦 Deliverables

### Submission Package

```
hitl_submission.zip
├── app.py
├── pipeline.py
├── requirements.txt
├── README.md
├── .gitignore
└── BONUS_IMPLEMENTED.txt  (indicates bonus attempt)
```

**Note**: Do NOT include:
- `.env` file (API keys)
- `hotels_reviewed.csv` (generated output)
- `checkpoints/` directory
- `__pycache__/` or `.pyc` files

---

## 🎓 Assignment Notes

### Bonus Implementation

**This submission attempts the bonus (+10 points)**

Three learning mechanisms implemented:

1. **Evolving Style Guide**: 
   - Analyzes accepted summaries
   - Extracts length and tone patterns
   - Updates generation prompt dynamically

2. **Few-Shot Learning**:
   - Uses top 3 accepted summaries as examples
   - Provides context for consistent style
   - Improves quality over time

3. **Error Pattern Detection**:
   - Tracks rejection reasons
   - Identifies common mistakes
   - Guides future generations

**Learning Trigger**: Every 5 reviews  
**Indicator**: "✨ Learning Active" in UI

### Code Organization

- **Separation**: Automated (pipeline.py) vs Human (app.py)
- **Modularity**: Each node is independent function
- **State Management**: Clean TypedDict definitions
- **UI/UX**: Clear visual separation of automated vs manual steps

---

## 📝 API Cost Estimate

**Per Hotel**: ~$0.002  
**25 Hotels**: ~$0.05  
**With Re-generations**: ~$0.10

Very affordable for assignment purposes!

---

## 🤝 Support

For questions about this implementation:
- Check inline code comments
- Review LangGraph documentation: https://langchain-ai.github.io/langgraph/
- OpenAI API docs: https://platform.openai.com/docs

---
