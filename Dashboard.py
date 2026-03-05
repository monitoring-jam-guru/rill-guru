import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
from PIL import Image, ImageDraw
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import matplotlib.pyplot as plt

st.set_page_config(page_title="DIMORA-SU", layout="wide")

# =========================
# DATABASE
# =========================

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
sekolah TEXT,
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

# =========================
# SIDEBAR MENU
# =========================

st.sidebar.title("DIMORA-SU")

menu = st.sidebar.selectbox(
"Menu Sistem",
[
"Dashboard",
"Tambah Guru",
"Tambah Jadwal",
"Edit / Hapus Jadwal",
"Upload Foto Mengajar",
"Monitoring Hari Ini",
"Peta Sekolah",
"Laporan Kadis"
]
)

# =========================
# WATERMARK FOTO
# =========================

def watermark(path,text):

    img = Image.open(path)
    draw = ImageDraw.Draw(img)
    draw.text((10,10), text, (255,0,0))
    img.save(path)

# =========================
# DASHBOARD
# =========================

if menu == "Dashboard":

    st.title("DIMORA-SU")
    st.caption("Digital Monitoring Jam Mengajar Guru")

    hari_ini = datetime.now().strftime("%Y-%m-%d")

    data_today = aktivitas[aktivitas["tanggal"] == hari_ini]

    sesuai = len(data_today[data_today["status"]=="Sesuai"])
    tidak = len(data_today[data_today["status"]=="Tidak Sesuai"])

    col1,col2,col3 = st.columns(3)

    col1.metric("Total Guru", len(guru))
    col2.metric("Mengajar Sesuai", sesuai)
    col3.metric("Tidak Sesuai", tidak)

    st.divider()

    st.subheader("Grafik Monitoring Hari Ini")

    if len(data_today)>0:

        grafik = data_today.groupby("status").size()

        st.bar_chart(grafik)

    else:
        st.info("Belum ada aktivitas hari ini")
    st.subheader("Aktivitas Guru")

    st.dataframe(
        aktivitas.sort_values("id", ascending=False)
    )
# =========================
# TAMBAH GURU
# =========================

elif menu == "Tambah Guru":

    st.title("Input Data Guru")

    nik = st.text_input("NIK")
    nama = st.text_input("Nama Guru")
    sekolah = st.text_input("Sekolah")
    mapel = st.text_input("Mata Pelajaran")

    st.subheader("Lokasi Sekolah")

    lat = st.number_input("Latitude", value=3.5952)
    lon = st.number_input("Longitude", value=98.6722)

    if st.button("Simpan Guru"):

        cursor.execute(
        "INSERT INTO guru (nik,nama,sekolah,mapel,lat,lon) VALUES (?,?,?,?,?,?)",
        (nik,nama,sekolah,mapel,lat,lon)
        )

        conn.commit()

        st.success("Guru berhasil disimpan")

# =========================
# TAMBAH JADWAL
# =========================

elif menu == "Tambah Jadwal":

    st.title("Input Jadwal Mengajar")

    if len(guru) == 0:
        st.warning("Tambahkan guru terlebih dahulu")
        st.stop()

    nama = st.selectbox("Nama Guru", guru["nama"])
    sekolah = st.selectbox("Sekolah", guru["sekolah"].unique())

    hari = st.selectbox(
    "Hari",
    ["Senin","Selasa","Rabu","Kamis","Jumat"]
    )

    kelas = st.text_input("Kelas")

    jam_mulai = st.time_input("Jam Mulai")
    jam_selesai = st.time_input("Jam Selesai")

    if st.button("Simpan Jadwal"):

        cursor.execute(
        """
        INSERT INTO jadwal (nama,sekolah,hari,kelas,jam_mulai,jam_selesai)
        VALUES (?,?,?,?,?,?)
        """,
        (nama,sekolah,hari,kelas,str(jam_mulai),str(jam_selesai))
        )

        conn.commit()

        st.success("Jadwal berhasil disimpan")

    st.subheader("Daftar Jadwal")

    st.dataframe(pd.read_sql("SELECT * FROM jadwal", conn))

# =========================
# EDIT / HAPUS JADWAL
# =========================

