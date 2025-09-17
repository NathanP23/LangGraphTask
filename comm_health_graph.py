from typing import Dict, Any, List, Union
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from dataclasses import dataclass

# Import all node functions
from nodes.input_detection import detect_input_type
from nodes.structure_extraction import structure_from_text
from nodes.normalization import normalize_structured
from nodes.validation import validate_schema, remediation_llm
from nodes.preprocessing import dedupe_threads, chunk_if_needed
from nodes.statistics import basic_stats_full, basic_stats_text
from nodes.llm_extract import llm_extract
from nodes.merge_chunks import merge_chunks
from nodes.evidence_collect import evidence_collect
from nodes.calibrate_scores import calibrate_scores
from nodes.reporting import generate_report, finalize_output

class StateReporter:
    """Interface for reporting logs and errors from helper functions.

    Security Design:
    - Provides controlled access to state logging without exposing full state
    - Prevents helper functions from accidentally modifying critical state fields
    - Follows principle of least privilege - only exposes what's needed
    - Maintains clear separation between main functions (full state access)
      and helper functions (logging-only access)
    """
    def __init__(self, state):
        self.__state = state  # Private: Use double underscore for name mangling

    def add_log(self, message: str, indent_level: int = 0, flush: bool = False):
        """Add log message with controlled access."""
        self.__state.add_log(message, indent_level, flush)

    def add_error(self, message: str, indent_level: int = 0):
        """Add error message with controlled access."""
        self.__state.add_error(message, indent_level)

@dataclass
class CommunicationState:
    """Shared state passed between all nodes in the graph."""
    # Input data
    raw_input: str = ""
    structured_data: List[Dict[str, Any]] = None

    # Processing flags
    is_raw_text: bool = False
    has_timestamps: bool = False
    needs_chunking: bool = False
    log_enabled: bool = True

    # Progress tracking
    current_step: int = 0
    total_steps: int = 11  # Base number of steps

    # Processed data
    validated_data: List[Dict[str, Any]] = None
    chunks: List[List[Dict[str, Any]]] = None

    # Analysis results
    basic_stats: Dict[str, Any] = None
    llm_insights: List[Dict[str, Any]] = None
    merged_insights: Dict[str, Any] = None
    evidence: Dict[str, Any] = None
    calibrated_scores: Dict[str, Any] = None

    # Metadata and auxiliary data
    metadata: Dict[str, Any] = None

    # Final output
    report: Dict[str, Any] = None
    errors: List[str] = None
    logs: List[str] = None

    def add_error(self, error_message: str, indent_level: int = 0):
        """Add error to state and print it.

        Args:
            error_message: The error message to log
            indent_level: Number of '    ' indentations to add before the message
        """
        if not self.errors:
            self.errors = []
        self.errors.append(error_message)
        print(f"{'    ' * indent_level}ERROR: {error_message}")

    def add_log(self, log_message: str, indent_level: int = 0, flush: bool = False):
        """Add log to state and print it if logging is enabled.

        Args:
            log_message: The message to log
            indent_level: Number of '    ' indentations to add before the message
            flush: If True, print with carriage return and flush for temporary messages
        """
        if self.log_enabled:
            if not self.logs:
                self.logs = []
            # Create indented message
            self.logs.append(log_message)

            if flush:
                print(f"    " * indent_level + log_message.ljust(50), end='\r', flush=True)
            else:
                print("    " * indent_level + log_message)

    def get_reporter(self):
        """Return a reporter interface for helper functions."""
        return StateReporter(self)

def should_structure_from_text(state: CommunicationState) -> str:
    """Route to text structuring if input is raw text."""

    state.add_log(f"Routing based on input type: {'structure_from_text' if state.is_raw_text else 'normalize_structured'}")
    return "structure_from_text" if state.is_raw_text else "normalize_structured"

