import streamlit as st
import datetime
import pytz
from io import BytesIO

# PDF生成用
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ================================
# 0. タイムゾーン設定 (2026年対応)
# ================================
def get_jst_now():
    return datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

# ================================
# 1. ページ構成・デザイン修正（見出しの可視化）
# ================================
st.set_page_config(page_title="水分出納管理システム", layout="wide")

st.markdown("""
    <style>
    /* 見出しを確実に表示させるための設定 */
    .report-header { 
        background-color: #f0f2f6; 
        padding: 15px; 
        border-radius: 10px; 
        border-left: 5px solid #007bff; 
        margin-bottom: 20px;
    }
    .report-header h4 {
        color: #1f1f1f !important; /* ダークモードでも黒文字で強制表示 */
        margin: 0;
        font-weight: bold;
    }
    .stMetric { 
        border: 1px solid #e9ecef; 
        padding: 15px; 
        border-radius: 8px; 
        background-color: #ffffff; 
    }
    /* スマホでのカラム折り返し対策 */
    @media (max-width: 640px) {
        .stMetric { margin-bottom: 10px; }
    }
    </style>
    """, unsafe_allow_html=True)

# ================================
# 2. PDF生成エンジン (レイアウト修正済み)
# ================================
try:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
except:
    pass

def generate_medical_report(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # ヘッダー
    c.setFont("HeiseiMin-W3", 18)
    c.drawCentredString(w/2, h - 20*mm, "水分出納管理記録 (Fluid Balance Report)")
    
    jst_now = get_jst_now().strftime('%Y/%m/%d %H:%M')
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(20*mm, h - 30*mm, f"記録日時: {jst_now}")
    c.drawString(150*mm, h - 30*mm, f"記録者: {data['recorder'] or '__________'}")
    c.setLineWidth(0.5)
    c.line(20*mm, h - 32*mm, 190*mm, h - 32*mm)

    # 基本情報（重なり防止のためy座標の間隔を確保）
    y = h - 45*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【基本情報】")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    base_info = [
        f"年齢: {data['age']} 歳", f"現体重: {data['weight']:.1f} kg", 
        f"体温: {data['temp']:.1f} ℃", f"室温: {data['room_temp']:.1f} ℃",
        f"推定体水分率: {data['bw_percent']:.1f} %", f"推定総体水分量: {data['bw_total']:.1f} L"
    ]
    for i, info in enumerate(base_info):
        col = i % 2
        row = i // 2
        c.drawString((25 + col*80)*mm, y - row*8*mm, info)
    
    y -= 22*mm
    c.line(20*mm, y, 190*mm, y)

    # 入出量詳細
    y -= 8*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【入出量詳細 / 24時間換算】")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25*mm, y, "項目 (IN / 摂取)")
    c.drawString(75*mm, y, "数値 (mL)")
    c.drawString(110*mm, y, "項目 (OUT / 排泄・損失)")
    c.drawString(165*mm, y, "数値 (mL)")
    y -= 4*mm
    c.line(20*mm, y, 190*mm, y)
    y -= 8*mm

    rows = [
        ("経口摂取", f"{data['oral']:.0f}", "尿量", f"{data['urine']:.0f}"),
        ("静脈輸液", f"{data['iv']:.0f}", "消化管・出血", f"{data['bleeding']:.0f}"),
        ("輸血製剤", f"{data['blood']:.0f}", "便中水分", f"{data['stool']:.0f}"),
        ("代謝水(推定)", f"{data['metabolic']:.0f}", "不感蒸泄(推定)", f"{data['insensible']:.0f}")
    ]

    for in_n, in_v, out_n, out_v in rows:
        c.drawString(25*mm, y, in_n)
        c.drawRightString(90*mm, y, in_v)
        c.drawString(110*mm, y, out_n)
        c.drawRightString(180*mm, y, out_v)
        y -= 8*mm

    y -= 2*mm
    c.line(20*mm, y, 190*mm, y)
    y -= 10*mm

    # 総合評価
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【水分バランス評価】")
    y -= 12*mm
    c.setFont("HeiseiMin-W3", 14)
    balance_text = f"ネットバランス: {data['net']:+.0f} mL / day"
    c.drawCentredString(w/2, y, balance_text)
    y -= 12*mm
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25*mm, y, f"総合判定: {data['judgment']}")
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ================================
# 3. アプリメインUI
# ================================
st.title("🏥 水分出納バランス記録システム")