elif menu == "Edit / Hapus Jadwal":

    st.title("Edit atau Hapus Jadwal")

    if len(jadwal) == 0:
        st.warning("Belum ada jadwal")
        st.stop()

    id_jadwal = st.selectbox("Pilih Jadwal", jadwal["id"])

    data = jadwal[jadwal["id"] == id_jadwal].iloc[0]

    nama = st.text_input("Nama Guru", data["nama"])
    sekolah = st.text_input("Sekolah", data["sekolah"])
    hari = st.text_input("Hari", data["hari"])
    kelas = st.text_input("Kelas", data["kelas"])
    jam_mulai = st.text_input("Jam Mulai", data["jam_mulai"])
    jam_selesai = st.text_input("Jam Selesai", data["jam_selesai"])

    col1,col2 = st.columns(2)

    if col1.button("Update Jadwal"):

        cursor.execute(
        """
        UPDATE jadwal
        SET nama=?, sekolah=?, hari=?, kelas=?, jam_mulai=?, jam_selesai=?
        WHERE id=?
        """,
        (nama,sekolah,hari,kelas,jam_mulai,jam_selesai,id_jadwal)
        )

        conn.commit()

        st.success("Jadwal diperbarui")

    if col2.button("Hapus Jadwal"):

        cursor.execute(
        "DELETE FROM jadwal WHERE id=?",
        (id_jadwal,)
        )

        conn.commit()

        st.warning("Jadwal dihapus")

# =========================
# UPLOAD FOTO
# =========================

elif menu == "Upload Foto Mengajar":

    st.title("Upload Bukti Mengajar")

    nama = st.selectbox("Guru", guru["nama"])

    foto = st.file_uploader("Upload Foto", type=["jpg","png"])

    if st.button("Upload"):

        if foto is None:
            st.error("Silakan upload foto")
            st.stop()

        waktu = datetime.now()

        tanggal = waktu.strftime("%Y-%m-%d")
        jam = waktu.strftime("%H:%M:%S")

        hari = waktu.strftime("%A")

        hari_map={
        "Monday":"Senin",
        "Tuesday":"Selasa",
        "Wednesday":"Rabu",
        "Thursday":"Kamis",
        "Friday":"Jumat"
        }

        hari = hari_map.get(hari,hari)

        jadwal_guru = pd.read_sql(
        "SELECT * FROM jadwal WHERE nama=? AND hari=?",
        conn,
        params=(nama,hari)
        )

        from datetime import datetime, timedelta

        status = "Tidak Sesuai"
        
        jam_upload = datetime.strptime(jam,"%H:%M:%S")
        
        for i,row in jadwal_guru.iterrows():
        
            mulai = datetime.strptime(row["jam_mulai"],"%H:%M:%S")
            selesai = datetime.strptime(row["jam_selesai"],"%H:%M:%S")
        
            # toleransi 10 menit
            selesai_toleransi = selesai + timedelta(minutes=10)
        
            if mulai <= jam_upload <= selesai_toleransi:
                status = "Sesuai"

        if not os.path.exists("uploads"):
            os.makedirs("uploads")

        filename = f"{nama}_{tanggal}_{jam}.jpg"

        path = os.path.join("uploads",filename)
        
        with open(path,"wb") as f:
            f.write(foto.getbuffer())

        watermark(path,f"{nama} {tanggal} {jam}")

        cursor.execute(
        "INSERT INTO aktivitas (nama,tanggal,jam,status,foto) VALUES (?,?,?,?,?)",
        (nama,tanggal,jam,status,foto.name)
        )

        conn.commit()

        st.success("Foto berhasil diupload")

# =========================
# MONITORING
# =========================

elif menu == "Monitoring Hari Ini":

    st.title("Monitoring Guru")

    hari_ini = datetime.now().strftime("%Y-%m-%d")

    data = pd.read_sql(
    "SELECT * FROM aktivitas WHERE tanggal=?",
    conn,
    params=(hari_ini,)
    )

    sekolah_filter = st.selectbox(
    "Filter Sekolah",
    ["Semua"] + list(guru["sekolah"].unique())
    )

    if sekolah_filter != "Semua":

        guru_sekolah = guru[guru["sekolah"]==sekolah_filter]["nama"]

        data = data[data["nama"].isin(guru_sekolah)]

    if len(data)==0:
        st.warning("Belum ada aktivitas hari ini")

    else:

        for i,row in data.iterrows():

            if row["status"]=="Sesuai":

                st.success(
                f"🟢 {row['nama']} - {row['jam']}"
                )

            else:

                st.error(
                f"🔴 {row['nama']} - {row['jam']}"
                )
# =========================
# PETA SEKOLAH
# =========================

elif menu == "Peta Sekolah":

    st.title("Peta Sekolah")

    m = folium.Map(location=[3.6,98.6], zoom_start=7)

    for i,row in guru.iterrows():

        folium.Marker(
        location=[row["lat"],row["lon"]],
        popup=row["sekolah"]
        ).add_to(m)

    st_folium(m,width=900)

# =========================
# LAPORAN PDF
# =========================

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
        pdf.cell(200,10,f"Tanggal: {hari_ini}",ln=True)

        pdf.ln(5)

        for i,row in data.iterrows():

            text=f"{row['nama']} - {row['jam']} - {row['status']}"

            pdf.cell(200,10,text,ln=True)

        pdf.output("laporan.pdf")

        with open("laporan.pdf","rb") as f:

            st.download_button(
            "Download Laporan",
            f,
            file_name="laporan_monitoring.pdf"
            )
