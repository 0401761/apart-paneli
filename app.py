import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Apart Yönetim Sistemi",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ÖZEL MODERN CSS TASARIMI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Ana Kart Yapısı */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px -2px rgba(0,0,0,0.3);
        margin-bottom: 12px;
    }
    
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 4px;
    }
    
    .metric-label {
        font-size: 13px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 600;
    }

    /* Kat ve Bina Görselleştirmesi */
    .floor-title {
        color: #38bdf8;
        font-size: 16px;
        font-weight: 600;
        border-bottom: 1px solid rgba(56, 189, 248, 0.2);
        padding-bottom: 6px;
        margin: 18px 0 10px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .room-box {
        border-radius: 14px;
        padding: 16px 18px;
        margin-bottom: 10px;
        transition: all 0.2s ease;
        border: 1px solid transparent;
    }

    .room-available {
        background: linear-gradient(145deg, rgba(16, 185, 129, 0.12), rgba(6, 78, 59, 0.25));
        border-color: rgba(16, 185, 129, 0.35);
    }

    .room-occupied {
        background: linear-gradient(145deg, rgba(239, 68, 68, 0.12), rgba(127, 29, 29, 0.25));
        border-color: rgba(239, 68, 68, 0.35);
    }

    .room-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }

    .room-name {
        font-size: 17px;
        font-weight: 700;
        color: #f8fafc;
    }

    .badge-free {
        background-color: #10b981;
        color: #022c22;
        font-size: 11px;
        font-weight: 700;
        padding: 3px 9px;
        border-radius: 20px;
    }

    .badge-busy {
        background-color: #ef4444;
        color: #ffffff;
        font-size: 11px;
        font-weight: 700;
        padding: 3px 9px;
        border-radius: 20px;
    }

    .room-detail {
        font-size: 13px;
        color: #cbd5e1;
        margin: 3px 0;
    }
    
    /* Buton İyileştirmeleri */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #2563eb, #3b82f6);
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 10px 24px;
        transition: transform 0.1s;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# --- VERİTABANI İŞLEMLERİ ---
