import streamlit as st
import datetime
import pytz
from io import BytesIO

# PDF生成用
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ================================
# 0. タイムゾーン設定 (2026年対応)
# ================================
def get_jst_now():
    return datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

# ================================
# 1. スマホ向けCSS・デザイン修正
# ================================
st.set_page_config(page_title="水分出納管理", layout="centered") # スマホはcenteredが見やすい

st.markdown("""
    <style>
    /* スマホでのフォントサイズ調整 */
    html { font-size: 16px; }
    .report-header { 
        background-color: #f8f9fa; padding: 15px; border-radius: 10px; 
        border-left: 5px solid #007bff; margin-bottom: 15px; 
    }
    /* ボタンを押しやすく大きくする */
    .stButton>button {
        width: 100%;
        height: 3em;
        font-weight: bold;
    }
    /* メトリックの枠線をスマホで見やすく */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 10px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ================================
# 2. PDF生成エンジン (レイアウト維持)
# ================================
try:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
except:
    pass

def generate_medical_report(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    jst_now = get_jst_now().strftime('%Y/%m/%d %H:%M')

    c.setFont("HeiseiMin-W3", 16)
    c.drawCentredString(w/2, h - 20*mm, "水分出納管理記録 (2026)")
    
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(20*mm, h - 30*mm, f"記録日時: {jst_now}")
    c.drawString(150*mm, h - 30*mm, f"記録者: {data['recorder']}")
    c.line(20*mm, h - 32*mm, 190*mm, h - 32*mm)

    # ... (中略: 前回のPDFロジックと同じ。PDFはA4固定なのでスマホでも綺麗に出力されます) ...
    # ※ 座標計算を調整した前回のロジックをここに含めます
    y = h - 45*mm
    c.drawString(20*mm, y, "【基本情報】")
    y -= 10*mm
    c.drawString(25*mm, y, f"年齢: {data['age']}歳 / 体重: {data['weight']:.1f}kg / 体温: {data['temp']:.1f}℃")
    y -= 10*mm
    c.line(20*mm, y, 190*mm, y)
    y -= 10*mm
    c.drawString(20*mm, y, f"IN 合計: {data['total_in']:.0f} mL")
    y -= 7*mm
    c.drawString(20*mm, y, f"OUT 合計: {data['total_out']:.0f} mL")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, f"ネットバランス: {data['net']:+.0f} mL")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ================================
# 3. アプリUI (スマホ最適化)
# ================================
st.title("🏥 水分出納記録")

# 基本情報 (スマホでは2列程度が限界)
st.markdown('<div class="report-header">基本情報</div>', unsafe_allow_html=True)
col_a, col_b = st.columns(2)
with col_a:
    age = st.number_input("年齢", 0, 120, 20)
    weight = st.number_input("体重 (kg)", 1.0, 200.0, 60.0, 0.1)
with col_b:
    temp = st.number_input("体温 (℃)", 34.0, 42.0, 36.5, 0.1)
    recorder = st.text_input("記録者", "担当者A")

# 入力セクションをタブで切り替え (スマホでスクロールを減らす)
tab1, tab2 = st.tabs(["📥 摂取 (IN)", "📤 排泄 (OUT)"])

with tab1:
    oral = st.number_input("経口/経管 (mL)", 0, 5000, 1500, 50)
    iv = st.number_input("静脈輸液 (mL)", 0, 5000, 0, 50)
    blood = st.number_input("輸血 (mL)", 0, 5000, 0, 50)
    metabolic = 5 * weight

with tab2:
    u_vol = st.number_input("尿量合計 (mL)", 0, 5000, 1200, 50)
    bleeding = st.number_input("出血/ドレーン (mL)", 0, 5000, 0, 50)
    stool_vol = st.number_input("便量 (g)", 0, 1000, 150, 10)
    # 不感蒸泄（計算は裏側で実施）
    insensible = 15 * weight
    if temp > 37: insensible *= (1 + 0.15 * (temp - 37))

# 計算
total_in = oral + iv + blood + metabolic
total_out = u_vol + bleeding + (stool_vol * 0.8) + insensible
net_bal = total_in - total_out

# 分析結果 (スマホでも見やすいメトリック)
st.markdown('<div class="report-header">分析結果</div>', unsafe_allow_html=True)
st.metric("ネットバランス", f"{net_bal:+.0f} mL")

if net_bal > 500:
    st.error("体液過剰の傾向")
elif net_bal < -200:
    st.warning("脱水リスクあり")
else:
    st.success("維持範囲内")

# PDFボタン
if st.button("📄 PDFレポートを生成"):
    report_data = {
        "age": age, "weight": weight, "temp": temp, "recorder": recorder,
        "total_in": total_in, "total_out": total_out, "net": net_bal
    }
    pdf = generate_medical_report(report_data)
    st.download_button(
        label="📥 ここをタップして保存",
        data=pdf,
        file_name=f"Report_{get_jst_now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )
