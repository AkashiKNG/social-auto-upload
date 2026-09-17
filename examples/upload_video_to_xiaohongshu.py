"""
O caminho atual é a CLI:

    sau xiaohongshu login --account <account_name>
    sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo"
    sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png --title "Título do post" --note "Texto do post"

Este script fica como entrada de depuração do uploader do Xiaohongshu, um caminho histórico.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from conf import BASE_DIR
from uploader.xiaohongshu_uploader.main import XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE
from uploader.xiaohongshu_uploader.main import XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED
from uploader.xiaohongshu_uploader.main import XiaoHongShuNote
from uploader.xiaohongshu_uploader.main import XiaoHongShuVideo


ACCOUNT_FILE = Path(BASE_DIR / "cookies" / "xiaohongshu_uploader" / "account.json")


def upload_video_to_xiaohongshu():
    video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
    thumbnail_path = video_file.with_suffix(".png")
    app = XiaoHongShuVideo(
        title="Exemplo de vídeo no Xiaohongshu",
        file_path=str(video_file),
        desc="Olá",
        tags=["xiaohongshu", "exemplovideo", "depuracao"],
        publish_strategy=XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
        publish_date=0,
        account_file=str(ACCOUNT_FILE),
        thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
    )
    asyncio.run(app.xiaohongshu_upload_video())


def upload_video_to_xiaohongshu_scheduled():
    video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
    thumbnail_path = video_file.with_suffix(".png")
    publish_time = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    app = XiaoHongShuVideo(
        title="Exemplo de vídeo agendado no Xiaohongshu",
        file_path=str(video_file),
        desc="Este é um exemplo de vídeo agendado no Xiaohongshu",
        tags=["xiaohongshu", "agendado", "depuracao"],
        publish_strategy=XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
        publish_date=publish_time,
        account_file=str(ACCOUNT_FILE),
        thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
    )
    asyncio.run(app.xiaohongshu_upload_video())


def upload_note_to_xiaohongshu():
    image_candidates = [
        Path(BASE_DIR) / "videos" / "demo.png",
        Path(BASE_DIR) / "videos" / "demo1.png",
        Path(BASE_DIR) / "videos" / "demo2.png",
    ]
    image_paths = [str(path) for path in image_candidates if path.exists()]
    app = XiaoHongShuNote(
        image_paths=image_paths,
        note="Exemplo de post de imagens no Xiaohongshu #depuracao",
        tags=["xiaohongshupost", "envioautomatico", "depuracao"],
        publish_strategy=XIAOHONGSHU_PUBLISH_STRATEGY_IMMEDIATE,
        publish_date=0,
        account_file=str(ACCOUNT_FILE),
        title="Exemplo de post no Xiaohongshu",
    )
    asyncio.run(app.xiaohongshu_upload_note())

def upload_note_to_xiaohongshu_scheduled():
    image_candidates = [
        Path(BASE_DIR) / "videos" / "demo.png",
        Path(BASE_DIR) / "videos" / "demo1.png",
        Path(BASE_DIR) / "videos" / "demo2.png",
    ]
    image_paths = [str(path) for path in image_candidates if path.exists()]
    publish_time = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    app = XiaoHongShuNote(
        image_paths=image_paths,
        note="Exemplo de post de imagens no Xiaohongshu #depuracao",
        tags=["xiaohongshupost", "envioautomatico", "depuracao"],
        publish_strategy=XIAOHONGSHU_PUBLISH_STRATEGY_SCHEDULED,
        publish_date=publish_time,
        account_file=str(ACCOUNT_FILE),
        title="Exemplo de post no Xiaohongshu",
    )
    asyncio.run(app.xiaohongshu_upload_note())


if __name__ == '__main__':
    # upload_video_to_xiaohongshu()
    # upload_video_to_xiaohongshu_scheduled()
    # upload_note_to_xiaohongshu()
    upload_note_to_xiaohongshu_scheduled()
