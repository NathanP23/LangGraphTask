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

## Detailed Function Breakdown

```{.plaintext}
LangGraphTask/
├── main.py
│   ├── save_report_to_file()           # Save analysis reports to JSON files with timestamps
│   ├── test_input_detection()          # Test input type detection with sample data
│   ├── test_normalization()            # Test data normalization process
│   ├── test_validation()               # Test schema validation logic
│   ├── test_statistics()               # Test statistics calculation
│   ├── test_structure_extraction()     # Test raw text to JSON conversion
│   └── debug_three_cases()             # Run comprehensive test suite for all input methods
│
├── comm_health_graph.py
│   ├── StateReporter                   # Secure logging interface for helper functions
│   ├── CommunicationState              # Shared state object passed between nodes
│   ├── should_structure_from_text()    # Route to text structuring vs normalization
│   ├── should_remediate()              # Route to remediation if validation fails
│   ├── has_timestamps()                # Route to appropriate stats calculation
│   ├── create_communication_health_graph() # Build and compile LangGraph workflow
│   ├── analyze_raw_text()              # Public API for raw text analysis
│   ├── analyze_structured_data()       # Public API for structured data analysis
│   └── analyze_communication_health()  # Main entry point with auto-detection
│
├── config.py                           # Centralized configuration (no functions)
│
├── nodes/input_detection.py
│   ├── detect_input_type()             # Determine if input is raw text or structured data
│   ├── _contains_timestamps()          # Check raw text for timestamp patterns
│   └── _has_timestamp_fields()         # Check structured data for timestamp fields
│
├── nodes/structure_extraction.py
│   ├── structure_from_text()           # Convert raw text to structured JSON using LLM
│   └── _create_structure_prompt()      # Generate prompt for LLM text structuring
│
├── nodes/normalization.py
│   ├── normalize_structured()          # Clean and standardize structured input data
│   ├── _normalize_single_item()        # Normalize individual communication item
│   ├── _extract_timestamp()            # Extract timestamp from various field names
│   ├── _parse_timestamp()              # Parse timestamp string to ISO format
│   ├── _extract_speaker()              # Extract speaker name from various fields
│   ├── _extract_text()                 # Extract text content from various fields
│   └── _extract_type()                 # Extract communication type from various fields
│
├── nodes/validation.py
│   ├── validate_schema()               # Validate data against expected schema
│   ├── _validate_single_item()         # Validate individual communication item
│   ├── _is_valid_timestamp()           # Check timestamp format validity
│   ├── remediation_llm()               # Use LLM to fix validation errors
│   ├── _fix_data_with_llm()            # Call LLM to repair problematic data
│   └── _create_remediation_prompt()    # Generate prompt for LLM data fixing
│
├── nodes/preprocessing.py
│   ├── dedupe_threads()                # Remove duplicate messages and collapse quotes
│   ├── _clean_for_dedup()              # Clean text for deduplication comparison
│   ├── _remove_quoted_content()        # Remove quoted content from email/message text
│   └── chunk_if_needed()               # Split large conversations into manageable chunks
│
├── nodes/statistics.py
│   ├── basic_stats_full()              # Calculate complete statistics with timestamps
│   ├── basic_stats_text()              # Calculate statistics without timestamp data
│   ├── _calculate_base_stats()         # Count messages, words, speakers, questions
│   ├── _count_questions()              # Detect and count question patterns
│   ├── _calculate_participation()      # Analyze participation balance across speakers
│   └── _calculate_response_times()     # Calculate response latencies between speakers
│
├── nodes/llm_extract.py
│   ├── llm_extract()                   # Extract semantic insights using LLM analysis
│   └── _create_analysis_prompt()       # Generate prompt for LLM health analysis
│
├── nodes/merge_chunks.py
│   ├── merge_chunks()                  # Combine insights from multiple conversation chunks
│   ├── _merge_insights()               # Aggregate LLM insights across chunks
│   ├── _merge_emotional_indicators()   # Combine emotional tone counts
│   ├── _merge_lists()                  # Merge and deduplicate list fields
│   ├── _calculate_weighted_average()   # Compute weighted averages for numeric scores
│   └── _calculate_health_flags()       # Determine overall health indicators
│
├── nodes/evidence_collect.py
│   ├── evidence_collect()              # Gather supporting evidence for health scores
│   ├── _collect_collaboration_evidence() # Find examples of positive collaboration
│   ├── _collect_conflict_evidence()    # Find examples of tension or conflict
│   ├── _collect_clarity_evidence()     # Find examples of clear/unclear communication
│   ├── _collect_engagement_evidence()  # Find examples of high/low engagement
│   ├── _collect_responsiveness_evidence() # Find examples of response patterns
│   ├── _count_pattern_matches()        # Count regex pattern matches in text
│   └── _get_examples_with_context()    # Extract text examples with speaker context
│
├── nodes/calibrate_scores.py
│   ├── calibrate_scores()              # Normalize and weight final health scores
│   ├── _calculate_participation_score() # Score participation balance
│   ├── _calculate_clarity_score()      # Score communication clarity
│   ├── _calculate_engagement_score()   # Score overall engagement level
│   ├── _calculate_responsiveness_score() # Score response timeliness and patterns
│   ├── _calculate_collaboration_score() # Score collaboration vs conflict
│   ├── _calculate_overall_health()     # Compute weighted overall health score
│   ├── _calculate_confidence_score()   # Assess confidence in analysis results
│   └── _generate_recommendations()     # Create actionable improvement suggestions
│
└── nodes/reporting.py
    ├── generate_report()               # Create natural language health report
    ├── finalize_output()               # Format and structure final JSON output
    ├── _create_summary()               # Generate executive summary text
    ├── _extract_key_content()          # Extract decisions and action items
    ├── _format_dimension_scores()      # Format health dimension scores with descriptions
    ├── _categorize_health_level()      # Determine health category (excellent/good/fair/poor)
    └── _add_metadata()                 # Add analysis metadata and timestamps
```

