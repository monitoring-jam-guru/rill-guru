from PIL import ImageFont
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
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

conn = sqlite3.connect(
    "database.db",
    check_same_thread=False,
    timeout=60
)

conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")

cursor = conn.cursor()

# TABEL GURU
cursor.execute("""
CREATE TABLE IF NOT EXISTS guru(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nik TEXT UNIQUE,
nama TEXT,
sekolah TEXT,
mapel TEXT,
lat REAL,
lon REAL
)
""")

# TABEL JADWAL
cursor.execute("""
CREATE TABLE IF NOT EXISTS jadwal(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nik TEXT,
nama TEXT,
sekolah TEXT,
hari TEXT,
kelas TEXT,
jam_mulai TEXT,
jam_selesai TEXT,
UNIQUE(nik,hari,kelas,jam_mulai)
)
""")

# TABEL AKTIVITAS
cursor.execute("""
CREATE TABLE IF NOT EXISTS aktivitas(
id INTEGER PRIMARY KEY AUTOINCREMENT,
nik TEXT,
nama TEXT,
tanggal TEXT,
jam TEXT,
kelas TEXT,
jenis TEXT,
status TEXT,
foto TEXT
)
""")

# TABEL USERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE,
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
    ("Operator_sman1","Sman1","operator_sekolah","SMAN 1 Medan")
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
    "Perbaiki Jadwal Guru",
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

def watermark(path, text):

    img = Image.open(path)

    draw = ImageDraw.Draw(img)

    draw.text((10,10), text, fill=(255,0,0))

    img.save(path)
if not os.path.exists("uploads"):
    os.makedirs("uploads")

