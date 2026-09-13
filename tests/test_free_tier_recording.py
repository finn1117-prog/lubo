import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.recording.record_manager import FreeTierLimitError, GlobalRecordingState, RecordingManager
from app.models.media.video_quality_model import VideoQuality
from app.models.recording.recording_model import Recording
from app.models.recording.recording_status_model import RecordingStatus


def make_recording(rec_id="one", quality=VideoQuality.OD, monitor_status=True):
    return Recording(
        rec_id,
        "https://example.com/live",
        "主播",
        "ts",
        quality,
        False,
        0,
        monitor_status,
        False,
        "",
        "",
        ".",
        False,
        False,
        False,
    )


def make_manager(*, membership_active=False):
    manager = RecordingManager.__new__(RecordingManager)
    manager.services = SimpleNamespace(
        membership_active=membership_active,
        broadcast_card_update=lambda recording: None,
    )
    manager._ = {VideoQuality.SD: "标清", "monitor_stopped": "已停止监控"}
    manager.active_recorders = {}
    manager.persist_recordings = AsyncMock()
    return manager


@pytest.fixture(autouse=True)
def clear_global_recordings():
    GlobalRecordingState.recordings = []
    yield
    GlobalRecordingState.recordings = []


def test_free_tier_accepts_one_room_and_rejects_second_with_clear_error():
    manager = make_manager()
    first = make_recording("first")
    second = make_recording("second")

    asyncio.run(manager.add_recording(first))

    with pytest.raises(FreeTierLimitError, match="最多可添加 1 个直播间"):
        asyncio.run(manager.add_recording(second))

    assert manager.recordings == [first]


def test_free_tier_uses_sd_without_overwriting_saved_quality():
    manager = make_manager()
    recording = make_recording(quality=VideoQuality.OD)

    assert manager.effective_recording_quality(recording) == VideoQuality.SD
    assert recording.quality == VideoQuality.OD
    assert recording.to_dict()["quality"] == VideoQuality.OD


def test_membership_keeps_requested_original_quality_and_automatic_monitoring():
    manager = make_manager(membership_active=True)
    recording = make_recording(quality=VideoQuality.OD)

    assert manager.effective_recording_quality(recording) == VideoQuality.OD
    assert manager.allows_automatic_monitoring() is True


def test_free_tier_cannot_enable_continuous_monitoring():
    manager = make_manager()
    recording = make_recording(monitor_status=False)
    GlobalRecordingState.recordings = [recording]

    with pytest.raises(FreeTierLimitError, match="不支持 24 小时自动监控"):
        asyncio.run(manager.start_monitor_recording(recording))


def test_free_tier_skips_automatic_check_but_allows_manual_check_path():
    manager = make_manager()
    recording = make_recording(monitor_status=False)
    GlobalRecordingState.recordings = [recording]

    asyncio.run(manager.check_if_live(recording, automatic=True))
    assert recording.status_info is None

    asyncio.run(manager.check_if_live(recording, automatic=False))
    assert recording.status_info == RecordingStatus.STOPPED_MONITORING


def test_free_tier_cannot_run_legacy_extra_room():
    manager = make_manager()
    first = make_recording("first", monitor_status=False)
    second = make_recording("second", monitor_status=False)
    GlobalRecordingState.recordings = [first, second]

    asyncio.run(manager.check_if_live(second, automatic=False))

    assert second.status_info == RecordingStatus.STOPPED_MONITORING
