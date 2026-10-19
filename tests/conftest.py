import subprocess

import pytest

from videoeditor.core.ffmpeg import ffmpeg_exe


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory):
    """12 soniyalik video: 30 fps, har 2 soniyada kalit kadr, AAC audio."""
    path = tmp_path_factory.mktemp("media") / "sample.mp4"
    subprocess.run(
        [
            ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30",
            "-f", "lavfi", "-i", "sine=f=440:sample_rate=48000",
            "-t", "12", "-c:v", "libx264", "-g", "60", "-keyint_min", "60",
            "-sc_threshold", "0", "-bf", "2", "-c:a", "aac", "-shortest", str(path),
        ],
        check=True,
    )
    return str(path)
