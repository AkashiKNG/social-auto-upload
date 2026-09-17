import asyncio
from pathlib import Path

from conf import BASE_DIR
from uploader.baijiahao_uploader.main import baijiahao_setup, BaiJiaHaoVideo
from utils.files_times import generate_schedule_time_next_day, get_title_and_hashtags


if __name__ == '__main__':
    filepath = Path(BASE_DIR) / "videos"
    account_file = Path(BASE_DIR / "cookies" / "baijiahao_uploader" / "account.json")
    # pega a pasta dos vídeos
    folder_path = Path(filepath)
    # lista todos os arquivos da pasta
    files = list(folder_path.glob("*.mp4"))
    file_num = len(files)
    publish_datetimes = generate_schedule_time_next_day(file_num, 1, daily_times=[16])
    cookie_setup = asyncio.run(baijiahao_setup(account_file, handle=False))
    for index, file in enumerate(files):
        title, tags = get_title_and_hashtags(str(file))
        thumbnail_path = file.with_suffix('.png')
        # mostra o nome do arquivo, o título e as hashtags
        print(f"arquivo de vídeo: {file}")
        print(f"título: {title}")
        print(f"Hashtag: {tags}")
        app = BaiJiaHaoVideo(title, file, tags, publish_datetimes[index], account_file)
        asyncio.run(app.main(), debug=False)
