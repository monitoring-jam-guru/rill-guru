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
# DASHBOARD
# ==============================

if menu == "Dashboard":

    st.title("DIMORA-SU")
    st.caption("Digital Monitoring Jam Mengajar Guru")

    # 🔥 SAMAKAN WAKTU (WIB)
    hari_ini = (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d")
    
    data_today = aktivitas[aktivitas["tanggal"] == hari_ini]
    
    # 🔥 DEBUG kalau kosong
    if len(data_today) == 0:
        st.warning("Tidak ada data hari ini")
        st.write("DEBUG tanggal:", hari_ini)
        st.write("Contoh tanggal di DB:", aktivitas["tanggal"].unique()[:5])
    
    # 🔥 ANTISIPASI kalau kolom belum ada
    if "validasi_admin" not in data_today.columns:
        data_today["validasi_admin"] = "Belum"
    
    # 🔥 PERHITUNGAN YANG BENAR
    sesuai = len(data_today[data_today["validasi_admin"] == "Sesuai"])
    tidak = len(data_today[data_today["validasi_admin"] == "Tidak Sesuai"])

    col1,col2,col3 = st.columns(3)

    col1.metric("Total Guru", len(guru))
    col2.metric("Mengajar Sesuai", sesuai)
    col3.metric("Tidak Sesuai", tidak)

    if len(data_today) > 0:
        st.bar_chart(data_today.groupby("validasi_admin").size())

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

                    jam_mulai = pd.to_datetime(
                        str(row.get("jam_mulai","")).replace(".",":"),
                        errors="coerce"
                    ).strftime("%H:%M:%S")
                    
                    jam_selesai = pd.to_datetime(
                        str(row.get("jam_selesai","")).replace(".",":"),
                        errors="coerce"
                    ).strftime("%H:%M:%S")

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
                    INSERT OR IGNORE INTO jadwal
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
# UPLOAD FOTO MENGAJAR (FINAL FIX)
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

    hari_map = {
        "Monday":"Senin",
        "Tuesday":"Selasa",
        "Wednesday":"Rabu",
        "Thursday":"Kamis",
        "Friday":"Jumat",
        "Saturday":"Sabtu",
        "Sunday":"Minggu"
    }

    hari = hari_map.get(tanggal.strftime("%A"))

    if hari is None:
        st.warning("Hari tidak valid")
        st.stop()

    st.write(f"Hari Mengajar : **{hari}**")

    # =========================
    # AMBIL & FILTER JADWAL (ANTI BUG)
    # =========================
    jadwal_hari_ini = pd.read_sql(
        "SELECT kelas,jam_mulai,jam_selesai,hari FROM jadwal WHERE nik=?",
        conn,
        params=(nik,)
    )

    if len(jadwal_hari_ini) == 0:
        st.warning("Tidak ada data jadwal")
        st.stop()

    # bersihkan
    jadwal_hari_ini["hari"] = jadwal_hari_ini["hari"].astype(str).str.strip().str.lower()
    jadwal_hari_ini["jam_mulai"] = jadwal_hari_ini["jam_mulai"].astype(str).str.replace(".",":")
    jadwal_hari_ini["jam_selesai"] = jadwal_hari_ini["jam_selesai"].astype(str).str.replace(".",":")

    # filter hari
    jadwal_hari_ini = jadwal_hari_ini[
        jadwal_hari_ini["hari"] == hari.lower()
    ]

    if len(jadwal_hari_ini) == 0:
        st.warning("Tidak ada jadwal mengajar hari ini")
        st.stop()

    # urutkan jam
    jadwal_hari_ini = jadwal_hari_ini.sort_values("jam_mulai")

    # =========================
    # TAMPILKAN JADWAL
    # =========================
    st.subheader("Jadwal Hari Ini")

    for i, row in jadwal_hari_ini.iterrows():

        kelas = row["kelas"]
        mulai = row["jam_mulai"]
        selesai = row["jam_selesai"]

        st.write(f"📚 {kelas} | {mulai} - {selesai}")

        if st.button(f"Pilih {kelas}", key=f"kelas_{kelas}_{i}"):
            st.session_state.kelas_aktif = kelas
            st.session_state.jam_mulai = mulai
            st.session_state.jam_selesai = selesai

    # =========================
    # SELFIE FOTO
    # =========================
    if "kelas_aktif" in st.session_state:

        st.subheader(f"Selfie Kelas {st.session_state.kelas_aktif}")

        jenis_absen = st.radio(
            "Jenis Absensi",
            ["Masuk Kelas", "Selesai Kelas"]
        )

        foto = st.camera_input("Ambil Foto")

        if st.button("Upload Foto"):

            if foto is None:
                st.error("Ambil foto dulu")
                st.stop()

            waktu = datetime.utcnow() + timedelta(hours=7)

            tanggal_str = waktu.strftime("%Y-%m-%d")
            jam = waktu.strftime("%H:%M:%S")

            jam_upload = datetime.strptime(jam, "%H:%M:%S")

            mulai = st.session_state.jam_mulai
            selesai = st.session_state.jam_selesai

            mulai_dt = datetime.strptime(mulai, "%H:%M:%S")
            selesai_dt = datetime.strptime(selesai, "%H:%M:%S")

            status = "Tidak Sesuai"

            # =========================
            # VALIDASI MASUK (±5 MENIT)
            # =========================
            if jenis_absen == "Masuk Kelas":

                awal = mulai_dt - timedelta(minutes=5)
                akhir = mulai_dt + timedelta(minutes=5)

                if awal <= jam_upload <= akhir:
                    status = "Sesuai"

            # =========================
            # VALIDASI KELUAR (±5 MENIT)
            # =========================
            elif jenis_absen == "Selesai Kelas":

                awal = selesai_dt - timedelta(minutes=5)
                akhir = selesai_dt + timedelta(minutes=5)

                if awal <= jam_upload <= akhir:
                    status = "Sesuai"

            # =========================
            # SIMPAN FOTO
            # =========================
            if not os.path.exists("uploads"):
                os.makedirs("uploads")

            filename = f"{nik}_{tanggal_str}_{jam.replace(':','-')}.jpg"
            path = os.path.join("uploads", filename)

            with open(path, "wb") as f:
                f.write(foto.getbuffer())

            watermark(
                path,
                f"{nama} {st.session_state.kelas_aktif} {tanggal_str} {jam}"
            )

            st.info("Upload berhasil")

            # =========================
            # SIMPAN DB
            # =========================
            hari_nama = hari_map[waktu.strftime("%A")]
            tanggal_format = waktu.strftime("%d-%m-%Y")

            if status == "Tidak Sesuai":
                alasan = f"{hari_nama}, {tanggal_format} | {jenis_absen} jam {jam} | jadwal {mulai}-{selesai}"
            else:
                alasan = "Sesuai Jadwal"

            cursor.execute(
            """
            INSERT INTO aktivitas
            (nik,nama,tanggal,jam,kelas,jenis,status,foto,jam_jadwal,alasan)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                nik,
                nama,
                tanggal_str,
                jam,
                st.session_state.kelas_aktif,
                jenis_absen,
                status,
                filename,
                f"{mulai} - {selesai}",
                alasan
            )
            )

            conn.commit()

            st.success(f"Berhasil ({status})")

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
