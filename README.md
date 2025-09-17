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
├── config.py                       # Configuration parameters and hardcoded values
├── requirements.txt                 # Dependencies (langgraph, langchain, openai, etc.)
├── .env.example                     # Template for API keys
├── nodes/
│   ├── input_detection.py          # Route raw text vs structured input
│   ├── structure_extraction.py     # structure_from_text node
│   ├── normalization.py            # normalize_structured node
│   ├── validation.py               # validate_schema + remediation_llm
│   ├── preprocessing.py            # dedupe_threads, chunk_if_needed
│   ├── statistics.py               # basic_stats_full/text (objective metrics)
│   ├── llm_extraction.py           # llm_extract (semantic analysis)
│   ├── merging.py                  # merge_chunks, evidence_collect
│   ├── scoring.py                  # calibrate_scores
│   └── reporting.py                # generate_report, finalize_output
├── schemas/
│   ├── communication_schema.py     # Input validation schemas
│   └── health_report_schema.py     # Output format definitions
├── utils/
│   ├── text_utils.py               # Cleaning, deduplication helpers
│   ├── time_utils.py               # Timestamp parsing utilities
│   └── scoring_utils.py            # Score calculation formulas
├── sample_data/
│   ├── email_thread.json           # Sample email conversation
│   ├── meeting_transcript.json     # Sample meeting data
│   └── raw_text_example.txt        # Unstructured text sample
└── README.md                       # This comprehensive documentation
```

## Testing with Sample Data

```bash
# Test with email thread
python -c "
import json
from comm_health_graph import analyze_communication_health

with open('sample_data/email_thread.json') as f:
    data = json.load(f)
    
report = analyze_communication_health(data)
print(json.dumps(report, indent=2))
"
```

## Extending the Analysis

### Adding New Metrics

1. Modify `basic_stats()` for deterministic calculations
2. Update `llm_extract()` JSON schema for new LLM-based features  
3. Adjust scoring weights in `aggregate_scores()`

### Alternative LLM Providers

Replace `ChatOpenAI` with `ChatAnthropic` or other LangChain-supported models:

```python
from langchain_anthropic import ChatAnthropic
model = ChatAnthropic(model="claude-3-sonnet-20240229")
```

### Persistence

Switch from `InMemorySaver` to `SqliteSaver` for persistent state:

```bash
pip install langgraph-checkpoint-sqlite
```

```python
from langgraph.checkpoint.sqlite import SqliteSaver
graph = builder.compile(checkpointer=SqliteSaver("checkpoints.db"))
```

## Design Philosophy

This implementation balances **product thinking** with **technical execution**:

- **Measurable**: Each dimension has clear 0-100 scoring with explainable formulas
- **Actionable**: Reports identify specific improvement areas with evidence
- **Scalable**: Graph design supports adding new analysis nodes and conditional routing
- **Reliable**: Graceful error handling ensures analysis completes even with LLM failures

The goal is not perfect accuracy, but rather **consistent, useful insights** that help teams improve their communication patterns over time.
