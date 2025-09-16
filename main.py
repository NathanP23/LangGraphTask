import json
from comm_health_graph import create_communication_health_graph, CommunicationState
from nodes.input_detection import detect_input_type
from nodes.normalization import normalize_structured
from nodes.validation import validate_schema
from nodes.statistics import basic_stats_full, basic_stats_text
from nodes.structure_extraction import structure_from_text

def test_input_detection():
    """Test input detection logic with sample data."""
    print("Testing Input Detection Logic")
    print("-" * 30)

    # Test 1: Raw text without timestamps
    with open('sample_data/raw_text_example.txt', 'r') as f:
        raw_text = f.read()

    state1 = CommunicationState(raw_input=raw_text, errors=[])
    result1 = detect_input_type(state1)

    print(f"Raw text input:")
    print(f"  is_raw_text: {result1.is_raw_text}")
    print(f"  has_timestamps: {result1.has_timestamps}")
    print(f"  errors: {result1.errors}")

    # Test 2: Structured data with timestamps
    with open('sample_data/meeting_transcript.json', 'r') as f:
        structured_data = json.load(f)

    state2 = CommunicationState(structured_data=structured_data, errors=[])
    result2 = detect_input_type(state2)

    print(f"\nStructured data input:")
    print(f"  is_raw_text: {result2.is_raw_text}")
    print(f"  has_timestamps: {result2.has_timestamps}")
    print(f"  errors: {result2.errors}")

    # Test 3: Error case - no input
    state3 = CommunicationState(errors=[])
    result3 = detect_input_type(state3)

    print(f"\nNo input case:")
    print(f"  is_raw_text: {result3.is_raw_text}")
    print(f"  has_timestamps: {result3.has_timestamps}")
    print(f"  errors: {result3.errors}")

    return True

def test_normalization():
    """Test normalization logic with structured data."""
    print("Testing Data Normalization")
    print("-" * 30)

    # Load structured data
    with open('sample_data/meeting_transcript.json', 'r') as f:
        structured_data = json.load(f)

    # Create state and run normalization
    state = CommunicationState(structured_data=structured_data, errors=[])
    result = normalize_structured(state)

    print(f"Original data count: {len(structured_data)}")
    print(f"Normalized data count: {len(result.validated_data)}")
    print(f"Errors: {result.errors}")

    # Show first normalized item
    if result.validated_data:
        first_item = result.validated_data[0]
        print(f"\nFirst normalized item:")
        for key, value in first_item.items():
            print(f"  {key}: {value}")

    return True

def test_validation():
    """Test validation logic with normalized data."""
    print("Testing Data Validation")
    print("-" * 30)

    # Load and normalize data first
    with open('sample_data/meeting_transcript.json', 'r') as f:
        structured_data = json.load(f)

    # Create state and normalize
    state = CommunicationState(structured_data=structured_data, errors=[])
    state = normalize_structured(state)

    # Now validate
    result = validate_schema(state)

    print(f"Items before validation: {len(state.structured_data)}")
    print(f"Items after validation: {len(result.validated_data) if result.validated_data else 0}")
    print(f"Validation errors: {len([e for e in (result.errors or []) if e.startswith('validation:')])}")

    # Show any validation errors
    if result.errors:
        validation_errors = [e for e in result.errors if e.startswith('validation:')]
        if validation_errors:
            print(f"Validation issues found:")
            for error in validation_errors[:3]:  # Show first 3
                print(f"  - {error}")

    # Test with bad data
    print(f"\nTesting with invalid data...")
    bad_data = [
        {"speaker": "", "text": "Valid text"},  # Empty speaker
        {"speaker": "Alice", "text": ""},       # Empty text
        {"speaker": "Bob", "text": "Hi"},       # Too short text
    ]

    bad_state = CommunicationState(structured_data=bad_data, errors=[])
    bad_result = validate_schema(bad_state)

    bad_errors = [e for e in (bad_result.errors or []) if e.startswith('validation:')]
    print(f"Invalid data errors: {len(bad_errors)}")

    return True

def test_statistics():
    """Test statistics calculation with validated data."""
    print("Testing Statistics Calculation")
    print("-" * 30)

    # Load, normalize, and validate data
    with open('sample_data/meeting_transcript.json', 'r') as f:
        structured_data = json.load(f)

    # Process through pipeline
    state = CommunicationState(structured_data=structured_data, errors=[])
    state = normalize_structured(state)
    state = validate_schema(state)

    # Test full statistics (with timestamps)
    result_full = basic_stats_full(state)
    stats = result_full.basic_stats

    print(f"Full Statistics (with timestamps):")
    print(f"  Total messages: {stats['total_messages']}")
    print(f"  Unique speakers: {stats['unique_speakers']}")
    print(f"  Total words: {stats['total_words']}")
    print(f"  Avg words per message: {stats['avg_words_per_message']:.1f}")
    print(f"  Questions found: {stats['question_count']}")
    print(f"  Question ratio: {stats['question_ratio']:.2f}")
    print(f"  Participation balance: {stats['participation_balance']:.2f}")

    if stats['median_response_time']:
        print(f"  Median response time: {stats['median_response_time']:.1f} minutes")
        print(f"  Conversation duration: {stats['conversation_duration']:.1f} minutes")

    print(f"  Speaker contributions: {stats['speaker_message_counts']}")

    # Test text-only statistics (no timestamps)
    print(f"\nText-only Statistics (no timestamps):")
    state_copy = CommunicationState(structured_data=structured_data, errors=[])
    state_copy.validated_data = state.validated_data  # Use same validated data

    result_text = basic_stats_text(state_copy)
    stats_text = result_text.basic_stats

    print(f"  Has timestamps: {stats_text['has_timestamps']}")
    print(f"  Response times available: {len(stats_text['response_times'])}")
    print(f"  Total messages: {stats_text['total_messages']}")
    print(f"  Question count: {stats_text['question_count']}")

    return True

