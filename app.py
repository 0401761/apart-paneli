import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime, timedelta
import urllib.parse
import calendar

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Apart Yönetim Portalı Pro",
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

    /* Balon Pill Navigasyon Butonları */
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    div[data-testid="stRadio"] label {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        padding: 10px 16px !important;
        border-radius: 50px !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
        margin: 0 !important;
    }

    div[data-testid="stRadio"] label:hover {
        background: rgba(56, 189, 248, 0.15) !important;
        border-color: rgba(56, 189, 248, 0.4) !important;
        transform: translateX(4px);
    }

    div[data-testid="stRadio"] label div:first-child {
        display: none !important;
    }

    div[data-testid="stRadio"] label[data-checked="true"],
    div[data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%) !important;
        border-color: #38bdf8 !important;
        box-shadow: 0 4px 18px rgba(37, 99, 235, 0.45) !important;
    }

    div[data-testid="stRadio"] label[data-checked="true"] p,
    div[data-testid="stRadio"] label:has(input:checked) p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* Metrik Kartları */
    .stat-box {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }

    .stat-label {
        font-size: 11px;
        color: #94a3b8;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    .stat-val {
        font-size: 28px;
        font-weight: 800;
        color: #f8fafc;
        margin-top: 4px;
    }

    /* Daire Kartları */
    .room-card {
        border-radius: 18px;
        padding: 16px 18px;
        margin-bottom: 12px;
        border: 1px solid;
        box-shadow: 0 6px 16px rgba(0,0,0,0.25);
    }

    .room-free-clean {
        background: linear-gradient(145deg, rgba(16, 185, 129, 0.12), rgba(6, 78, 59, 0.25));
        border-color: rgba(16, 185, 129, 0.4);
    }

    .room-free-dirty {
        background: linear-gradient(145deg, rgba(245, 158, 11, 0.15), rgba(120, 53, 15, 0.3));
        border-color: rgba(245, 158, 11, 0.5);
    }

    .room-busy {
        background: linear-gradient(145deg, rgba(239, 68, 68, 0.12), rgba(127, 29, 29, 0.3));
        border-color: rgba(239, 68, 68, 0.4);
    }

    .pill-badge {
        font-size: 11px;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 30px;
    }

    .pill-free { background: #10b981; color: #022c22; }
    .pill-dirty { background: #f59e0b; color: #451a03; }
    .pill-busy { background: #ef4444; color: #ffffff; }

    div.stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 8px 18px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- HIZLANDIRILMIŞ TURSO HTTP BAĞLANTISI ---
TURSO_URL = st.secrets["TURSO_URL"].replace("libsql://", "https://")
TURSO_TOKEN = st.secrets["TURSO_TOKEN"]

@st.cache_resource
def get_http_session():
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    })
    return s

def turso_execute(sql, params=None):
    session = get_http_session()
    url = f"{TURSO_URL}/v2/pipeline"
    
    stmt = {"sql": sql}
    if params:
        formatted_args = []
        for p in params:
            if p is None:
                formatted_args.append({"type": "null"})
            elif isinstance(p, (int, float)):
                formatted_args.append({"type": "float" if isinstance(p, float) else "integer", "value": p})
            else:
                formatted_args.append({"type": "text", "value": str(p)})
        stmt["args"] = formatted_args

    payload = {
        "requests": [
            {"type": "execute", "stmt": stmt},
            {"type": "close"}
        ]
    }
    
    resp = session.post(url, json=payload, timeout=8)
    if not resp.ok:
        raise Exception(f"Turso Hatası: {resp.text}")
        
    data = resp.json()
    result = data["results"][0]
    if result["type"] == "error":
        raise Exception(result["error"]["message"])
        
    resp_obj = result["response"]["result"]
    cols = [c["name"] for c in resp_obj.get("cols", [])]
    rows = []
    for r in resp_obj.get("rows", []):
        row_vals = [v.get("value") if v.get("type") != "null" else None for v in r]
        rows.append(row_vals)
    return cols, rows

def query_df(sql, params=None):
    cols, rows = turso_execute(sql, params)
    return pd.DataFrame(rows, columns=cols)

def init_db():
    turso_execute("""
        CREATE TABLE IF NOT EXISTS ayarlar (
            anahtar TEXT PRIMARY KEY,
            deger TEXT
        )
    """)
    turso_execute("""
        CREATE TABLE IF NOT EXISTS odalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oda_adi TEXT NOT NULL,
            kat TEXT NOT NULL,
            kapasite INTEGER DEFAULT 3,
            gecelik_fiyat REAL DEFAULT 1500,
            temizlik_durumu TEXT DEFAULT 'Temiz'
        )
    """)
    turso_execute("""
        CREATE TABLE IF NOT EXISTS rezervasyonlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oda_id INTEGER NOT NULL,
            misafir_adi TEXT NOT NULL,
            telefon TEXT,
            tc_pasaport TEXT,
            plaka TEXT,
            giris_tarihi TEXT NOT NULL,
            cikis_tarihi TEXT NOT NULL,
            toplam_ucret REAL DEFAULT 0,
            alinan_kapora REAL DEFAULT 0,
            durum TEXT DEFAULT 'Aktif'
        )
    """)
    turso_execute("""
        CREATE TABLE IF NOT EXISTS tahsilatlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rezervasyon_id INTEGER NOT NULL,
            tutar REAL NOT NULL,
            yontem TEXT NOT NULL,
            tarih TEXT NOT NULL
        )
    """)
    turso_execute("""
        CREATE TABLE IF NOT EXISTS giderler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT NOT NULL,
            kategori TEXT NOT NULL,
            tutar REAL NOT NULL,
            tarih TEXT NOT NULL
        )
    """)

    # Göç kontrolü (temizlik sütunu eksikse ekle)
    try:
        turso_execute("ALTER TABLE odalar ADD COLUMN temizlik_durumu TEXT DEFAULT 'Temiz'")
    except Exception:
        pass

    # Varsayılan Ayarlar
    turso_execute("INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('apart_adi', 'LUX APART')")
    turso_execute("INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('wifi_adi', 'Apart_Misafir')")
    turso_execute("INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('wifi_sifre', '12345678')")
    turso_execute("INSERT OR IGNORE INTO ayarlar (anahtar, deger) VALUES ('konum_linki', 'https://maps.google.com')")

    _, count_rows = turso_execute("SELECT COUNT(*) FROM odalar")
    if count_rows[0][0] == 0:
        varsayilan = [
            ("Çatı Katı Daire", "Çatı Katı", 2, 1800, "Temiz"),
            ("Daire 301", "3. Kat", 4, 1500, "Temiz"),
            ("Daire 302", "3. Kat", 4, 1500, "Temiz"),
            ("Daire 201", "2. Kat", 4, 1500, "Temiz"),
            ("Daire 202", "2. Kat", 4, 1500, "Temiz"),
            ("Daire 101", "1. Kat", 4, 1500, "Temiz"),
            ("Daire 102", "1. Kat", 4, 1500, "Temiz"),
            ("Zemin Daire 1", "Zemin Kat", 3, 1300, "Temiz"),
            ("Zemin Daire 2", "Zemin Kat", 3, 1300, "Temiz")
        ]
        for o_adi, kat, kap, fyt, tmz in varsayilan:
            turso_execute("INSERT INTO odalar (oda_adi, kat, kapasite, gecelik_fiyat, temizlik_durumu) VALUES (?, ?, ?, ?, ?)", [o_adi, kat, kap, fyt, tmz])

init_db()

def get_ayar(anahtar, varsayilan=""):
    _, rows = turso_execute("SELECT deger FROM ayarlar WHERE anahtar = ?", [anahtar])
    if rows:
        return rows[0][0]
    return varsayilan

apart_baslik = get_ayar('apart_adi', 'LUX APART')
wifi_adi = get_ayar('wifi_adi', 'Apart_Misafir')
wifi_sifre = get_ayar('wifi_sifre', '12345678')
konum_linki = get_ayar('konum_linki', 'https://maps.google.com')

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"## 🏢 {apart_baslik}")
    st.caption("Akıllı Apart Yönetim Portalı")
    st.markdown("---")
    
    menu = st.radio(
        "Gezinme",
        [
            "🏢 Kat Planı & Temizlik",
            "✨ Yeni Rezervasyon",
            "📅 Aylık Doluluk Takvimi",
            "💳 Kasa & Parçalı Tahsilat",
            "📋 Günlük KBS & Girişler",
            "🔍 Rezervasyon Ara",
            "📉 Gider & Net Kâr",
            "📁 Rezervasyon Arşivi",
            "⚙️ Daire & Apart Ayarları"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("#### 🗓️ Gözlem Tarihi")
    secilen_tarih = st.date_input("İncelenen Tarih", value=date.today())
    secilen_tarih_str = secilen_tarih.strftime("%Y-%m-%d")

# ==========================================
# 1. KAT PLANI & CANLI DURUM & TEMİZLİK
# ==========================================
if menu == "🏢 Kat Planı & Temizlik":
    st.markdown(f"## 🏢 {apart_baslik} - Kat Planı & Temizlik Durumu")
    st.caption(f"Tarih: **{secilen_tarih.strftime('%d.%m.%Y')}**")

    _, oda_rows = turso_execute("SELECT id, oda_adi, kat, kapasite, gecelik_fiyat, temizlik_durumu FROM odalar ORDER BY id ASC")
    tum_odalar = [{"id": r[0], "oda_adi": r[1], "kat": r[2], "kapasite": r[3], "fiyat": r[4], "temizlik": r[5] or 'Temiz'} for r in oda_rows]
    
    rez_df = query_df("""
        SELECT r.*, o.oda_adi 
        FROM rezervasyonlar r 
        JOIN odalar o ON r.oda_id = o.id 
        WHERE r.durum = 'Aktif'
    """)

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
    kirli_sayisi = len([o for o in tum_odalar if o['id'] not in dolu_odalar and o['temizlik'] == 'Kirli'])

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="stat-box"><div class="stat-label">Toplam Daire</div><div class="stat-val">{toplam_daire}</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="stat-box"><div class="stat-label">Müsait Daire</div><div class="stat-val" style="color:#10b981;">{bos_sayisi}</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="stat-box"><div class="stat-label">Temizlik Bekleyen</div><div class="stat-val" style="color:#f59e0b;">{kirli_sayisi}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="stat-box"><div class="stat-label">Bugün Giriş / Çıkış</div><div class="stat-val" style="color:#38bdf8;">{len(girisler)} / {len(cikislar)}</div></div>', unsafe_allow_html=True)

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
                    kalan = float(rez['toplam_ucret']) - float(rez['alinan_kapora'])
                    st.markdown(f"""
                    <div class="room-card room-busy">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b style="font-size:16px; color:#fff;">{oda['oda_adi']}</b>
                            <span class="pill-badge pill-busy">DOLU</span>
                        </div>
                        <div style="margin-top:8px; font-size:13px; color:#cbd5e1; line-height:1.6;">
                            👤 <b>{str(rez['misafir_adi']).upper()}</b><br>
                            📞 <code>{rez['telefon'] or 'Yok'}</code><br>
                            🆔 TC: <b>{rez['tc_pasaport'] or '-'}</b> | 🚗 {rez['plaka'] or '-'}<br>
                            📅 Çıkış: <b>{rez['cikis_tarihi']}</b><br>
                            💰 Kalan: <b style="color:#ef4444;">{kalan:,.0f} TL</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    is_dirty = oda["temizlik"] == "Kirli"
                    card_class = "room-free-dirty" if is_dirty else "room-free-clean"
                    badge_class = "pill-dirty" if is_dirty else "pill-free"
                    badge_text = "🧹 KİRLİ" if is_dirty else "🟢 MÜSAİT"
                    
                    st.markdown(f"""
                    <div class="room-card {card_class}">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <b style="font-size:16px; color:#fff;">{oda['oda_adi']}</b>
                            <span class="pill-badge {badge_class}">{badge_text}</span>
                        </div>
                        <div style="margin-top:8px; font-size:13px; color:#cbd5e1; line-height:1.6;">
                            👥 Kapasite: <b>{oda['kapasite']} Kişi</b><br>
                            💵 Gecelik: <b>{float(oda['fiyat']):,.0f} TL</b><br>
                            Durum: <b>{'Temizlik Bekliyor' if is_dirty else 'Misafire Hazır'}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    btn_label = "✨ Temizlendi Yap" if is_dirty else "🧹 Kirli Olarak İşaretle"
                    yeni_durum = "Temiz" if is_dirty else "Kirli"
                    if st.button(btn_label, key=f"tmz_{oda['id']}", use_container_width=True):
                        turso_execute("UPDATE odalar SET temizlik_durumu = ? WHERE id = ?", [yeni_durum, oda['id']])
                        st.rerun()

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

    gece_sayisi = (cikis - giris).days

    if gece_sayisi <= 0:
        st.error("Çıkış tarihi giriş tarihinden sonra olmalıdır.")
    else:
        st.info(f"🌙 Konaklama Süresi: **{gece_sayisi} Gece**")
        g_str = giris.strftime("%Y-%m-%d")
        c_str = cikis.strftime("%Y-%m-%d")

        _, musaitler = turso_execute("""
            SELECT id, oda_adi, kat, kapasite, gecelik_fiyat FROM odalar
            WHERE id NOT IN (
                SELECT oda_id FROM rezervasyonlar
                WHERE durum = 'Aktif'
                  AND NOT (cikis_tarihi <= ? OR giris_tarihi >= ?)
            )
            ORDER BY id ASC
        """, [g_str, c_str])

        if musaitler:
            secenekler = {f"{r[1]} ({r[2]} - {r[3]} Kişi - {float(r[4]):,.0f} TL/gece)": r for r in musaitler}
            secilen_etiket = st.selectbox("TAHSİS EDİLECEK MÜSAİT DAİRE *", options=list(secenekler.keys()))
            secilen_oda_data = secenekler[secilen_etiket]
            secilen_id = secilen_oda_data[0]
            otomatik_fiyat = float(secilen_oda_data[4]) * gece_sayisi

            with st.form("yeni_rez_form"):
                f1, f2 = st.columns(2)
                with f1:
                    misafir = st.text_input("MİSAFİR ADI SOYADI *", placeholder="Örn: Hasan Yılmaz")
                    telefon = st.text_input("TELEFON NUMARASI (05XXXXXXXXX)", placeholder="05XXXXXXXXX")
                    tc_pas = st.text_input("TC KİMLİK / PASAPORT NO (KBS İçin)", placeholder="11 Haneli TC veya Pasaport")
                with f2:
                    plaka = st.text_input("ARAÇ PLAKASI (Opsiyonel)", placeholder="Örn: 61 AB 123")
                    toplam = st.number_input("TOPLAM ÜCRET (TL)", min_value=0.0, step=100.0, value=float(otomatik_fiyat))
                    kapora = st.number_input("ALINAN İLK KAPORA (TL)", min_value=0.0, step=100.0, value=500.0)
                    odeme_tipi = st.selectbox("KAPORA ÖDEME ŞEKLİ", ["Havale / EFT", "Nakit", "Kredi Kartı"])

                kalan_ucret = max(0.0, toplam - kapora)
                st.caption(f"💵 Girişte Tahsil Edilecek Kalan Tutar: **{kalan_ucret:,.2f} TL**")

                onayla = st.form_submit_button("🚀 Rezervasyonu Kesinleştir ve Kaydet", use_container_width=True)
                if onayla:
                    if not misafir.strip():
                        st.error("Lütfen misafir adını giriniz.")
                    else:
                        turso_execute("""
                            INSERT INTO rezervasyonlar (oda_id, misafir_adi, telefon, tc_pasaport, plaka, giris_tarihi, cikis_tarihi, toplam_ucret, alinan_kapora)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, [secilen_id, misafir.strip(), telefon.strip(), tc_pas.strip(), plaka.strip(), g_str, c_str, toplam, kapora])
                        
                        _, son_id_res = turso_execute("SELECT last_insert_rowid()")
                        yeni_rez_id = son_id_res[0][0]

                        if kapora > 0:
                            turso_execute("""
                                INSERT INTO tahsilatlar (rezervasyon_id, tutar, yontem, tarih)
                                VALUES (?, ?, ?, ?)
                            """, [yeni_rez_id, kapora, f"İlk Kapora ({odeme_tipi})", date.today().strftime("%Y-%m-%d")])

                        st.session_state["son_rez"] = {
                            "misafir": misafir.strip(),
                            "tel": telefon.strip(),
                            "oda": secilen_oda_data[1],
                            "giris": giris.strftime('%d.%m.%Y'),
                            "cikis": cikis.strftime('%d.%m.%Y'),
                            "kalan": kalan_ucret
                        }
                        st.success(f"🎉 {secilen_oda_data[1]} için rezervasyon kaydedildi!")
                        st.balloons()
                        st.rerun()

            # Kayıt Sonrası Çift WhatsApp Butonu
            if "son_rez" in st.session_state:
                sr = st.session_state["son_rez"]
                clean_tel = "".join(filter(str.isdigit, sr['tel']))
                if clean_tel.startswith("0"):
                    clean_tel = "90" + clean_tel[1:]
                elif not clean_tel.startswith("90") and len(clean_tel) == 10:
                    clean_tel = "90" + clean_tel

                # Mesaj 1: Onay
                onay_msg = (
                    f"Sayın {sr['misafir']},\n\n"
                    f"{apart_baslik} bünyesinde {sr['oda']} için rezervasyonunuz onaylanmıştır.\n"
                    f"📅 Giriş: {sr['giris']}\n"
                    f"📅 Çıkış: {sr['cikis']}\n"
                    f"💰 Kalan Ödeme: {sr['kalan']:,.0f} TL\n\n"
                    f"Giriş günü görüşmek üzere, iyi yolculuklar dileriz!"
                )
                wa_onay_url = f"https://wa.me/{clean_tel}?text={urllib.parse.quote(onay_msg)}"

                # Mesaj 2: Konum & Wi-Fi
                bilgi_msg = (
                    f"Sayın {sr['misafir']},\n\n"
                    f"{apart_baslik} konaklamanız için pratik bilgiler:\n"
                    f"📍 Google Maps Konumumuz: {konum_linki}\n"
                    f"📶 Wi-Fi Ağı: {wifi_adi}\n"
                    f"🔑 Wi-Fi Şifresi: {wifi_sifre}\n"
                    f"🕒 Giriş Saati: 14:00 | Çıkış Saati: 11:00\n\n"
                    f"İyi tatiller dileriz!"
                )
                wa_bilgi_url = f"https://wa.me/{clean_tel}?text={urllib.parse.quote(bilgi_msg)}"

                st.markdown(f"""
                <div style="background: rgba(34, 197, 94, 0.12); border: 1px solid #22c55e; padding: 16px; border-radius: 14px; margin-top: 15px;">
                    <b>📲 Misafire WhatsApp'tan Hızlı Bilgi Gönderin ({sr['misafir']})</b>
                    <div style="display:flex; gap:12px; margin-top:10px;">
                        <a href="{wa_onay_url}" target="_blank" style="background:#22c55e; color:white; padding:9px 16px; border-radius:8px; text-decoration:none; font-weight:700;">✅ 1. Rezervasyon Onayı Gönder</a>
                        <a href="{wa_bilgi_url}" target="_blank" style="background:#0284c7; color:white; padding:9px 16px; border-radius:8px; text-decoration:none; font-weight:700;">📍 2. Konum & Wi-Fi Kartı Gönder</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Bu tarihlerde tüm daireler doludur.")

# ==========================================
# 3. AYLIK DOLULUK TAKVİMİ
# ==========================================
elif menu == "📅 Aylık Doluluk Takvimi":
    st.markdown("## 📅 Aylık Doluluk Takvimi")

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

    _, odalar_rows = turso_execute("SELECT id, oda_adi, kat FROM odalar ORDER BY id ASC")
    _, rez_rows = turso_execute("SELECT oda_id, misafir_adi, giris_tarihi, cikis_tarihi FROM rezervasyonlar WHERE durum = 'Aktif'")

    matris = []
    for o_id, o_adi, o_kat in odalar_rows:
        satir = {"DAİRE": f"🏠 {o_adi}"}
        for g, baslik in zip(gunler, basliklar):
            g_str = g.strftime("%Y-%m-%d")
            isim = ""
            for r_oid, r_isim, r_gir, r_cik in rez_rows:
                if r_oid == o_id and (r_gir <= g_str < r_cik):
                    isim = str(r_isim).split()[0].upper()
                    break
            satir[baslik] = f"🔴 {isim}" if isim else "🟢 Boş"
        matris.append(satir)

    df_ay = pd.DataFrame(matris).set_index("DAİRE")
    st.dataframe(df_ay, use_container_width=True)

# ==========================================
# 4. KASA & PARÇALI TAHSİLAT
# ==========================================
elif menu == "💳 Kasa & Parçalı Tahsilat":
    st.markdown("## 💳 Kasa, Tahsilat & Ara Ödeme Girişi")

    df = query_df("""
        SELECT r.id, o.oda_adi, r.oda_id, r.misafir_adi, r.telefon, r.tc_pasaport, r.plaka, 
               r.giris_tarihi, r.cikis_tarihi, r.toplam_ucret, r.alinan_kapora, 
               (r.toplam_ucret - r.alinan_kapora) as kalan_bakiye
        FROM rezervasyonlar r
        JOIN odalar o ON r.oda_id = o.id
        WHERE r.durum = 'Aktif'
        ORDER BY r.giris_tarihi ASC
    """)

    # Tahsilat yöntemleri kırılımı
    tahsilat_df = query_df("SELECT * FROM tahsilatlar")
    nakit_toplam = tahsilat_df[tahsilat_df['yontem'].str.contains('Nakit', case=False, na=False)]['tutar'].astype(float).sum() if not tahsilat_df.empty else 0.0
    havale_toplam = tahsilat_df[tahsilat_df['yontem'].str.contains('Havale', case=False, na=False)]['tutar'].astype(float).sum() if not tahsilat_df.empty else 0.0
    kart_toplam = tahsilat_df[tahsilat_df['yontem'].str.contains('Kart', case=False, na=False)]['tutar'].astype(float).sum() if not tahsilat_df.empty else 0.0

    if not df.empty:
        ciro = df['toplam_ucret'].astype(float).sum()
        tahsilat = df['alinan_kapora'].astype(float).sum()
        kalan = df['kalan_bakiye'].astype(float).sum()

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="stat-box"><div class="stat-label">Toplam Ciro Sözleşme</div><div class="stat-val">{ciro:,.0f} TL</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-box"><div class="stat-label">Toplam Tahsilat</div><div class="stat-val" style="color:#10b981;">{tahsilat:,.0f} TL</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-box"><div class="stat-label">Bekleyen Tahsilat</div><div class="stat-val" style="color:#ef4444;">{kalan:,.0f} TL</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="stat-box"><div class="stat-label">Nakit / Havale / Kart</div><div class="stat-val" style="font-size:18px; line-height:1.4;">💵 {nakit_toplam:,.0f}<br>🏦 {havale_toplam:,.0f}<br>💳 {kart_toplam:,.0f}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            st.markdown("#### 📋 Aktif Rezervasyon Listesi")
        with col_btn2:
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Aktif Rezervasyonları İndir (CSV)", data=csv_data, file_name=f"rezervasyonlar_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv", use_container_width=True)

        gosterim = df.rename(columns={
            'oda_adi': 'DAİRE',
            'misafir_adi': 'MİSAFİR ADI SOYADI',
            'telefon': 'TELEFON',
            'tc_pasaport': 'TC/PAS',
            'plaka': 'PLAKA',
            'giris_tarihi': 'GİRİŞ',
            'cikis_tarihi': 'ÇIKIŞ',
            'toplam_ucret': 'TOPLAM ÜCRET',
            'alinan_kapora': 'ÖDENEN',
            'kalan_bakiye': 'KALAN'
        })
        st.dataframe(gosterim.drop(columns=['id', 'oda_id']), use_container_width=True, hide_index=True)

        st.markdown("---")

        tah_c1, tah_c2, tah_c3 = st.columns(3, gap="medium")

        # 1. Kolon: Ara Ödeme / Tahsilat Ekle
        with tah_c1:
            st.markdown("#### 💵 Ara Ödeme / Tahsilat Al")
            secilen_tah_id = st.selectbox(
                "MİSAFİR SEÇİN:",
                options=df['id'].tolist(),
                key="sec_tah",
                format_func=lambda x: f"{df[df['id']==x]['misafir_adi'].values[0]} (Kalan: {float(df[df['id']==x]['kalan_bakiye'].values[0]):,.0f} TL)"
            )
            with st.form("ara_odeme_form"):
                eklenen_tutar = st.number_input("Tahsil Edilen Tutar (TL)", min_value=10.0, step=100.0, value=1000.0)
                eklenen_yontem = st.selectbox("Ödeme Türü", ["Nakit", "Havale / EFT", "Kredi Kartı"])
                kaydet_odeme = st.form_submit_button("💰 Ödemeyi Kaydet", use_container_width=True)
                if kaydet_odeme:
                    turso_execute("""
                        INSERT INTO tahsilatlar (rezervasyon_id, tutar, yontem, tarih)
                        VALUES (?, ?, ?, ?)
                    """, [secilen_tah_id, eklenen_tutar, eklenen_yontem, date.today().strftime("%Y-%m-%d")])
                    
                    # Rezervasyon ödenen tutarını artır
                    turso_execute("""
                        UPDATE rezervasyonlar SET alinan_kapora = alinan_kapora + ? WHERE id = ?
                    """, [eklenen_tutar, secilen_tah_id])
                    st.success("Ödeme işlendi!")
                    st.rerun()

        # 2. Kolon: Bilgi Düzelt
        with tah_c2:
            st.markdown("#### ✏️ Bilgileri Düzenle")
            secilen_duzenle_id = st.selectbox(
                "DÜZENLENECEK KİŞİ:",
                options=df['id'].tolist(),
                key="sec_duz",
                format_func=lambda x: f"{df[df['id']==x]['misafir_adi'].values[0]} ({df[df['id']==x]['oda_adi'].values[0]})"
            )
            rez_secili = df[df['id'] == secilen_duzenle_id].iloc[0]
            with st.form("rez_guncelle_form"):
                yeni_misafir = st.text_input("Ad Soyad", value=rez_secili['misafir_adi'])
                yeni_tel = st.text_input("Telefon", value=rez_secili['telefon'])
                yeni_tc = st.text_input("TC / Pasaport", value=rez_secili['tc_pasaport'] or "")
                yeni_plaka = st.text_input("Plaka", value=rez_secili['plaka'] or "")
                yeni_toplam = st.number_input("Toplam Ücret", value=float(rez_secili['toplam_ucret']), step=100.0)
                
                guncelle_btn = st.form_submit_button("💾 Bilgileri Güncelle", use_container_width=True)
                if guncelle_btn:
                    turso_execute("""
                        UPDATE rezervasyonlar 
                        SET misafir_adi = ?, telefon = ?, tc_pasaport = ?, plaka = ?, toplam_ucret = ?
                        WHERE id = ?
                    """, [yeni_misafir.strip(), yeni_tel.strip(), yeni_tc.strip(), yeni_plaka.strip(), yeni_toplam, secilen_duzenle_id])
                    st.success("Güncellendi!")
                    st.rerun()

        # 3. Kolon: Çıkış & İptal
        with tah_c3:
            st.markdown("#### 🚪 Çıkış & Oda Boşaltma")
            secilen_islem_id = st.selectbox(
                "İŞLEM YAPILACAK ODA:",
                options=df['id'].tolist(),
                key="sec_islem",
                format_func=lambda x: f"{df[df['id']==x]['oda_adi'].values[0]} - {df[df['id']==x]['misafir_adi'].values[0]}"
            )
            
            secili_oda_id = int(df[df['id'] == secilen_islem_id]['oda_id'].values[0])

            if st.button("✅ Çıkış Yap (Odayı Kirli Yap & Arşivle)", use_container_width=True):
                # Rezervasyonu tamamla
                turso_execute("UPDATE rezervasyonlar SET durum = 'Tamamlandı' WHERE id = ?", [secilen_islem_id])
                # Odayı temizlik bekliyor (Kirli) statüsüne al
                turso_execute("UPDATE odalar SET temizlik_durumu = 'Kirli' WHERE id = ?", [secili_oda_id])
                st.success("Çıkış yapıldı! Oda 'Temizlik Bekliyor' olarak işaretlendi.")
                st.rerun()

            if st.button("❌ Rezervasyonu İptal Et", use_container_width=True):
                turso_execute("UPDATE rezervasyonlar SET durum = 'İptal Edildi' WHERE id = ?", [secilen_islem_id])
                st.warning("Rezervasyon iptal edildi, oda boşa çıkarıldı.")
                st.rerun()
    else:
        st.info("Aktif konaklayan misafir bulunmuyor.")

# ==========================================
# 5. GÜNLÜK KBS LİSTESİ
# ==========================================
elif menu == "📋 Günlük KBS & Girişler":
    st.markdown("## 📋 Günlük KBS (Kimlik Bildirim) & Giriş Listesi")
    st.caption("Emniyet / Jandarma KBS sistemine bildirim yaparken tek tek uğraşmayın, buradan kopyalayın.")

    kbs_df = query_df("""
        SELECT o.oda_adi, r.misafir_adi, r.tc_pasaport, r.plaka, r.telefon, r.giris_tarihi, r.cikis_tarihi
        FROM rezervasyonlar r
        JOIN odalar o ON r.oda_id = o.id
        WHERE r.durum = 'Aktif' AND r.giris_tarihi = ?
    """, [secilen_tarih_str])

    if not kbs_df.empty:
        st.success(f"🗓️ **{secilen_tarih.strftime('%d.%m.%Y')}** tarihinde giriş yapacak **{len(kbs_df)}** misafir var.")
        
        st.dataframe(kbs_df.rename(columns={
            'oda_adi': 'DAİRE',
            'misafir_adi': 'MİSAFİR ADI SOYADI',
            'tc_pasaport': 'TC / PASAPORT',
            'plaka': 'PLAKA',
            'telefon': 'TELEFON',
            'giris_tarihi': 'GİRİŞ',
            'cikis_tarihi': 'ÇIKIŞ'
        }), use_container_width=True, hide_index=True)

        # Tek tuşla kopyalama paneli
        kbs_metin = ""
        for _, r in kbs_df.iterrows():
            kbs_metin += f"Daire: {r['oda_adi']} | Ad Soyad: {r['misafir_adi']} | TC: {r['tc_pasaport']} | Plaka: {r['plaka']} | Tel: {r['telefon']}\n"

        st.text_area("📋 Toplu Kopyalama Alanı (KBS İçin):", value=kbs_metin, height=120)
    else:
        st.info(f"{secilen_tarih.strftime('%d.%m.%Y')} tarihinde beklenen yeni giriş bulunmuyor.")

# ==========================================
# 6. REZERVASYON ARA
# ==========================================
elif menu == "🔍 Rezervasyon Ara":
    st.markdown("## 🔍 Rezervasyon Arama & Hızlı Filtre")
    st.caption("Misafir adı, telefon, plaka veya TC kimlik numarası ile geçmiş ve aktif tüm kayıtları anında bulun.")

    arama_terimi = st.text_input("Arama Yapın (Ad, Soyad, Tel, Plaka, TC):", placeholder="Örn: 555..., Ahmet, 61 AB...")

    if arama_terimi.strip():
        ara_pattern = f"%{arama_terimi.strip()}%"
        sonuc_df = query_df("""
            SELECT o.oda_adi, r.misafir_adi, r.telefon, r.tc_pasaport, r.plaka, r.giris_tarihi, r.cikis_tarihi, r.toplam_ucret, r.durum
            FROM rezervasyonlar r
            JOIN odalar o ON r.oda_id = o.id
            WHERE r.misafir_adi LIKE ? OR r.telefon LIKE ? OR r.tc_pasaport LIKE ? OR r.plaka LIKE ?
            ORDER BY r.giris_tarihi DESC
        """, [ara_pattern, ara_pattern, ara_pattern, ara_pattern])

        if not sonuc_df.empty:
            st.success(f"Toplam **{len(sonuc_df)}** kayıt bulundu:")
            st.dataframe(sonuc_df.rename(columns={
                'oda_adi': 'DAİRE',
                'misafir_adi': 'MİSAFİR',
                'telefon': 'TELEFON',
                'tc_pasaport': 'TC/PAS',
                'plaka': 'PLAKA',
                'giris_tarihi': 'GİRİŞ',
                'cikis_tarihi': 'ÇIKIŞ',
                'toplam_ucret': 'ÜCRET',
                'durum': 'DURUM'
            }), use_container_width=True, hide_index=True)
        else:
            st.warning("Eşleşen rezervasyon bulunamadı.")

# ==========================================
# 7. GİDER & NET KÂR
# ==========================================
elif menu == "📉 Gider & Net Kâr":
    st.markdown("## 📉 Gider Takibi & Net Kâr Hesabı")

    gider_df = query_df("SELECT * FROM giderler ORDER BY tarih DESC")
    _, gel_rows = turso_execute("SELECT SUM(toplam_ucret) FROM rezervasyonlar WHERE durum IN ('Aktif', 'Tamamlandı')")
    toplam_gelir_val = float(gel_rows[0][0]) if (gel_rows and gel_rows[0][0] is not None) else 0.0

    toplam_gider = gider_df['tutar'].astype(float).sum() if not gider_df.empty else 0.0
    net_kar = toplam_gelir_val - toplam_gider

    g1, g2, g3 = st.columns(3)
    g1.markdown(f'<div class="stat-box"><div class="stat-label">Toplam Hasılat (Tahakkuk)</div><div class="stat-val" style="color:#10b981;">{toplam_gelir_val:,.0f} TL</div></div>', unsafe_allow_html=True)
    g2.markdown(f'<div class="stat-box"><div class="stat-label">Toplam Gider</div><div class="stat-val" style="color:#ef4444;">{toplam_gider:,.0f} TL</div></div>', unsafe_allow_html=True)
    g3.markdown(f'<div class="stat-box"><div class="stat-label">Net Kalan Kâr</div><div class="stat-val" style="color:#38bdf8;">{net_kar:,.0f} TL</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    col_g1, col_g2 = st.columns([1, 2], gap="large")
    with col_g1:
        st.markdown("#### ➕ Yeni Gider Ekle")
        with st.form("yeni_gider_form"):
            g_baslik = st.text_input("Gider Açıklaması", placeholder="Örn: Elektrik faturası, Temizlik malzemesi")
            g_kat = st.selectbox("Kategori", ["Faturalar (Elektrik/Su/Net)", "Temizlik & Çamaşır", "Tamirat & Bakım", "Personel / Hizmet", "Diğer"])
            g_tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0, value=250.0)
            g_tarih = st.date_input("Harcama Tarihi", value=date.today())

            ekle_btn = st.form_submit_button("Gideri Kaydet", use_container_width=True)
            if ekle_btn and g_baslik.strip():
                turso_execute("INSERT INTO giderler (baslik, kategori, tutar, tarih) VALUES (?, ?, ?, ?)",
                              [g_baslik.strip(), g_kat, g_tutar, g_tarih.strftime("%Y-%m-%d")])
                st.success("Gider kaydedildi!")
                st.rerun()

    with col_g2:
        st.markdown("#### 📜 Gider Geçmişi")
        if not gider_df.empty:
            g_tablo = gider_df.rename(columns={
                'baslik': 'AÇIKLAMA',
                'kategori': 'KATEGORİ',
                'tutar': 'TUTAR (TL)',
                'tarih': 'TARİH'
            })
            st.dataframe(g_tablo.drop(columns=['id']), use_container_width=True, hide_index=True)
        else:
            st.info("Kayıtlı gider bulunmuyor.")

# ==========================================
# 8. REZERVASYON ARŞİVİ
# ==========================================
elif menu == "📁 Rezervasyon Arşivi":
    st.markdown("## 📁 Tamamlanan & İptal Edilen Rezervasyon Arşivi")

    arsiv_df = query_df("""
        SELECT o.oda_adi, r.misafir_adi, r.telefon, r.tc_pasaport, r.plaka, r.giris_tarihi, r.cikis_tarihi, r.toplam_ucret, r.durum
        FROM rezervasyonlar r
        JOIN odalar o ON r.oda_id = o.id
        WHERE r.durum IN ('Tamamlandı', 'İptal Edildi')
        ORDER BY r.cikis_tarihi DESC
    """)

    if not arsiv_df.empty:
        tamamlananlar = arsiv_df[arsiv_df['durum'] == 'Tamamlandı']
        toplam_kazanc = tamamlananlar['toplam_ucret'].astype(float).sum()
        
        st.markdown(f'<div class="stat-box" style="max-width:350px;"><div class="stat-label">Arşivdeki Tamamlanan Ciro</div><div class="stat-val" style="color:#10b981;">{toplam_kazanc:,.0f} TL</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        csv_arsiv = arsiv_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Tüm Arşivi İndir (CSV)", data=csv_arsiv, file_name=f"arsiv_{date.today().strftime('%Y%m%d')}.csv", mime="text/csv")

        goster = arsiv_df.rename(columns={
            'oda_adi': 'DAİRE',
            'misafir_adi': 'MİSAFİR ADI SOYADI',
            'telefon': 'TELEFON',
            'tc_pasaport': 'TC/PASAPORT',
            'plaka': 'PLAKA',
            'giris_tarihi': 'GİRİŞ',
            'cikis_tarihi': 'ÇIKIŞ',
            'toplam_ucret': 'ÜCRET (TL)',
            'durum': 'DURUM'
        })
        st.dataframe(goster, use_container_width=True, hide_index=True)
    else:
        st.info("Arşivde tamamlanmış veya iptal edilmiş kayıt bulunmuyor.")

# ==========================================
# 9. DAİRE & APART AYARLARI
# ==========================================
elif menu == "⚙️ Daire & Apart Ayarları":
    st.markdown("## ⚙️ Apart, Wi-Fi, Konum ve Daire Ayarları")

    with st.expander("🏨 Apart İsmi, Wi-Fi & Konum Bilgileri (WhatsApp İçin)", expanded=True):
        with st.form("genel_ayarlar_form"):
            c_ay1, c_ay2 = st.columns(2)
            with c_ay1:
                y_apart = st.text_input("Apart İsmi / Tabelası", value=apart_baslik)
                y_wifi_ad = st.text_input("Misafir Wi-Fi Ağ Adı", value=wifi_adi)
            with c_ay2:
                y_wifi_sif = st.text_input("Misafir Wi-Fi Şifresi", value=wifi_sifre)
                y_konum = st.text_input("Google Maps Konum Linki", value=konum_linki)

            if st.form_submit_button("💾 Genel Ayarları Kaydet", use_container_width=True):
                turso_execute("UPDATE ayarlar SET deger = ? WHERE anahtar = 'apart_adi'", [y_apart.strip()])
                turso_execute("UPDATE ayarlar SET deger = ? WHERE anahtar = 'wifi_adi'", [y_wifi_ad.strip()])
                turso_execute("UPDATE ayarlar SET deger = ? WHERE anahtar = 'wifi_sifre'", [y_wifi_sif.strip()])
                turso_execute("UPDATE ayarlar SET deger = ? WHERE anahtar = 'konum_linki'", [y_konum.strip()])
                st.success("Tüm işletme ayarları güncellendi!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### 🏢 Daire İsimleri, Katları & Taban Fiyatları")

    _, daire_rows = turso_execute("SELECT id, oda_adi, kat, kapasite, gecelik_fiyat FROM odalar ORDER BY id ASC")

    for d_id, d_adi, d_kat, d_kap, d_fiyat in daire_rows:
        with st.expander(f"🏠 {d_adi} ({d_kat} - {d_kap} Kişilik - {float(d_fiyat or 1500):,.0f} TL/gece)", expanded=False):
            with st.form(f"form_daire_{d_id}"):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    duz_ad = st.text_input("Daire Adı / No", value=d_adi)
                with c2:
                    kat_secenek = ["Çatı Katı", "3. Kat", "2. Kat", "1. Kat", "Zemin Kat", "Bahçe Katı"]
                    kat_idx = kat_secenek.index(d_kat) if d_kat in kat_secenek else 0
                    duz_kat = st.selectbox("Katı", options=kat_secenek, index=kat_idx)
                with c3:
                    duz_kap = st.number_input("Kapasite (Kişi)", min_value=1, max_value=20, value=int(d_kap))
                with c4:
                    duz_fiyat = st.number_input("Gecelik Taban Fiyat (TL)", min_value=0.0, step=100.0, value=float(d_fiyat or 1500))

                kaydet_daire = st.form_submit_button("💾 Daireyi Güncelle")
                if kaydet_daire:
                    turso_execute("UPDATE odalar SET oda_adi = ?, kat = ?, kapasite = ?, gecelik_fiyat = ? WHERE id = ?",
                                  [duz_ad.strip(), duz_kat, duz_kap, duz_fiyat, d_id])
                    st.success(f"{duz_ad} güncellendi!")
                    st.rerun()