def should_remediate(state: CommunicationState) -> str:
    """Route to remediation if validation failed."""
    state.add_log(f"Routing based on validation errors: {'remediation_llm' if state.errors and any('validation' in error for error in state.errors) else 'dedupe_threads'}")
    if state.errors and any("validation" in error for error in state.errors):
        return "remediation_llm"
    return "dedupe_threads"

def has_timestamps(state: CommunicationState) -> str:
    """Route to appropriate stats calculation based on timestamp presence."""
    return "basic_stats_full" if state.has_timestamps else "basic_stats_text"

def create_communication_health_graph():
    print("Creating communication health analysis graph...")
    """Create and compile the LangGraph workflow."""

    # Create the state graph
    workflow = StateGraph(CommunicationState)

    # Add all nodes
    workflow.add_node("detect_input_type", detect_input_type)
    workflow.add_node("structure_from_text", structure_from_text)
    workflow.add_node("normalize_structured", normalize_structured)
    workflow.add_node("validate_schema", validate_schema)
    workflow.add_node("remediation_llm", remediation_llm)
    workflow.add_node("dedupe_threads", dedupe_threads)
    workflow.add_node("chunk_if_needed", chunk_if_needed)
    workflow.add_node("basic_stats_full", basic_stats_full)
    workflow.add_node("basic_stats_text", basic_stats_text)
    workflow.add_node("llm_extract", llm_extract)
    workflow.add_node("merge_chunks", merge_chunks)
    workflow.add_node("evidence_collect", evidence_collect)
    workflow.add_node("calibrate_scores", calibrate_scores)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("finalize_output", finalize_output)

    # Set entry point
    workflow.add_edge(START, "detect_input_type")

    # Add conditional edges for routing
    workflow.add_conditional_edges(
        "detect_input_type",
        should_structure_from_text
    )

    # Both paths lead to validation
    workflow.add_edge("structure_from_text", "validate_schema")
    workflow.add_edge("normalize_structured", "validate_schema")

    # Validation with potential remediation
    workflow.add_conditional_edges(
        "validate_schema",
        should_remediate
    )
    workflow.add_edge("remediation_llm", "dedupe_threads")

    # Linear flow through preprocessing
    workflow.add_edge("dedupe_threads", "chunk_if_needed")

    # Conditional stats calculation
    workflow.add_conditional_edges(
        "chunk_if_needed",
        has_timestamps
    )

    # Both stats paths lead to LLM extraction
    workflow.add_edge("basic_stats_full", "llm_extract")
    workflow.add_edge("basic_stats_text", "llm_extract")

    # Final analysis pipeline
    workflow.add_edge("llm_extract", "merge_chunks")
    workflow.add_edge("merge_chunks", "evidence_collect")
    workflow.add_edge("evidence_collect", "calibrate_scores")
    workflow.add_edge("calibrate_scores", "generate_report")
    workflow.add_edge("generate_report", "finalize_output")
    workflow.add_edge("finalize_output", END)

    print("Graph creation complete.")
    # Compile with memory checkpointer
    return workflow.compile(checkpointer=MemorySaver())

# Public API functions
def analyze_raw_text(raw_text: str) -> Dict[str, Any]:
    """Analyze raw text input and return communication health report."""
    graph = create_communication_health_graph()

    initial_state = CommunicationState(
        raw_input=raw_text,
        errors=[]
    )

    result = graph.invoke(initial_state, {"configurable": {"thread_id": "1"}})
    return result.get('report')

def analyze_structured_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze structured data and return communication health report."""
    graph = create_communication_health_graph()

    initial_state = CommunicationState(
        structured_data=data,
        errors=[]
    )

    result = graph.invoke(initial_state, {"configurable": {"thread_id": "1"}})
    return result.get('report')

def analyze_communication_health(input_data: Union[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Main entry point - detects input type and routes appropriately."""
    if isinstance(input_data, str):
        return analyze_raw_text(input_data)
    else:
        return analyze_structured_data(input_data)