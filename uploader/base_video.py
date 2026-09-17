from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


class BaseVideoUploader:
    SUPPORTED_VIDEO_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".m4v",
        ".webm",
        ".flv",
        ".wmv",
    }
    SUPPORTED_IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
    }
    MIN_SCHEDULE_LEAD_TIME = timedelta(hours=2)

    @classmethod
    def validate_video_file(cls, file_path: str | Path) -> Path:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"arquivo de vídeo inexistente: {path}")
        if not path.is_file():
            raise ValueError(f"o caminho do vídeo não é um arquivo: {path}")
        if path.suffix.lower() not in cls.SUPPORTED_VIDEO_EXTENSIONS:
            raise ValueError(
                f"formato de vídeo não suportado: {path.suffix}; aceitos: {', '.join(sorted(cls.SUPPORTED_VIDEO_EXTENSIONS))}"
            )

        return path

    @classmethod
    def validate_image_file(cls, file_path: str | Path) -> Path:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"arquivo de imagem inexistente: {path}")
        if not path.is_file():
            raise ValueError(f"o caminho da imagem não é um arquivo: {path}")
        if path.suffix.lower() not in cls.SUPPORTED_IMAGE_EXTENSIONS:
            raise ValueError(
                f"formato de imagem não suportado: {path.suffix}; aceitos: {', '.join(sorted(cls.SUPPORTED_IMAGE_EXTENSIONS))}"
            )
        return path

    @classmethod
    def validate_publish_date(cls, publish_date: datetime | int | None) -> datetime | int:
        if publish_date in (None, 0):
            return 0

        if not isinstance(publish_date, datetime):
            raise TypeError("publish_date precisa ser um datetime ou 0")

        now = datetime.now(tz=publish_date.tzinfo) if publish_date.tzinfo else datetime.now()
        if publish_date <= now:
            raise ValueError("o horário agendado precisa ser depois de agora")

        min_publish_time = now + cls.MIN_SCHEDULE_LEAD_TIME
        if publish_date <= min_publish_time:
            raise ValueError("o horário agendado precisa estar a mais de 2 horas de agora")

        return publish_date
