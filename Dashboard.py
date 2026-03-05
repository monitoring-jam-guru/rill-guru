import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os

st.set_page_config(
    page_title="DIMORA-SU",
    layout="wide"
)

# ===============================
# DATABASE CONNECTION
# ===============================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# ===============================
# CREATE TABLE IF NOT EXIST
# ===============================

cursor.execute("""
CREATE TABLE IF NOT EXISTS guru(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nama TEXT,
sekolah TEXT,
mapel TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS jadwal(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nama TEXT,
hari TEXT,
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

# ===============================
# STYLE
# ===============================

st.markdown("""
<style>

.big-title{
font-size:40px;
font-weight:bold;
color:#0d47a1;
}

.card{
padding:20px;
border-radius:15px;
background-color:#f5f5f5;
}

</style>
""", unsafe_allow_html=True)

# ===============================
# HEADER
# ===============================

st.markdown('<p class="big-title">DIMORA-SU Dashboard</p>', unsafe_allow_html=True)

st.write("Digital Monitoring Jam Mengajar Guru")

# ===============================
# DATA STATISTICS
# ===============================

guru = pd.read_sql("SELECT * FROM guru", conn)
aktivitas = pd.read_sql("SELECT * FROM aktivitas", conn)

total_guru = len(guru)
total_upload = len(aktivitas)

hari_ini = datetime.now().strftime("%Y-%m-%d")

today = aktivitas[aktivitas["tanggal"] == hari_ini]

mengajar = len(today[today["status"] == "Sesuai"])
tidak_mengajar = len(today[today["status"] == "Tidak Sesuai"])

# ===============================
# DASHBOARD CARD
# ===============================

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Guru", total_guru)
col2.metric("Upload Hari Ini", len(today))
col3.metric("Mengajar Sesuai", mengajar)
col4.metric("Tidak Sesuai", tidak_mengajar)

st.divider()

# ===============================
# MENU
# ===============================

menu = st.sidebar.selectbox(
"Menu",
[
"Dashboard",
"Tambah Guru",
"Tambah Jadwal",
"Upload Foto Mengajar",
"Monitoring Hari Ini"
]
)

# ===============================
# TAMBAH DATA GURU
# ===============================

if menu == "Tambah Guru":

    st.subheader("Input Data Guru")

    nama = st.text_input("Nama Guru")
    sekolah = st.text_input("Sekolah")
    mapel = st.text_input("Mata Pelajaran")

    if st.button("Simpan Guru"):

        cursor.execute(
        "INSERT INTO guru (nama,sekolah,mapel) VALUES (?,?,?)",
        (nama,sekolah,mapel)
        )

        conn.commit()

        st.success("Data Guru Berhasil Disimpan")

# ===============================
# TAMBAH JADWAL
# ===============================

elif menu == "Tambah Jadwal":

    st.subheader("Input Jadwal Mengajar")

    guru_list = guru["nama"].tolist()

    nama = st.selectbox("Nama Guru", guru_list)

    hari = st.selectbox(
    "Hari",
    ["Senin","Selasa","Rabu","Kamis","Jumat"]
    )

    jam_mulai = st.time_input("Jam Mulai")
    jam_selesai = st.time_input("Jam Selesai")

    if st.button("Simpan Jadwal"):

        cursor.execute(
        "INSERT INTO jadwal (nama,hari,jam_mulai,jam_selesai) VALUES (?,?,?,?)",
        (nama,hari,str(jam_mulai),str(jam_selesai))
        )

        conn.commit()

        st.success("Jadwal Berhasil Disimpan")

# ===============================
# UPLOAD FOTO MENGAJAR
# ===============================

elif menu == "Upload Foto Mengajar":

    st.subheader("Upload Bukti Mengajar")

    guru_list = guru["nama"].tolist()

    nama = st.selectbox("Nama Guru", guru_list)

    foto = st.file_uploader("Upload Foto", type=["jpg","png"])

    if st.button("Upload"):

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

        jadwal = pd.read_sql(
        f"SELECT * FROM jadwal WHERE nama='{nama}' AND hari='{hari}'",
        conn
        )

        status = "Tidak Sesuai"

        if len(jadwal) > 0:

            jm = jadwal.iloc[0]["jam_mulai"]
            js = jadwal.iloc[0]["jam_selesai"]

            if jm <= jam <= js:
                status = "Sesuai"

        if foto is not None:

            folder = "uploads"

            if not os.path.exists(folder):
                os.makedirs(folder)

            path = os.path.join(folder, foto.name)

            with open(path, "wb") as f:
                f.write(foto.getbuffer())

        cursor.execute(
        "INSERT INTO aktivitas (nama,tanggal,jam,status,foto) VALUES (?,?,?,?,?)",
        (nama,tanggal,jam,status,foto.name)
        )

        conn.commit()

        st.success("Foto Berhasil Diupload")

        st.write("Timestamp:", waktu)

# ===============================
# MONITORING
# ===============================

elif menu == "Monitoring Hari Ini":

    st.subheader("Monitoring Mengajar Hari Ini")

    data = pd.read_sql(
    f"SELECT * FROM aktivitas WHERE tanggal='{hari_ini}'",
    conn
    )

    if len(data) == 0:

        st.warning("Belum ada aktivitas hari ini")

    else:

        for i,row in data.iterrows():

            if row["status"] == "Sesuai":
                st.success(f"{row['nama']} - {row['jam']}")

            else:
                st.error(f"{row['nama']} - {row['jam']}")

# ===============================
# DASHBOARD
# ===============================

else:

    st.subheader("Aktivitas Terbaru")

    data = pd.read_sql(
    "SELECT * FROM aktivitas ORDER BY id DESC LIMIT 10",
    conn
    )

    st.dataframe(data)
