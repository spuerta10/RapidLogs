from datetime import datetime
from http import HTTPStatus
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from src.application.api import API
from src.model.log_entry import LogEntry
from src.services.sqlite_conn import SQliteConn
from src.services.temporal_cache import TemporalCache

# Test constants
SAMPLE_TIMESTAMP = "2023-04-23T10:00:00"
SAMPLE_LOG = {"timestamp": SAMPLE_TIMESTAMP, "tag": "INFO", "message": "Test log"}
MULTIPLE_LOGS_COUNT = 2
SINGLE_LOG_COUNT = 1

HTTP_201_CREATED = HTTPStatus.CREATED
HTTP_200_OK = HTTPStatus.OK


@pytest.fixture
def mock_cache() -> Mock:
    """Creates a mock TemporalCache."""
    return Mock(spec=TemporalCache)


@pytest.fixture
def mock_db() -> Mock:
    """Creates a mock SQLiteConn."""
    return Mock(spec=SQliteConn)


@pytest.fixture
def api(mock_cache: Mock, mock_db: Mock) -> API:
    """Creates an API instance with mocked dependencies."""
    return API(mock_cache, mock_db)


@pytest.fixture
def client(api: API) -> TestClient:
    """Creates a TestClient for the FastAPI app."""
    return TestClient(api.app)


def test_add_single_log(client: TestClient, mock_cache: Mock) -> None:
    """Test adding a single log entry."""
    response = client.post("/logs", json=SAMPLE_LOG)

    assert response.status_code == HTTP_201_CREATED
    assert response.json()["count"] == SINGLE_LOG_COUNT
    mock_cache.add_log.assert_called_once()


def test_add_multiple_logs(client: TestClient, mock_cache: Mock) -> None:
    """Test adding multiple logs."""
    logs = {"logs": [SAMPLE_LOG, SAMPLE_LOG]}

    response = client.post("/logs", json=logs)

    assert response.status_code == HTTP_201_CREATED
    assert response.json()["count"] == MULTIPLE_LOGS_COUNT
    assert mock_cache.add_log.call_count == MULTIPLE_LOGS_COUNT


def test_get_logs_from_cache(client: TestClient, mock_cache: Mock) -> None:
    """Test retrieving logs from cache."""
    mock_cache.get_logs.return_value = [
        LogEntry(timestamp=datetime.fromisoformat(SAMPLE_TIMESTAMP), tag="INFO", message="Test log")
    ]

    response = client.get(
        "/logs", params={"start_time": SAMPLE_TIMESTAMP, "end_time": SAMPLE_TIMESTAMP}
    )

    assert response.status_code == HTTP_200_OK
    assert len(response.json()["logs"]) == SINGLE_LOG_COUNT
    mock_cache.get_logs.assert_called_once()


def test_get_logs_fallback_to_db(client: TestClient, mock_cache: Mock, mock_db: Mock) -> None:
    """Test fallback to database when cache misses."""
    mock_cache.get_logs.return_value = []
    mock_db.get_logs.return_value = [
        LogEntry(timestamp=datetime.fromisoformat(SAMPLE_TIMESTAMP), tag="INFO", message="Test log")
    ]

    response = client.get(
        "/logs", params={"start_time": SAMPLE_TIMESTAMP, "end_time": SAMPLE_TIMESTAMP}
    )

    assert response.status_code == HTTP_200_OK
    assert len(response.json()["logs"]) == SINGLE_LOG_COUNT
    mock_cache.get_logs.assert_called_once()
    mock_db.get_logs.assert_called_once()


def test_get_all_logs(client: TestClient, mock_cache: Mock) -> None:
    """Test retrieving all logs from cache."""
    mock_cache.get_all_logs.return_value = [
        LogEntry(timestamp=datetime.fromisoformat(SAMPLE_TIMESTAMP), tag="INFO", message="Test log")
    ]

    response = client.get("/logs/all")

    assert response.status_code == HTTP_200_OK
    assert len(response.json()["logs"]) == SINGLE_LOG_COUNT
    mock_cache.get_all_logs.assert_called_once()


def test_background_pruning(client: TestClient, mock_cache: Mock, mock_db: Mock) -> None:
    """Test that pruning happens in background after adding logs."""
    mock_cache.prune_cache.return_value = [
        LogEntry(timestamp=datetime.fromisoformat(SAMPLE_TIMESTAMP), tag="INFO", message="Old log")
    ]

    response = client.post("/logs", json=SAMPLE_LOG)

    assert response.status_code == HTTP_201_CREATED
    mock_cache.prune_cache.assert_called_once()
    mock_db.save_logs.assert_called_once()
