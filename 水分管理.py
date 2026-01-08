import streamlit as st
import datetime
from io import BytesIO

# PDF生成用ライブラリ
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ================================
# 1. ページ基本設定
# ================================
st.set_page_config(
    page_title="水分出納バランス管理アプリ",
    layout="wide"
)

# Google翻訳除外設定とカスタムスタイル
st.markdown(
    """
    <meta name="google" content="notranslate">
    <style>
        html { notranslate: google; }
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True
)

# ================================
# 2. ロジック関数（計算・PDF生成）
# ================================

def estimate_body_water(age: int) -> float:
    """年齢に基づき体水分率(%)を推定する"""
    if age <= 1:
        return 80 - (age / 1) * 10
    elif age <= 13:
        return 70 - ((age - 1) / 12) * 10
    elif age <= 65:
        return 60 - ((age - 13) / 52) * 10
    else:
        return 50

# 日本語フォント（標準的な明朝体）を登録
try:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
except Exception:
    pass # フォント登録に失敗しても処理は続行

def generate_pdf_report(
    age, weight, temp, room_temp,
    body_water_percent, body_total_water,
    oral, iv, blood_transfusion, total_in,
    urine, bleeding, stool_loss, total_out,
    insensible, metabolic_water,
    net_balance, judgment,
    recorder
):
    """入力データからPDFファイルを生成する"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    today = datetime.date.today().strftime("%Y-%m-%d")

    # タイトル
    c.setFont("HeiseiMin-W3", 16)
    c.drawString(20*mm, 280*mm, "水分出納バランスレポート")
    c.setFont("HeiseiMin-W3", 10)
    c.drawString(20*mm, 275*mm, f"作成日: {today}    記録者: {recorder if recorder else '（未入力）'}")

    y = 265

    # ヘルパー関数
    def section(title):
        nonlocal y
        c.setFont("HeiseiMin-W3", 12)
        c.drawString(20*mm, y*mm, f"■ {title}")
        y -= 7

    def row(label, value):
        nonlocal y
        c.setFont("HeiseiMin-W3", 11)
        c.drawString(25*mm, y*mm, f"{label}: {value}")
        y -= 6

    # 内容描画
    section("基本情報")
    row("年齢", f"{age} 歳")
    row("体重", f"{weight:.1f} kg")
    row("体温", f"{temp:.1f} ℃")
    row("室温", f"{room_temp:.1f} ℃")
    row("推定体水分率", f"{body_water_percent:.1f} %")
    row("推定総体水分量", f"{body_total_water:.1f} L")

    section("In（摂取量）")
    row("経口摂取量", f"{oral:.0f} mL/day")
    row("点滴・輸液量", f"{iv:.0f} mL/day")
    row("輸血量", f"{blood_transfusion:.0f} mL/day")
    row("合計 In", f"{total_in:.0f} mL/day")

    section("Out（排泄量）")
    row("尿量", f"{urine:.0f} mL/day")
    row("出血量", f"{bleeding:.0f} mL/day")
    row("便による水分損失", f"{stool_loss:.0f} mL/day")
    row("合計 Out", f"{total_out:.0f} mL/day")

    section("不感蒸泄・代謝水")
    row("不感蒸泄 推定値", f"{insensible:.0f} mL/day")
    row("代謝水 推定値", f"{metabolic_water:.0f} mL/day")

    section("水分バランス評価")
    row("水分バランス", f"{net_balance:.0f} mL/day")
    row("総合判定", judgment)

    y -= 10
    c.setFont("HeiseiMin-W3", 9)
    c.drawString(20*mm, y*mm, "※本レポートは推定値に基づく参考資料です。診断・治療は必ず臨床症状を優先してください。")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ================================
# 3. UI表示（入力・計算）
# ================================

st.title("水分出納バランス管理アプリ")
st.caption("生活・医療・看護で利用できる実用的な水分管理・評価ツール")

st.markdown("## 基本情報")
col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)
with col_p1:
    age = st.number_input("年齢 (歳)", 0, 120, 35)
with col_p2:
    weight = st.number_input("体重 (kg)", 1.0, 300.0, 50.0)
with col_p3:
    temp = st.number_input("体温 (℃)", 30.0, 42.0, 36.5, 0.1)
with col_p4:
    room_temp = st.number_input("室温 (℃)", 10.0, 40.0, 25.0)
with col_p5:
    recorder = st.text_input("記録者（任意）", value="")

body_water_percent = estimate_body_water(age)
body_total_water = weight * (body_water_percent / 100)

info_col1, info_col2 = st.columns(2)
with info_col1:
    st.info(f"推定体水分率：**{body_water_percent:.1f}%**")
