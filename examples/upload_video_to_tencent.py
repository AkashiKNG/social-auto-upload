"""
Este arquivo fica como entrada de depuração do uploader do Channels, um caminho histórico.

Atenção:
1. a interação com a página em `uploader/tencent_uploader/main.py` ainda é um esqueleto;
2. você precisa escrever os métodos do vídeo: `fill_title_and_tags`, `wait_for_upload_complete`, `set_thumbnail`, `submit_publish` e afins;
3. e os métodos do post de imagens: `switch_to_note_mode`, `upload_note_images`, `fill_note_title_and_tags`, `submit_publish` e afins;
4. terminado isso, este exemplo serve como entrada de depuração local.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from conf import BASE_DIR
from uploader.tencent_uploader.main import TENCENT_PUBLISH_STRATEGY_IMMEDIATE
from uploader.tencent_uploader.main import TENCENT_PUBLISH_STRATEGY_SCHEDULED
from uploader.tencent_uploader.main import TencentNote
from uploader.tencent_uploader.main import TencentVideo


ACCOUNT_FILE = Path(BASE_DIR / "cookies" / "tencent_uploader" / "account.json")


def upload_video_to_tencent():
    video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
    thumbnail_path = video_file.with_suffix(".png")
    app = TencentVideo(
        title="Exemplo de vídeo no Channels",
        file_path=str(video_file),
        tags=["channels", "envioautomatico", "depuracao"],
        publish_strategy=TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        publish_date=0,
        account_file=str(ACCOUNT_FILE),
        desc="Aqui vai a descrição do vídeo que você for escrever",
        thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
        short_title="Exemplo Channels",
        category=None,
        is_draft=False,
    )
    asyncio.run(app.tencent_upload_video())


def upload_video_to_tencent_scheduled():
    video_file = Path(BASE_DIR) / "videos" / "demo.mp4"
    thumbnail_path = video_file.with_suffix(".png")
    publish_time = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    app = TencentVideo(
        title="Exemplo de publicação agendada no Channels",
        file_path=str(video_file),
        tags=["channels", "agendado", "depuracao"],
        publish_strategy=TENCENT_PUBLISH_STRATEGY_SCHEDULED,
        publish_date=publish_time,
        account_file=str(ACCOUNT_FILE),
        desc="Descrição de exemplo para a publicação agendada",
        thumbnail_path=str(thumbnail_path) if thumbnail_path.exists() else None,
        short_title="Exemplo agendado",
        category=None,
        is_draft=False,
    )
    asyncio.run(app.tencent_upload_video())


def upload_note_to_tencent():
    image_candidates = [
        Path(BASE_DIR) / "videos" / "demo.png",
        Path(BASE_DIR) / "videos" / "demo1.png",
        Path(BASE_DIR) / "videos" / "demo2.png",
    ]
    image_paths = [str(path) for path in image_candidates if path.exists()]
    app = TencentNote(
        image_paths=image_paths,
        note="Exemplo de post de imagens no Channels #depuracao",
        tags=["channelspost", "envioautomatico", "depuracao"],
        publish_strategy=TENCENT_PUBLISH_STRATEGY_IMMEDIATE,
        publish_date=0,
        account_file=str(ACCOUNT_FILE),
        title="Exemplo de post no Channels",
        is_draft=False,
    )
    asyncio.run(app.tencent_upload_note())


def upload_note_to_tencent_scheduled():
    image_candidates = [
        Path(BASE_DIR) / "videos" / "demo.png",
        Path(BASE_DIR) / "videos" / "demo1.png",
        Path(BASE_DIR) / "videos" / "demo2.png",
    ]
    image_paths = [str(path) for path in image_candidates if path.exists()]
    publish_time = (datetime.now() + timedelta(hours=3)).replace(second=0, microsecond=0)
    app = TencentNote(
        image_paths=image_paths,
        note="Exemplo de post agendado no Channels #depuracao",
        tags=["channelspost", "agendado", "depuracao"],
        publish_strategy=TENCENT_PUBLISH_STRATEGY_SCHEDULED,
        publish_date=publish_time,
        account_file=str(ACCOUNT_FILE),
        title="Exemplo de post agendado no Channels",
        is_draft=False,
    )
    asyncio.run(app.tencent_upload_note())


if __name__ == "__main__":
    upload_video_to_tencent()
    # upload_video_to_tencent_scheduled()
    # upload_note_to_tencent()
    # upload_note_to_tencent_scheduled()
