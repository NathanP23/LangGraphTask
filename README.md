# Communication Health Analysis with LangGraph

This project analyzes communication threads (emails/messages) or meeting transcripts to produce structured "communication health" metrics using LangGraph and LLMs.

## What is Communication Health?

Communication health reflects how effectively a team or group communicates, measured across five key dimensions:

- **Tone** (25%): Sentiment, civility, and absence of toxic language
- **Clarity** (25%): Clear action items, decision ownership, and unambiguous language  
- **Responsiveness** (20%): Timeliness of responses between participants
- **Participation** (15%): Balanced contribution across team members
- **Engagement** (15%): Active participation through questions and acknowledgments

The overall score combines these dimensions into a 0-100 health rating with actionable insights.

## LangGraph Workflow Architecture

```{.plaintext}
           Input Detection & Routing
                       ↓
           ┌───────────────────────┐
           │ Raw text or JSON blob │
           └───────────────────────┘
           ↓ yes                ↓ no
┌─────────────────────┐ ┌──────────────────────┐
│ structure_from_text │ │ normalize_structured │
│ LLM → draft JSON    │ │ Clean, coerce types  │
└─────────────────────┘ └──────────────────────┘
           ↓                       ↓
           └───────────┬───────────┘
                       ↓
              ┌──────────────────┐
              │ validate_schema  │  ← if hard fail → remediation_llm
              └──────────────────┘
                       ↓
              ┌──────────────────┐
              │ dedupe_threads   │  ← collapse quoted emails, merge repeats
              └──────────────────┘
                       ↓
              ┌──────────────────┐
              │ chunk_if_needed  │  ← batch by tokens, retain turn map
              └──────────────────┘
                       ↓
      ┌──────────────────────────────────────┐
      │ conditional_edge: timestamps_present?│
      └──────────────────────────────────────┘
             ↓ yes                ↓ no
      ┌──────────────────┐ ┌──────────────────┐
      │ basic_stats_full │ │ basic_stats_text │
      │ incl. latency    │ │ excludes latency │
      └──────────────────┘ └──────────────────┘
           ↓                       ↓
           └───────────┬───────────┘
                       ↓
              ┌────────────────┐
              │  llm_extract   │  ← fan out per chunk
              └────────────────┘
                       ↓
              ┌────────────────┐
              │  merge_chunks  │  ← reconcile per-turn outputs
              └────────────────┘
                       ↓
              ┌────────────────┐
              │evidence_collect│
              └────────────────┘
                       ↓
              ┌────────────────┐
              │calibrate_scores│ ← optional scaling by baselines
              └────────────────┘
                       ↓
              ┌────────────────┐
              │generate_report │
              └────────────────┘
                       ↓
              ┌────────────────┐
              │finalize_output │ ← schema, version, run_id
              └────────────────┘
                       ↓
                  Final JSON

[Graph compiled with checkpointer]
- dev: InMemory
- optional: SQLite for reproducible threads


```

### Why This Design?

1. **Hybrid Analysis**: Combines objective metrics (response times, word counts) with LLM semantic analysis (tone, decisions)
2. **Single-Pass LLM**: One structured extraction call for efficiency, with fallback error handling
3. **Stateful Pipeline**: Each node reads/writes shared state, enabling complex data flow
4. **Explainable Scoring**: Clear formulas and weights that stakeholders can understand and adjust

## Quick Start

### 1. Download and Setup Project

```bash
# Clone the repository
git clone https://github.com/NathanP23/LangGraphTask.git
cd LangGraphTask

# Create and activate virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set API Key

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
export OPENAI_API_KEY="your-key-here"
```

### 4. Run Analysis

```bash
python main.py
```

### 5. Use with Your Data

#### Option A: Raw Text Input

```python
from comm_health_graph import analyze_raw_text

# Raw transcript or email thread
raw_text = """
Alice: Let's discuss the project timeline
Bob: Sounds good, what's the current status?
Alice: We're on track but need to finalize the requirements
"""

report = analyze_raw_text(raw_text)
print(json.dumps(report, indent=2))
```

#### Option B: Structured JSON Input

```python
from comm_health_graph import analyze_structured_data

# Pre-structured data
data = [
    {
        "ts": "2025-09-12T09:00:00Z",
        "speaker": "Alice", 
        "text": "Let's discuss the project timeline",
        "kind": "meeting"
    },
    # ... more turns
]

report = analyze_structured_data(data)
print(json.dumps(report, indent=2))
```

## Sample Output