DB_NAME = "apart_yonetim.db"

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        # Odalar tablosu
        c.execute("""
            CREATE TABLE IF NOT EXISTS odalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oda_adi TEXT UNIQUE NOT NULL,
                kat TEXT NOT NULL,
                kapasite INTEGER DEFAULT 3
            )
        """)
        # Rezervasyonlar tablosu
        c.execute("""
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
        
        # 9 Daireyi tam mimariye göre hazırla (Zemin: 2, 1. Kat: 2, 2. Kat: 2, 3. Kat: 2, Çatı: 1)
        c.execute("SELECT COUNT(*) FROM odalar")
        if c.fetchone()[0] == 0:
            varsayilan_daireler = [
                ("Çatı Katı Daire", "Çatı Katı", 2),
                ("Daire 301", "3. Kat", 4),
                ("Daire 302", "3. Kat", 4),
                ("Daire 201", "2. Kat", 4),
                ("Daire 202", "2. Kat", 4),
                ("Daire 101", "1. Kat", 4),
                ("Daire 102", "1. Kat", 4),
                ("Zemin Daire 1", "Zemin Kat", 3),
                ("Zemin Daire 2", "Zemin Kat", 3)
            ]
            c.executemany("INSERT INTO odalar (oda_adi, kat, kapasite) VALUES (?, ?, ?)", varsayilan_daireler)
        conn.commit()

init_db()

# --- YARDIMCI SORGULAR ---
def fetch_odalar():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, oda_adi, kat, kapasite FROM odalar ORDER BY id ASC")
        rows = c.fetchall()
        return [{"id": r[0], "oda_adi": r[1], "kat": r[2], "kapasite": r[3]} for r in rows]

def musait_odalar_bul(giris_tarihi, cikis_tarihi):
    g_str = giris_tarihi.strftime("%Y-%m-%d")
    c_str = cikis_tarihi.strftime("%Y-%m-%d")
    with get_db() as conn:
        c = conn.cursor()
        # Çakışan aktif rezervasyonları filtrele
        c.execute("""
            SELECT id, oda_adi, kat, kapasite FROM odalar
            WHERE id NOT IN (
                SELECT oda_id FROM rezervasyonlar
                WHERE durum = 'Aktif'
                  AND NOT (cikis_tarihi <= ? OR giris_tarihi >= ?)
            )
            ORDER BY id ASC
        """, (g_str, c_str))
        rows = c.fetchall()
        return [{"id": r[0], "oda_adi": r[1], "kat": r[2], "kapasite": r[3]} for r in rows]

bugun = date.today()
bugun_str = bugun.strftime("%Y-%m-%d")

# --- MENÜ ---
with st.sidebar:
    st.markdown("## 🏢 Apart Sistemi")
    st.caption("Yönetim & Rezervasyon")
    menu = st.radio(
        "Gezinme",
        ["📊 Kat Planı & Durum", "➕ Yeni Rezervasyon", "📅 Doluluk Takvimi", "💰 Kasa & Bakiyeler", "⚙️ Daire Ayarları"],
        index=0
    )
    st.markdown("---")
    st.info(f"📅 Bugün: **{bugun.strftime('%d.%m.%Y')}**")

# ==========================================
# 1. KAT PLANI & CANLI DURUM
# ==========================================
if menu == "📊 Kat Planı & Durum":
    st.markdown("### 🏢 Apart Kat Planı & Anlık Doluluk")
    
    with get_db() as conn:
        rez_df = pd.read_sql_query("""
            SELECT r.*, o.oda_adi 
            FROM rezervasyonlar r 
            JOIN odalar o ON r.oda_id = o.id 
            WHERE r.durum = 'Aktif'
        """, conn)

    # Aktif konaklamalar
    if not rez_df.empty:
        su_an_dolu = rez_df[(rez_df['giris_tarihi'] <= bugun_str) & (rez_df['cikis_tarihi'] > bugun_str)]
        dolu_odalar = {row['oda_id']: row for _, row in su_an_dolu.iterrows()}
        girisler = rez_df[rez_df['giris_tarihi'] == bugun_str]
        cikislar = rez_df[rez_df['cikis_tarihi'] == bugun_str]
    else:
        dolu_odalar = {}
        girisler = pd.DataFrame()
        cikislar = pd.DataFrame()

    tum_odalar = fetch_odalar()
    toplam_daire = len(tum_odalar)
    dolu_sayisi = len(dolu_odalar)
    bos_sayisi = toplam_daire - dolu_sayisi

    # Üst İstatistik Kartları
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="metric-card"><div class="metric-label">Toplam Daire</div><div class="metric-value">{toplam_daire}</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="metric-card"><div class="metric-label">Boş Daireler</div><div class="metric-value" style="color:#10b981;">{bos_sayisi}</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="metric-card"><div class="metric-label">Bugün Giriş</div><div class="metric-value" style="color:#38bdf8;">{len(girisler)}</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="metric-card"><div class="metric-label">Bugün Çıkış</div><div class="metric-value" style="color:#f59e0b;">{len(cikislar)}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Katlara Göre Gruplama (Yukarıdan aşağıya: Çatı -> 3 -> 2 -> 1 -> Zemin)
    kat_sirasi = ["Çatı Katı", "3. Kat", "2. Kat", "1. Kat", "Zemin Kat"]
    
    for kat in kat_sirasi:
        kat_odalari = [o for o in tum_odalar if o["kat"] == kat]
        if not kat_odalari:
            continue
            
        st.markdown(f'<div class="floor-title">🏠 {kat}</div>', unsafe_allow_html=True)
        cols = st.columns(len(kat_odalari))
        
        for idx, oda in enumerate(kat_odalari):
            with cols[idx]:
                is_busy = oda["id"] in dolu_odalar
                if is_busy:
                    rez = dolu_odalar[oda["id"]]
                    kalan_tutar = rez['toplam_ucret'] - rez['alinan_kapora']
                    st.markdown(f"""
                    <div class="room-box room-occupied">
                        <div class="room-header">
                            <span class="room-name">{oda['oda_adi']}</span>
                            <span class="badge-busy">DOLU</span>
                        </div>
                        <div class="room-detail">👤 <b>{rez['misafir_adi']}</b></div>
                        <div class="room-detail">📞 {rez['telefon'] or 'Yok'}</div>
                        <div class="room-detail">📅 Çıkış: {rez['cikis_tarihi']}</div>
                        <div class="room-detail" style="color:#f87171; font-weight:600;">Kalan: {kalan_tutar:,.0f} TL</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="room-box room-available">
                        <div class="room-header">
                            <span class="room-name">{oda['oda_adi']}</span>
                            <span class="badge-free">BOŞ</span>
                        </div>
                        <div class="room-detail">👥 Kapasite: {oda['kapasite']} Kişilik</div>
                        <div class="room-detail" style="color:#34d399;">Yeni misafire hazır</div>
                    </div>
                    """, unsafe_allow_html=True)

    if not girisler.empty or not cikislar.empty:
        st.markdown("---")
        h1, h2 = st.columns(2)
        with h1:
            if not girisler.empty:
                st.markdown("#### 📥 Bugün Gelecekler")
                st.dataframe(girisler[['oda_adi', 'misafir_adi', 'telefon', 'cikis_tarihi']], use_container_width=True, hide_index=True)
        with h2:
            if not cikislar.empty:
                st.markdown("#### 📤 Bugün Çıkacaklar")
                st.dataframe(cikislar[['oda_adi', 'misafir_adi', 'telefon']], use_container_width=True, hide_index=True)

# ==========================================
# 2. YENİ REZERVASYON (HATASIZ & AKILLI)
# ==========================================
elif menu == "➕ Yeni Rezervasyon":
    st.markdown("### ➕ Yeni Rezervasyon Oluştur")
    st.caption("Tarihleri belirlediğinizde sistem yalnızca o günlerde boş olan daireleri listeler.")

    with st.container():
        c_tarih1, c_tarih2 = st.columns(2)
        with c_tarih1:
            giris = st.date_input("Giriş Tarihi", value=bugun, min_value=bugun)
        with c_tarih2:
            cikis = st.date_input("Çıkış Tarihi", value=bugun + timedelta(days=1), min_value=bugun + timedelta(days=1))

    if cikis <= giris:
        st.error("⚠️ Çıkış tarihi giriş tarihinden en az 1 gün sonra olmalıdır.")
    else:
        # Müsait odaları çek (Sözlük formatında, deepcopy hatasını engeller)
        musaitler = musait_odalar_bul(giris, cikis)
        
        with st.form("yeni_rezervasyon_formu"):
            st.markdown("#### Misafir ve Daire Bilgileri")
            
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                misafir_adi = st.text_input("Misafir Adı Soyadı *", placeholder="Örn: Ahmet Yılmaz")
                telefon = st.text_input("Telefon Numarası", placeholder="05XXXXXXXXX")
            with c_m2:
                toplam_ucret = st.number_input("Toplam Anlaşılan Ücret (TL)", min_value=0.0, step=250.0, value=1500.0)
                alinan_kapora = st.number_input("Alınan Peşinat / Kapora (TL)", min_value=0.0, step=100.0, value=500.0)

            kalan_ucret = max(0.0, toplam_ucret - alinan_kapora)
            st.info(f"💡 Girişte Alınacak Kalan Tutar: **{kalan_ucret:,.2f} TL**")

            st.markdown("---")
            
            if musaitler:
                oda_secenekleri = {f"{oda['oda_adi']} ({oda['kat']} - {oda['kapasite']} Kişi)": oda['id'] for oda in musaitler}
                secilen_etiket = st.selectbox("Boş Daire Seçiniz *", options=list(oda_secenekleri.keys()))
                secilen_oda_id = oda_secenekleri[secilen_etiket]
                
                kaydet_butonu = st.form_submit_button("✅ Rezervasyonu Kesinleştir ve Kaydet", use_container_width=True)
                
                if kaydet_butonu:
                    if not misafir_adi.strip():
                        st.error("Lütfen misafir adını giriniz.")
                    else:
                        with get_db() as conn:
                            conn.execute("""
                                INSERT INTO rezervasyonlar (oda_id, misafir_adi, telefon, giris_tarihi, cikis_tarihi, toplam_ucret, alinan_kapora)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (secilen_oda_id, misafir_adi.strip(), telefon.strip(), giris.strftime("%Y-%m-%d"), cikis.strftime("%Y-%m-%d"), toplam_ucret, alinan_kapora))
                            conn.commit()
                        st.success(f"🎉 {secilen_etiket} için rezervasyon başarıyla oluşturuldu!")
                        st.balloons()
            else:
                st.warning("❌ Seçilen tarih aralığında tüm daireler doludur.")
                st.form_submit_button("Daire Bulunamadı", disabled=True, use_container_width=True)

