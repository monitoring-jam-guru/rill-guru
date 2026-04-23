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
foto TEXT,
validasi_admin TEXT DEFAULT 'Belum'
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
# TAMBAH KOLOM JIKA BELUM ADA
# ==============================
try:
    cursor.execute("""
        ALTER TABLE aktivitas 
        ADD COLUMN validasi_admin TEXT DEFAULT 'Belum'
    """)
except:
    pass

try:
    cursor.execute("ALTER TABLE aktivitas ADD COLUMN jam_jadwal TEXT")
except:
    pass

try:
    cursor.execute("ALTER TABLE aktivitas ADD COLUMN alasan TEXT")
except:
    pass

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
        "Rekap JP",   # 👈 TAMBAHKAN INI
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
# MENU UTAMA (WAJIB RAPI - FINAL)
# ==============================

if menu == "Dashboard":

    st.title("DIMORA-SU")
    st.write("Dashboard")


# ==============================
# IMPORT EXCEL (FINAL BERSIH)
# ==============================
elif menu == "Import Excel":

    st.title("Import Data Guru & Jadwal")

    file = st.file_uploader("Upload File Excel", type=["xlsx"])

    if file is not None:

        try:
            # ======================
            # BACA EXCEL
            # ======================
            df_guru = pd.read_excel(file, sheet_name="Guru")
            df_jadwal = pd.read_excel(file, sheet_name="Jadwal")

            # bersihkan kolom
            df_guru.columns = df_guru.columns.str.lower().str.strip()
            df_jadwal.columns = df_jadwal.columns.str.lower().str.strip()

            st.subheader("Preview Guru")
            st.dataframe(df_guru)

            st.subheader("Preview Jadwal")
            st.dataframe(df_jadwal)

            # ======================
            # FUNGSI BERSIHKAN JAM
            # ======================
            def clean_jam(jam):
                jam = str(jam).replace(".",":").strip()
                try:
                    return pd.to_datetime(jam, errors="coerce").strftime("%H:%M:%S")
                except:
                    return None

            # ======================
            # PROSES IMPORT
            # ======================
            if st.button("Import Sekarang"):

                conn.execute("BEGIN")

                # ===== IMPORT GURU =====
                for _, row in df_guru.iterrows():

                    nik = str(row.get("nik","")).strip()
                    nama = str(row.get("nama","")).strip().upper()
                    sekolah = str(row.get("sekolah","")).strip()
                    mapel = str(row.get("mapel","")).strip()

                    try:
                        lat = float(row.get("lat",0))
                    except:
                        lat = 0

                    try:
                        lon = float(row.get("lon",0))
                    except:
                        lon = 0

                    if nik == "":
                        continue

                    cursor.execute("""
                        INSERT OR REPLACE INTO guru
                        (nik,nama,sekolah,mapel,lat,lon)
                        VALUES (?,?,?,?,?,?)
                    """,(nik,nama,sekolah,mapel,lat,lon))

                    cursor.execute("""
                        INSERT OR IGNORE INTO users
                        (username,password,role,sekolah)
                        VALUES (?,?,?,?)
                    """,(nik,"12345","guru",sekolah))


                # ===== IMPORT JADWAL =====
                for _, row in df_jadwal.iterrows():

                    nama = str(row.get("nama","")).strip().upper()
                    sekolah = str(row.get("sekolah","")).strip()
                    hari = str(row.get("hari","")).strip().lower()
                    kelas = str(row.get("kelas","")).strip()

                    jam_mulai = clean_jam(row.get("jam_mulai"))
                    jam_selesai = clean_jam(row.get("jam_selesai"))

                    if jam_mulai is None or jam_selesai is None:
                        st.warning(f"Jam error di kelas {kelas}")
                        continue

                    data = cursor.execute(
                        "SELECT nik FROM guru WHERE UPPER(nama)=?",
                        (nama,)
                    ).fetchone()

                    if data is None:
                        st.warning(f"Nama tidak cocok: {nama}")
                        continue

                    nik = data[0]

                    cursor.execute("""
                        INSERT OR REPLACE INTO jadwal
                        (nik,nama,sekolah,hari,kelas,jam_mulai,jam_selesai)
                        VALUES (?,?,?,?,?,?,?)
                    """,(nik,nama,sekolah,hari,kelas,jam_mulai,jam_selesai))

                conn.commit()
                st.success("✅ Import berhasil")

        except Exception as e:
            conn.rollback()
            st.error("❌ Error import")
            st.write(e)


