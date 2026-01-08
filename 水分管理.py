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
# 1. ページ構成・デザイン（視認性向上）
# ================================
st.set_page_config(page_title="水分出納管理システム", layout="wide")

st.markdown("""
    <style>
    .report-header-box {
        background-color: #e9ecef;
        padding: 10px 20px;
        border-radius: 8px;
        border-left: 6px solid #007bff;
        margin: 20px 0;
    }
    .report-header-box h4 { color: #000000 !important; margin: 0 !important; }
    [data-testid="stMetricValue"] { color: #007bff !important; }
    </style>
    """, unsafe_allow_html=True)

# ================================
# 2. PDF生成エンジン（レイアウト崩れ防止版）
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
    c.drawCentredString(w/2, h - 20*mm, "水分出納管理記録 (2026)")
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(20*mm, h - 30*mm, f"記録日時: {jst_now}")
    c.drawString(150*mm, h - 30*mm, f"記録者: {data['recorder'] or '未記入'}")
    c.line(20*mm, h - 32*mm, 190*mm, h - 32*mm)

    y = h - 45*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【基本情報】")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25*mm, y, f"年齢: {data['age']}歳 / 体重: {data['weight']:.1f}kg / 体温: {data['temp']:.1f}℃ / 室温: {data['room_temp']:.1f}℃")
    
    y -= 15*mm
    c.line(20*mm, y, 190*mm, y)
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20*mm, y, "【入出量内訳】")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25*mm, y, f"IN - 経口: {data['oral']} / 輸液: {data['iv']} / 輸血: {data['blood']} / 代謝水: {data['metabolic']:.0f}")
    y -= 7*mm
    c.drawString(25*mm, y, f"OUT - 尿量: {data['urine']} / その他: {data['bleeding']} / 便水分: {data['stool']:.0f} / 不感蒸泄: {data['insensible']:.0f}")

    y -= 15*mm
    c.setFont("HeiseiMin-W3", 14)
    c.drawString(20*mm, y, f"ネットバランス: {data['net']:+.0f} mL / day")
    y -= 10*mm
    c.setFont("HeiseiMin-W3", 11)
    c.drawString(20*mm, y, f"判定: {data['judgment']}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ================================
# 3. ナビゲーション
# ================================
st.sidebar.title("メニュー")
page = st.sidebar.radio("画面切り替え", ["🏠 メイン計算", "📖 推算根拠"])

# ================================
# 4. メイン計算ページ
# ================================
if page == "🏠 メイン計算":
    st.title("🏥 水分出納バランス記録")

    # 1. パラメータ入力
    st.markdown('<div class="report-header-box"><h4>1. 基本・臨床パラメータ</h4></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: age = st.number_input("年齢", 0, 120, 20)
    with c2: weight = st.number_input("体重 (kg)", 1.0, 200.0, 60.0, 0.1)
    with c3: temp = st.number_input("体温 (℃)", 34.0, 42.0, 36.5, 0.1)
    with c4: r_temp = st.number_input("室温 (℃)", 10.0, 40.0, 24.0, 0.5)
    with c5: recorder = st.text_input("記録責任者", "")

    st.markdown("---")

    # 2. IN / OUT 入力
    col_in, col_out = st.columns(2)
    with col_in:
        st.subheader("📥 Intake (摂取)")
        oral = st.number_input("経口・経管栄養 (mL)", 0, 10000, 1500, 50)
        iv = st.number_input("静脈輸液 (mL)", 0, 10000, 0, 50)
        blood = st.number_input("輸血 (mL)", 0, 5000, 0, 50)
        metabolic = 5 * weight # 代謝水

    with col_out:
        st.subheader("📤 Output (排泄)")
        u_times = st.number_input("排尿回数/日", 0, 20, 5)
        u_vol = st.number_input("平均1回尿量 (mL)", 0, 1000, 250)
        urine = u_times * u_vol
        bleeding = st.number_input("出血・ドレーン等 (mL)", 0, 5000, 0)
        s_type = st.selectbox("便性状", ["普通", "軟便", "下痢"])
        s_vol = st.number_input("便重量 (g)", 0, 1000, 150)
        stool = s_vol * (0.75 if s_type=="普通" else 0.85 if s_type=="軟便" else 0.95)

    # 不感蒸泄計算（補正あり）
    insensible = 15 * weight
    if temp > 37: insensible *= (1 + 0.15 * (temp - 37))
    if r_temp > 30: insensible *= (1 + 0.175 * (r_temp - 30))

    total_in = oral + iv + blood + metabolic
    total_out = urine + bleeding + stool + insensible
    net_bal = total_in - total_out

    # 3. 分析結果表示
    st.markdown('<div class="report-header-box"><h4>2. 分析結果</h4></div>', unsafe_allow_html=True)
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

    # 4. PDFダウンロード
    st.markdown("---")
    if st.button("📝 医療レポート(PDF)を生成"):
        report_data = {
            "age": age, "weight": weight, "temp": temp, "room_temp": r_temp,
            "oral": oral, "iv": iv, "blood": blood, "metabolic": metabolic,
            "urine": urine, "bleeding": bleeding, "stool": stool, "insensible": insensible,
            "net": net_bal, "judgment": judg, "recorder": recorder
        }
        pdf = generate_medical_report(report_data)
        st.download_button(label="📥 レポートをダウンロード", data=pdf, 
                           file_name=f"Report_{get_jst_now().strftime('%Y%m%d')}.pdf", mime="application/pdf")

# ================================
# 5. 推算根拠ページ
# ================================
else:
    st.title("📖 推算根拠（計算式）")
    st.info("2026年現在の一般的な臨床指標に基づいています。")
    
    st.subheader("1. 代謝水 (Metabolic Water)")
    st.latex(r"5 \, \text{mL} \times \text{Weight(kg)}")
    
    st.subheader("2. 不感蒸泄 (Insensible Water)")
    st.latex(r"15 \, \text{mL} \times \text{Weight(kg)} \times \text{補正係数}")
    st.write("**体温補正:** 37℃以上で1℃につき+15%")
    st.write("**室温補正:** 30℃以上で1℃につき+17.5%")
    
    st.subheader("3. 便中水分率")
    st.write("・普通便: 75% / ・軟便: 85% / ・下痢: 95%")
    
    st.subheader("4. 判定基準 (24時間)")
    st.table({
        "判定": ["体液過剰", "維持範囲", "脱水リスク"],
        "しきい値": ["> +500 mL", "-200 ～ +500 mL", "< -200 mL"]
    })
