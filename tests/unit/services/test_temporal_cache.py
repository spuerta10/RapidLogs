from datetime import datetime
from unittest.mock import Mock

import pytest

from src.model.log_entry import LogEntry
from src.services.log_pruner import LogPruner
from src.services.temporal_cache import TemporalCache

LOGS_IN_RANGE: int = 3
TOTAL_SAMPLE_LOGS: int = 4
LOGS_WITH_SAME_TIMESTAMP: int = 2
BOUNDARY_LOGS_COUNT: int = 2


@pytest.fixture
def mock_pruner() -> Mock:
    return Mock(spec=LogPruner)


@pytest.fixture
def temporal_cache(mock_pruner: Mock) -> TemporalCache:
    return TemporalCache(mock_pruner)


@pytest.fixture
def sample_logs() -> list[LogEntry]:
    return [
        LogEntry(timestamp=datetime(2023, 1, 1, 10, 0), message="log1", tag="INFO"),
        LogEntry(timestamp=datetime(2023, 1, 1, 10, 0), message="log2", tag="INFO"),
        LogEntry(timestamp=datetime(2023, 1, 1, 11, 0), message="log3", tag="ERROR"),
        LogEntry(timestamp=datetime(2023, 1, 1, 12, 0), message="log4", tag="INFO"),
    ]


def test_add_log_registers_timestamp(temporal_cache: TemporalCache, mock_pruner: Mock) -> None:
    """Test that adding a log registers its timestamp with the pruner.

    Args:
        temporal_cache (TemporalCache): The temporal cache instance under test
        mock_pruner (Mock): Mock pruner to verify timestamp registration

    Tests that when a log is added, its timestamp is properly registered
    with the pruner for tracking purposes.
    """
    log: LogEntry = LogEntry(timestamp=datetime(2023, 1, 1), message="test", tag="INFO")
    temporal_cache.add_log(log)
    mock_pruner.register_timestamp.assert_called_once_with(log.timestamp)


def test_add_log_returns_self(temporal_cache: TemporalCache) -> None:
    """Test that add_log method returns self for method chaining.

    Args:
        temporal_cache (TemporalCache): The temporal cache instance under test

    Verifies that add_log returns the cache instance to enable method chaining.
    """
    log: LogEntry = LogEntry(timestamp=datetime(2023, 1, 1), message="test", tag="INFO")
    result = temporal_cache.add_log(log)
    assert result is temporal_cache


def test_get_logs_empty_cache(temporal_cache: TemporalCache) -> None:
    """Test that getting logs from an empty cache returns empty list.

    Args:
        temporal_cache (TemporalCache): The temporal cache instance under test

    Verifies that attempting to get logs from an empty cache returns an
    empty list rather than raising an exception.
    """
    start: datetime = datetime(2023, 1, 1)
    end: datetime = datetime(2023, 1, 2)
    assert temporal_cache.get_logs(start, end) == []


def test_get_logs_within_range(temporal_cache: TemporalCache, sample_logs: list[LogEntry]) -> None:
    """Test retrieving logs within a specific time range.

    Args:
        temporal_cache (TemporalCache): The temporal cache instance under test
        sample_logs (list[LogEntry]): Predefined sample logs for testing

    Verifies that only logs within the specified time range are returned
    and in the correct order.
    """
    for log in sample_logs:
        temporal_cache.add_log(log)

    start: datetime = datetime(2023, 1, 1, 10, 0)
    end: datetime = datetime(2023, 1, 1, 11, 0)
    logs: list[LogEntry] = temporal_cache.get_logs(start, end)

    assert len(logs) == LOGS_IN_RANGE
    assert logs[0].message == "log1"
    assert logs[1].message == "log2"
    assert logs[2].message == "log3"


def test_get_all_logs(temporal_cache: TemporalCache, sample_logs: list[LogEntry]) -> None:
    """Test retrieving all logs from the cache.

    Args:
        temporal_cache (TemporalCache): The temporal cache instance under test
        sample_logs (list[LogEntry]): Predefined sample logs for testing

    Verifies that all logs are returned in the correct order and no logs
    are missing from the result.
    """
    for log in sample_logs:
        temporal_cache.add_log(log)

    logs: list[LogEntry] = temporal_cache.get_all_logs()
    assert len(logs) == TOTAL_SAMPLE_LOGS
    assert [log.message for log in logs] == ["log1", "log2", "log3", "log4"]


