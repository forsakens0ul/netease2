import requests
from notion_client import Client
from datetime import datetime
import time
import os

# === 改为从环境变量中读取配置 ===
NETEASE_API = os.getenv("NETEASE_API", "https://netease-cloud-music-api-tau-one-92.vercel.app/")
COOKIE = os.getenv("NETEASE_COOKIE")
UID = os.getenv("NETEASE_UID")
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")


notion = Client(auth=NOTION_TOKEN)

def fetch_listening_data():
    url = f"{NETEASE_API}/user/record?uid={UID}&type=0"
    headers = {"Cookie": COOKIE}
    res = requests.get(url, headers=headers)
    data = res.json()
    return data['allData'] if data.get('code') == 200 else []

def get_existing_pages():
    pages = {}
    has_more = True
    start_cursor = None
    while has_more:
        res = notion.databases.query(
            database_id=NOTION_DB_ID,
            start_cursor=start_cursor
        )
        for result in res['results']:
            title = result['properties']['歌曲']['title'][0]['text']['content']
            pages[title] = result['id']
        has_more = res.get('has_more', False)
        start_cursor = res.get('next_cursor', None)
        time.sleep(0.5)  # 防止 API 速率限制
    return pages

def format_song(entry):
    song = entry['song']
    return {
        "name": song['name'],
        "artist": song['ar'][0]['name'],
        "album": song['al']['name'],
        "duration_ms": song['dt'],
        "play_count": entry['playCount'],
        "total_time_min": round(entry['playCount'] * song['dt'] / 1000 / 60, 2),
    }

def create_or_update_page(song_data, page_id=None):
    props = {
        "歌曲": {"title": [{"text": {"content": song_data['name']}}]},
        "歌手": {"rich_text": [{"text": {"content": song_data['artist']}}]},
        "专辑": {"rich_text": [{"text": {"content": song_data['album']}}]},
        "播放次数": {"number": song_data['play_count']},
        "累计时间(min)": {"number": song_data['total_time_min']},
        "同步时间": {"date": {"start": datetime.utcnow().isoformat()}}
    }

    if page_id:
        notion.pages.update(page_id=page_id, properties=props)
    else:
        notion.pages.create(parent={"database_id": NOTION_DB_ID}, properties=props)

def main():
    print("🔄 获取网易云记录...")
    records = fetch_listening_data()
    print(f"✅ 共拉取到 {len(records)} 条记录")

    print("📌 获取 Notion 已有数据...")
    existing = get_existing_pages()

    for entry in records:
        song = format_song(entry)
        page_id = existing.get(song['name'])  # 用歌曲名做唯一识别（也可加 artist 更精确）
        create_or_update_page(song, page_id=page_id)
        print(f"{'更新' if page_id else '新建'}：{song['name']}（{song['play_count']}次）")

    print("✅ 同步完成")

if __name__ == "__main__":
    main()
