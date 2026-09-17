import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
import calendar

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Apart Otel Yönetim Portalı",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GELİŞMİŞ CSS & ULTRA MODERN ARAYÜZ ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Arka Plan & Sidebar Yumuşatma */
    .stApp {
        background-color: #0b0f19;
    }
    
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    /* Modern İstatistik Kartları */
    .stat-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        position: relative;
        overflow: hidden;
    }
    
    .stat-card::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
    }

    .stat-label {
        font-size: 12px;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stat-num {
        font-size: 32px;
        font-weight: 800;
        color: #ffffff;
        margin-top: 6px;
    }

    /* Kat Başlıkları */
    .floor-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(56, 189, 248, 0.12);
        border: 1px solid rgba(56, 189, 248, 0.3);
        color: #38bdf8;
        font-size: 14px;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 30px;
        margin: 20px 0 12px 0;
    }

    /* Daire Kutuları */
    .room-card {
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 12px;
        border: 1px solid;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .room-card:hover {
        transform: translateY(-3px);
    }

    .room-card.empty {
        background: linear-gradient(145deg, rgba(16, 185, 129, 0.1), rgba(6, 78, 59, 0.2));
        border-color: rgba(16, 185, 129, 0.3);
    }

    .room-card.full {
        background: linear-gradient(145deg, rgba(239, 68, 68, 0.1), rgba(127, 29, 29, 0.25));
        border-color: rgba(239, 68, 68, 0.3);
    }

    .room-title {
        font-size: 17px;
        font-weight: 700;
        color: #f8fafc;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .badge-status {
        font-size: 11px;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 20px;
        letter-spacing: 0.5px;
    }
    
    .badge-empty {
        background: #10b981;
        color: #022c22;
    }
    
    .badge-full {
        background: #ef4444;
        color: #ffffff;
    }

    .room-info {
        font-size: 13px;
        color: #cbd5e1;
        margin-top: 10px;
        line-height: 1.6;
    }

    /* Form ve Buton İyileştirmeleri */
    div.stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
    }

    div.stButton > button:hover {
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# --- VERİTABANI İŞLEMLERİ ---
DB_NAME = "apart_yonetim.db"

def get_db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS odalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oda_adi TEXT UNIQUE NOT NULL,
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

bugun = date.today()
bugun_str = bugun.strftime("%Y-%m-%d")

# --- MENÜ ---
with st.sidebar:
    st.markdown("## 🏨 LUX APART")
    st.caption("Yönetim & Misafir Takip Portalı")
    
    menu = st.radio(
        "Gezinme Menüsü",
        [
            "🏢 Kat Planı & Durum",
            "✨ Yeni Rezervasyon",
            "📅 Aylık Doluluk Takvimi",
            "💳 Kasa & Bakiyeler",
            "📁 Rezervasyon Arşivi",
            "⚙️ Daire Ayarları & Düzenleme"
        ]
    )
    st.markdown("---")
    st.markdown(f"🗓️ **Bugünün Tarihi:** `{bugun.strftime('%d.%m.%Y')}`")

# ==========================================
# 1. KAT PLANI & CANLI DURUM
# ==========================================
if menu == "🏢 Kat Planı & Durum":
    st.markdown("## 🏢 Bina Kat Planı ve Anlık Durum")
    
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
        su_an_dolu = rez_df[(rez_df['giris_tarihi'] <= bugun_str) & (rez_df['cikis_tarihi'] > bugun_str)]
        dolu_odalar = {row['oda_id']: row for _, row in su_an_dolu.iterrows()}
        girisler = rez_df[rez_df['giris_tarihi'] == bugun_str]
        cikislar = rez_df[rez_df['cikis_tarihi'] == bugun_str]
    else:
        dolu_odalar = {}
        girisler = pd.DataFrame()
        cikislar = pd.DataFrame()

    toplam_daire = len(tum_odalar)
    dolu_sayisi = len(dolu_odalar)
    bos_sayisi = toplam_daire - dolu_sayisi

    # Metrik Kartları
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="stat-card"><div class="stat-label">Toplam Daire</div><div class="stat-num">{toplam_daire}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-card"><div class="stat-label">Müsait Daire</div><div class="stat-num" style="color:#10b981;">{bos_sayisi}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-card"><div class="stat-label">Bugün Giriş</div><div class="stat-num" style="color:#38bdf8;">{len(girisler)}</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-card"><div class="stat-label">Bugün Çıkış</div><div class="stat-num" style="color:#f59e0b;">{len(cikislar)}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Kat Hiyerarşisi
    kat_sirasi = ["Çatı Katı", "3. Kat", "2. Kat", "1. Kat", "Zemin Kat"]
    for kat in kat_sirasi:
        kat_odalari = [o for o in tum_odalar if o["kat"] == kat]
        if not kat_odalari:
            continue
            
        st.markdown(f'<div class="floor-badge">📍 {kat.upper()}</div>', unsafe_allow_html=True)
        cols = st.columns(len(kat_odalari))
        
        for idx, oda in enumerate(kat_odalari):
            with cols[idx]:
                if oda["id"] in dolu_odalar:
                    rez = dolu_odalar[oda["id"]]
                    kalan = rez['toplam_ucret'] - rez['alinan_kapora']
                    st.markdown(f"""
                    <div class="room-card full">
                        <div class="room-title">
                            <span>{oda['oda_adi']}</span>
                            <span class="badge-status badge-full">DOLU</span>
                        </div>
                        <div class="room-info">
                            👤 <b>{rez['misafir_adi'].upper()}</b><br>
                            📞 <code>{rez['telefon'] or 'Belirtilmedi'}</code><br>
                            🗓️ Çıkış: <b>{rez['cikis_tarihi']}</b><br>
                            💰 Kalan Bakiye: <b style="color:#ef4444;">{kalan:,.0f} TL</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="room-card empty">
                        <div class="room-title">
                            <span>{oda['oda_adi']}</span>
                            <span class="badge-status badge-empty">MÜSAİT</span>
                        </div>
                        <div class="room-info">
                            👥 Kapasite: <b>{oda['kapasite']} Kişilik</b><br>
                            ✨ Hazır & Temiz<br>
                            🌟 Girişe Uygun
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# ==========================================
# 2. YENİ REZERVASYON
# ==========================================
elif menu == "✨ Yeni Rezervasyon":
    st.markdown("## ✨ Yeni Misafir Rezervasyonu")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        giris = st.date_input("🗓️ GİRİŞ TARİHİ", value=bugun, min_value=bugun)
    with col_t2:
        cikis = st.date_input("🗓️ ÇIKIŞ TARİHİ", value=bugun + timedelta(days=1), min_value=bugun + timedelta(days=1))

    if cikis <= giris:
        st.error("Çıkış tarihi giriş tarihinden sonra olmalıdır.")
    else:
        # Müsait odaları bul
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

        with st.form("rezervasyon_ekle_form"):
            st.markdown("#### 👤 Misafir ve Ücret Bilgileri")
            f1, f2 = st.columns(2)
            with f1:
                misafir = st.text_input("MİSAFİR ADI SOYADI *", placeholder="Örn: Mehmet Demir")
                telefon = st.text_input("TELEFON NUMARASI", placeholder="05XXXXXXXXX")
            with f2:
                toplam = st.number_input("TOPLAM KONAKLAMA ÜCRETİ (TL)", min_value=0.0, step=100.0, value=2000.0)
                kapora = st.number_input("ALINAN KAPORA (TL)", min_value=0.0, step=100.0, value=500.0)

            kalan_para = max(0.0, toplam - kapora)
            st.info(f"💵 Girişte Tahsil Edilecek Tutar: **{kalan_para:,.2f} TL**")
            
            st.markdown("---")
            if musaitler:
                secenekler = {f"{r[1]} ({r[2]} - {r[3]} Kişi)": r[0] for r in musaitler}
                secilen_etiket = st.selectbox("TAHSİS EDİLECEK BOŞ DAİRE *", options=list(secenekler.keys()))
                secilen_id = secenekler[secilen_etiket]

                onayla = st.form_submit_button("🚀 Rezervasyonu Onayla ve Kaydet", use_container_width=True)
                if onayla:
                    if not misafir.strip():
                        st.error("Misafir adı zorunludur.")
                    else:
                        with get_db() as conn:
                            conn.execute("""
                                INSERT INTO rezervasyonlar (oda_id, misafir_adi, telefon, giris_tarihi, cikis_tarihi, toplam_ucret, alinan_kapora)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (secilen_id, misafir.strip(), telefon.strip(), g_str, c_str, toplam, kapora))
                            conn.commit()
                        st.success(f"🎉 {secilen_etiket} için rezervasyon başarıyla tamamlandı!")
                        st.balloons()
            else:
                st.warning("⚠️ Bu tarihlerde müsait daire bulunmamaktadır.")
                st.form_submit_button("Daire Yok", disabled=True, use_container_width=True)

# ==========================================
# 3. AYLIK DOLULUK TAKVİMİ
# ==========================================
elif menu == "📅 Aylık Doluluk Takvimi":
    st.markdown("## 📅 Aylık Doluluk Takvimi")
    st.caption("İstediğiniz ayı seçerek sadece o ayın tam doluluk matrisini inceleyin.")

    ay_isimleri = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    t1, t2 = st.columns(2)
    with t1:
        secilen_ay_adi = st.selectbox("GÖRÜNTÜLENECEK AY", ay_isimleri, index=bugun.month - 1)
        secilen_ay = ay_isimleri.index(secilen_ay_adi) + 1
    with t2:
        secilen_yil = st.selectbox("GÖRÜNTÜLENECEK YIL", [2025, 2026, 2027], index=1)

    # Seçilen ayın gün sayısı
    toplam_gun = calendar.monthrange(secilen_yil, secilen_ay)[1]
    gun_listesi = [date(secilen_yil, secilen_ay, d) for d in range(1, toplam_gun + 1)]
    basliklar = [f"{d.day:02d} {secilen_ay_adi[:3]}" for d in gun_listesi]

    with get_db() as conn:
        odalar = conn.execute("SELECT id, oda_adi, kat FROM odalar ORDER BY id ASC").fetchall()
        rezler = conn.execute("SELECT oda_id, misafir_adi, giris_tarihi, cikis_tarihi FROM rezervasyonlar WHERE durum = 'Aktif'").fetchall()

    matris = []
    for o_id, o_adi, o_kat in odalar:
        satir = {"DAİRE BİLGİSİ": f"🏠 {o_adi} ({o_kat})"}
        for g, baslik in zip(gun_listesi, basliklar):
            g_str = g.strftime("%Y-%m-%d")
            isim = ""
            for r_oid, r_isim, r_gir, r_cik in rezler:
                if r_oid == o_id and (r_gir <= g_str < r_cik):
                    isim = r_isim.split()[0].upper()
                    break
            satir[baslik] = f"🔴 {isim}" if isim else "🟢 Boş"
        matris.append(satir)

    df_aylik = pd.DataFrame(matris).set_index("DAİRE BİLGİSİ")
    st.dataframe(df_aylik, use_container_width=True)

# ==========================================
# 4. KASA & BAKİYELER
# ==========================================
elif menu == "💳 Kasa & Bakiyeler":
    st.markdown("## 💳 Kasa, Tahsilat & Aktif Bakiyeler")
    
    with get_db() as conn:
        df = pd.read_sql_query("""
            SELECT r.id, o.oda_adi, r.misafir_adi, r.telefon, r.giris_tarihi, r.cikis_tarihi,
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
        c1.markdown(f'<div class="stat-card"><div class="stat-label">Toplam Sözleşme</div><div class="stat-num">{ciro:,.0f} TL</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-card"><div class="stat-label">Tahsil Edilen Kapora</div><div class="stat-num" style="color:#10b981;">{tahsilat:,.0f} TL</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-card"><div class="stat-label">Bekleyen Tahsilat</div><div class="stat-num" style="color:#ef4444;">{kalan:,.0f} TL</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📋 Aktif Rezervasyon Listesi")
        
        gosterim_df = df.rename(columns={
            'oda_adi': 'DAİRE',
            'misafir_adi': 'MİSAFİR ADI SOYADI',
            'telefon': 'TELEFON',
            'giris_tarihi': 'GİRİŞ TARİHİ',
            'cikis_tarihi': 'ÇIKIŞ TARİHİ',
            'toplam_ucret': 'TOPLAM ÜCRET (TL)',
            'alinan_kapora': 'KAPORA (TL)',
            'kalan_bakiye': 'KALAN BAKİYE (TL)'
        })
        st.dataframe(gosterim_df.drop(columns=['id']), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🚪 Misafir Çıkışı & Arşive Gönderme")
        with st.form("cikis_form"):
            secilen_id = st.selectbox(
                "ÇIKIŞI YAPILACAK MİSAFİRİ SEÇİN:",
                options=df['id'].tolist(),
                format_func=lambda x: f"{df[df['id']==x]['misafir_adi'].values[0]} | {df[df['id']==x]['oda_adi'].values[0]}"
            )
            tamamla = st.form_submit_button("✅ Çıkışı Onayla ve Arşive Taşı", use_container_width=True)
            if tamamla:
                with get_db() as conn:
                    conn.execute("UPDATE rezervasyonlar SET durum = 'Tamamlandı' WHERE id = ?", (secilen_id,))
                    conn.commit()
                st.success("Misafir çıkışı yapıldı ve arşive aktarıldı!")
                st.rerun()
    else:
        st.info("Aktif konaklama kaydı bulunmuyor.")

# ==========================================
# 5. REZERVASYON ARŞİVİ
# ==========================================
elif menu == "📁 Rezervasyon Arşivi":
    st.markdown("## 📁 Tamamlanan & Geçmiş Rezervasyon Arşivi")
    st.caption("Çıkışı verilmiş olan tüm geçmiş misafir kayıtları ve gelir dökümü.")

    with get_db() as conn:
        arsiv_df = pd.read_sql_query("""
            SELECT o.oda_adi, r.misafir_adi, r.telefon, r.giris_tarihi, r.cikis_tarihi, r.toplam_ucret, r.durum
            FROM rezervasyonlar r
            JOIN odalar o ON r.oda_id = o.id
            WHERE r.durum = 'Tamamlandı'
            ORDER BY r.cikis_tarihi DESC
        """, conn)

    if not arsiv_df.empty:
        toplam_kazanc = arsiv_df['toplam_ucret'].sum()
        st.markdown(f'<div class="stat-card" style="max-width:350px;"><div class="stat-label">Arşivdeki Toplam Hasılat</div><div class="stat-num" style="color:#10b981;">{toplam_kazanc:,.0f} TL</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        arsiv_goster = arsiv_df.rename(columns={
            'oda_adi': 'DAİRE',
            'misafir_adi': 'MİSAFİR ADI SOYADI',
            'telefon': 'TELEFON',
            'giris_tarihi': 'GİRİŞ TARİHİ',
            'cikis_tarihi': 'ÇIKIŞ TARİHİ',
            'toplam_ucret': 'TAHSİL EDİLEN TUTAR (TL)',
            'durum': 'DURUM'
        })
        st.dataframe(arsiv_goster, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz arşive kaldırılmış tamamlanmış bir rezervasyon kaydı yok.")

# ==========================================
# 6. DAİRE AYARLARI & DÜZENLEME
# ==========================================
elif menu == "⚙️ Daire Ayarları & Düzenleme":
    st.markdown("## ⚙️ Daire Ayarları ve İsim Düzenleme")
    st.caption("Dairelerin isimlerini, bulundukları katı veya kapasitelerini tablodan değiştirip kaydedebilirsiniz.")

    with get_db() as conn:
        daireler_df = pd.read_sql_query("SELECT id, oda_adi, kat, kapasite FROM odalar ORDER BY id ASC", conn)

    daireler_df = daireler_df.rename(columns={
        'id': 'ID',
        'oda_adi': 'DAİRE ADI',
        'kat': 'BULUNDUĞU KAT',
        'kapasite': 'KAPASİTE (KİŞİ)'
    })

    with st.form("daire_duzenle_form"):
        st.markdown("#### ✏️ Daire Bilgilerini Düzenlenebilir Tablo")
        duzenlenmis_df = st.data_editor(
            daireler_df,
            disabled=["ID"],
            use_container_width=True,
            hide_index=True
        )
        
        kaydet_btn = st.form_submit_button("💾 Değişiklikleri Veritabanına Kaydet", use_container_width=True)
        if kaydet_btn:
            with get_db() as conn:
                for _, row in duzenlenmis_df.iterrows():
                    conn.execute("""
                        UPDATE odalar 
                        SET oda_adi = ?, kat = ?, kapasite = ?
                        WHERE id = ?
                    """, (row['DAİRE ADI'], row['BULUNDUĞU KAT'], int(row['KAPASİTE (KİŞİ)']), int(row['ID'])))
                conn.commit()
            st.success("🎉 Daire bilgileri başarıyla güncellendi!")
            st.rerun()