```json
{
  "summary": "Communication shows strong engagement with 4 questions asked and collaborative problem-solving. The team demonstrated good responsiveness with a median response time of 98 minutes. However, clarity could improve as 0 action items lack clear ownership. Overall tone remains positive throughout the discussion.",
  "overall_health": {
    "score": 78.3,
    "label": "healthy"
  },
  "dimensions": {
    "tone": {"score": 85.0, "description": "Sentiment and civility of communication"},
    "clarity": {"score": 100.0, "description": "Clear action items and decision ownership"},
    "responsiveness": {"score": 76.9, "description": "Timeliness of responses"},
    "participation": {"score": 66.7, "description": "Balance of contribution"},
    "engagement": {"score": 56.0, "description": "Level of active participation"}
  },
  "extracted_content": {
    "decisions": ["Launch with basic OAuth only", "Postpone custom registration flows"],
    "action_items": [
      {"task": "Create wireframes for simplified auth flow", "owner": "Alex", "due_date": "end of week"},
      {"task": "Backend OAuth implementation", "owner": "Mike", "due_date": "next Friday"}
    ],
    "risk_flags": []
  }
}
```

## Key Features

### LLM Integration Points

- **Primary Analysis** (`llm_extract`): Structured JSON extraction of tone, decisions, action items, and risks
- **Report Generation** (`generate_report`): Natural language explanation of health scores with evidence

### Deterministic Metrics

- Response latency calculation between different speakers
- Participation balance via word count distribution  
- Question counting and engagement proxies
- Risk detection for unassigned action items

### Robust Error Handling

- Graceful LLM parsing failures with fallback data
- Timestamp parsing with multiple format support
- Empty turn filtering and quote stripping for emails

## Project Structure

```{.plaintext}
LangGraphTask/
├── main.py                          # Entry point - demo/test runner
├── comm_health_graph.py             # Main graph construction and public API
├── config.py                       # Centralized configuration organized by LangGraph node flow
├── requirements.txt                 # Dependencies (langgraph, openai, python-dotenv)
├── .env.example                     # Template for API keys
├── nodes/                           # LangGraph workflow nodes
│   ├── input_detection.py          # detect_input_type - route raw text vs structured input
│   ├── structure_extraction.py     # structure_from_text - LLM converts text to JSON
│   ├── normalization.py            # normalize_structured - clean and standardize fields
│   ├── validation.py               # validate_schema + remediation_llm - data validation/fixing
│   ├── preprocessing.py            # dedupe_threads + chunk_if_needed - data preprocessing
│   ├── statistics.py               # basic_stats_full/text - objective metrics calculation
│   ├── llm_extract.py              # llm_extract - semantic analysis via LLM
│   ├── merge_chunks.py             # merge_chunks - combine insights from multiple chunks
│   ├── evidence_collect.py         # evidence_collect - gather supporting evidence
│   ├── calibrate_scores.py         # calibrate_scores - normalize and weight scores
│   └── reporting.py                # generate_report + finalize_output - create final report
├── sample_data/                     # Test data samples
│   ├── meeting_transcript.json     # Sample meeting data
│   └── raw_text_example.txt        # Unstructured text sample
├── reports/                         # Generated analysis reports (created at runtime)
└── README.md                       # This comprehensive documentation
```

## Testing with Sample Data

The main.py script includes comprehensive testing of all input methods:

```bash
# Run the complete test suite
python main.py

# This tests all 4 scenarios:
# 1. analyze_structured_data() with meeting transcript
# 2. analyze_raw_text() with unstructured text
# 3. analyze_communication_health() auto-detecting structured data
# 4. analyze_communication_health() auto-detecting raw text

# All reports are saved to reports/ directory with timestamps
```

**Manual Testing:**
```python
from comm_health_graph import analyze_communication_health

# Auto-detect input type (recommended)
with open('sample_data/raw_text_example.txt') as f:
    raw_text = f.read()

report = analyze_communication_health(raw_text)
print(json.dumps(report, indent=2))
```

## Extending the Analysis

### Adding New Metrics

1. **Deterministic metrics**: Add calculations to `nodes/statistics.py`
2. **LLM-based metrics**: Update JSON schema in `config.py` HEALTH_INSIGHTS_JSON_SCHEMA
3. **Scoring**: Modify weights and formulas in `nodes/calibrate_scores.py`
4. **Configuration**: Add new parameters to `config.py` organized by node

### Alternative LLM Providers

To use different LLM providers, update the OpenAI client calls in:
- `nodes/structure_extraction.py`
- `nodes/validation.py`
- `nodes/llm_extract.py`

Example for Anthropic Claude:
```python
# Replace OpenAI client with Anthropic
from anthropic import Anthropic
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

### Persistence

Switch from `MemorySaver` to `SqliteSaver` for persistent state:

```bash
pip install langgraph-checkpoint-sqlite
```

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from comm_health_graph import create_communication_health_graph

# Modify comm_health_graph.py to use SqliteSaver
graph = workflow.compile(checkpointer=SqliteSaver("checkpoints.db"))
```

## Design Philosophy

This implementation balances **product thinking** with **technical execution**:

- **Measurable**: Each dimension has clear 0-100 scoring with explainable formulas
- **Actionable**: Reports identify specific improvement areas with evidence
- **Scalable**: Graph design supports adding new analysis nodes and conditional routing
- **Reliable**: Graceful error handling ensures analysis completes even with LLM failures

The goal is not perfect accuracy, but rather **consistent, useful insights** that help teams improve their communication patterns over time.
