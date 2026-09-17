import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta

# --- VERİTABANI BAĞLANTISI VE TABLOLAR ---
def get_db():
    conn = sqlite3.connect("apart_yonetim.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Odalar tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS odalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oda_adi TEXT UNIQUE NOT NULL,
                kapasite INTEGER DEFAULT 2
            )
        """)
        # Rezervasyonlar tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rezervasyonlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oda_id INTEGER NOT NULL,
                misafir_adi TEXT NOT NULL,
                telefon TEXT,
                giris_tarihi TEXT NOT NULL,
                cikis_tarihi TEXT NOT NULL,
                toplam_ucret REAL DEFAULT 0,
                alinan_kapora REAL DEFAULT 0,
                durum TEXT DEFAULT 'Aktif',
                FOREIGN KEY (oda_id) REFERENCES odalar (id)
            )
        """)
        # Başlangıç için örnek odalar (yoksa ekler)
        cursor.execute("SELECT COUNT(*) FROM odalar")
        if cursor.fetchone()[0] == 0:
            ornek_odalar = [("Daire 101", 3), ("Daire 102", 4), ("Daire 201", 2), ("Daire 202", 5)]
            cursor.executemany("INSERT INTO odalar (oda_adi, kapasite) VALUES (?, ?)", ornek_odalar)
        conn.commit()

init_db()

# --- YARDIMCI FONKSİYONLAR ---
def tarih_cakisiyor_mu(oda_id, giris, cikis, ignore_id=None):
    with get_db() as conn:
        cursor = conn.cursor()
        query = """
            SELECT COUNT(*) FROM rezervasyonlar
            WHERE oda_id = ? 
              AND durum = 'Aktif'
              AND NOT (cikis_tarihi <= ? OR giris_tarihi >= ?)
        """
        params = [oda_id, giris.strftime("%Y-%m-%d"), cikis.strftime("%Y-%m-%d")]
        if ignore_id:
            query += " AND id != ?"
            params.append(ignore_id)
        cursor.execute(query, params)
        return cursor.fetchone()[0] > 0

# --- ARAYÜZ YAPILANDIRMASI ---
st.set_page_config(page_title="Apart Yönetim Paneli", layout="wide", page_icon="🏢")
st.title("🏢 Apart Rezervasyon & Yönetim Paneli")

menu = st.sidebar.radio("Menü", ["📊 Genel Durum", "➕ Yeni Rezervasyon", "📅 Doluluk Takvimi", "💰 Kasa & Ödemeler", "⚙️ Daire Yönetimi"])

bugun = date.today()