# 1. 基本・臨床パラメータ
st.markdown('<div class="report-header"><h4>1. 基本・臨床パラメータ</h4></div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns([1,1,1,1,2])
with c1: age = st.number_input("年齢", 0, 120, 20) # デフォルト20歳
with c2: weight = st.number_input("体重 (kg)", 1.0, 200.0, 60.0, 0.1)
with c3: temp = st.number_input("体温 (℃)", 34.0, 42.0, 36.5, 0.1)
with c4: r_temp = st.number_input("室温 (℃)", 10.0, 40.0, 24.0, 0.5)
with c5: recorder = st.text_input("記録責任者", "")

# 計算ロジック
bw_p = (80 - (age/1)*10) if age<=1 else (70 - ((age-1)/12)*10) if age<=13 else (60 - ((age-13)/52)*10) if age<=65 else 50
bw_t = weight * (bw_p / 100)

st.markdown("---")

# 入力セクション
col_in_ui, col_out_ui = st.columns(2)
with col_in_ui:
    st.subheader("📥 Intake (摂取)")
    oral = st.number_input("経口・経管栄養 (mL)", 0, 10000, 1500, 50)
    iv = st.number_input("静脈輸液 (mL)", 0, 10000, 0, 50) # デフォルト0ml
    blood = st.number_input("輸血 (mL)", 0, 5000, 0, 50)
    metabolic = 5 * weight 

with col_out_ui:
    st.subheader("📤 Output (排泄)")
    u_times = st.number_input("排尿回数/日", 0, 20, 5)
    u_vol = st.number_input("平均1回尿量 (mL)", 0, 1000, 250)
    urine = u_times * u_vol
    bleeding = st.number_input("出血・ドレーン等 (mL)", 0, 5000, 0)
    s_type = st.selectbox("便性状", ["普通", "軟便", "下痢"])
    s_vol = st.number_input("便重量 (g)", 0, 1000, 150)
    stool = s_vol * (0.75 if s_type=="普通" else 0.85 if s_type=="軟便" else 0.95)

# 不感蒸泄計算
insensible = 15 * weight
if temp > 37: insensible *= (1 + 0.15 * (temp - 37))
if r_temp > 30: insensible *= (1 + 0.175 * (r_temp - 30))

total_in = oral + iv + blood + metabolic
total_out = urine + bleeding + stool + insensible
net_bal = total_in - total_out

# 2. 分析結果
st.markdown('<div class="report-header"><h4>2. 分析結果</h4></div>', unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)
m1.metric("総 IN", f"{total_in:.0f} mL")
m2.metric("総 OUT", f"{total_out:.0f} mL")
m3.metric("バランス", f"{net_bal:+.0f} mL", delta_color="inverse")

if net_bal > 500:
    judg = "体液過剰 (Overhydration) の傾向あり。"
    st.error(judg)
elif net_bal < -200:
    judg = "脱水 (Dehydration) のリスクあり。"
    st.warning(judg)
else:
    judg = "維持範囲内 (Maintenance range)。"
    st.success(judg)

# レポート生成
if st.button("📝 医療レポート(PDF)を生成"):
    report_data = {
        "age": age, "weight": weight, "temp": temp, "room_temp": r_temp,
        "bw_percent": bw_p, "bw_total": bw_t,
        "oral": oral, "iv": iv, "blood": blood, "metabolic": metabolic,
        "urine": urine, "bleeding": bleeding, "stool": stool, "insensible": insensible,
        "net": net_bal, "judgment": judg, "recorder": recorder
    }
    pdf = generate_medical_report(report_data)
    st.download_button(
        label="📥 レポートをダウンロード",
        data=pdf,
        file_name=f"Report_{get_jst_now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )
