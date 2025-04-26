from collections import deque
from datetime import datetime, timedelta

import pytest
from sortedcontainers import SortedDict

from src.model.log_entry import LogEntry
from src.services.log_pruner import LogPruner

WINDOW_MINUTES = 5
OLD_LOGS_COUNT = 2
TOTAL_SAMPLE_LOGS = 3
RECENT_LOGS_COUNT = 2
EMPTY_CACHE = 0


@pytest.fixture
def log_pruner() -> LogPruner:
    return LogPruner(window_minutes=WINDOW_MINUTES)


@pytest.fixture
def sample_logs() -> SortedDict[datetime, list[LogEntry]]:
    now = datetime.now()
    logs = {
        now - timedelta(minutes=10): [
            LogEntry(timestamp=now - timedelta(minutes=10), tag="INFO", message="Old log 1"),
            LogEntry(timestamp=now - timedelta(minutes=10), tag="INFO", message="Old log 2"),
        ],
        now - timedelta(minutes=2): [
            LogEntry(timestamp=now - timedelta(minutes=2), tag="INFO", message="Recent log 1")
        ],
        now: [LogEntry(timestamp=now, tag="INFO", message="Current log 1")],
    }
    return SortedDict(logs)


def test_init_log_pruner() -> None:
    """Test LogPruner initialization"""
    pruner: LogPruner = LogPruner(window_minutes=WINDOW_MINUTES)
    assert pruner._LogPruner__window_minutes == WINDOW_MINUTES  # type: ignore[attr-defined]
    assert isinstance(pruner._LogPruner__timestamps, deque)  # type: ignore[attr-defined]
    assert len(pruner._LogPruner__timestamps) == EMPTY_CACHE  # type: ignore[attr-defined]


def test_register_timestamp(log_pruner: LogPruner) -> None:
    """Test timestamp registration"""
    now = datetime.now()
    result = log_pruner.register_timestamp(now)

    assert len(log_pruner._LogPruner__timestamps) == 1  # type: ignore[attr-defined]
    assert log_pruner._LogPruner__timestamps[0] == now  # type: ignore[attr-defined]
    assert result == log_pruner  # Test method chaining


def test_prune_empty_cache(log_pruner: LogPruner) -> None:
    """Test pruning with empty cache"""
    empty_cache = SortedDict()
    pruned = log_pruner.prune(empty_cache)
    assert len(pruned) == EMPTY_CACHE


def test_prune_no_timestamps(
    log_pruner: LogPruner, sample_logs: dict[datetime, list[LogEntry]]
) -> None:
    """Test pruning when no timestamps are registered"""
    pruned = log_pruner.prune(sample_logs)
    assert len(pruned) == EMPTY_CACHE
    assert len(sample_logs) == TOTAL_SAMPLE_LOGS  # Cache should remain unchanged


def test_prune_old_logs(
    log_pruner: LogPruner, sample_logs: SortedDict[datetime, list[LogEntry]]
) -> None:
    """Test pruning logs older than window"""
    now = datetime.now()

    # Register all timestamps
    for timestamp in sample_logs:
        log_pruner.register_timestamp(timestamp)

    pruned = log_pruner.prune(sample_logs)

    # Should prune logs older than 5 minutes
    assert len(pruned) == OLD_LOGS_COUNT  # Two old logs from 10 minutes ago
    assert all(log.timestamp < (now - timedelta(minutes=WINDOW_MINUTES)) for log in pruned)
    assert len(sample_logs) == RECENT_LOGS_COUNT  # Two timestamps remain in cache


def test_prune_chain_calls(
    log_pruner: LogPruner, sample_logs: SortedDict[datetime, list[LogEntry]]
) -> None:
    """Test multiple consecutive prune calls"""
    # First prune
    for timestamp in sample_logs:
        log_pruner.register_timestamp(timestamp)
    first_pruned = log_pruner.prune(sample_logs)

    # Second prune immediately after
    second_pruned = log_pruner.prune(sample_logs)

    assert len(first_pruned) == OLD_LOGS_COUNT  # First prune removes old logs
    assert len(second_pruned) == EMPTY_CACHE  # Second prune should find nothing to remove
    assert len(sample_logs) == RECENT_LOGS_COUNT  # Cache should maintain recent logs


def test_prune_boundary_conditions(log_pruner: LogPruner) -> None:
    """Test pruning at exactly the window boundary"""
    base_time = datetime(2024, 1, 1, 12, 0, 0)  # Use fixed time for deterministic test
    boundary_time = base_time - timedelta(minutes=5)

    cache = SortedDict(
        {boundary_time: [LogEntry(timestamp=boundary_time, tag="INFO", message="Boundary log")]}
    )

    # Register timestamps in chronological order
    log_pruner.register_timestamp(boundary_time)  # Register older timestamp first
    log_pruner.register_timestamp(base_time)  # Then register newer timestamp

    pruned = log_pruner.prune(cache)

    assert len(pruned) == 1, "Expected exactly one log to be pruned"
    assert pruned[0].timestamp == boundary_time, "Wrong log was pruned"
    assert pruned[0].message == "Boundary log", "Wrong log content was pruned"
    assert len(cache) == 0, "Cache should be empty after pruning"
