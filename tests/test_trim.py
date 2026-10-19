import hashlib
import os
import threading

import av
import pytest

from videoeditor.core import media, trim


def _video_packets(path):
    with av.open(path) as c:
        vs = c.streams.video[0]
        return [hashlib.md5(bytes(p)).hexdigest() for p in c.demux(vs) if p.size]


def test_probe(sample_video):
    info = media.probe(sample_video)
    assert info.duration == pytest.approx(12, abs=0.1)
    assert (info.width, info.height) == (320, 180)
    assert info.fps == pytest.approx(30)
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"


def test_keyframes(sample_video):
    kfs = media.scan_keyframes(sample_video)
    assert kfs == pytest.approx([0, 2, 4, 6, 8, 10], abs=0.01)
    assert media.snap_to_keyframe(kfs, 5.3) == pytest.approx(4)
    assert media.snap_to_keyframe(kfs, 4.0) == pytest.approx(4)
    assert media.snap_to_keyframe(kfs, 0.5) == 0
    assert media.keyframe_before(sample_video, 5.3) == pytest.approx(4, abs=0.01)
    assert media.keyframe_before(sample_video, 6.0) == pytest.approx(6, abs=0.01)


def test_cancel_scan(sample_video):
    ev = threading.Event()
    ev.set()
    assert media.scan_keyframes(sample_video, ev) == []


@pytest.mark.parametrize("start,end", [(4.0, 7.0), (0.0, 3.5), (8.0, 12.0)])
def test_trim_is_lossless(sample_video, tmp_path, start, end):
    dst = str(tmp_path / "out.mp4")
    seen = []
    info = media.probe(sample_video)
    plan = trim.TrimPlan(sample_video, dst, start, end, info.duration)
    trim.trim(plan, progress=seen.append)

    out = media.probe(dst)
    assert out.duration == pytest.approx(end - start, abs=0.12)
    assert out.video_codec == "h264" and out.audio_codec == "aac"
    assert (out.width, out.height) == (320, 180)
    assert seen and seen[-1] == 1.0
    # Qayta kodlash yo'q: har bir video paket manbadagi bilan baytma-bayt bir xil
    src_packets = _video_packets(sample_video)
    out_packets = _video_packets(dst)
    i = src_packets.index(out_packets[0])
    assert out_packets == src_packets[i : i + len(out_packets)]
    assert i == round(start * 30)
    # Birinchi kadr aynan tanlangan boshlanishdagi kadr
    with av.open(dst) as c:
        first = next(c.decode(video=0))
        assert first.time == pytest.approx(0, abs=0.01)


def test_mkv_container(sample_video, tmp_path):
    dst = str(tmp_path / "out.mkv")
    info = media.probe(sample_video)
    trim.trim(trim.TrimPlan(sample_video, dst, 2.0, 6.0, info.duration))
    # MKV'da tahrir ro'yxati yo'q, shuning uchun davomiylikni kadrlar soni bilan tekshiramiz
    out_packets = _video_packets(dst)
    assert abs(len(out_packets) - 4 * 30) <= 3
    src_packets = _video_packets(sample_video)
    assert out_packets == src_packets[60 : 60 + len(out_packets)]


def test_command_shape(sample_video):
    plan = trim.TrimPlan("in.mp4", "out.mp4", 0.0, 12.0, 12.0)
    cmd = trim.build_command(plan, ffmpeg="ffmpeg")
    assert "-ss" not in cmd and "-t" not in cmd
    assert cmd[cmd.index("-c") + 1] == "copy"
    assert "+faststart" in cmd
    cmd = trim.build_command(trim.TrimPlan("in.mkv", "out.mkv", 4.0, 7.0, 12.0), ffmpeg="ffmpeg")
    assert float(cmd[cmd.index("-ss") + 1]) == pytest.approx(4.001)
    assert float(cmd[cmd.index("-t") + 1]) == pytest.approx(2.999)
    assert "+faststart" not in cmd


def test_errors(sample_video, tmp_path):
    with pytest.raises(trim.TrimError):
        trim.trim(trim.TrimPlan(sample_video, str(tmp_path / "x.mp4"), 5, 5, 12))
    with pytest.raises(trim.TrimError):
        trim.trim(trim.TrimPlan(sample_video, sample_video, 0, 5, 12))


def test_cancel_removes_output(sample_video, tmp_path):
    dst = str(tmp_path / "c.mp4")
    ev = threading.Event()
    ev.set()
    with pytest.raises(trim.TrimCancelled):
        trim.trim(trim.TrimPlan(sample_video, dst, 0, 12, 12), cancel=ev)
    assert not os.path.exists(dst)


def test_suggest_output_path(tmp_path):
    src = tmp_path / "kino.mp4"
    src.write_bytes(b"")
    p1 = trim.suggest_output_path(str(src), 65, 3725)
    assert os.path.basename(p1) == "kino_qirqim_01-05_1-02-05.mp4"
    open(p1, "w").close()
    assert trim.suggest_output_path(str(src), 65, 3725).endswith("_2.mp4")
