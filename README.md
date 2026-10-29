# Streamlit OCR Harga Minyak Mentah

## Instalasi

Python 3.10+ disarankan.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

Salin `.env.example` menjadi `.env`, lalu isi `OCR_SPACE_API_KEY` dengan API key pribadi OCR.space.

```bash
streamlit run app.py
```

Buka alamat lokal yang ditampilkan Streamlit (umumnya http://localhost:8501).

## Alur
1. Upload gambar (bisa banyak file).
2. Klik Jalankan OCR. Hasil teks muncul dan dapat diperbaiki.
3. Parsing menghasilkan enam baris tabel dari tepat 18 angka desimal.
4. Periksa dan edit angka pada tabel, lalu export Excel atau simpan SQLite.
5. Lihat histori, detail, dan download ulang pada tab Histori.

## Catatan penting
- Parser menggunakan urutan 18 angka desimal, sama seperti contoh awal. Jika gambar mengandung angka lain atau kolom teracak, hasil tidak boleh dianggap otomatis benar. Selalu cocokkan dengan gambar sumber.
- Koreksi teks: klik **Parsing ulang dari teks**. Koreksi angka: langsung edit tabel.
- SQLite menyimpan metadata, teks OCR dan angka hasil akhir, **bukan gambar asli**.
- Setiap klik simpan membuat histori baru (termasuk file yang sama).
- API key hanya disimpan di `.env` lokal; jangan unggah `.env` ke Git.
- OCR.space menerima gambar yang diunggah ke layanan eksternal. Pastikan dokumen boleh diproses oleh pihak ketiga.
- Aplikasi ini belum memakai autentikasi. Jangan mengeksposnya ke internet publik tanpa login, HTTPS, dan pembatasan akses.
- `OCR_MAX_FILE_MB` default 5 MB; batas paket OCR.space dapat berbeda.