# ==============================
# PERBAIKI JADWAL
# ==============================
elif menu == "Perbaiki Jadwal Guru":

    st.title("Perbaiki Jadwal Guru")
    st.write("Menu edit jadwal")


# ==============================
# UPLOAD FOTO
# ==============================
elif menu == "Upload Foto Mengajar":

    st.title("Absensi Mengajar Guru")

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

    st.title("📊 Monitoring & Validasi Admin")

    # =========================
    # DATA WILAYAH
    # =========================

    cabang_dinas = [
        "Cabdisdik Wilayah I","Cabdisdik Wilayah II","Cabdisdik Wilayah III",
        "Cabdisdik Wilayah IV","Cabdisdik Wilayah V","Cabdisdik Wilayah VI",
        "Cabdisdik Wilayah VII","Cabdisdik Wilayah VIII","Cabdisdik Wilayah IX",
        "Cabdisdik Wilayah X","Cabdisdik Wilayah XI","Cabdisdik Wilayah XII",
        "Cabdisdik Wilayah XIII","Cabdisdik Wilayah XIV"
    ]

    kabupaten_map = {
        "Cabdisdik Wilayah I": ["Deli Serdang","Kota Medan"],
        "Cabdisdik Wilayah II": ["Langkat","Kota Binjai"],
        "Cabdisdik Wilayah III": ["Serdang Bedagai","Kota Tebing Tinggi"],
        "Cabdisdik Wilayah IV": ["Karo","Dairi","Pakpak Bharat"],
        "Cabdisdik Wilayah V": ["Asahan","Batu Bara","Kota Tanjungbalai"],
        "Cabdisdik Wilayah VI": ["Simalungun","Kota Pematangsiantar"],
        "Cabdisdik Wilayah VII": ["Labuhanbatu","Labuhanbatu Utara","Labuhanbatu Selatan"],
        "Cabdisdik Wilayah VIII": ["Toba","Samosir"],
        "Cabdisdik Wilayah IX": ["Tapanuli Utara","Humbang Hasundutan"],
        "Cabdisdik Wilayah X": ["Tapanuli Tengah","Kota Sibolga"],
        "Cabdisdik Wilayah XI": ["Padangsidimpuan","Tapanuli Selatan","Mandailing Natal"],
        "Cabdisdik Wilayah XII": ["Padang Lawas","Padang Lawas Utara"],
        "Cabdisdik Wilayah XIII": ["Nias","Nias Utara","Kota Gunungsitoli"],
        "Cabdisdik Wilayah XIV": ["Nias Selatan","Nias Barat"]
    }

    # =========================
    # FILTER BERJENJANG
    # =========================

    col1, col2, col3 = st.columns(3)

    with col1:
        cabang = st.selectbox("Cabang Dinas", cabang_dinas)

    with col2:
        kabupaten = st.selectbox("Kabupaten", kabupaten_map[cabang])

    with col3:
        tanggal = st.date_input("Tanggal", datetime.now())

    # =========================
    # AMBIL DATA
    # =========================

    tgl = tanggal.strftime("%Y-%m-%d")

    data = pd.read_sql(
        "SELECT * FROM aktivitas WHERE tanggal=?",
        conn,
        params=(tgl,)
    )

    if len(data) == 0:
        st.warning("Tidak ada data")
        st.stop()

    # =========================
    # JOIN GURU (WAJIB)
    # =========================

    guru_map = pd.read_sql("SELECT nik,nama,sekolah FROM guru", conn)

    data = data.merge(guru_map, on="nama", how="left")

    # =========================
    # FILTER SEKOLAH (BARU MUNCUL SETELAH CABDIS + KAB)
    # =========================

    sekolah_list = sorted(data["sekolah"].dropna().unique().tolist())

    sekolah = st.selectbox("Sekolah", ["Semua"] + sekolah_list)

    if sekolah != "Semua":
        data = data[data["sekolah"] == sekolah]

    # =========================
    # TAMPILKAN DATA (FIX DUPLIKAT + FOTO)
    # =========================
    
    for i, row in data.iterrows():
    
        col1, col2, col3 = st.columns([1,2,1])
    
        # =========================
        # FOTO (1 SAJA)
        # =========================
        with col1:
    
            path = os.path.join("uploads", row.get("foto",""))
    
            if os.path.exists(path):
                st.image(path, width=120)
            else:
                st.warning("Foto tidak ada")
    
        # =========================
        # INFO
        # =========================
        with col2:
    
            st.write(f"**{row['nama']}**")
            st.write(f"Sekolah: {row.get('sekolah','-')}")
            st.write(f"Kelas: {row.get('kelas','-')}")
            st.write(f"Jam: {row.get('jam','-')} ({row.get('jenis','-')})")
            st.write(f"Status Sistem: {row.get('status','-')}")
            st.write(f"Validasi Admin: {row.get('validasi_admin','Belum')}")
    
        # =========================
        # VALIDASI (1 SAJA)
        # =========================
        with col3:
    
            pilihan = ["Belum", "Sesuai", "Tidak Sesuai"]
    
            current = row.get("validasi_admin", "Belum")
    
            if current not in pilihan:
                current = "Belum"
    
            valid = st.selectbox(
                "Validasi",
                pilihan,
                index=pilihan.index(current),
                key=f"val_{row['id']}"
            )
    
            if st.button("Simpan", key=f"btn_{row['id']}"):
    
                cursor.execute("""
                    UPDATE aktivitas
                    SET validasi_admin=?
                    WHERE id=?
                """, (valid, row["id"]))
    
                conn.commit()
    
                st.success("Validasi tersimpan")
                st.rerun()
    
        st.markdown("---")