# --- 1. GENEL DURUM (DASHBOARD) ---
if menu == "📊 Genel Durum":
    st.subheader(f"Günün Özeti ({bugun.strftime('%d.%m.%Y')})")
    
    with get_db() as conn:
        odalar_df = pd.read_sql_query("SELECT * FROM odalar", conn)
        rez_df = pd.read_sql_query("SELECT r.*, o.oda_adi FROM rezervasyonlar r JOIN odalar o ON r.oda_id = o.id WHERE r.durum = 'Aktif'", conn)

    # Bugün giriş/çıkış ve aktif konaklamalar
    bugun_str = bugun.strftime("%Y-%m-%d")
    girisler = rez_df[rez_df['giris_tarihi'] == bugun_str] if not rez_df.empty else pd.DataFrame()
    cikislar = rez_df[rez_df['cikis_tarihi'] == bugun_str] if not rez_df.empty else pd.DataFrame()
    
    # Şu an içinde bulunulan konaklamalar
    if not rez_df.empty:
        su_an_dolu = rez_df[(rez_df['giris_tarihi'] <= bugun_str) & (rez_df['cikis_tarihi'] > bugun_str)]
        dolu_oda_idleri = set(su_an_dolu['oda_id'].tolist())
    else:
        dolu_oda_idleri = set()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Daire", len(odalar_df))
    c2.metric("Şu An Dolu Daireler", len(dolu_oda_idleri))
    c3.metric("Bugün Giriş Yapacaklar", len(girisler))
    c4.metric("Bugün Çıkış Yapacaklar", len(cikislar))

    st.markdown("---")
    st.markdown("### Dairelerin Anlık Durumu")
    
    cols = st.columns(4)
    for idx, row in odalar_df.iterrows():
        col = cols[idx % 4]
        is_dolu = row['id'] in dolu_oda_idleri
        with col:
            if is_dolu:
                rez_bilgi = su_an_dolu[su_an_dolu['oda_id'] == row['id']].iloc[0]
                st.error(f"🔴 **{row['oda_adi']}**\n\n**Dolu**\n\nMisafir: {rez_bilgi['misafir_adi']}\n\nÇıkış: {rez_bilgi['cikis_tarihi']}")
            else:
                st.success(f"🟢 **{row['oda_adi']}**\n\n**Boş (Müsait)**\n\nKapasite: {row['kapasite']} Kişi")

    if not girisler.empty:
        st.markdown("### 📥 Bugün Giriş Yapacak Misafirler")
        st.dataframe(girisler[['oda_adi', 'misafir_adi', 'telefon', 'cikis_tarihi', 'toplam_ucret', 'alinan_kapora']], use_container_width=True)

    if not cikislar.empty:
        st.markdown("### 📤 Bugün Çıkış Yapacak Misafirler")
        st.dataframe(cikislar[['oda_adi', 'misafir_adi', 'telefon', 'toplam_ucret', 'alinan_kapora']], use_container_width=True)


