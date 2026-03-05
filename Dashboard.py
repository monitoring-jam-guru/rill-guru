import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os

st.set_page_config(page_title="DIMORA-SU", layout="wide")

st.title("DIMORA-SU")
st.subheader("Digital Monitoring Jam Mengajar Guru")

# =====================================
# DATABASE
# =====================================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# =====================================
# TABLE GURU
# =====================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS guru(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nik TEXT,
nama TEXT,
sekolah TEXT,
mapel TEXT
)
""")

# =====================================
# TABLE JADWAL
# =====================================

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

# =====================================
# TABLE AKTIVITAS
# =====================================

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

# =====================================
# MENU
# =====================================

menu = st.sidebar.selectbox(
"Menu",
[
"Dashboard",
"Tambah Guru",
"Tambah Jadwal",
"Edit Jadwal",
"Upload Foto Mengajar",
"Monitoring Hari Ini"
]
)

# =====================================
# DASHBOARD
# =====================================

if menu == "Dashboard":

    st.subheader("Statistik")

    total_guru = len(guru)

    hari_ini = datetime.now().strftime("%Y-%m-%d")

    today = aktivitas[aktivitas["tanggal"] == hari_ini]

    sesuai = len(today[today["status"] == "Sesuai"])
    tidak = len(today[today["status"] == "Tidak Sesuai"])

    col1,col2,col3 = st.columns(3)

    col1.metric("Total Guru", total_guru)
    col2.metric("Jam Sesuai", sesuai)
    col3.metric("Tidak Sesuai", tidak)

# =====================================
# TAMBAH GURU
# =====================================

elif menu == "Tambah Guru":

    st.subheader("Tambah Data Guru")

    nik = st.text_input("NIK Guru")
    nama = st.text_input("Nama Guru")
    sekolah = st.text_input("Sekolah")
    mapel = st.text_input("Mata Pelajaran")

    if st.button("Simpan Guru"):

        cursor.execute(
        "INSERT INTO guru (nik,nama,sekolah,mapel) VALUES (?,?,?,?)",
        (nik,nama,sekolah,mapel)
        )

        conn.commit()

        st.success("Guru Berhasil Ditambahkan")

# =====================================
# TAMBAH JADWAL
# =====================================

elif menu == "Tambah Jadwal":

    st.subheader("Tambah Jadwal Mengajar")

    guru_list = guru["nama"].tolist()

    nama = st.selectbox("Nama Guru", guru_list)

    hari = st.selectbox(
    "Hari",
    ["Senin","Selasa","Rabu","Kamis","Jumat"]
    )

    kelas = st.text_input("Kelas")

    jam_mulai = st.time_input("Jam Mulai")
    jam_selesai = st.time_input("Jam Selesai")

    if st.button("Tambah Jadwal"):

        cursor.execute(
        "INSERT INTO jadwal (nama,hari,kelas,jam_mulai,jam_selesai) VALUES (?,?,?,?,?)",
        (nama,hari,kelas,str(jam_mulai),str(jam_selesai))
        )

        conn.commit()

        st.success("Jadwal Ditambahkan")

    st.divider()

    st.subheader("Daftar Jadwal")

    data = pd.read_sql("SELECT * FROM jadwal", conn)

    st.dataframe(data)

# =====================================
# EDIT JADWAL
# =====================================

elif menu == "Edit Jadwal":

    st.subheader("Edit Jadwal Guru")

    data = pd.read_sql("SELECT * FROM jadwal", conn)

    if len(data) == 0:

        st.warning("Belum ada jadwal")

    else:

        id_jadwal = st.selectbox(
        "Pilih Jadwal",
        data["id"]
        )

        row = data[data["id"] == id_jadwal].iloc[0]

        kelas = st.text_input("Kelas", row["kelas"])

        jam_mulai = st.time_input(
        "Jam Mulai",
        datetime.strptime(row["jam_mulai"], "%H:%M:%S").time()
        )

        jam_selesai = st.time_input(
        "Jam Selesai",
        datetime.strptime(row["jam_selesai"], "%H:%M:%S").time()
        )

        if st.button("Update Jadwal"):

            cursor.execute(
            """
            UPDATE jadwal
            SET kelas=?, jam_mulai=?, jam_selesai=?
            WHERE id=?
            """,
            (kelas,str(jam_mulai),str(jam_selesai),id_jadwal)
            )

            conn.commit()

            st.success("Jadwal Berhasil Diubah")

        if st.button("Hapus Jadwal"):

            cursor.execute(
            "DELETE FROM jadwal WHERE id=?",
            (id_jadwal,)
            )

            conn.commit()

            st.warning("Jadwal Dihapus")

# =====================================
# UPLOAD FOTO
# =====================================

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

        jadwal_guru = pd.read_sql(
        f"SELECT * FROM jadwal WHERE nama='{nama}' AND hari='{hari}'",
        conn
        )

        status = "Tidak Sesuai"

        for i,row in jadwal_guru.iterrows():

            if row["jam_mulai"] <= jam <= row["jam_selesai"]:
                status = "Sesuai"

        if foto is not None:

            if not os.path.exists("uploads"):
                os.makedirs("uploads")

            path = os.path.join("uploads", foto.name)

            with open(path,"wb") as f:
                f.write(foto.getbuffer())

        cursor.execute(
        "INSERT INTO aktivitas (nama,tanggal,jam,status,foto) VALUES (?,?,?,?,?)",
        (nama,tanggal,jam,status,foto.name)
        )

        conn.commit()

        st.success("Upload Berhasil")
        st.write("Timestamp:", waktu)

# =====================================
# MONITORING
# =====================================

elif menu == "Monitoring Hari Ini":

    st.subheader("Monitoring Guru")

    hari_ini = datetime.now().strftime("%Y-%m-%d")

    data = pd.read_sql(
    f"SELECT * FROM aktivitas WHERE tanggal='{hari_ini}'",
    conn
    )

    if len(data) == 0:

        st.warning("Belum ada aktivitas")

    else:

        for i,row in data.iterrows():

            if row["status"] == "Sesuai":
                st.success(f"{row['nama']} - {row['jam']}")

            else:
                st.error(f"{row['nama']} - {row['jam']}")
