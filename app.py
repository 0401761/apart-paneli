import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
import calendar

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Apart Yönetim Portalı",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN BALON / PILL CSS TASARIMI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .stApp {
        background-color: #090d16;
    }

    section[data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Modern Balon / Pill Navigasyon Butonları */
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }

    div[data-testid="stRadio"] label {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        padding: 12px 18px !important;
        border-radius: 50px !important; /* Balon hap stili */
        cursor: pointer !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        margin: 0 !important;
    }

    div[data-testid="stRadio"] label:hover {
        background: rgba(56, 189, 248, 0.15) !important;
        border-color: rgba(56, 189, 248, 0.4) !important;
        transform: translateX(4px);
    }

    /* Seçili Radyo Butonu Gizle ve Arka Planını Parla */
    div[data-testid="stRadio"] label div:first-child {
        display: none !important;
    }

    div[data-testid="stRadio"] label[data-checked="true"],
    div[data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
        border-color: #38bdf8 !important;
        box-shadow: 0 4px 20px rgba(37, 99, 235, 0.45) !important;
    }

    div[data-testid="stRadio"] label[data-checked="true"] p,
    div[data-testid="stRadio"] label:has(input:checked) p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* İstatistik Kartları */
    .stat-box {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 22px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }

    .stat-label {
        font-size: 12px;
        color: #94a3b8;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    .stat-val {
        font-size: 32px;
        font-weight: 800;
        color: #f8fafc;
        margin-top: 6px;
    }

    /* Daire Kartları */
    .room-card {
        border-radius: 18px;
        padding: 18px 20px;
        margin-bottom: 14px;
        border: 1px solid;
        box-shadow: 0 6px 16px rgba(0,0,0,0.25);
    }

    .room-free {
        background: linear-gradient(145deg, rgba(16, 185, 129, 0.12), rgba(6, 78, 59, 0.25));
        border-color: rgba(16, 185, 129, 0.4);
    }

    .room-busy {
        background: linear-gradient(145deg, rgba(239, 68, 68, 0.12), rgba(127, 29, 29, 0.3));
        border-color: rgba(239, 68, 68, 0.4);
    }

    .pill-badge {
        font-size: 11px;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 30px;
    }

    .pill-free { background: #10b981; color: #022c22; }
    .pill-busy { background: #ef4444; color: #ffffff; }

    /* Butonlar */
    div.stButton > button {
        border-radius: 14px !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- VERİTABANI VE AYARLAR ---
DB_NAME = "apart_yonetim.db"

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS ayarlar (
                anahtar TEXT PRIMARY KEY,
                deger TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS odalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oda_adi TEXT NOT NULL,
                kat TEXT NOT NULL,
                kapasite INTEGER DEFAULT 3
            )
        """)
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
        
        # Varsayılan apart ismi
        c.execute("INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('apart_adi', 'LUX APART')")

        # 9 Daireyi yükle (Yoksa)
        c.execute("SELECT COUNT(*) FROM odalar")
        if c.fetchone()[0] == 0:
            varsayilan = [
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
            c.executemany("INSERT INTO odalar (oda_adi, kat, kapasite) VALUES (?, ?, ?)", varsayilan)
        conn.commit()

init_db()

def get_apart_adi():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT deger FROM ayarlar WHERE anahtar = 'apart_adi'")
        res = c.fetchone()
        return res[0] if res else "APART YÖNETİM"

# --- SIDEBAR (NAVİGASYON & TARİH GEZGİNİ) ---
apart_baslik = get_apart_adi()

with st.sidebar:
    st.markdown(f"## 🏢 {apart_baslik}")
    st.caption("Apart Yönetim & Takip Sistemi")
    st.markdown("---")
    
    menu = st.radio(
        "Menü",
        [
            "🏢 Kat Planı & Durum",
            "✨ Yeni Rezervasyon",
            "📅 Aylık Doluluk Takvimi",
            "💳 Kasa & Bakiyeler",
            "📁 Rezervasyon Arşivi",
            "⚙️ Daire & Apart Ayarları"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("#### 🗓️ Gözlem Tarihi")
    st.caption("Farklı tarihlerdeki doluluk durumuna anında bakın:")
    secilen_tarih = st.date_input("İncelenen Tarih", value=date.today())
    secilen_tarih_str = secilen_tarih.strftime("%Y-%m-%d")

# ==========================================
# 1. KAT PLANI & CANLI DURUM
# ==========================================
if menu == "🏢 Kat Planı & Durum":
    st.markdown(f"## 🏢 {apart_baslik} - Kat Planı ve Doluluk")
    st.caption(f"İncelenen Tarih: **{secilen_tarih.strftime('%d.%m.%Y')}**")

    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT id, oda_adi, kat, kapasite FROM odalar ORDER BY id ASC")
        tum_odalar = [{"id": r[0], "oda_adi": r[1], "kat": r[2], "kapasite": r[3]} for r in c.fetchall()]
        
        rez_df = pd.read_sql_query("""
            SELECT r.*, o.oda_adi 
            FROM rezervasyonlar r 
            JOIN odalar o ON r.oda_id = o.id 
            WHERE r.durum = 'Aktif'
        """, conn)

    if not rez_df.empty:
        su_an_dolu = rez_df[(rez_df['giris_tarihi'] <= secilen_tarih_str) & (rez_df['cikis_tarihi'] > secilen_tarih_str)]
        dolu_odalar = {row['oda_id']: row for _, row in su_an_dolu.iterrows()}
        girisler = rez_df[rez_df['giris_tarihi'] == secilen_tarih_str]
        cikislar = rez_df[rez_df['cikis_tarihi'] == secilen_tarih_str]
    else:
        dolu_odalar = {}
        girisler = pd.DataFrame()
        cikislar = pd.DataFrame()

    toplam_daire = len(tum_odalar)
    dolu_sayisi = len(dolu_odalar)
    bos_sayisi = toplam_daire - dolu_sayisi

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="stat-box"><div class="stat-label">Toplam Daire</div><div class="stat-val">{toplam_daire}</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="stat-box"><div class="stat-label">Müsait Daire</div><div class="stat-val" style="color:#10b981;">{bos_sayisi}</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="stat-box"><div class="stat-label">O Gün Girişler</div><div class="stat-val" style="color:#38bdf8;">{len(girisler)}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="stat-box"><div class="stat-label">O Gün Çıkışlar</div><div class="stat-val" style="color:#f59e0b;">{len(cikislar)}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    kat_sirasi = ["Çatı Katı", "3. Kat", "2. Kat", "1. Kat", "Zemin Kat"]
    for kat in kat_sirasi:
        kat_odalari = [o for o in tum_odalar if o["kat"] == kat]
        if not kat_odalari:
            continue
            
        st.markdown(f"#### 📍 {kat.upper()}")
        cols = st.columns(len(kat_odalari))
        for idx, oda in enumerate(kat_odalari):
            with cols[idx]:
                if oda["id"] in dolu_odalar:
                    rez = dolu_odalar[oda["id"]]
                    kalan = rez['toplam_ucret'] - rez['alinan_kapora']
                    st.markdown(f"""
                    <div class="room-card room-busy">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b style="font-size:17px; color:#fff;">{oda['oda_adi']}</b>
                            <span class="pill-badge pill-busy">DOLU</span>
                        </div>
                        <div style="margin-top:10px; font-size:13px; color:#cbd5e1; line-height:1.6;">
                            👤 <b>{rez['misafir_adi'].upper()}</b><br>
                            📞 <code>{rez['telefon'] or 'Yok'}</code><br>
                            📅 Çıkış: <b>{rez['cikis_tarihi']}</b><br>
                            💰 Kalan: <b style="color:#ef4444;">{kalan:,.0f} TL</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="room-card room-free">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b style="font-size:17px; color:#fff;">{oda['oda_adi']}</b>
                            <span class="pill-badge pill-free">BOŞ</span>
                        </div>
                        <div style="margin-top:10px; font-size:13px; color:#cbd5e1; line-height:1.6;">
                            👥 Kapasite: <b>{oda['kapasite']} Kişilik</b><br>
                            ✨ Müsait ve Hazır
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# ==========================================
# 2. YENİ REZERVASYON
# ==========================================
elif menu == "✨ Yeni Rezervasyon":
    st.markdown("## ✨ Yeni Misafir Rezervasyonu")
    
    t1, t2 = st.columns(2)
    with t1:
        giris = st.date_input("🗓️ GİRİŞ TARİHİ", value=date.today())
    with t2:
        cikis = st.date_input("🗓️ ÇIKIŞ TARİHİ", value=date.today() + timedelta(days=1))

    if cikis <= giris:
        st.error("Çıkış tarihi giriş tarihinden sonra olmalıdır.")
    else:
        g_str = giris.strftime("%Y-%m-%d")
        c_str = cikis.strftime("%Y-%m-%d")
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, oda_adi, kat, kapasite FROM odalar
                WHERE id NOT IN (
                    SELECT oda_id FROM rezervasyonlar
                    WHERE durum = 'Aktif'
                      AND NOT (cikis_tarihi <= ? OR giris_tarihi >= ?)
                )
                ORDER BY id ASC
            """, (g_str, c_str))
            musaitler = c.fetchall()

        with st.form("yeni_rez_form"):
            f1, f2 = st.columns(2)
            with f1:
                misafir = st.text_input("MİSAFİR ADI SOYADI *", placeholder="Örn: Hasan Yılmaz")
                telefon = st.text_input("TELEFON NUMARASI", placeholder="05XXXXXXXXX")
            with f2:
                toplam = st.number_input("TOPLAM ÜCRET (TL)", min_value=0.0, step=100.0, value=2000.0)
                kapora = st.number_input("ALINAN KAPORA (TL)", min_value=0.0, step=100.0, value=500.0)

            kalan_ucret = max(0.0, toplam - kapora)
            st.info(f"💵 Tahsil Edilecek Açık Bakiye: **{kalan_ucret:,.2f} TL**")

            st.markdown("---")
            if musaitler:
                secenekler = {f"{r[1]} ({r[2]} - {r[3]} Kişilik)": r[0] for r in musaitler}
                secilen_etiket = st.selectbox("TAHSİS EDİLECEK DAİRE *", options=list(secenekler.keys()))
                secilen_id = secenekler[secilen_etiket]

                onayla = st.form_submit_button("🚀 Rezervasyonu Onayla ve Kaydet", use_container_width=True)
                if onayla:
                    if not misafir.strip():
                        st.error("Lütfen misafir adını giriniz.")
                    else:
                        with get_db() as conn:
                            conn.execute("""
                                INSERT INTO rezervasyonlar (oda_id, misafir_adi, telefon, giris_tarihi, cikis_tarihi, toplam_ucret, alinan_kapora)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (secilen_id, misafir.strip(), telefon.strip(), g_str, c_str, toplam, kapora))
                            conn.commit()
                        st.success(f"🎉 {secilen_etiket} için rezervasyon başarıyla açıldı!")
                        st.balloons()
            else:
                st.warning("⚠️ Bu tarihlerde tüm daireler doludur.")
                st.form_submit_button("Daire Bulunamadı", disabled=True, use_container_width=True)

# ==========================================
# 3. AYLIK DOLULUK TAKVİMİ
# ==========================================
elif menu == "📅 Aylık Doluluk Takvimi":
    st.markdown("## 📅 Aylık Doluluk Takvimi")
    st.caption("Aylar arasında gezinin, hiçbir gün taşmadan tüm ayı inceleyin.")

    aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    ay_col1, ay_col2 = st.columns(2)
    with ay_col1:
        secilen_ay_adi = st.selectbox("AY SEÇİMİ", aylar, index=date.today().month - 1)
        secilen_ay_num = aylar.index(secilen_ay_adi) + 1
    with ay_col2:
        secilen_yil = st.selectbox("YIL SEÇİMİ", [2025, 2026, 2027], index=1)

    toplam_gun = calendar.monthrange(secilen_yil, secilen_ay_num)[1]
    gunler = [date(secilen_yil, secilen_ay_num, d) for d in range(1, toplam_gun + 1)]
    basliklar = [f"{d.day:02d} {secilen_ay_adi[:3]}" for d in gunler]

    with get_db() as conn:
        odalar = conn.execute("SELECT id, oda_adi, kat FROM odalar ORDER BY id ASC").fetchall()
        rezler = conn.execute("SELECT oda_id, misafir_adi, giris_tarihi, cikis_tarihi FROM rezervasyonlar WHERE durum = 'Aktif'").fetchall()

    matris = []
    for o_id, o_adi, o_kat in odalar:
        satir = {"DAİRE": f"🏠 {o_adi}"}
        for g, baslik in zip(gunler, basliklar):
            g_str = g.strftime("%Y-%m-%d")
            isim = ""
            for r_oid, r_isim, r_gir, r_cik in rezler:
                if r_oid == o_id and (r_gir <= g_str < r_cik):
                    isim = r_isim.split()[0].upper()
                    break
            satir[baslik] = f"🔴 {isim}" if isim else "🟢 Boş"
        matris.append(satir)

    df_ay = pd.DataFrame(matris).set_index("DAİRE")
    st.dataframe(df_ay, use_container_width=True)

# ==========================================
# 4. KASA, BAKİYELER & DÜZENLEME
# ==========================================
elif menu == "💳 Kasa & Bakiyeler":
    st.markdown("## 💳 Kasa, Tahsilat & Rezervasyon Düzenleme")

    with get_db() as conn:
        df = pd.read_sql_query("""
            SELECT r.id, o.oda_adi, r.oda_id, r.misafir_adi, r.telefon, r.giris_tarihi, r.cikis_tarihi,
                   r.toplam_ucret, r.alinan_kapora, (r.toplam_ucret - r.alinan_kapora) as kalan_bakiye
            FROM rezervasyonlar r
            JOIN odalar o ON r.oda_id = o.id
            WHERE r.durum = 'Aktif'
            ORDER BY r.giris_tarihi ASC
        """, conn)

    if not df.empty:
        ciro = df['toplam_ucret'].sum()
        tahsilat = df['alinan_kapora'].sum()
        kalan = df['kalan_bakiye'].sum()

        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="stat-box"><div class="stat-label">Toplam Sözleşme</div><div class="stat-val">{ciro:,.0f} TL</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-box"><div class="stat-label">Tahsil Edilen Kapora</div><div class="stat-val" style="color:#10b981;">{tahsilat:,.0f} TL</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-box"><div class="stat-label">Bekleyen Tahsilat</div><div class="stat-val" style="color:#ef4444;">{kalan:,.0f} TL</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📋 Aktif Rezervasyonlar")
        
        gosterim = df.rename(columns={
            'oda_adi': 'DAİRE',
            'misafir_adi': 'MİSAFİR ADI SOYADI',
            'telefon': 'TELEFON',
            'giris_tarihi': 'GİRİŞ TARİHİ',
            'cikis_tarihi': 'ÇIKIŞ TARİHİ',
            'toplam_ucret': 'TOPLAM ÜCRET (TL)',
            'alinan_kapora': 'KAPORA (TL)',
            'kalan_bakiye': 'KALAN BAKİYE (TL)'
        })
        st.dataframe(gosterim.drop(columns=['id', 'oda_id']), use_container_width=True, hide_index=True)

        st.markdown("---")

        # İki Sütunlu Operasyon: Düzenle & Çıkış Yap
        op1, op2 = st.columns(2, gap="large")

        with op1:
            st.markdown("#### ✏️ Rezervasyon Bilgisini Düzelt")
            st.caption("İsim, telefon veya ücret yanlış girildiyse buradan düzeltin:")
            secilen_duzenle_id = st.selectbox(
                "DÜZENLENECEK REZERVASYON:",
                options=df['id'].tolist(),
                format_func=lambda x: f"{df[df['id']==x]['misafir_adi'].values[0]} ({df[df['id']==x]['oda_adi'].values[0]})"
            )
            
            rez_secili = df[df['id'] == secilen_duzenle_id].iloc[0]
            
            with st.form("rez_guncelle_form"):
                yeni_misafir = st.text_input("Misafir Adı Soyadı", value=rez_secili['misafir_adi'])
                yeni_tel = st.text_input("Telefon Numarası", value=rez_secili['telefon'])
                yeni_toplam = st.number_input("Toplam Ücret (TL)", value=float(rez_secili['toplam_ucret']), step=100.0)
                yeni_kapora = st.number_input("Tahsil Edilen Kapora (TL)", value=float(rez_secili['alinan_kapora']), step=100.0)
                
                guncelle_btn = st.form_submit_button("💾 Bilgileri Güncelle")
                if guncelle_btn:
                    with get_db() as conn:
                        conn.execute("""
                            UPDATE rezervasyonlar 
                            SET misafir_adi = ?, telefon = ?, toplam_ucret = ?, alinan_kapora = ?
                            WHERE id = ?
                        """, (yeni_misafir.strip(), yeni_tel.strip(), yeni_toplam, yeni_kapora, secilen_duzenle_id))
                        conn.commit()
                    st.success("Rezervasyon başarıyla güncellendi!")
                    st.rerun()

        with op2:
            st.markdown("#### 🚪 Çıkış Onayı & Arşiv")
            st.caption("Konaklaması biten misafiri arşive gönderin:")
            secilen_cikis_id = st.selectbox(
                "ÇIKIŞI YAPILACAK MİSAFİR:",
                options=df['id'].tolist(),
                format_func=lambda x: f"{df[df['id']==x]['misafir_adi'].values[0]} ({df[df['id']==x]['oda_adi'].values[0]})"
            )
            with st.form("cikis_onay_form"):
                cikis_yap = st.form_submit_button("✅ Çıkışı Tamamla ve Arşive Al", use_container_width=True)
                if cikis_yap:
                    with get_db() as conn:
                        conn.execute("UPDATE rezervasyonlar SET durum = 'Tamamlandı' WHERE id = ?", (secilen_cikis_id,))
                        conn.commit()
                    st.success("Çıkış yapıldı ve arşive kaldırıldı.")
                    st.rerun()
    else:
        st.info("Aktif rezervasyon bulunmuyor.")

# ==========================================
# 5. REZERVASYON ARŞİVİ
# ==========================================
elif menu == "📁 Rezervasyon Arşivi":
    st.markdown("## 📁 Tamamlanan Rezervasyon Arşivi")

    with get_db() as conn:
        arsiv_df = pd.read_sql_query("""
            SELECT o.oda_adi, r.misafir_adi, r.telefon, r.giris_tarihi, r.cikis_tarihi, r.toplam_ucret
            FROM rezervasyonlar r
            JOIN odalar o ON r.oda_id = o.id
            WHERE r.durum = 'Tamamlandı'
            ORDER BY r.cikis_tarihi DESC
        """, conn)

    if not arsiv_df.empty:
        toplam_kazanc = arsiv_df['toplam_ucret'].sum()
        st.markdown(f'<div class="stat-box" style="max-width:350px;"><div class="stat-label">Arşivdeki Toplam Ciro</div><div class="stat-val" style="color:#10b981;">{toplam_kazanc:,.0f} TL</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        goster = arsiv_df.rename(columns={
            'oda_adi': 'DAİRE',
            'misafir_adi': 'MİSAFİR ADI SOYADI',
            'telefon': 'TELEFON',
            'giris_tarihi': 'GİRİŞ TARİHİ',
            'cikis_tarihi': 'ÇIKIŞ TARİHİ',
            'toplam_ucret': 'TAHSİL EDİLEN (TL)'
        })
        st.dataframe(goster, use_container_width=True, hide_index=True)
    else:
        st.info("Arşivde tamamlanmış kayıt bulunmuyor.")

# ==========================================
# 6. DAİRE & APART AYARLARI
# ==========================================
elif menu == "⚙️ Daire & Apart Ayarları":
    st.markdown("## ⚙️ Apart İsmi ve Daire Yönetimi")

    # 1. Apart İsmi Ayarı
    with st.container():
        st.markdown("#### 🏷️ Apart Adını Değiştir")
        col_ad1, col_ad2 = st.columns([3, 1])
        with col_ad1:
            yeni_apart_adi = st.text_input("Apart Başlığı / Tabelası", value=apart_baslik)
        with col_ad2:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("İsmi Kaydet", use_container_width=True):
                with get_db() as conn:
                    conn.execute("UPDATE ayarlar SET deger = ? WHERE anahtar = 'apart_adi'", (yeni_apart_adi.strip(),))
                    conn.commit()
                st.success("Apart ismi güncellendi!")
                st.rerun()

    st.markdown("---")

    # 2. Daireleri Özgürce Düzenleme Paneli
    st.markdown("#### 🏢 Mevcut Daireleri Özgürce Düzenle")
    st.caption("Her dairenin ismini, katını ve kapasitesini tek tek özgürce değiştirin:")

    with get_db() as conn:
        daireler = conn.execute("SELECT id, oda_adi, kat, kapasite FROM odalar ORDER BY id ASC").fetchall()

    for d_id, d_adi, d_kat, d_kap in daireler:
        with st.expander(f"🏠 {d_adi} ({d_kat} - {d_kap} Kişilik)", expanded=False):
            with st.form(f"form_daire_{d_id}"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    duz_ad = st.text_input("Daire Adı / No", value=d_adi)
                with c2:
                    kat_secenek = ["Çatı Katı", "3. Kat", "2. Kat", "1. Kat", "Zemin Kat", "Bahçe Katı"]
                    kat_idx = kat_secenek.index(d_kat) if d_kat in kat_secenek else 0
                    duz_kat = st.selectbox("Katı", options=kat_secenek, index=kat_idx)
                with c3:
                    duz_kap = st.number_input("Kapasite (Kişi)", min_value=1, max_value=20, value=d_kap)

                kaydet_daire = st.form_submit_button("💾 Daireyi Güncelle")
                if kaydet_daire:
                    with get_db() as conn:
                        conn.execute("UPDATE odalar SET oda_adi = ?, kat = ?, kapasite = ? WHERE id = ?", (duz_ad.strip(), duz_kat, duz_kap, d_id))
                        conn.commit()
                    st.success(f"{duz_ad} başarıyla güncellendi!")
                    st.rerun()