# ==============================
# LAPORAN KADIS
# ==============================

elif menu == "Laporan Kadis":

    st.title("📊 Laporan Rekap Kadis")

    data = pd.read_sql("SELECT * FROM aktivitas", conn)

    if len(data) == 0:
        st.warning("Belum ada data")
        st.stop()

    # hanya yang sudah divalidasi admin
    data = data[data["validasi_admin"] != "Belum"]

    rekap_list = []

    for nama in data["nama"].unique():

        df = data[data["nama"] == nama]

        nik = df.iloc[0]["nik"]

        sesuai = len(df[df["validasi_admin"] == "Sesuai"])
        tidak = len(df[df["validasi_admin"] == "Tidak Sesuai"])

        kelas_sesuai = ", ".join(df[df["validasi_admin"]=="Sesuai"]["kelas"].unique())
        kelas_tidak = ", ".join(df[df["validasi_admin"]=="Tidak Sesuai"]["kelas"].unique())

        alasan = "\n".join(df[df["validasi_admin"]=="Tidak Sesuai"]["alasan"].dropna().unique())

        rekap_list.append({
            "Nama Guru": nama,
            "NIK": nik,
            "Jam Sesuai": sesuai,
            "Jam Tidak Sesuai": tidak,
            "Kelas Sesuai": kelas_sesuai,
            "Kelas Tidak Sesuai": kelas_tidak,
            "Alasan": alasan
        })

    rekap = pd.DataFrame(rekap_list)

    st.dataframe(rekap)

    # DOWNLOAD CSV
    csv = rekap.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Rekap Kadis",
        csv,
        "laporan_kadis.csv",
        "text/csv"
    )

    # =========================
    # AMANKAN FORMAT TANGGAL
    # =========================
    data["tanggal"] = pd.to_datetime(data["tanggal"], errors="coerce")
    
    # buang data yang tanggalnya error
    data = data.dropna(subset=["tanggal"])
    
    # =========================
    # REKAP MINGGUAN
    # =========================
    mingguan = data.groupby([
        "nama",
        pd.Grouper(key="tanggal", freq="W"),
        "validasi_admin"
    ]).size().unstack(fill_value=0)
    
    st.subheader("Rekap Mingguan")
    st.dataframe(mingguan)
    
    # =========================
    # REKAP BULANAN (FIX)
    # =========================
    bulanan = data.groupby([
        "nama",
        pd.Grouper(key="tanggal", freq="MS"),  # 🔥 FIX DI SINI
        "validasi_admin"
    ]).size().unstack(fill_value=0)
    
    st.subheader("Rekap Bulanan")
    st.dataframe(bulanan)
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
# ==============================
# REKAP JP
# ==============================

elif menu == "Rekap JP":

    st.title("📊 Rekap JP Guru")

    data = pd.read_sql("SELECT * FROM aktivitas", conn)

    if len(data) == 0:
        st.warning("Belum ada data")
        st.stop()

    # hanya yang sudah divalidasi
    data = data[data["validasi_admin"] != "Belum"]

    # hitung jumlah
    rekap = data.groupby(["nama","validasi_admin"]).size().unstack(fill_value=0)

    st.dataframe(rekap)

    # download
    csv = rekap.to_csv().encode("utf-8")

    st.download_button(
        "Download Rekap JP",
        csv,
        "rekap_jp_guru.csv",
        "text/csv"
    )
