# Olist E-Commerce Dashboard ✨

Proyek analisis data Olist E-Commerce Public Dataset (Jan 2017 - Agu 2018) beserta dashboard interaktif menggunakan Streamlit.

## Pertanyaan Bisnis
1. Bagaimana tren jumlah order dan revenue per bulan (Month-over-Month) pada Januari 2017 - Agustus 2018, dan 5 kategori produk apa yang menyumbang revenue terbesar?
2. Negara bagian mana (minimal 100 order) yang memiliki rata-rata review score terendah dan waktu pengiriman terlama pada Januari - Agustus 2018, dan seberapa besar keterlambatan pengiriman menurunkan review score?
3. Metode pembayaran dan jumlah cicilan apa yang paling banyak dipakai pada Januari 2017 - Agustus 2018, dan bagaimana kaitannya dengan nilai order?

Analisis lanjutan: RFM Analysis, Manual Grouping (Binning), dan Geospatial Analysis.

## Setup Environment - Anaconda
```
conda create --name main-ds python=3.11
conda activate main-ds
pip install -r requirements.txt
```

## Setup Environment - Shell/Terminal
```
cd submission
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run Streamlit App
Jalankan dari folder `submission`:
```
streamlit run dashboard/dashboard.py
```
Atau dari dalam folder `dashboard`:
```
cd dashboard
streamlit run dashboard.py
```
Dashboard akan terbuka di http://localhost:8501

## Notebook
Pastikan CSV dataset ada di folder `data/`, lalu jalankan `notebook.ipynb` dari folder `submission`.

## Dashboard Online
Tautan dashboard yang sudah di-deploy ada di `url.txt`.
