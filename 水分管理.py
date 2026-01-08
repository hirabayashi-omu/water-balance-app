import streamlit as st
import datetime
import pandas as pd
from io import BytesIO

# PDF生成用
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ================================
# 1. ページ構成・デザイン
# ================================
st.set_page_config(page_title="水分出納管理システム", layout="wide")

st.markdown("""
    <style>
    .main-header { background-color: #004a99; color: white; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 2rem; }
    .status-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 1px solid #dcdfe6; }
    .stTable { font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# ================================
# 2. PDF生成エンジン
# ================================
try:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
except:
    pass

def generate_medical_report(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont("HeiseiMin-W3", 18)
    c.drawCentredString(w/2, h - 20*mm, "水分出納管理記録 (Fluid Balance Report)")
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(20*mm, h - 30*mm, f"記録日時: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M')}")
    c.drawString(150*mm, h - 30*mm, f"記録者: {data['recorder'] or '__________'}")
    c.line(20*mm, h - 32*mm, 190*mm, h - 32*mm)
    y = h - 45*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【患者基本情報】")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25*mm, y, f"年齢: {data['age']} 歳 / 体重: {data['weight']} kg / 体温: {data['temp']} ℃ / 室温: {data['room_temp']} ℃")
    y -= 15*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【入出量詳細テーブル】")
    y -= 8*mm
    # PDF内簡易テーブル
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25*mm, y, "項目 (IN)")
    c.drawString(60*mm, y, "量(mL)")
    c.drawString(110*mm, y, "項目 (OUT)")
    c.drawString(155*mm, y, "量(mL)")
    y -= 2*mm
    c.line(20*mm, y, 190*mm, y)
    y -= 7*mm
    items = [
        ("経口/経管", f"{data['oral']}", "尿量", f"{data['urine']}"),
        ("静脈輸液", f"{data['iv']}", "出血/ドレーン", f"{data['bleeding']}"),
        ("輸血", f"{data['blood']}", "便中水分", f"{data['stool']}"),
        ("代謝水", f"{data['metabolic']}", "不感蒸泄", f"{data['insensible']}")
    ]
    for i1, v1, i2, v2 in items:
        c.drawString(25*mm, y, i1)
        c.drawRightString(85*mm, y, v1)
        c.drawString(110*mm, y, i2)
        c.drawRightString(180*mm, y, v2)
        y -= 6*mm
    y -= 15*mm
    c.setFont("HeiseiMin-W3", 14)
    c.drawCentredString(w/2, y, f"24h ネットバランス: {data['net']:+.0f} mL")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25*mm, y, f"総合評価: {data['judgment']}")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ================================
# 3. メインUI
# ================================
st.markdown('<div class="main-header"><h1>🏥 水分出納管理システム</h1></div>', unsafe_allow_html=True)

# 入力セクション
with st.sidebar:
    st.header("📋 患者基本データ")
    recorder = st.text_input("記録責任者", "")
    age = st.number_input("年齢", 0, 120, 65)
    weight = st.number_input("体重 (kg)", 1.0, 200.0, 60.0)
    temp = st.number_input("体温 (℃)", 34.0, 42.0, 36.5, 0.1)
    r_temp = st.number_input("室温 (℃)", 10.0, 40.0, 24.0)

# 1. 摂取・排泄データの入力
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📥 Intake (摂取量)")
    oral = st.number_input("経口摂取・経管栄養 (mL)", 0, 10000, 1500)
    iv = st.number_input("点滴・静脈輸液 (mL)", 0, 10000, 500)
    blood = st.number_input("輸血製剤 (mL)", 0, 5000, 0)
    metabolic = 5 * weight # 代謝水

with col2:
    st.markdown("### 📤 Output (排泄量)")
    u_vol = st.number_input("総尿量 (mL)", 0, 10000, 1200)
    bleeding = st.number_input("出血・ドレーン等 (mL)", 0, 5000, 0)
    s_type = st.selectbox("便性状", ["普通便", "軟便", "下痢便"])
    s_vol = st.number_input("便量 (g)", 0, 1000, 150)
    stool = s_vol * (0.75 if s_type=="普通便" else 0.85 if s_type=="軟便" else 0.95)

# 不感蒸泄計算
insensible = 15 * weight
if temp > 37: insensible *= (1 + 0.15 * (temp - 37))
if r_temp > 30: insensible *= (1 + 0.175 * (r_temp - 30))

total_in = oral + iv + blood + metabolic
total_out = u_vol + bleeding + stool + insensible
net_bal = total_in - total_out

# 2. 結果のテーブル化表示
st.markdown("---")
st.header("📊 水分出納詳細テーブル")

# データの構造化
df_in = pd.DataFrame({
    "項目": ["経口/経管", "静脈輸液", "輸血", "代謝水(推定)"],
    "量 (mL)": [oral, iv, blood, metabolic]
})

df_out = pd.DataFrame({
    "項目": ["尿量", "出血/ドレーン", "便中水分", "不感蒸泄(推定)"],
    "量 (mL)": [u_vol, bleeding, stool, insensible]
})

t_col1, t_col2 = st.columns(2)
with t_col1:
    st.subheader("摂取詳細")
    st.table(df_in)
    st.markdown(f"**摂取合計: {total_in:.0f} mL**")

with t_col2:
    st.subheader("排泄詳細")
    st.table(df_out)
    st.markdown(f"**排泄合計: {total_out:.0f} mL**")

# 3. 総合判定サマリー
st.markdown("---")
st.header("🩺 臨床評価サマリー")

res_col1, res_col2 = st.columns([1, 2])

with res_col1:
    st.metric("Net Balance", f"{net_bal:+.0f} mL", delta=net_bal, delta_color="inverse")

with res_col2:
    if net_bal > 500:
        judg = "【注意】体液過剰傾向。心不全症状（浮腫・喘鳴）や血圧上昇に留意してください。"
        st.error(judg)
    elif net_bal < -200:
        judg = "【注意】脱水傾向。皮膚ツルゴール低下、口渇、血圧低下、尿量減少を要確認。"
        st.warning(judg)
    else:
        judg = "【正常】水分バランスは維持範囲内です。現在の管理を継続してください。"
        st.success(judg)

# PDF出力用データ
report_data = {
    "age": age, "weight": weight, "temp": temp, "room_temp": r_temp,
    "oral": oral, "iv": iv, "blood": blood, "metabolic": metabolic,
    "urine": u_vol, "bleeding": bleeding, "stool": stool, "insensible": insensible,
    "net": net_bal, "judgment": judg, "recorder": recorder
}

st.markdown("---")
if st.button("📄 医療レポート(PDF)を生成"):
    pdf = generate_medical_report(report_data)
    st.download_button(
        label="📥 レポートをダウンロード",
        data=pdf,
        file_name=f"Report_FluidBalance_{datetime.date.today()}.pdf",
        mime="application/pdf"
    )
