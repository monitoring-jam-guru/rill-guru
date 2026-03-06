import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
from PIL import Image, ImageDraw
from fpdf import FPDF

st.set_page_config(page_title="DIMORA-SU", layout="wide")

# ==============================
# DATABASE
# ==============================

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
jenis TEXT,
status TEXT,
foto TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
password TEXT,
role TEXT,
sekolah TEXT
)
""")

conn.commit()

# ==============================
# USER DEFAULT
# ==============================

cek_user = pd.read_sql("SELECT * FROM users", conn)

if len(cek_user) == 0:

    # ADMIN DINAS
    cursor.execute(
    "INSERT INTO users (username,password,role,sekolah) VALUES (?,?,?,?)",
    ("admin","admin123","operator_dinas","-")
    )

    # KABID
    cursor.execute(
    "INSERT INTO users (username,password,role,sekolah) VALUES (?,?,?,?)",
    ("kabid","kabid123","kabid","-")
    )

    # OPERATOR SEKOLAH
    cursor.execute(
    "INSERT INTO users (username,password,role,sekolah) VALUES (?,?,?,?)",
    ("Operator_sman1","SMan1","operator_sekolah","SMAN 1 Medan")
    )

    cursor.execute(
    "INSERT INTO users (username,password,role,sekolah) VALUES (?,?,?,?)",
    ("Operator_sman2","Sman2","operator_sekolah","SMAN 2 Medan")
    )

    conn.commit()

# ==============================
# LOGIN
# ==============================

if "login" not in st.session_state:
    st.session_state.login = False

if st.session_state.login == False:

    st.title("LOGIN DIMORA-SU")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        user = pd.read_sql(
        "SELECT * FROM users WHERE username=? AND password=?",
        conn,
        params=(username,password)
        )

        if len(user) > 0:

            st.session_state.login = True
            st.session_state.username = user.iloc[0]["username"]
            st.session_state.role = user.iloc[0]["role"]
            st.session_state.sekolah = user.iloc[0]["sekolah"]

            st.rerun()

        else:
            st.error("Username atau Password salah")

    st.stop()

# ==============================
# SIDEBAR
# ==============================

st.sidebar.title("DIMORA-SU")

role = st.session_state.role

if role == "operator_dinas":

    menu = st.sidebar.selectbox(
    "Menu",
    [
    "Dashboard",
    "Import Excel",
    "Monitoring Hari Ini",
    "Laporan Kadis",
    "Manajemen User"
    ]
    )

elif role == "operator_sekolah":

    menu = st.sidebar.selectbox(
    "Menu",
    [
    "Dashboard",
    "Import Excel",
    "Monitoring Hari Ini"
    ]
    )

elif role == "guru":

    menu = st.sidebar.selectbox(
    "Menu",
    [
    "Upload Foto Mengajar",
    "Riwayat Mengajar"
    ]
    )

elif role == "kabid":

    menu = st.sidebar.selectbox(
    "Menu",
    [
    "Dashboard",
    "Monitoring Hari Ini",
    "Laporan Kadis"
    ]
    )

st.sidebar.write("Login sebagai")
st.sidebar.success(st.session_state.username)

if st.sidebar.button("Logout"):
    st.session_state.login=False
    st.rerun()

# ==============================
# LOAD DATA
# ==============================

guru = pd.read_sql("SELECT * FROM guru", conn)
jadwal = pd.read_sql("SELECT * FROM jadwal", conn)
aktivitas = pd.read_sql("SELECT * FROM aktivitas", conn)

# ==============================
# WATERMARK FOTO
# ==============================

def watermark(path,text):

    img = Image.open(path)
    draw = ImageDraw.Draw(img)
    draw.text((10,10), text, (255,0,0))
    img.save(path)

# ==============================
# DASHBOARD
# ==============================

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

    st.bar_chart(data_today.groupby("status").size())

# ==============================
# IMPORT EXCEL
# ==============================

elif menu == "Import Excel":

    st.title("Import Data Guru & Jadwal")

    st.info("Upload Excel dengan 2 Sheet : Guru dan Jadwal")

    file = st.file_uploader("Upload File Excel", type=["xlsx"])

    if file is not None:

        df_guru = pd.read_excel(file, sheet_name="Guru")
        df_jadwal = pd.read_excel(file, sheet_name="Jadwal")

        for i,row in df_guru.iterrows():

            cursor.execute(
            "INSERT INTO guru (nik,nama,sekolah,mapel,lat,lon) VALUES (?,?,?,?,?,?)",
            (
            row["nik"],
            row["nama"],
            row["sekolah"],
            row["mapel"],
            row["lat"],
            row["lon"]
            )
            )

            username=row["nik"]
            password="12345"

            cursor.execute(
            "INSERT INTO users (username,password,role,sekolah) VALUES (?,?,?,?)",
            (username,password,"guru",row["sekolah"])
            )

        for i,row in df_jadwal.iterrows():

            cursor.execute(
            """
            INSERT INTO jadwal (nama,sekolah,hari,kelas,jam_mulai,jam_selesai)
            VALUES (?,?,?,?,?,?)
            """,
            (
            row["nama"],
            row["sekolah"],
            row["hari"],
            row["kelas"],
            row["jam_mulai"],
            row["jam_selesai"]
            )
            )

        conn.commit()

        st.success("Data berhasil diimport")

# ==============================
# UPLOAD FOTO (GURU)
# ==============================

elif menu == "Upload Foto Mengajar":

    st.title("Upload Bukti Mengajar")

    nama = st.session_state.username

    jenis = st.selectbox(
    "Jenis Aktivitas",
    ["Masuk Kelas","Keluar Kelas"]
    )

    foto = st.camera_input("Ambil Foto dari Kamera")

    if st.button("Upload"):

        if foto is None:
            st.error("Ambil foto dulu")
            st.stop()

        waktu = datetime.utcnow() + timedelta(hours=7)

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

        hari=hari_map.get(hari,hari)

        jadwal_guru = pd.read_sql(
        "SELECT * FROM jadwal WHERE nama=?",
        conn,
        params=(nama,)
        )

        jadwal_guru = jadwal_guru[jadwal_guru["hari"]==hari]

        status="Tidak Sesuai"

        jam_upload=datetime.strptime(jam,"%H:%M:%S")

        for i,row in jadwal_guru.iterrows():

            mulai=datetime.strptime(row["jam_mulai"],"%H:%M:%S")
            selesai=datetime.strptime(row["jam_selesai"],"%H:%M:%S")

            selesai=selesai+timedelta(minutes=15)

            if mulai<=jam_upload<=selesai:
                status="Sesuai"

        if not os.path.exists("uploads"):
            os.makedirs("uploads")

        filename=f"{nama}_{tanggal}_{jam}.jpg"
        path=os.path.join("uploads",filename)

        with open(path,"wb") as f:
            f.write(foto.getbuffer())

        watermark(path,f"{nama} {tanggal} {jam}")

        cursor.execute(
        "INSERT INTO aktivitas (nama,tanggal,jam,jenis,status,foto) VALUES (?,?,?,?,?,?)",
        (nama,tanggal,jam,jenis,status,filename)
        )

        conn.commit()

        st.success("Foto berhasil diupload")

# ==============================
# RIWAYAT GURU
# ==============================

elif menu == "Riwayat Mengajar":

    st.title("Riwayat Mengajar")

    nama=st.session_state.username

    data=pd.read_sql(
    "SELECT * FROM aktivitas WHERE nama=?",
    conn,
    params=(nama,)
    )

    st.dataframe(data)

# ==============================
# MONITORING
# ==============================

elif menu == "Monitoring Hari Ini":

    st.title("Monitoring Guru")

    hari_ini=datetime.now().strftime("%Y-%m-%d")

    data=pd.read_sql(
    "SELECT * FROM aktivitas WHERE tanggal=?",
    conn,
    params=(hari_ini,)
    )

    if len(data)==0:
        st.warning("Belum ada aktivitas")

    else:

        for i,row in data.iterrows():

            if row["status"]=="Sesuai":

                st.success(
                f"{row['nama']} - {row['jam']} - {row['jenis']}"
                )

            else:

                st.error(
                f"{row['nama']} - {row['jam']} - {row['jenis']}"
                )

# ==============================
# LAPORAN PDF
# ==============================

elif menu == "Laporan Kadis":

    st.title("Laporan Monitoring")

    hari_ini=datetime.now().strftime("%Y-%m-%d")

    data=pd.read_sql(
    "SELECT * FROM aktivitas WHERE tanggal=?",
    conn,
    params=(hari_ini,)
    )

    if st.button("Generate PDF"):

        pdf=FPDF()

        pdf.add_page()
        pdf.set_font("Arial", size=12)

        pdf.cell(200,10,"Laporan Monitoring Guru",ln=True)
        pdf.cell(200,10,f"Tanggal: {hari_ini}",ln=True)

        pdf.ln(10)

        for i,row in data.iterrows():

            text=f"{row['nama']} - {row['jam']} - {row['status']}"

            pdf.cell(200,10,text,ln=True)

        pdf.output("laporan.pdf")

        with open("laporan.pdf","rb") as f:

            st.download_button(
            "Download PDF",
            f,
            file_name="laporan_monitoring.pdf"
            )

# ==============================
# MANAJEMEN USER
# ==============================

elif menu == "Manajemen User":

    st.title("Manajemen User")

    username=st.text_input("Username")
    password=st.text_input("Password")

    role=st.selectbox(
    "Role",
    ["operator_dinas","operator_sekolah","kabid","guru"]
    )

    sekolah=st.text_input("Sekolah")

    if st.button("Tambah User"):

        cursor.execute(
        "INSERT INTO users (username,password,role,sekolah) VALUES (?,?,?,?)",
        (username,password,role,sekolah)
        )

        conn.commit()

        st.success("User berhasil ditambahkan")

    st.dataframe(pd.read_sql("SELECT * FROM users",conn))
