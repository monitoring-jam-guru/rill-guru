import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
from PIL import Image, ImageDraw
from fpdf import FPDF
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# ==========================
# DATABASE
# ==========================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS guru(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nik TEXT,
nama TEXT,
sekolah TEXT,
mapel TEXT,
lat REAL,
lon REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS jadwal(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nama TEXT,
hari TEXT,
kelas TEXT,
jam_mulai TEXT,
jam_selesai TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS aktivitas(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nama TEXT,
tanggal TEXT,
jam TEXT,
status TEXT,
foto TEXT
)
""")

conn.commit()

guru = pd.read_sql("SELECT * FROM guru", conn)
jadwal = pd.read_sql("SELECT * FROM jadwal", conn)
aktivitas = pd.read_sql("SELECT * FROM aktivitas", conn)

# ==========================
# MENU
# ==========================

menu = st.sidebar.selectbox(
"Menu",
[
"Dashboard",
"Tambah Guru",
"Tambah Jadwal",
"Upload Foto Mengajar",
"Monitoring Hari Ini",
"Peta Sekolah",
"Laporan Kadis"
]
)

# ==========================
# DASHBOARD
# ==========================

if menu == "Dashboard":

    st.title("DIMORA-SU")
    st.subheader("Dashboard Monitoring Guru")

    hari_ini = datetime.now().strftime("%Y-%m-%d")

    data_today = aktivitas[aktivitas["tanggal"] == hari_ini]

    sesuai = len(data_today[data_today["status"] == "Sesuai"])
    tidak = len(data_today[data_today["status"] == "Tidak Sesuai"])

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Guru", len(guru))
    col2.metric("Mengajar Sesuai", sesuai)
    col3.metric("Tidak Mengajar", tidak)

    st.subheader("Grafik Aktivitas")

    if len(data_today) > 0:
        chart = data_today.groupby("status").size()
        st.bar_chart(chart)

# ==========================
# TAMBAH GURU
# ==========================

elif menu == "Tambah Guru":

    st.title("Tambah Guru")

    nik = st.text_input("NIK")
    nama = st.text_input("Nama Guru")
    sekolah = st.text_input("Sekolah")
    mapel = st.text_input("Mata Pelajaran")

    st.subheader("Lokasi Sekolah")

    lat = st.number_input("Latitude", value=3.5952)
    lon = st.number_input("Longitude", value=98.6722)

    if st.button("Simpan"):

        cursor.execute(
        "INSERT INTO guru (nik,nama,sekolah,mapel,lat,lon) VALUES (?,?,?,?,?,?)",
        (nik,nama,sekolah,mapel,lat,lon)
        )

        conn.commit()

        st.success("Guru berhasil disimpan")

# ==========================
# TAMBAH JADWAL
# ==========================

elif menu == "Tambah Jadwal":

    st.title("Tambah Jadwal")

    if len(guru) == 0:
        st.warning("Tambahkan guru terlebih dahulu")
        st.stop()

    nama = st.selectbox("Guru", guru["nama"].tolist())

    hari = st.selectbox("Hari", ["Senin","Selasa","Rabu","Kamis","Jumat"])

    kelas = st.text_input("Kelas")

    jam_mulai = st.time_input("Jam Mulai")
    jam_selesai = st.time_input("Jam Selesai")

    if st.button("Simpan Jadwal"):

        cursor.execute(
        "INSERT INTO jadwal (nama,hari,kelas,jam_mulai,jam_selesai) VALUES (?,?,?,?,?)",
        (nama,hari,kelas,str(jam_mulai),str(jam_selesai))
        )

        conn.commit()

        st.success("Jadwal disimpan")

# ==========================
# WATERMARK FOTO
# ==========================

def watermark(img_path,text):

    img = Image.open(img_path)

    draw = ImageDraw.Draw(img)

    draw.text((10,10),text,(255,0,0))

    img.save(img_path)

# ==========================
# UPLOAD FOTO
# ==========================

elif menu == "Upload Foto Mengajar":

    st.title("Upload Bukti Mengajar")

    if len(guru) == 0:
        st.warning("Belum ada data guru")
        st.stop()

    nama = st.selectbox("Guru", guru["nama"].tolist())

    foto = st.file_uploader("Upload Foto", type=["jpg","png"])

    if st.button("Upload"):

        if foto is None:
            st.error("Silakan upload foto terlebih dahulu")
            st.stop()

        waktu = datetime.now()

        tanggal = waktu.strftime("%Y-%m-%d")
        jam = waktu.strftime("%H:%M:%S")

        hari = waktu.strftime("%A")

        hari_map = {
        "Monday":"Senin",
        "Tuesday":"Selasa",
        "Wednesday":"Rabu",
        "Thursday":"Kamis",
        "Friday":"Jumat"
        }

        hari = hari_map.get(hari, hari)

        jadwal_guru = pd.read_sql(
        "SELECT * FROM jadwal WHERE nama=? AND hari=?",
        conn,
        params=(nama,hari)
        )

        status = "Tidak Sesuai"

        for i,row in jadwal_guru.iterrows():

            if row["jam_mulai"] <= jam <= row["jam_selesai"]:
                status = "Sesuai"

        if not os.path.exists("uploads"):
            os.makedirs("uploads")

        path = os.path.join("uploads", foto.name)

        with open(path,"wb") as f:
            f.write(foto.getbuffer())

        watermark(path,f"{nama} {tanggal} {jam}")

        cursor.execute(
        "INSERT INTO aktivitas (nama,tanggal,jam,status,foto) VALUES (?,?,?,?,?)",
        (nama,tanggal,jam,status,foto.name)
        )

        conn.commit()

        st.success("Foto berhasil diupload")

# ==========================
# MONITORING
# ==========================

elif menu == "Monitoring Hari Ini":

    st.title("Monitoring Guru")

    hari_ini = datetime.now().strftime("%Y-%m-%d")

    data = pd.read_sql(
    "SELECT * FROM aktivitas WHERE tanggal=?",
    conn,
    params=(hari_ini,)
    )

    if len(data) == 0:

        st.warning("Belum ada aktivitas")

    else:

        for i,row in data.iterrows():

            if row["status"] == "Sesuai":
                st.success(f"{row['nama']} - {row['jam']}")

            else:
                st.error(f"{row['nama']} - {row['jam']}")

# ==========================
# PETA SEKOLAH
# ==========================

elif menu == "Peta Sekolah":

    st.title("Peta Sekolah")

    m = folium.Map(location=[3.6,98.6], zoom_start=7)

    for i,row in guru.iterrows():

        folium.Marker(
        location=[row["lat"],row["lon"]],
        popup=row["sekolah"]
        ).add_to(m)

    st_folium(m,width=700)

# ==========================
# LAPORAN PDF
# ==========================

elif menu == "Laporan Kadis":

    st.title("Laporan Monitoring")

    hari_ini = datetime.now().strftime("%Y-%m-%d")

    data = pd.read_sql(
    "SELECT * FROM aktivitas WHERE tanggal=?",
    conn,
    params=(hari_ini,)
    )

    if st.button("Generate PDF"):

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200,10,"Laporan Monitoring Guru",ln=True)

        for i,row in data.iterrows():

            text = f"{row['nama']} - {row['jam']} - {row['status']}"

            pdf.cell(200,10,text,ln=True)

        pdf.output("laporan.pdf")

        with open("laporan.pdf","rb") as f:

            st.download_button(
            "Download Laporan",
            f,
            file_name="laporan_monitoring.pdf"
            )
