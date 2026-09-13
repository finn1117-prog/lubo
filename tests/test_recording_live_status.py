from types import SimpleNamespace

from app.core.recording.record_manager import RecordingManager


def test_offline_stream_without_anchor_is_not_fetch_error():
    stream_info = SimpleNamespace(is_live=False, anchor_name="")

    assert RecordingManager._stream_fetch_failed(stream_info) is False


def test_live_stream_without_anchor_is_fetch_error():
    stream_info = SimpleNamespace(is_live=True, anchor_name="")

    assert RecordingManager._stream_fetch_failed(stream_info) is True


def test_missing_stream_response_is_fetch_error():
    assert RecordingManager._stream_fetch_failed(None) is True