## Function Call Flow

```{.plaintext}
                    User Entry Points
                          ↓
    ┌─────────────────────────────────────────────────────────┐
    │ analyze_communication_health() [auto-detect]           │
    │ analyze_raw_text() [force raw]                         │
    │ analyze_structured_data() [force structured]           │
    └─────────────────────┬───────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │ create_communication_health_graph() │
        └─────────────────┬───────────────────┘
                          ↓
                 ┌─────────────────┐
                 │ LangGraph Flow  │ ← State management via CommunicationState
                 └─────────────────┘
                          ↓
            ┌─────────────────────────────────┐
            │ detect_input_type()             │
            │ ├── _contains_timestamps()      │ ← for raw text
            │ └── _has_timestamp_fields()     │ ← for structured data
            └─────────────┬───────────────────┘
                          ↓
                ┌─────────────────────┐
                │ Conditional Routing │
                └─────────────────────┘
                ↓ raw text    ↓ structured
    ┌───────────────────────┐ ┌─────────────────────────┐
    │ structure_from_text() │ │ normalize_structured()  │
    │ └── _create_structure │ │ ├── _normalize_single_  │
    │     _prompt()         │ │ │   _item()             │
    └───────────────────────┘ │ ├── _extract_timestamp()│
                              │ ├── _parse_timestamp()  │
                              │ ├── _extract_speaker()  │
                              │ ├── _extract_text()     │
                              │ └── _extract_type()     │
                              └─────────────────────────┘
                ↓                           ↓
                └─────────────┬─────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ validate_schema()               │
                │ ├── _validate_single_item()     │
                │ └── _is_valid_timestamp()       │
                └─────────────┬───────────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ Validation Routing              │
                └─────────────────────────────────┘
                ↓ has errors          ↓ valid
    ┌───────────────────────┐ ┌─────────────────┐
    │ remediation_llm()     │ │ dedupe_threads()│
    │ ├── _fix_data_with_  │ │ ├── _clean_for_ │
    │ │   _llm()           │ │ │   _dedup()    │
    │ └── _create_         │ │ └── _remove_    │
    │     _remediation_    │ │     _quoted_    │
    │     _prompt()        │ │     _content()  │
    └───────────┬─────────┘ └─────────────────┘
                ↓                     ↓
                └─────────────┬───────┘
                              ↓
                ┌─────────────────────────────────┐
                │ chunk_if_needed()               │ ← part of preprocessing.py
                └─────────────┬───────────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ Stats Routing                   │
                └─────────────────────────────────┘
                ↓ timestamps      ↓ no timestamps
    ┌───────────────────────┐ ┌─────────────────────┐
    │ basic_stats_full()    │ │ basic_stats_text()  │
    │ ├── _calculate_base_  │ │ ├── _calculate_base_│
    │ │   _stats()          │ │ │   _stats()        │
    │ ├── _count_questions()│ │ ├── _count_questions│
    │ ├── _calculate_       │ │ │   ()              │
    │ │   _participation()  │ │ └── _calculate_     │
    │ └── _calculate_       │ │     _participation()│
    │     _response_times() │ │                     │
    └───────────────────────┘ └─────────────────────┘
                ↓                           ↓
                └─────────────┬─────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ llm_extract()                   │
                │ └── _create_analysis_prompt()   │
                └─────────────┬───────────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ merge_chunks()                  │
                │ ├── _merge_insights()           │
                │ ├── _merge_emotional_indicators│
                │ ├── _merge_lists()              │
                │ ├── _calculate_weighted_average│
                │ └── _calculate_health_flags()   │
                └─────────────┬───────────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ evidence_collect()              │
                │ ├── _collect_collaboration_     │
                │ │   _evidence()                 │
                │ ├── _collect_conflict_evidence()│
                │ ├── _collect_clarity_evidence() │
                │ ├── _collect_engagement_        │
                │ │   _evidence()                 │
                │ ├── _collect_responsiveness_    │
                │ │   _evidence()                 │
                │ ├── _count_pattern_matches()    │
                │ └── _get_examples_with_context()│
                └─────────────┬───────────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ calibrate_scores()              │
                │ ├── _calculate_participation_   │
                │ │   _score()                    │
                │ ├── _calculate_clarity_score()  │
                │ ├── _calculate_engagement_score│
                │ ├── _calculate_responsiveness_  │
                │ │   _score()                    │
                │ ├── _calculate_collaboration_   │
                │ │   _score()                    │
                │ ├── _calculate_overall_health() │
                │ ├── _calculate_confidence_score│
                │ └── _generate_recommendations() │
                └─────────────┬───────────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ generate_report()               │
                │ ├── _create_summary()           │
                │ ├── _extract_key_content()      │
                │ ├── _format_dimension_scores()  │
                │ └── _categorize_health_level()  │
                └─────────────┬───────────────────┘
                              ↓
                ┌─────────────────────────────────┐
                │ finalize_output()               │
                │ └── _add_metadata()             │
                └─────────────┬───────────────────┘
                              ↓
                      Final JSON Report

State Flow:
- CommunicationState object passed through all nodes
- StateReporter provides controlled logging access
- Each node modifies specific state fields:
  • raw_input → structured_data → validated_data → chunks
  • basic_stats → llm_insights → merged_insights → evidence
  • calibrated_scores → report (final output)

Routing Functions:
- should_structure_from_text() → routes based on is_raw_text flag
- should_remediate() → routes based on validation errors
- has_timestamps() → routes based on timestamp presence
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
