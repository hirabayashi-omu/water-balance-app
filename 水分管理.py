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
# 0. タイムゾーン設定 (2026年1月対応)
# ================================
def get_jst_now():
    return datetime.datetime.now(pytz.timezone('Asia/Tokyo'))

# ================================
# 1. ページ構成・デザイン修正（視認性重視）
# ================================
st.set_page_config(page_title="水分出納管理システム", layout="wide")

# 背景色に依存せず文字を確実に見せるためのCSS
st.markdown("""
    <style>
    /* 見出しエリアの文字色を強制的に黒に固定 (ライト/ダーク両対応) */
    .report-header-box {
        background-color: #e9ecef;
        padding: 10px 20px;
        border-radius: 8px;
        border-left: 6px solid #007bff;
        margin: 20px 0;
    }
    .report-header-box h4 {
        color: #000000 !important;
        margin: 0 !important;
    }
    /* メトリック（分析結果）の視認性向上 */
    [data-testid="stMetricValue"] {
        color: #007bff !important;
    }
    [data-testid="stMetricLabel"] {
        color: #333333 !important;
    }
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
    jst_now = get_jst_now().strftime('%Y/%m/%d %H:%M')

    c.setFont("HeiseiMin-W3", 18)
    c.drawCentredString(w/2, h - 20*mm, "水分出納管理判定 (2026)")
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(20*mm, h - 30*mm, f"記録日時: {jst_now}")
    c.drawString(150*mm, h - 30*mm, f"記録者: {data['recorder'] or '未記入'}")
    c.line(20*mm, h - 32*mm, 190*mm, h - 32*mm)

    y = h - 45*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【基本情報】")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    info_text = f"年齢: {data['age']}歳 / 体重: {data['weight']:.1f}kg / 体温: {data['temp']:.1f}℃ / 室温: {data['room_temp']:.1f}℃"
    c.drawString(25*mm, y, info_text)
    
    y -= 15*mm
    c.line(20*mm, y, 190*mm, y)
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【バランス結果】")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25*mm, y, f"総摂取 (IN): {data['total_in']:.0f} mL")
    y -= 7*mm
    c.drawString(25*mm, y, f"総排泄 (OUT): {data['total_out']:.0f} mL")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 14)
    c.drawString(20*mm, y, f"ネットバランス: {data['net']:+.0f} mL / day")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(20*mm, y, f"判定: {data['judgment']}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ================================
# 3. アプリメインUI
# ================================
st.title("🏥 水分出納バランス記録")

# 1. 基本・臨床パラメータ
st.markdown('<div class="report-header-box"><h4>1. 基本・臨床パラメータ</h4></div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([1,1,1,2])
with c1: age = st.number_input("年齢", 0, 120, 20)
with c2: weight = st.number_input("体重(kg)", 1.0, 200.0, 60.0, 0.1)
with c3: temp = st.number_input("体温(℃)", 34.0, 42.0, 36.5, 0.1)
with c4: recorder = st.text_input("記録者", "")

r_temp = 24.0 # 室温は固定または非表示に近くても計算は維持

# --- 計算ロジック ---
metabolic = 5 * weight
insensible = 15 * weight
if temp > 37: insensible *= (1 + 0.15 * (temp - 37))

st.markdown("---")

# 入力セクション
col_in, col_out = st.columns(2)
with col_in:
    st.subheader("📥 IN (摂取)")
    oral = st.number_input("経口・経管 (mL)", 0, 10000, 1500, 50)
    iv = st.number_input("静脈輸液 (mL)", 0, 10000, 0, 50)
    blood = st.number_input("輸血 (mL)", 0, 5000, 0, 50)

with col_out:
    st.subheader("📤 OUT (排泄)")
    urine = st.number_input("尿量合計 (mL)", 0, 10000, 1250, 50)
    other_out = st.number_input("その他(出血/便) (mL)", 0, 5000, 150, 50)

# 合計計算
total_in = oral + iv + blood + metabolic
total_out = urine + other_out + insensible
net_bal = total_in - total_out

# 2. 分析結果 (ここが確実に表示されるように変更)
st.markdown('<div class="report-header-box"><h4>2. 分析結果</h4></div>', unsafe_allow_html=True)

# スマホでも見えるよう、あえてカラムを分けすぎない
res_in, res_out, res_net = st.columns(3)
res_in.metric("総 IN", f"{total_in:.0f} mL")
res_out.metric("総 OUT", f"{total_out:.0f} mL")
res_net.metric("バランス", f"{net_bal:+.0f} mL")

if net_bal > 500:
    judg = "体液過剰の傾向あり。浮腫に注意。"
    st.error(judg)
elif net_bal < -200:
    judg = "脱水リスクあり。循環動態を確認。"
    st.warning(judg)
else:
    judg = "維持範囲内です。"
    st.success(judg)

# レポート生成
st.markdown("---")
if st.button("📝 医療レポート(PDF)を生成"):
    report_data = {
        "age": age, "weight": weight, "temp": temp, "room_temp": r_temp,
        "oral": oral, "iv": iv, "blood": blood, "metabolic": metabolic,
        "urine": urine, "bleeding": other_out, "insensible": insensible,
        "total_in": total_in, "total_out": total_out,
        "net": net_bal, "judgment": judg, "recorder": recorder
    }
    pdf = generate_medical_report(report_data)
    st.download_button(
        label="📥 レポートをダウンロード",
        data=pdf,
        file_name=f"Report_{get_jst_now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )


