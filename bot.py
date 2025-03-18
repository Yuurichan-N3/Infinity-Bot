import requests
import time
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler
import logging
import os
from datetime import datetime, timedelta
import pytz

# Setup Rich console dan logging
console = Console()
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console)]
)
logger = logging.getLogger("infinity_bot")

# Banner
BANNER = """
╔══════════════════════════════════════════════╗
║       🌟 INFINITY BOT - Task Master          ║
║   Automate your Infinity Ground tasks!       ║
║  Developed by: https://t.me/sentineldiscus   ║
╚══════════════════════════════════════════════╝
"""

# Konfigurasi dasar
BASE_URL = 'https://api.infinityg.ai/api/v1'

# Header default
headers_template = {
    'Content-Type': 'application/json',
    'Accept': '*/*',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
}

# Baca token dari file data.txt
def load_tokens():
    tokens = []
    try:
        with open('data.txt', 'r') as f:
            for line in f:
                token = line.strip()
                if token:
                    tokens.append(token)
        if not tokens:
            logger.error("File data.txt kosong atau tidak ditemukan!")
            return None
        logger.info(f"Berhasil memuat {len(tokens)} akun dari data.txt")
        return tokens
    except FileNotFoundError:
        logger.error("File data.txt tidak ditemukan!")
        return None

def daily_check_in(token):
    headers = headers_template.copy()
    headers['Authorization'] = f'Bearer {token}'
    try:
        response = requests.post(f'{BASE_URL}/task/checkIn/', headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get('code') == '90000' and data.get('message') == '成功':
            logger.info("Check-in harian berhasil!")
            return True
        else:
            logger.warning(f"Check-in gagal: {data.get('message')}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Gagal melakukan check-in: {e}")
        return False

def get_task_list(token):
    headers = headers_template.copy()
    headers['Authorization'] = f'Bearer {token}'
    try:
        response = requests.post(f'{BASE_URL}/task/list', headers=headers)
        response.raise_for_status()
        raw_data = response.json()
        
        all_tasks = []
        if 'data' in raw_data and 'taskModelResponses' in raw_data['data']:
            for model in raw_data['data']['taskModelResponses']:
                if 'taskResponseList' in model:
                    all_tasks.extend(model['taskResponseList'])
        return all_tasks if all_tasks else []
    except requests.exceptions.RequestException as e:
        logger.error(f"Gagal mengambil daftar task: {e}")
        return None

def complete_task(token, task_id):
    headers = headers_template.copy()
    headers['Authorization'] = f'Bearer {token}'
    try:
        payload = {'taskId': task_id}
        response = requests.post(f'{BASE_URL}/task/complete', headers=headers, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False

def claim_reward(token, task_id):
    headers = headers_template.copy()
    headers['Authorization'] = f'Bearer {token}'
    try:
        payload = {'taskId': task_id}
        response = requests.post(f'{BASE_URL}/task/claim', headers=headers, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False

def process_account(token):
    logger.info(f"Memulai proses untuk akun dengan token: {token[:10]}...")

    # Lakukan check-in harian
    logger.info("Melakukan check-in harian...")
    daily_check_in(token)
    time.sleep(2)

    # Ambil daftar task
    tasks = get_task_list(token)
    if tasks is None:
        logger.error("Tidak bisa melanjutkan proses akun ini.")
        return

    # Tampilkan tabel task
    table = Table(title=f"Task untuk akun {token[:10]}...")
    table.add_column("ID", style="cyan")
    table.add_column("Nama Task", style="magenta")
    table.add_column("Status", style="green")
    
    for task in tasks:
        task_id = str(task.get('taskId', 'Unknown'))
        task_name = task.get('taskName', 'Unknown Task')
        status = task.get('status', 0)
        status_text = 'Belum Selesai' if status == 0 else f'Selesai (Status: {status})'
        table.add_row(task_id, task_name, status_text)
    
    console.print(table)

    # Proses task yang belum selesai
    for task in tasks:
        task_id = task.get('taskId')
        status = task.get('status', 0)
        
        if task_id and status == 0:
            logger.info(f"Mengerjakan task {task_id}...")
            if complete_task(token, task_id):
                logger.info(f"Task {task_id} selesai!")
                time.sleep(1)
                logger.info(f"Mengklaim hadiah untuk task {task_id}...")
                if claim_reward(token, task_id):
                    logger.info(f"Hadiah task {task_id} berhasil diklaim!")
                else:
                    logger.error(f"Gagal mengklaim hadiah task {task_id}!")
            else:
                logger.error(f"Gagal menyelesaikan task {task_id}!")
            time.sleep(1)

    # Klaim task untuk yang sudah selesai
    for task in tasks:
        task_id = task.get('taskId')
        status = task.get('status', 0)
        if task_id and status != 0:
            logger.info(f"Memeriksa hadiah untuk task {task_id} yang sudah selesai...")
            if claim_reward(token, task_id):
                logger.info(f"Hadiah task {task_id} berhasil diklaim!")
            else:
                logger.warning(f"Hadiah task {task_id} mungkin sudah diklaim atau gagal.")
            time.sleep(1)

def get_time_until_next_run():
    # WITA adalah UTC+8
    wita = pytz.timezone('Asia/Makassar')
    now = datetime.now(wita)
    
    # Set waktu target ke 08:10 WITA hari ini
    next_run = now.replace(hour=8, minute=10, second=0, microsecond=0)
    
    # Jika sudah lewat 08:10, jadwalkan untuk besok
    if now > next_run:
        next_run = next_run + timedelta(days=1)
    
    return (next_run - now).total_seconds()

def main():
    console.print(BANNER, style="bold green")
    
    tokens = load_tokens()
    if not tokens:
        return

    while True:
        # Proses semua akun
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(process_account, tokens)
        
        # Hitung waktu hingga eksekusi berikutnya
        sleep_time = get_time_until_next_run()
        logger.info(f"Menunggu hingga jadwal berikutnya pada pukul 08:10 WITA")
        logger.info(f"Waktu tersisa: {int(sleep_time // 3600)} jam {(int(sleep_time % 3600) // 60)} menit")
        
        # Tunggu hingga waktu yang ditentukan
        time.sleep(sleep_time)

if __name__ == '__main__':
    main()