with info_col2:
    st.info(f"推定総体水分量：**{body_total_water:.1f} L**")

st.markdown("## 入出量の記録")
col_in, col_out = st.columns(2)

# Intake
with col_in:
    st.markdown("### In（摂取量）")
    oral = st.number_input("経口摂取量 (mL/day)", 0, 10000, 2000, 50)
    iv = st.number_input("点滴・輸液量 (mL/day)", 0, 10000, 0, 50)
    blood_transfusion = st.number_input("輸血量 (mL/day)", 0, 5000, 0, 50)
    total_in = oral + iv + blood_transfusion
    st.markdown(f"**合計 In： {total_in:.0f} mL/day**")

# Output
with col_out:
    st.markdown("### Out（排泄量）")
    st.markdown("#### 尿量計算")
    urine_times = st.number_input("排尿回数（回/日）", 0, 30, 5)
    # 1回尿量のデフォルトを体重から推定 (200-400ml)
    est_per_void = min(max(200 + (weight / 10 * 20), 200), 400)
    per_void = st.number_input("1回あたりの尿量 (mL)", 0, 1000, int(est_per_void), 10)
    urine = urine_times * per_void
    st.write(f"1日予測尿量： **{urine:.0f} mL/day**")

    bleeding = st.number_input("出血量 (mL/day)", 0, 5000, 0, 10)
    
    st.markdown("#### 便の水分")
    stool_weight = st.number_input("1日の便量 (g/day)", 0, 2000, 150, 10)
    stool_type = st.selectbox("便性状", ["正常便（成形）", "軟便（泥状）", "下痢（水様）"])
    stool_ratio = {"正常便（成形）": 0.75, "軟便（泥状）": 0.85, "下痢（水様）": 0.90}[stool_type]
    stool_loss = stool_weight * stool_ratio
    
    total_out = urine + bleeding + stool_loss
    st.markdown(f"**合計 Out： {total_out:.0f} mL/day**")

# 自動計算（不感蒸泄・代謝水）
# 不感蒸泄：標準15ml/kg、37度以上で1度につき15%増、室温30度以上で1度につき17.5%増
insensible = 15 * weight
if temp > 37:
    insensible *= (1 + 0.15 * (temp - 37))
if room_temp > 30:
    insensible *= (1 + 0.175 * (room_temp - 30))

metabolic_water = 5 * weight

# ================================
# 4. 結果表示
# ================================
st.markdown("---")
st.markdown("## 水分出納バランス評価結果")

net_balance = total_in - total_out - insensible + metabolic_water

r1, r2, r3, r4 = st.columns(4)
r1.metric("総 In", f"{total_in:.0f} mL")
r2.metric("総 Out (尿/便/血)", f"{total_out:.0f} mL")
r3.metric("不感蒸泄(推定)", f"{insensible:.0f} mL")
r4.metric("代謝水(推定)", f"{metabolic_water:.0f} mL")

st.subheader(f"1日の水分バランス： **{net_balance:.0f} mL/day**")

if net_balance > 700:
    st.error("【判定】バランスが大きくプラス：体液過剰、心不全・腎不全の悪化に注意。")
    judgment = "体液過剰の可能性（+700 mL超）"
elif net_balance > 300:
    st.warning("【判定】ややプラス：通常の成人では許容範囲。浮腫・呼吸状態を観察。")
    judgment = "ややプラス（+300〜700 mL）"
elif -200 <= net_balance <= 300:
    st.success("【判定】適正範囲：臨床症状と併せて経過観察。")
    judgment = "ほぼ適正範囲（-200〜+300 mL）"
else:
    st.error("【判定】マイナス：脱水リスクあり。口渇・皮膚ツルゴール・尿量を評価。")
    judgment = "脱水リスクあり（-200 mL未満）"

# ================================
# 5. PDF レポート生成ボタン（最下部）
# ================================
st.markdown("---")
st.markdown("### レポート出力")

if st.button("PDFレポートを作成"):
    # ここで上部の定義済み関数を呼び出す
    pdf_buffer = generate_pdf_report(
        age, weight, temp, room_temp,
        body_water_percent, body_total_water,
        oral, iv, blood_transfusion, total_in,
        urine, bleeding, stool_loss, total_out,
        insensible, metabolic_water,
        net_balance, judgment,
        recorder
    )

    st.success("PDFが正常に作成されました。")
    st.download_button(
        label="📄 PDFファイルをダウンロード",
        data=pdf_buffer,
        file_name=f"water_balance_{datetime.date.today()}.pdf",
        mime="application/pdf"
    )
