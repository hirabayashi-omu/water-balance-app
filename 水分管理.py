import streamlit as st
import datetime

# ================================
#  ページ設定
# ================================
st.set_page_config(
    page_title="水分出納バランス管理アプリ",
    layout="wide"
)

st.markdown(
    """
    <meta name="google" content="notranslate">
    <style>
        html { notranslate: google; }
        .report-title {
            font-size: 1.4rem;
            font-weight: 600;
        }
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 1rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("水分出納バランス管理アプリ")
st.caption("生活・医療・看護で利用できる実用的な水分管理・評価ツール")

# ================================
#  関数：年齢 → 体水分量（％）の線形近似
# ================================
def estimate_body_water(age: int) -> float:
    if age <= 1:
        return 80 - (age / 1) * 10          # 0〜1歳：80→70%
    elif age <= 13:
        return 70 - ((age - 1) / 12) * 10   # 1〜13歳：70→60%
    elif age <= 65:
        return 60 - ((age - 13) / 52) * 10  # 13〜65歳：60→50%
    else:
        return 50                           # 65歳以上：固定50%

# ================================
#  0. 基本情報・作成者情報
# ================================
st.markdown("## 基本情報")

col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)

with col_p1:
    age = st.number_input(
        "年齢 (歳)",
        min_value=0,
        max_value=120,
        value=35,
        help="0〜1歳：体水分率が高く脱水進行が速い／高齢者：体水分率が低く脱水リスクが高い。"
    )
with col_p2:
    weight = st.number_input(
        "体重 (kg)",
        min_value=1.0,
        value=50.0,
        help="推定体水分量や不感蒸泄・代謝水の計算に使用します。"
    )
with col_p3:
    temp = st.number_input(
        "体温 (℃)",
        min_value=30.0,
        max_value=42.0,
        value=36.5,
        step=0.1,
        help="37℃以上で不感蒸泄が増加します。発熱時は特に注意してください。"
    )
with col_p4:
    room_temp = st.number_input(
        "室温 (℃)",
        min_value=10.0,
        max_value=40.0,
        value=25.0,
        help="30℃以上で環境による不感蒸泄が増加します。"
    )
with col_p5:
    recorder = st.text_input(
        "記録者（氏名・IDなど）",
        value="",
        help="PDF レポートに記載されます（任意）。"
    )

# 年齢に基づく体水分率
body_water_percent = estimate_body_water(age)
body_total_water = weight * (body_water_percent / 100)

info_col1, info_col2 = st.columns(2)
with info_col1:
    st.info(f"推定体水分率：**{body_water_percent:.1f}%**")
with info_col2:
    st.info(f"推定総体水分量：**{body_total_water:.1f} L**")

# ================================
#  1. In / Out 入力（臨床ワークフローに合わせて）
# ================================
st.markdown("## 入出量の記録")

col_in, col_out = st.columns(2)

# ---------- In ----------
with col_in:
    st.markdown("### In（摂取量）")

    oral = st.number_input(
        "経口摂取量 (mL/day)",
        min_value=0,
        value=2500,
        step=50,
        help="水・お茶・経口補水液など。アルコール・カフェイン飲料は除いて入力してください。"
    )
    iv = st.number_input(
        "点滴・輸液量 (mL/day)",
        min_value=0,
        value=0,
        step=50,
        help="維持輸液・補正輸液・栄養輸液など、全ての静脈輸液量の合計。"
    )
    blood_transfusion = st.number_input(
        "輸血量 (mL/day)",
        min_value=0,
        value=0,
        step=50,
        help="赤血球製剤・FFP・アルブミン製剤などの輸液量としてカウント。"
    )

    total_in = oral + iv + blood_transfusion
    st.markdown(f"**合計 In： {total_in:.0f} mL/day**")

# ---------- Out ----------
with col_out:
    st.markdown("### Out（排泄量）")

    st.markdown("#### 尿量")
    urine_times = st.number_input(
        "排尿回数（回/日）",
        min_value=0,
        value=4,
        help="おおよその回数でも構いません。"
    )

    estimated_per_void = 200 + (weight / 10 * 20)
    estimated_per_void = min(max(estimated_per_void, 200), 400)

    per_void = st.number_input(
        "1回あたりの尿量 (mL)",
        min_value=0,
        value=int(estimated_per_void),
        step=10,
        help="実測値があれば実測値を入力。なければ体重からの目安値（200〜400 mL）を使用。"
    )

    urine = urine_times * per_void
    st.write(f"1日尿量： **{urine:.0f} mL/day**")

    st.markdown("#### 出血")
    bleeding = st.number_input(
        "出血量 (mL/day)",
        min_value=0,
        value=0,
        step=10,
        help="術後ドレーン・月経・消化管出血など、1日の総出血量。"
    )

    st.markdown("#### 便による水分損失")
    stool_weight = st.number_input(
        "1日の便量 (g/day)",
        min_value=0,
        value=150,
        step=10,
        help="おおよその重量。下痢・軟便が続く場合は多めに見積もります。"
    )

    stool_type = st.selectbox(
        "便性状",
        ["正常便（成形）", "軟便（泥状）", "下痢（水様）"],
        help="便性状に応じて水分率を変えます。"
    )

    if stool_type == "正常便（成形）":
        stool_water_ratio = 0.75
    elif stool_type == "軟便（泥状）":
        stool_water_ratio = 0.85
    else:
        stool_water_ratio = 0.90

    stool_loss = stool_weight * stool_water_ratio
    st.write(f"便の水分損失： **{stool_loss:.0f} mL/day**")

    total_out = urine + bleeding + stool_loss
    st.markdown(f"**合計 Out： {total_out:.0f} mL/day**")

# ================================
#  2. 不感蒸泄・代謝水の計算
# ================================
st.markdown("## 不感蒸泄・代謝水（自動計算）")

insensible = 15 * weight  # 基本
if temp > 37:
    insensible *= 1 + 0.15 * (temp - 37)  # 発熱補正
if room_temp > 30:
    insensible *= 1 + 0.175 * (room_temp - 30)  # 高温環境補正

metabolic_water = 5 * weight

col_i1, col_i2 = st.columns(2)
with col_i1:
    st.write(f"不感蒸泄量： **{insensible:.0f} mL/day**")
with col_i2:
    st.write(f"代謝水（Out から差し引く）： **{metabolic_water:.0f} mL/day**")

# ================================
#  3. 水分バランスの結果
# ================================
st.markdown("---")
st.markdown("## 水分出納バランス結果")

net_balance = total_in - total_out - insensible + metabolic_water

col_r1, col_r2, col_r3, col_r4 = st.columns(4)
with col_r1:
    st.metric("総 In", f"{total_in:.0f} mL")
with col_r2:
    st.metric("総 Out", f"{total_out:.0f} mL")
with col_r3:
    st.metric("不感蒸泄", f"{insensible:.0f} mL")
with col_r4:
    st.metric("代謝水", f"{metabolic_water:.0f} mL")

st.subheader(f"水分バランス： **{net_balance:.0f} mL/day**")

# 判定メッセージ（医療者向けコメント）
if net_balance > 700:
    st.error("バランスが大きくプラス → 体液過剰の可能性。心不全・腎不全では特に注意が必要です。")
    judgment = "体液過剰の可能性（+700 mL/day 超）"
elif net_balance > 300:
    st.warning("ややプラス（通常の成人では許容範囲）。浮腫・呼吸状態の変化に注意して経過観察。")
    judgment = "ややプラス（+300〜700 mL/day）"
elif -200 <= net_balance <= 300:
    st.success("ほぼ適正範囲です。臨床症状と併せて経過観察。")
    judgment = "ほぼ適正範囲（-200〜+300 mL/day）"
else:
    st.error("マイナス → 脱水リスクあり。口渇・皮膚ツルゴール・尿量・血圧などを総合的に評価。")
    judgment = "脱水リスクあり（-200 mL/day 未満）"

st.info(
    """
    ### 判定の目安（総論）
    - 新生児：体水分量が多いため脱水進行が速い  
    - 高齢者：体水分量が低く脱水リスクが高い  
    - 健康成人：+500〜600 mL/day 程度で適正  
    - 発熱・高温環境：不感蒸泄が増加  
    - 心不全・腎不全：±0 〜 マイナスで管理  
    """
)

# ================================
#  4. PDF レポート生成（HTML ベース）
# ================================
st.markdown("---")
st.markdown("## PDF レポート出力")

st.caption("※ pdfkit + wkhtmltopdf を環境にインストールしておく必要があります。")

from io import BytesIO

def build_report_html():
    today = datetime.date.today().strftime("%Y-%m-%d")
    recorder_str = recorder if recorder.strip() != "" else "（未入力）"

    html = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 11pt;
            margin: 20px;
        }}
        h1 {{
            font-size: 18pt;
            text-align: center;
            margin-bottom: 10px;
        }}
        h2 {{
            font-size: 13pt;
            border-bottom: 1px solid #888;
            margin-top: 18px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 6px;
            margin-bottom: 6px;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 4px 6px;
            font-size: 10pt;
        }}
        th {{
            background-color: #f0f0f0;
        }}
        .right {{
            text-align: right;
        }}
        .small {{
            font-size: 9pt;
            color: #555;
        }}
    </style>
    </head>
    <body>
        <h1>水分出納バランスレポート</h1>
        <p class="small">作成日: {today}　記録者: {recorder_str}</p>

        <h2>1. 基本情報</h2>
        <table>
            <tr><th>年齢</th><td>{age} 歳</td></tr>
            <tr><th>体重</th><td>{weight:.1f} kg</td></tr>
            <tr><th>体温</th><td>{temp:.1f} ℃</td></tr>
            <tr><th>室温</th><td>{room_temp:.1f} ℃</td></tr>
            <tr><th>推定体水分率</th><td>{body_water_percent:.1f} %</td></tr>
            <tr><th>推定総体水分量</th><td>{body_total_water:.1f} L</td></tr>
        </table>

        <h2>2. In（摂取量）</h2>
        <table>
            <tr><th>項目</th><th class="right">量 (mL/day)</th></tr>
            <tr><td>経口摂取量</td><td class="right">{oral:.0f}</td></tr>
            <tr><td>点滴・輸液量</td><td class="right">{iv:.0f}</td></tr>
            <tr><td>輸血量</td><td class="right">{blood_transfusion:.0f}</td></tr>
            <tr><th>合計 In</th><th class="right">{total_in:.0f}</th></tr>
        </table>

        <h2>3. Out（排泄量）</h2>
        <table>
            <tr><th>項目</th><th class="right">量 (mL/day)</th></tr>
            <tr><td>尿量（回数×1回量）</td><td class="right">{urine:.0f}</td></tr>
            <tr><td>出血量</td><td class="right">{bleeding:.0f}</td></tr>
            <tr><td>便による水分損失</td><td class="right">{stool_loss:.0f}</td></tr>
            <tr><th>合計 Out</th><th class="right">{total_out:.0f}</th></tr>
        </table>

        <h2>4. 不感蒸泄・代謝水</h2>
        <table>
            <tr><th>項目</th><th class="right">量 (mL/day)</th></tr>
            <tr><td>不感蒸泄 推定値</td><td class="right">{insensible:.0f}</td></tr>
            <tr><td>代謝水 推定値</td><td class="right">{metabolic_water:.0f}</td></tr>
        </table>

        <h2>5. 水分バランス評価</h2>
        <table>
            <tr><th>総 In</th><td class="right">{total_in:.0f} mL/day</td></tr>
            <tr><th>総 Out</th><td class="right">{total_out:.0f} mL/day</td></tr>
            <tr><th>不感蒸泄</th><td class="right">{insensible:.0f} mL/day</td></tr>
            <tr><th>代謝水</th><td class="right">{metabolic_water:.0f} mL/day</td></tr>
            <tr><th>水分バランス</th><td class="right">{net_balance:.0f} mL/day</td></tr>
            <tr><th>総合判定</th><td>{judgment}</td></tr>
        </table>

        <p class="small">
        ※本レポートは簡易的な推定値に基づくものであり、診断・治療方針は必ず臨床症状・検査値・主治医の判断と総合して行ってください。
        </p>
    </body>
    </html>
    """
    return html


# 実際に PDF を生成してダウンロードする部分
generate_pdf = st.button("PDF レポートを生成してダウンロード")

if generate_pdf:
    try:
        import pdfkit

        html = build_report_html()
        # wkhtmltopdf がインストールされている前提
        pdf_bytes = pdfkit.from_string(html, False)

        st.download_button(
            label="PDF レポートをダウンロード",
            data=pdf_bytes,
            file_name="water_balance_report.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(
            "PDF 生成中にエラーが発生しました。サーバ側に `pdfkit` と `wkhtmltopdf` がインストールされているか確認してください。"
        )
        st.code(str(e))