# --- 2. YENİ REZERVASYON ---
elif menu == "➕ Yeni Rezervasyon":
    st.subheader("Yeni Misafir Kaydı")

    with get_db() as conn:
        odalar = conn.execute("SELECT id, oda_adi FROM odalar").fetchall()

    with st.form("rezervasyon_formu"):
        col1, col2 = st.columns(2)
        with col1:
            misafir = st.text_input("Misafir Adı Soyadı *")
            telefon = st.text_input("Telefon Numarası")
            giris = st.date_input("Giriş Tarihi", value=bugun, min_value=bugun)
        with col2:
            cikis = st.date_input("Çıkış Tarihi", value=bugun + timedelta(days=1), min_value=bugun + timedelta(days=1))
            toplam_ucret = st.number_input("Toplam Ücret (TL)", min_value=0.0, step=100.0)
            kapora = st.number_input("Alınan Kapora (TL)", min_value=0.0, step=100.0)

        # Seçilen tarihlerde boş olan odaları tespit et
        musait_odalar = []
        if cikis > giris:
            for oda in odalar:
                if not tarih_cakisiyor_mu(oda['id'], giris, cikis):
                    musait_odalar.append(oda)

        secilen_oda = None
        if musait_odalar:
            secilen_oda = st.selectbox("Müsait Daire Seçin *", options=musait_odalar, format_func=lambda x: x['oda_adi'])
        else:
            st.warning("⚠️ Seçilen tarih aralığında boş daire bulunmuyor.")

        kaydet = st.form_submit_button("Rezervasyonu Onayla ve Kaydet")

        if kaydet:
            if not misafir.strip():
                st.error("Misafir adı zorunludur.")
            elif not secilen_oda:
                st.error("Müsait bir daire seçilmedi.")
            elif giris >= cikis:
                st.error("Çıkış tarihi giriş tarihinden sonra olmalıdır.")
            else:
                with get_db() as conn:
                    conn.execute("""
                        INSERT INTO rezervasyonlar (oda_id, misafir_adi, telefon, giris_tarihi, cikis_tarihi, toplam_ucret, alinan_kapora)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (secilen_oda['id'], misafir, telefon, giris.strftime("%Y-%m-%d"), cikis.strftime("%Y-%m-%d"), toplam_ucret, kapora))
                    conn.commit()
                st.success(f"{secilen_oda['oda_adi']} için rezervasyon başarıyla kaydedildi!")


# --- 3. DOLULUK TAKVİMİ ---
elif menu == "📅 Doluluk Takvimi":
    st.subheader("Önümüzdeki 15 Günün Doluluk Haritası")
    
    gunler = [bugun + timedelta(days=i) for i in range(15)]
    tarih_basliklari = [g.strftime("%d/%m") for g in gunler]

    with get_db() as conn:
        odalar = conn.execute("SELECT id, oda_adi FROM odalar").fetchall()
        rezervasyonlar = conn.execute("SELECT * FROM rezervasyonlar WHERE durum = 'Aktif'").fetchall()

    matris_data = []
    for oda in odalar:
        satir = {"Daire": oda['oda_adi']}
        for g, baslik in zip(gunler, tarih_basliklari):
            g_str = g.strftime("%Y-%m-%d")
            # O güne denk gelen aktif rezervasyon
            dolu = False
            misafir = ""
            for r in rezervasyonlar:
                if r['oda_id'] == oda['id'] and (r['giris_tarihi'] <= g_str < r['cikis_tarihi']):
                    dolu = True
                    misafir = r['misafir_adi'].split()[0]
                    break
            satir[baslik] = f"🔴 {misafir}" if dolu else "🟢 Boş"
        matris_data.append(satir)

    df_takvim = pd.DataFrame(matris_data).set_index("Daire")
    st.dataframe(df_takvim, use_container_width=True)


# --- 4. KASA & ÖDEMELER ---
elif menu == "💰 Kasa & Ödemeler":
    st.subheader("Alacak & Tahsilat Durumu")
    
    with get_db() as conn:
        df = pd.read_sql_query("""
            SELECT r.id, o.oda_adi, r.misafir_adi, r.telefon, r.giris_tarihi, r.cikis_tarihi, 
                   r.toplam_ucret, r.alinan_kapora, (r.toplam_ucret - r.alinan_kapora) as kalan_bakiye, r.durum
            FROM rezervasyonlar r 
            JOIN odalar o ON r.oda_id = o.id 
            WHERE r.durum = 'Aktif'
            ORDER BY r.giris_tarihi ASC
        """, conn)

    if not df.empty:
        toplam_ciro = df['toplam_ucret'].sum()
        toplam_tahsilat = df['alinan_kapora'].sum()
        bekleyen_alacak = df['kalan_bakiye'].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Rezervasyon Tutarı", f"{toplam_ciro:,.2f} TL")
        c2.metric("Tahsil Edilen (Kapora Dahil)", f"{toplam_tahsilat:,.2f} TL")
        c3.metric("Kalan Açık Bakiye", f"{bekleyen_alacak:,.2f} TL")

        st.markdown("---")
        st.dataframe(df[['oda_adi', 'misafir_adi', 'giris_tarihi', 'cikis_tarihi', 'toplam_ucret', 'alinan_kapora', 'kalan_bakiye']], use_container_width=True)
    else:
        st.info("Henüz aktif bir rezervasyon kaydı yok.")


# --- 5. DAİRE YÖNETİMİ ---
elif menu == "⚙️ Daire Yönetimi":
    st.subheader("Daire Tanımlama & Düzenleme")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### Yeni Daire Ekle")
        with st.form("yeni_oda"):
            yeni_oda_adi = st.text_input("Daire Adı / No (Örn: 203)")
            yeni_kapasite = st.number_input("Kişi Kapasitesi", min_value=1, max_value=20, value=3)
            ekle = st.form_submit_button("Daireyi Ekle")
            if ekle and yeni_oda_adi.strip():
                try:
                    with get_db() as conn:
                        conn.execute("INSERT INTO odalar (oda_adi, kapasite) VALUES (?, ?)", (yeni_oda_adi.strip(), yeni_kapasite))
                        conn.commit()
                    st.success("Daire başarıyla eklendi!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Bu isimde bir daire zaten var.")

    with col2:
        st.markdown("#### Mevcut Daireler")
        with get_db() as conn:
            mevcut_odalar = pd.read_sql_query("SELECT id, oda_adi, kapasite FROM odalar", conn)
        st.dataframe(mevcut_odalar, use_container_width=True)