def upload_drive(path):

    try:

        gauth = GoogleAuth()

        gauth.LoadCredentialsFile("credentials.json")

        if gauth.credentials is None:
            gauth.LocalWebserverAuth()

        elif gauth.access_token_expired:
            gauth.Refresh()

        else:
            gauth.Authorize()

        gauth.SaveCredentialsFile("credentials.json")

        drive = GoogleDrive(gauth)

        file_drive = drive.CreateFile(
        {"title": os.path.basename(path)}
        )

        file_drive.SetContentFile(path)

        file_drive.Upload()

        return "Upload berhasil"

    except Exception as e:

        return str(e)

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

    file = st.file_uploader("Upload File Excel", type=["xlsx"])

    if file is not None:

        try:

            df_guru = pd.read_excel(file, sheet_name="Guru")
            df_jadwal = pd.read_excel(file, sheet_name="Jadwal")

            df_guru.columns = df_guru.columns.str.lower().str.strip()
            df_jadwal.columns = df_jadwal.columns.str.lower().str.strip()

            st.subheader("Preview Data Guru")
            st.dataframe(df_guru)

            st.subheader("Preview Data Jadwal")
            st.dataframe(df_jadwal)

            if st.button("Import Sekarang"):

                conn.execute("BEGIN")

                # ======================
                # IMPORT GURU
                # ======================

                for _, row in df_guru.iterrows():

                    nik = str(row.get("nik","")).strip()
                    nama = str(row.get("nama","")).strip()
                    sekolah = str(row.get("sekolah","")).strip()
                    mapel = str(row.get("mapel","")).strip()

                    lat = float(row.get("lat",0))
                    lon = float(row.get("lon",0))

                    if nik == "":
                        continue

                    cursor.execute(
                    """
                    INSERT OR REPLACE INTO guru
                    (nik,nama,sekolah,mapel,lat,lon)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (nik,nama,sekolah,mapel,lat,lon)
                    )

                    cursor.execute(
                    """
                    INSERT OR IGNORE INTO users
                    (username,password,role,sekolah)
                    VALUES (?,?,?,?)
                    """,
                    (nik,"12345","guru",sekolah)
                    )


                # ======================
                # IMPORT JADWAL
                # ======================

                for _, row in df_jadwal.iterrows():

                    nama = str(row.get("nama","")).strip()
                    sekolah = str(row.get("sekolah","")).strip()
                    hari = str(row.get("hari","")).strip().lower()
                    kelas = str(row.get("kelas","")).strip()

                    jam_mulai = str(row.get("jam_mulai","")).replace(".",":")
                    jam_selesai = str(row.get("jam_selesai","")).replace(".",":")

                    if len(jam_mulai) == 5:
                        jam_mulai += ":00"

                    if len(jam_selesai) == 5:
                        jam_selesai += ":00"

                    data = cursor.execute(
                    "SELECT nik FROM guru WHERE nama=?",
                    (nama,)
                    ).fetchone()

                    if data is None:
                        continue

                    nik = data[0]

                    cursor.execute(
                    """
                    INSERT OR REPLACE INTO jadwal
                    (nik,nama,sekolah,hari,kelas,jam_mulai,jam_selesai)
                    VALUES (?,?,?,?,?,?,?)
                    """,
                    (nik,nama,sekolah,hari,kelas,jam_mulai,jam_selesai)
                    )

                conn.commit()

                st.success("Import Excel berhasil")

        except Exception as e:

            conn.rollback()

            st.error("Terjadi kesalahan saat membaca Excel")
            st.write(e)
# ==============================
# PERBAIKI JADWAL GURU
# ==============================

elif menu == "Perbaiki Jadwal Guru":

    st.title("Perbaiki Jadwal Guru")

    data = pd.read_sql(
        "SELECT * FROM jadwal ORDER BY nama,hari,jam_mulai",
        conn
    )

    if len(data) == 0:
        st.warning("Belum ada jadwal")
        st.stop()

    guru = st.selectbox(
        "Pilih Guru",
        sorted(data["nama"].unique())
    )

    jadwal_guru = data[data["nama"] == guru]

    for i,row in jadwal_guru.iterrows():

        col1,col2,col3,col4,col5 = st.columns(5)

        hari = col1.selectbox(
            "Hari",
            ["senin","selasa","rabu","kamis","jumat"],
            index=["senin","selasa","rabu","kamis","jumat"].index(row["hari"]),
            key=f"h{i}"
        )

        kelas = col2.text_input(
            "Kelas",
            row["kelas"],
            key=f"k{i}"
        )

        mulai = col3.text_input(
            "Jam Mulai",
            row["jam_mulai"],
            key=f"m{i}"
        )

        selesai = col4.text_input(
            "Jam Selesai",
            row["jam_selesai"],
            key=f"s{i}"
        )

        if col5.button("Update",key=f"u{i}"):

            cursor.execute(
            """
            UPDATE jadwal
            SET hari=?,kelas=?,jam_mulai=?,jam_selesai=?
            WHERE id=?
            """,
            (hari,kelas,mulai,selesai,row["id"])
            )

            conn.commit()

            st.success("Jadwal berhasil diperbarui")
            st.rerun()
# =========================
# UPLOAD FOTO MENGAJAR
# =========================

elif menu == "Upload Foto Mengajar":

    st.title("Absensi Mengajar Guru")

    nik = st.session_state.username

    # =========================
    # AMBIL DATA GURU
    # =========================

    data_guru = pd.read_sql(
        "SELECT * FROM guru WHERE nik=?",
        conn,
        params=(nik,)
    )

    if len(data_guru) == 0:
        st.error("Data guru tidak ditemukan")
        st.stop()

    nama = data_guru.iloc[0]["nama"]

    st.success(f"Nama : {nama}")
    st.info(f"NIK : {nik}")

    # =========================
    # PILIH TANGGAL
    # =========================

    tanggal = st.date_input("Pilih Tanggal Mengajar", datetime.now())

    hari_inggris = tanggal.strftime("%A")

    hari_map = {
        "Monday":"Senin",
        "Tuesday":"Selasa",
        "Wednesday":"Rabu",
        "Thursday":"Kamis",
        "Friday":"Jumat"
    }

    hari = hari_map.get(hari_inggris)
    st.write("Hari yang dipilih:", hari)

    if hari is None:

        st.warning("Hari ini bukan jadwal sekolah")
        st.stop()

    st.write(f"Hari Mengajar : **{hari.capitalize()}**")

    # =========================
    # AMBIL JADWAL HARI INI
    # =========================

    jadwal_hari_ini = pd.read_sql(
    """
    SELECT kelas,jam_mulai,jam_selesai
    FROM jadwal
    WHERE nik=? AND lower(hari)=?
    ORDER BY jam_mulai
    """,
    conn,
    params=(nik,hari.lower())
    )

    if len(jadwal_hari_ini) == 0:

        st.warning("Tidak ada jadwal mengajar hari ini")
        st.stop()

    st.subheader("Jadwal Mengajar Hari Ini")

    # =========================
    # TAMPILKAN JADWAL
    # =========================

    for i,row in jadwal_hari_ini.iterrows():

        kelas = row["kelas"]
        mulai = str(row["jam_mulai"])
        selesai = str(row["jam_selesai"])
    
        st.write(f"📚 {kelas} | {mulai} - {selesai}")
    
        if st.button(
            f"Masuk Kelas {kelas}",
            key=f"kelas_{i}"
        ):

            st.session_state.kelas_aktif = kelas
            st.session_state.jam_mulai = mulai
            st.session_state.jam_selesai = selesai

    # =========================
    # SELFIE FOTO
    # =========================
    
    if "kelas_aktif" in st.session_state:
    
        st.subheader(
            f"Selfie Kelas {st.session_state.kelas_aktif}"
        )
    
        foto = st.camera_input("Ambil Foto")
    
        if st.button("Upload Foto", key="upload_foto"):
    
            if foto is None:
                st.error("Silakan ambil foto terlebih dahulu")
                st.stop()
    
            waktu = datetime.utcnow() + timedelta(hours=7)
    
            tanggal_str = waktu.strftime("%Y-%m-%d")
            jam = waktu.strftime("%H:%M:%S")
    
            jam_upload = datetime.strptime(jam, "%H:%M:%S")
    
            mulai = st.session_state.jam_mulai.replace(".", ":")
            selesai = st.session_state.jam_selesai.replace(".", ":")
    
            mulai_dt = datetime.strptime(mulai, "%H:%M:%S")
            selesai_dt = datetime.strptime(selesai, "%H:%M:%S")
    
            # toleransi
            mulai_toleransi = mulai_dt + timedelta(minutes=15)
            selesai_toleransi = selesai_dt + timedelta(minutes=15)
    
            jenis_absen = ""
            status = "Tidak Sesuai"

        # =========================
        # ABSENSI MASUK
        # =========================
        if jam_upload <= mulai_toleransi:

            jenis_absen = "Masuk Kelas"

            if mulai_dt <= jam_upload <= mulai_toleransi:
                status = "Sesuai"

        # =========================
        # ABSENSI SELESAI
        # =========================
        elif jam_upload >= selesai_dt:

            jenis_absen = "Selesai Kelas"

            if selesai_dt <= jam_upload <= selesai_toleransi:
                status = "Sesuai"

        else:

            jenis_absen = "Di Luar Jadwal"

            # =========================
            # SIMPAN FOTO
            # =========================

            if not os.path.exists("uploads"):
                os.makedirs("uploads")

            filename=f"{nik}_{tanggal_str}_{jam}.jpg"

            path=os.path.join("uploads",filename)

            with open(path,"wb") as f:
                f.write(foto.getbuffer())
            
            watermark(
                path,
                f"{nama} {st.session_state.kelas_aktif} {tanggal_str} {jam}"
            )
            
            hasil_upload = upload_drive(path)
            
            st.info(hasil_upload)

            # =========================
            # SIMPAN DATABASE
            # =========================
            
            kelas = st.session_state.get("kelas_aktif","")

            if kelas == "":
                st.error("Kelas belum dipilih")
                st.stop()
            
            cursor.execute(
            """
            INSERT INTO aktivitas
            (nik,nama,tanggal,jam,kelas,jenis,status,foto)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
            str(nik),
            str(nama),
            str(tanggal_str),
            str(jam),
            str(kelas),
            "Masuk Kelas",
            str(status),
            str(filename)
            )
            )
            
            conn.commit()
            
            st.success(f"Absensi berhasil - Status : {status}")

# ==============================
# RIWAYAT GURU
# ==============================

elif menu == "Riwayat Mengajar":

    st.title("Riwayat Mengajar")

    nik = st.session_state.username

    data=pd.read_sql(
    "SELECT * FROM aktivitas WHERE nik=?",
    conn,
    params=(nik,)
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