# ==========================================
# 3. DOLULUK TAKVİMİ
# ==========================================
elif menu == "📅 Doluluk Takvimi":
    st.markdown("### 📅 15 Günlük Doluluk Matrisi")
    st.caption("Dairelerin önümüzdeki iki haftalık doluluk durumu.")

    gunler = [bugun + timedelta(days=i) for i in range(15)]
    basliklar = [g.strftime("%d/%m") for g in gunler]

    with get_db() as conn:
        odalar = conn.execute("SELECT id, oda_adi, kat FROM odalar ORDER BY id ASC").fetchall()
        rezervasyonlar = conn.execute("SELECT oda_id, misafir_adi, giris_tarihi, cikis_tarihi FROM rezervasyonlar WHERE durum = 'Aktif'").fetchall()

    matris = []
    for o_id, o_adi, o_kat in odalar:
        satir = {"Daire": f"{o_adi} ({o_kat})"}
        for g, baslik in zip(gunler, basliklar):
            g_str = g.strftime("%Y-%m-%d")
            isim = ""
            for r_oid, r_isim, r_gir, r_cik in rezervasyonlar:
                if r_oid == o_id and (r_gir <= g_str < r_cik):
                    isim = r_isim.split()[0] # sadece ilk adı göster
                    break
            satir[baslik] = f"🔴 {isim}" if isim else "🟢 Boş"
        matris.append(satir)

    df_takvim = pd.DataFrame(matris).set_index("Daire")
    st.dataframe(df_takvim, use_container_width=True)