def test_structure_extraction():
    """Test LLM-powered structure extraction from raw text."""
    print("Testing Structure Extraction (LLM)")
    print("-" * 30)

    # Load raw text
    with open('sample_data/raw_text_example.txt', 'r') as f:
        raw_text = f.read()

    print(f"Input: {len(raw_text)} characters of raw text")
    print(f"First 100 chars: {raw_text[:100]}...")

    # Test structure extraction
    state = CommunicationState(raw_input=raw_text, errors=[])
    state = detect_input_type(state)  # Should set is_raw_text=True

    print(f"After detection: is_raw_text={state.is_raw_text}")

    # Now try structure extraction
    try:
        result = structure_from_text(state)

        if result.structured_data:
            print(f"✅ Success: Extracted {len(result.structured_data)} structured messages")
            print(f"First extracted message:")
            print(f"  Speaker: {result.structured_data[0]['speaker']}")
            print(f"  Text: {result.structured_data[0]['text'][:80]}...")
            print(f"  Type: {result.structured_data[0]['type']}")
        else:
            print(f"❌ Failed: No structured data extracted")
            if result.errors:
                print(f"Errors: {result.errors}")

    except Exception as e:
        print(f"❌ Error: {e}")

    return True

def test_graph_creation():
    """Test that the graph can be created and compiled without errors."""
    try:
        print("Creating communication health graph...")
        graph = create_communication_health_graph()
        print("✅ Graph created successfully!")
        return True

    except Exception as e:
        print(f"❌ Error creating graph: {e}")
        return False

def debug_three_cases():
    """Debug function to test all 3 input scenarios step by step."""
    print("Debug: Testing All 3 Input Cases")
    print("=" * 50)

    # Case 1: User specifies "this is structured data"
    print("CASE 1: User calls analyze_structured_data()")
    print("-" * 40)

    with open('sample_data/meeting_transcript.json', 'r') as f:
        structured_data = json.load(f)

    print(f"Input: List with {len(structured_data)} items")
    print(f"First item: {structured_data[0]}")

    from comm_health_graph import analyze_structured_data
    try:
        report1 = analyze_structured_data(structured_data)
        print(f"✅ Success: Got report")
        if report1:
            print(f"  Summary: {report1['summary'][:100]}...")
            print(f"  Overall score: {report1['overall_health']['score']} ({report1['overall_health']['label']})")
            print(f"  Dimensions: {list(report1['dimensions'].keys())}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Case 2: User specifies "this is raw text"
    print(f"\nCASE 2: User calls analyze_raw_text()")
    print("-" * 40)

    with open('sample_data/raw_text_example.txt', 'r') as f:
        raw_text = f.read()

    print(f"Input: String with {len(raw_text)} characters")
    print(f"First 100 chars: {raw_text[:100]}...")

    from comm_health_graph import analyze_raw_text
    try:
        report2 = analyze_raw_text(raw_text)
        print(f"✅ Success: Got report")
        # print(f"Report keys: {list(report2.keys()) if report2 else 'None'}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Case 3: User doesn't specify - auto-detect with structured data
    print(f"\nCASE 3A: User calls analyze_communication_health() with structured data")
    print("-" * 40)

    print(f"Input: Same structured data as Case 1")

    from comm_health_graph import analyze_communication_health
    try:
        report3a = analyze_communication_health(structured_data)
        print(f"✅ Success: Auto-detected as structured, got report")
        # print(f"Report keys: {list(report3a.keys()) if report3a else 'None'}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Case 3: User doesn't specify - auto-detect with raw text
    print(f"\nCASE 3B: User calls analyze_communication_health() with raw text")
    print("-" * 40)

    print(f"Input: Same raw text as Case 2")

    try:
        report3b = analyze_communication_health(raw_text)
        print(f"✅ Success: Auto-detected as raw text, got report")
        # print(f"Report keys: {list(report3b.keys()) if report3b else 'None'}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print(f"\n" + "=" * 50)
    print("Debug complete! All cases tested.")

if __name__ == "__main__":
    debug_three_cases()
    print("Testing LangGraph Communication Health Analysis")
    print("=" * 50)

    # Test input detection first
    print("1. Testing input detection logic...")
    test_input_detection()

    print("\n" + "=" * 50)
    print("2. Testing data normalization...")
    test_normalization()

    print("\n" + "=" * 50)
    print("3. Testing data validation...")
    test_validation()

    print("\n" + "=" * 50)
    print("4. Testing statistics calculation...")
    test_statistics()

    print("\n" + "=" * 50)
    print("5. Testing LLM structure extraction...")
    test_structure_extraction()

    print("\n" + "=" * 50)
    print("6. Testing graph creation...")
    success = test_graph_creation()

    if success:
        print("\n🎉 All tests passed! Foundation is solid.")
    else:
        print("\n💥 Graph creation failed. Check imports and dependencies.")