def test_prune_cache_delegates_to_pruner(temporal_cache: TemporalCache, mock_pruner: Mock) -> None:
    """Test that cache pruning is properly delegated to the pruner.

    Args:
        temporal_cache (TemporalCache): The temporal cache instance under test
        mock_pruner (Mock): Mock pruner to verify delegation behavior

    Verifies that:
        1. The pruner's prune method is called with the correct cache
        2. The pruned logs are returned unchanged from the pruner
    """
    pruned_logs: list[LogEntry] = [
        LogEntry(timestamp=datetime(2023, 1, 1), message="old", tag="INFO")
    ]
    mock_pruner.prune.return_value = pruned_logs

    result: list[LogEntry] = temporal_cache.prune_cache()

    mock_pruner.prune.assert_called_once_with(temporal_cache._TemporalCache__cache)  # type: ignore[attr-defined]
    assert result == pruned_logs


def test_add_multiple_logs_different_timestamps(temporal_cache: TemporalCache) -> None:
    """Test adding multiple logs with different timestamps.

    Tests that logs with different timestamps are stored correctly and can be
    retrieved in chronological order.

    Args:
        temporal_cache: Fixture providing initialized TemporalCache instance
    """
    logs: list[LogEntry] = [
        LogEntry(timestamp=datetime(2023, 1, 1, 9, 0), message="early", tag="INFO"),
        LogEntry(timestamp=datetime(2023, 1, 1, 11, 0), message="late", tag="INFO"),
    ]

    for log in logs:
        temporal_cache.add_log(log)

    result = temporal_cache.get_all_logs()
    assert len(result) == LOGS_WITH_SAME_TIMESTAMP
    assert [log.message for log in result] == ["early", "late"]


def test_get_logs_partial_overlap_range(
    temporal_cache: TemporalCache, sample_logs: list[LogEntry]
) -> None:
    """Test getting logs with a range that partially overlaps timestamps.

    Tests retrieval of logs when the time range partially overlaps with stored
    timestamps, ensuring only logs within range are returned.

    Args:
        temporal_cache: Fixture providing initialized TemporalCache instance
        sample_logs: Fixture providing sample log entries
    """
    for log in sample_logs:
        temporal_cache.add_log(log)

    start: datetime = datetime(2023, 1, 1, 9, 59)  # Just before first log
    end: datetime = datetime(2023, 1, 1, 10, 30)  # Between first and second group

    logs = temporal_cache.get_logs(start, end)
    assert len(logs) == LOGS_WITH_SAME_TIMESTAMP
    assert [log.message for log in logs] == ["log1", "log2"]


def test_get_logs_exact_timestamp_boundaries(temporal_cache: TemporalCache) -> None:
    """Test getting logs with exact timestamp boundaries.

    Verifies that logs are correctly retrieved when the search range exactly
    matches log timestamps at the boundaries.

    Args:
        temporal_cache: Fixture providing initialized TemporalCache instance
    """
    timestamps: list[datetime] = [
        datetime(2023, 1, 1, 10, 0),
        datetime(2023, 1, 1, 11, 0),
        datetime(2023, 1, 1, 12, 0),
    ]

    for i, ts in enumerate(timestamps):
        temporal_cache.add_log(LogEntry(timestamp=ts, message=f"log{i}", tag="INFO"))

    logs: list[LogEntry] = temporal_cache.get_logs(timestamps[0], timestamps[1])
    assert len(logs) == BOUNDARY_LOGS_COUNT
    assert [log.message for log in logs] == ["log0", "log1"]


def test_get_logs_timestamp_order_preserved(temporal_cache: TemporalCache) -> None:
    """Test that log order is preserved within same timestamp.

    Verifies that logs added with the same timestamp maintain their
    insertion order when retrieved.

    Args:
        temporal_cache: Fixture providing initialized TemporalCache instance
    """
    timestamp: datetime = datetime(2023, 1, 1, 10, 0)
    messages: list[str] = ["first", "second", "third"]

    for msg in messages:
        temporal_cache.add_log(LogEntry(timestamp=timestamp, message=msg, tag="INFO"))

    logs: list[LogEntry] = temporal_cache.get_logs(timestamp, timestamp)
    assert [log.message for log in logs] == messages
