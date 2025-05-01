💸 Discord Mining Coin Bot
Bot ini merupakan sistem ekonomi berbasis cryptocurrency simulasi yang dirancang untuk komunitas Discord. User bisa menambang coin, membeli rig, upgrade hardware, serta memiliki sistem wallet publik, private, dan server dengan fitur keamanan dan sistem rig rusak.

🧠 Fitur Utama
⛏️ mine_coin – Menambang coin berdasarkan jumlah rig.
🤖 server_mine – Mining otomatis melalui wallet server pribadi.
🛠️ Sistem rig rusak jika terlalu sering menambang.
🔒 Private wallet dengan password unik (dapat dicairkan siapa pun yang tahu password).
🏷️ Server wallet & rig untuk passive income.
🎫 Sistem tiket support via tombol dan kategori.
📉 Market dinamis, harga coin naik-turun tergantung aktivitas.

⛏️ Developer
AgusSamp – Developer utama dan desainer sistem.

Bot dikembangkan dengan bahasa Python 3.11, menggunakan:
discord.py 2.3.2
psutil

1. Install Bot
🛠️ Cara Install & Jalankan
git clone https://github.com/AgusSampXD/Python-discord-mine-and-moderator-bot
cd Python-discord-mine-and-moderator
atau isi folder .env dengan bot token dan jalankan startbot.bat

2. Install Dependency
pip install -r requirements.txt
Contoh isi requirements.txt:
discord.py==2.3.2
python-dotenv
matplotlib
psutil

3. Konfigurasi Bot
Buat file .env atau isi TOKEN, DB_HOST, dll di coin_system.py:
DISCORD_TOKEN=ISI DENGAN TOKEN KAMU SENDIRI DI .ENV

DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = "password"
DB_NAME = "coin_system"

4. Jalankan Bot
python bot.py

🧪 Cara Menggunakan di Discord
Menambang Coin
/mine_coin
User akan menjalankan proses mining 10x (1x per 13 detik) dan melihat hasilnya per ronde.

Cek Saldo
/balance
Menampilkan saldo coin, rig, dan status rig rusak jika ada.

Claim Income Harian
/claim_income
Mendapatkan income berdasarkan jumlah rig (1x per 24 jam).

Mining Server
/server_mine
Hanya bisa dijalankan di channel private server. Coin masuk ke wallet server.

Wallet Private
/buat_wallet_private – Buat wallet dengan password acak.
/claim_wallet <password> – Cairkan coin jika password benar.

Wallet bisa dicuri oleh siapa pun yang mengetahui password-nya.

💬 Support & Komunitas
Join Discord developer atau kirim saran melalui sistem tiket di server.
