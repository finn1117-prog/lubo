from app.models.recording.recording_model import Recording


def make_recording():
    return Recording(
        1, "https://example.com/live", "主播", "ts", "OD", False, 0, True, False, "", "", ".", False, False, False
    )


def test_recording_speed_tracks_output_file_growth(tmp_path):
    output = tmp_path / "recording.ts"
    output.write_bytes(b"")
    recording = make_recording()
    recording.is_recording = True
    recording.begin_transfer(str(output))

    assert recording.update_transfer_speed(now=1.0) == "计算中…"
    output.write_bytes(b"x" * 2048)
    assert recording.update_transfer_speed(now=2.0) == "2.0 KB/s"


def test_recording_speed_resets_when_recording_stops(tmp_path):
    recording = make_recording()
    recording.begin_transfer(str(tmp_path / "recording.ts"))

    assert recording.update_transfer_speed(now=1.0) == "等待录制"
