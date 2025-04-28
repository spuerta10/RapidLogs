from datetime import datetime

import pytest
from pydantic_core import ValidationError

from src.model.log_entry import LogEntry

# Test constants
SAMPLE_TIMESTAMP = "2023-04-23T10:00:00"
SAMPLE_TAG = "INFO"
SAMPLE_MESSAGE = "Test message"


@pytest.fixture
def sample_log_entry() -> LogEntry:
    """Creates a sample LogEntry for testing."""
    return LogEntry(
        timestamp=datetime.fromisoformat(SAMPLE_TIMESTAMP), tag=SAMPLE_TAG, message=SAMPLE_MESSAGE
    )


def test_create_log_entry() -> None:
    """Test basic LogEntry creation."""
    log = LogEntry(
        timestamp=datetime.fromisoformat(SAMPLE_TIMESTAMP), tag=SAMPLE_TAG, message=SAMPLE_MESSAGE
    )

    assert log.timestamp == datetime.fromisoformat(SAMPLE_TIMESTAMP)
    assert log.tag == SAMPLE_TAG
    assert log.message == SAMPLE_MESSAGE


def test_log_entry_immutability(sample_log_entry: LogEntry) -> None:
    """Test that LogEntry is immutable."""
    with pytest.raises(ValidationError):
        sample_log_entry.message = "New message"


def test_log_entry_comparison() -> None:
    """Test LogEntry comparison operators."""
    early_log = LogEntry(timestamp=datetime(2023, 1, 1), tag="INFO", message="Early log")
    late_log = LogEntry(timestamp=datetime(2023, 1, 2), tag="INFO", message="Late log")

    assert early_log < late_log
    assert min(late_log, early_log) == early_log
    assert max(late_log, early_log) == late_log


def test_log_entry_from_db_row() -> None:
    """Test creating LogEntry from database row."""
    db_row = (SAMPLE_TIMESTAMP, SAMPLE_TAG, SAMPLE_MESSAGE)
    log = LogEntry.from_db_row(db_row)

    assert log.timestamp == datetime.fromisoformat(SAMPLE_TIMESTAMP)
    assert log.tag == SAMPLE_TAG
    assert log.message == SAMPLE_MESSAGE


def test_invalid_comparison() -> None:
    """Test that comparing LogEntry with other types raises error."""
    log = LogEntry(timestamp=datetime.now(), tag="INFO", message="Test")

    with pytest.raises(AssertionError):
        _ = log < "not a log entry"


def test_log_entry_equality(sample_log_entry: LogEntry) -> None:
    """Test LogEntry equality comparison."""
    same_log = LogEntry(
        timestamp=datetime.fromisoformat(SAMPLE_TIMESTAMP), tag=SAMPLE_TAG, message=SAMPLE_MESSAGE
    )

    assert sample_log_entry == same_log
