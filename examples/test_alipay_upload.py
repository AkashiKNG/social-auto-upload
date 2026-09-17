# -*- coding: utf-8 -*-
"""Teste de envio para a conta de vida do Alipay: usa o cookie salvo para enviar e publicar um vídeo."""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from uploader.alipay_uploader.main import AlipayVideo


async def main():
    base = Path(__file__).resolve().parents[1]
    video_path = Path(r"D:\video-moving\assets\outro\outro_horizontal.mp4")
    account_file = base / "cookies" / "alipay_uploader" / "account.json"

    app = AlipayVideo(
        title="Título de teste",
        file_path=str(video_path),
        tags=["teste", "automacao"],
        account_file=str(account_file),
        desc="Descrição de teste",
        thumbnail_path=r"C:\Users\admin\Downloads\ScreenShot_2026-08-04_170159_630.png",
        collection_name="",
        headless=False,
    )
    await app.main()


if __name__ == "__main__":
    asyncio.run(main())