# ==========================================
# 4. KASA & BAKİYELER
# ==========================================
elif menu == "💰 Kasa & Bakiyeler":
    st.markdown("### 💰 Kasa & Misafir Alacak Takibi")
    
    with get_db() as conn:
        df = pd.read_sql_query("""
            SELECT r.id, o.oda_adi, r.misafir_adi, r.telefon, r.giris_tarihi, r.cikis_tarihi,
                   r.toplam_ucret, r.alinan_kapora, (r.toplam_ucret - r.alinan_kapora) as kalan_tutar
            FROM rezervasyonlar r
            JOIN odalar o ON r.oda_id = o.id
            WHERE r.durum = 'Aktif'
            ORDER BY r.giris_tarihi ASC
        """, conn)

    if not df.empty:
        toplam_anlasma = df['toplam_ucret'].sum()
        toplam_kapora = df['alinan_kapora'].sum()
        bekleyen = df['kalan_tutar'].sum()

        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="metric-card"><div class="metric-label">Toplam Ciro</div><div class="metric-value">{toplam_anlasma:,.0f} TL</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card"><div class="metric-label">Tahsil Edilen (Kapora)</div><div class="metric-value" style="color:#10b981;">{toplam_kapora:,.0f} TL</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card"><div class="metric-label">Bekleyen Alacak</div><div class="metric-value" style="color:#ef4444;">{bekleyen:,.0f} TL</div></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Aktif Rezervasyon Listesi")
        st.dataframe(df[['oda_adi', 'misafir_adi', 'telefon', 'giris_tarihi', 'cikis_tarihi', 'toplam_ucret', 'alinan_kapora', 'kalan_tutar']], use_container_width=True, hide_index=True)
        
        # Rezervasyon İptal/Tamamlama
        st.markdown("#### Rezervasyon Tamamlama / Çıkış Verme")
        with st.form("cikis_ver_form"):
            secilen_rez_id = st.selectbox("İşlem yapılacak misafiri seçin:", options=df['id'].tolist(), format_func=lambda x: f"{df[df['id']==x]['misafir_adi'].values[0]} - {df[df['id']==x]['oda_adi'].values[0]}")
            cikis_yap = st.form_submit_button("Misafirin Çıkışını Tamamla (Arşive Al)")
            if cikis_yap:
                with get_db() as conn:
                    conn.execute("UPDATE rezervasyonlar SET durum = 'Tamamlandı' WHERE id = ?", (secilen_rez_id,))
                    conn.commit()
                st.success("İşlem tamamlandı, oda boşa çıkarıldı.")
                st.rerun()
    else:
        st.info("Kayıtlı aktif rezervasyon bulunmuyor.")

# ==========================================
# 5. DAİRE AYARLARI
# ==========================================
elif menu == "⚙️ Daire Ayarları":
    st.markdown("### ⚙️ Daire Tanımları")
    st.caption("Apartınızda kayıtlı mevcut 9 dairenin listesi:")
    
    with get_db() as conn:
        daireler_df = pd.read_sql_query("SELECT id, oda_adi, kat, kapasite FROM odalar ORDER BY id ASC", conn)
    
    st.dataframe(daireler_df, use_container_width=True, hide_index=True)
