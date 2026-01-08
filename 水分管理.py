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
# 0. タイムゾーン設定
# ================================
def get_jst_now():
    return datetime.datetime.now(pytz.timezone("Asia/Tokyo"))

# ================================
# 1. ページ基本設定
# ================================
st.set_page_config(page_title="水分出納管理システム", layout="wide")

st.markdown("""
<style>
/* IN / OUT 見出し専用（ダークモード完全対応） */
.section-header {
    background-color: rgba(30, 30, 30, 0.85);
    color: #F5F5F5 !important;
    padding: 0.6em 0.8em;
    border-radius: 0.6em;
    font-weight: 700;
    font-size: 1.05rem;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.25);
}

/* ライトモード補正 */
@media (prefers-color-scheme: light) {
    .section-header {
        background-color: #F1F3F6;
        color: #111111 !important;
        border: 1px solid #D0D4DA;
    }
}
</style>
""", unsafe_allow_html=True)


# ================================
# session_state 初期化（必須）
# ================================
if "u_times" not in st.session_state:
    st.session_state.u_times = 5

if "u_vol" not in st.session_state:
    st.session_state.u_vol = 250

if "s_vol" not in st.session_state:
    st.session_state.s_vol = 150

if "show_urine_dialog" not in st.session_state:
    st.session_state.show_urine_dialog = False

if "show_stool_dialog" not in st.session_state:
    st.session_state.show_stool_dialog = False

if "weight" not in st.session_state:
    st.session_state.weight = 60.0



# ================================
# 尿量推算ダイアログ（定義だけ）
# ================================
@st.dialog("🚻 標準尿量の推算（体重補正）")
def urine_dialog():
    weight = st.session_state.get("weight", 60.0)

    std_type = st.selectbox(
        "評価基準を選択",
        ["正常（20 mL/kg/day）", "少尿境界（10 mL/kg/day）", "多尿境界（40 mL/kg/day）"]
    )

    coef = 20 if "20" in std_type else 10 if "10" in std_type else 40
    std_urine = coef * weight
    est_u_vol = std_urine / max(st.session_state.u_times, 1)

    st.info(f"推算24時間尿量：{std_urine:.0f} mL/day\n1回尿量：約 {est_u_vol:.0f} mL")

    c_ok, c_ng = st.columns(2)
    if c_ok.button("✅ 入力に反映"):
        st.session_state.u_vol = int(est_u_vol)
        st.session_state.show_urine_dialog = False
        st.rerun()
    if c_ng.button("❌ キャンセル"):
        st.session_state.show_urine_dialog = False
        st.rerun()

        


# ================================
# 便量推算ダイアログ（定義だけ）
# ================================
@st.dialog("標準的な便量の推算（体重・状態別）")
def stool_dialog():
    weight = st.session_state.get("weight", 60.0)
    condition = st.selectbox(
        "状態・疾患区分",
        [
            "標準（健康時）",
            "軟便",
            "下痢",
            "発熱・感染症",
            "経腸栄養中",
            "便秘傾向"
        ]
    )

    factor_table = {
        "標準（健康時）": 1.0,
        "軟便": 1.5,
        "下痢": 3.0,
        "発熱・感染症": 1.3,
        "経腸栄養中": 1.8,
        "便秘傾向": 0.6
    }

    est_stool = 2.0 * weight * factor_table[condition]
    st.metric("推算便重量（1日）", f"{est_stool:.0f} g")

    col_ok, col_ng = st.columns(2)
    if col_ok.button("入力に反映"):
        st.session_state.s_vol = int(est_stool)
        st.session_state.show_stool_dialog = False
        st.rerun()

    if col_ng.button("キャンセル"):
        st.session_state.show_stool_dialog = False
        st.rerun()

st.markdown("""
<style>
.report-header-box {
    background-color: #e9ecef;
    padding: 10px 20px;
    border-radius: 8px;
    border-left: 6px solid #007bff;
    margin: 20px 0;
}
.report-header-box h4 { margin: 0; }
div.stButton > button {
    border-radius: 10px;
    font-weight: bold;
    height: 3em;
}
[data-testid="stMetricValue"] { color: #007bff; }
</style>
""", unsafe_allow_html=True)

# ================================
# 2. PDF設定
# ================================
try:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
except:
    pass

def generate_medical_report(data):
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    room_temp = data.get("room_temp", data.get("r_temp", 0))

    # ================================
    # タイトル
    # ================================
    c.setFont("HeiseiMin-W3", 18)
    c.drawCentredString(w / 2, h - 20 * mm, "水分出納管理報告書（サマリー）")

    c.setFont("HeiseiMin-W3", 10)
    c.drawString(20 * mm, h - 30 * mm, f"記録日時：{get_jst_now().strftime('%Y/%m/%d %H:%M')}")
    c.drawRightString(w - 20 * mm, h - 30 * mm, f"記録者：{data.get('recorder', '未記入')}")

    y = h - 42 * mm

    # ================================
    # 【基本情報】（箇条書き）
    # ================================
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20 * mm, y, "【基本情報】")
    y -= 6 * mm

    c.setFont("HeiseiMin-W3", 10)
    c.drawString(25 * mm, y, f"・年齢：{data['age']} 歳")
    y -= 5 * mm
    c.drawString(25 * mm, y, f"・体重：{data['weight']:.1f} kg")
    y -= 5 * mm
    c.drawString(25 * mm, y, f"・体温：{data['temp']:.1f} ℃")
    y -= 5 * mm
    c.drawString(25 * mm, y, f"・室温：{room_temp:.1f} ℃")

    y -= 8 * mm

    # ================================
    # 【入出量内訳】（IN/OUT 横並び・合計行付き）
    # ================================
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(20 * mm, y, "【入出量内訳】")
    y -= 6 * mm

    total_in = (
        data["oral"]
        + data["iv"]
        + data["blood"]
        + data["metabolic"]
    )
    total_out = (
        data["urine"]
        + data["bleeding"]
        + data["stool"]
        + data["insensible"]
    )

    io_table = Table(
        [
            ["IN（流入）", "", "OUT（流出）", ""],
            ["経口摂取", f"{data['oral']} mL", "尿量", f"{data['urine']} mL"],
            ["静脈輸液", f"{data['iv']} mL", "出血等", f"{data['bleeding']} mL"],
            ["輸血", f"{data['blood']} mL", "便中水分", f"{data['stool']:.0f} mL"],
            ["代謝水", f"{data['metabolic']:.0f} mL", "不感蒸泄", f"{data['insensible']:.0f} mL"],
            ["合計", f"{total_in:.0f} mL", "合計", f"{total_out:.0f} mL"],
        ],
        colWidths=[38 * mm, 32 * mm, 38 * mm, 32 * mm]
    )

    io_table.setStyle(TableStyle([
        # 見出し上下罫線
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.black),

        # 合計行の強調（上罫線＋下罫線）
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),

        # IN / OUT 境界線
        ("LINEBEFORE", (2, 0), (2, -1), 0.8, colors.black),

        # フォント
        ("FONT", (0, 0), (-1, 0), "HeiseiMin-W3", 10),
        ("FONT", (0, 1), (-1, -2), "HeiseiMin-W3", 10),
        ("FONT", (0, -1), (-1, -1), "HeiseiMin-W3", 10),

        # 配置
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    table_width, table_height = io_table.wrap(w - 40 * mm, h)
    io_table.drawOn(c, 20 * mm, y - table_height)
    y -= table_height + 10 * mm

    # ================================
    # 【判定】（薄いグレー帯）
    # ================================
    band_height = 14 * mm
    c.setFillColor(colors.whitesmoke)
    c.rect(20 * mm, y - band_height, w - 40 * mm, band_height, fill=1, stroke=0)

    c.setFillColor(colors.black)
    c.setFont("HeiseiMin-W3", 12)
    c.drawString(22 * mm, y - 5 * mm, "【判定】")

    c.setFont("HeiseiMin-W3", 14)
    c.drawRightString(
        w - 22 * mm,
        y - 5 * mm,
        f"ネットバランス： {data['net']:+.0f} mL / day"
    )

    y -= band_height + 4 * mm

    c.setFont("HeiseiMin-W3", 11)
    c.drawString(25 * mm, y, f"評価： {data['judgment']}")

    y -= 10 * mm

    # ================================
    # 注意書き
    # ================================
    c.setFont("HeiseiMin-W3", 9)
    c.drawString(
        20 * mm, y,
        "※本報告書は水分出納管理の補助を目的としたものであり、"
        "最終的な臨床判断は医師が行ってください。"
    )

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ================================
# 3. ページ状態管理
# ================================
if "page" not in st.session_state:
    st.session_state.page = "main"

# ================================
# 4. タブ風ナビゲーション
# ================================
b1, b2, b3, b4 = st.columns(4)

with b1:
    if st.button("🏠 メイン計算", use_container_width=True):
        st.session_state.page = "main"
with b2:
    if st.button("📖 推算根拠", use_container_width=True):
        st.session_state.page = "theory"
with b3:
    if st.button("🧭 使い方", use_container_width=True):
        st.session_state.page = "usage"
with b4:
    if st.button("📚 引用・参考文献", use_container_width=True):
        st.session_state.page = "refs"


st.markdown("---")

# ================================
# 5. メイン計算ページ
# ================================
if st.session_state.page == "main":

    # ================================
    # dialog 呼び出し（最上流）
    # ================================
    if st.session_state.page == "main":
    
        if st.session_state.show_urine_dialog:
            urine_dialog()
    
        if st.session_state.show_stool_dialog:
            stool_dialog()
    
        # ↓↓↓ ここから通常の UI ↓↓↓
        st.title("🏥 水分出納バランス記録")

    # ---- session_state 初期化 ----
    if "u_times" not in st.session_state:
        st.session_state.u_times = 5
    if "u_vol" not in st.session_state:
        st.session_state.u_vol = 250
    if "s_vol" not in st.session_state:
        st.session_state.s_vol = 150
    if "show_urine_dialog" not in st.session_state:
        st.session_state.show_urine_dialog = False
    if "show_stool_dialog" not in st.session_state:
        st.session_state.show_stool_dialog = False

    # ---- 基本情報 ----
    c1, c2, c3, c4, c5 = st.columns(5)
    age = c1.number_input("年齢", 0, 120, 20)
    weight = st.number_input(
        "体重(kg)",
        1.0,
        200.0,
        step=0.1,
        key="weight"
    )
    temp = c3.number_input("体温(℃)", 34.0, 42.0, 36.5, 0.1)
    r_temp = c4.number_input("室温(℃)", 10.0, 40.0, 24.0, 0.5)
    recorder = c5.text_input("記録者")

    # ---- IN / OUT ----
    col_in, col_out = st.columns(2)

    with col_in:
        st.markdown("### 💧 IN（摂取・流入）")
        st.markdown("---")

        oral = st.number_input("経口摂取(mL) ※酒類・カフェイン飲料を除く", 0, 10000, 1500, 50)
        iv = st.number_input("静脈輸液(mL) ※医療機関で実施", 0, 10000, 0, 50)
        blood = st.number_input("輸血(mL) ※医療機関で実施", 0, 5000, 0, 50)
        metabolic = 5 * weight

    with col_out:
        st.markdown("### 🚻 OUT（排出・喪失）")
        st.markdown("---")

        # 排尿回数
        st.session_state.u_times = st.number_input(
            "排尿回数",
            0,
            20,
            st.session_state.u_times
        )

        # 1回尿量（左）＋ 推算ボタン（右）
        ucol_l, ucol_r = st.columns([3, 2])

        with ucol_l:
            st.session_state.u_vol = st.number_input(
                "1回尿量(mL)",
                0,
                1000,
                st.session_state.u_vol
            )

        with ucol_r:
            st.markdown("###### ")
            if st.button("📐 標準尿量から推算", use_container_width=True):
                st.session_state.show_urine_dialog = True

        bleeding = st.number_input("出血等(mL)", 0, 5000, 0)

        # ---- 便量（実測＋推算） ----
        scol_l, scol_r = st.columns([3, 2])

        with scol_l:
            st.session_state.s_vol = st.number_input(
                "便重量(g)",
                0,
                1000,
                st.session_state.s_vol
            )

        with scol_r:
            st.markdown("###### ")
            if st.button("📐 標準便量から推算", use_container_width=True):
                st.session_state.show_stool_dialog = True

        s_type = st.selectbox("便性状", ["普通", "軟便", "下痢"])


    # ---- 尿量・便量の確定計算（必ず定義） ----
    urine = st.session_state.u_times * st.session_state.u_vol

    stool = st.session_state.s_vol * (
        0.75 if s_type == "普通"
        else 0.85 if s_type == "軟便"
        else 0.95
    )

    # ---- 不感蒸泄 ----
    insensible = 15 * weight
    if temp > 37:
        insensible *= (1 + 0.15 * (temp - 37))
    if r_temp > 30:
        insensible *= (1 + 0.175 * (r_temp - 30))

    # ---- 集計 ----
    total_in = oral + iv + blood + metabolic
    total_out = urine + bleeding + stool + insensible
    net = total_in - total_out

    m1, m2, m3 = st.columns(3)
    m1.metric("総IN", f"{total_in:.0f} mL")
    m2.metric("総OUT", f"{total_out:.0f} mL")
    m3.metric("バランス", f"{net:+.0f} mL")

    # ---- 判定 ----
    if net > 500:
        judg = "体液過剰の傾向"
        st.error(judg)
    elif net < -200:
        judg = "脱水リスク"
        st.warning(judg)
    else:
        judg = "維持範囲"
        st.success(judg)

    # ---- PDF ----
    if st.button("📝 PDF生成"):
        report_data = {
            "age": age,
            "weight": weight,
            "temp": temp,
            "room_temp": r_temp,
            "oral": oral,
            "iv": iv,
            "blood": blood,
            "metabolic": metabolic,
            "urine": urine,
            "bleeding": bleeding,
            "stool": stool,
            "insensible": insensible,
            "net": net,
            "judgment": judg,
            "recorder": recorder
        }

        pdf = generate_medical_report(report_data)
        st.download_button("📥 ダウンロード", pdf, "fluid_balance.pdf")

        stool_dialog() 

# ================================
# ダークモード対応CSS
# ================================
    st.markdown("""
    <style>
    /* 共通 */
    .report-header-box {
        padding: 0.5em 1em;
        border-left: 6px solid;
        margin: 1.5em 0 0.5em 0;
        border-radius: 4px;
    }
    
    /* ライトモード */
    @media (prefers-color-scheme: light) {
        .report-header-box {
            background-color: #f2f2f2;
            border-color: #2c7be5;
            color: #000000;
        }
    }
    
    /* ダークモード */
    @media (prefers-color-scheme: dark) {
        .report-header-box {
            background-color: #2b2b2b;
            border-color: #6ea8fe;
            color: #ffffff;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ================================
# 推算根拠ページ
# ================================
elif st.session_state.page == "theory":
    st.title("📖 水分出納の推算根拠と判定基準")
    
    st.info(
        "本プログラムで使用している各種推算式は以下の通りです。"
        "これらは臨床現場で一般的に用いられる指標に基づいています。"
    )

    # 1. 入出量合計の算出式
    st.markdown(
        '<h4 class="report-header">1. 入出量合計の算出式</h4>',
        unsafe_allow_html=True
    )

    st.write("**■ 総 Intake (総流入量)**")
    st.latex(r"\text{総IN} = \text{経口摂取(経管)} + \text{静脈輸液} + \text{輸血製剤} + \text{代謝水}")
    
    st.write("**■ 総 Output (総流出量)**")
    st.latex(r"\text{総OUT} = \text{尿量} + \text{出血・ドレーン等} + \text{便中水分} + \text{不感蒸泄}")
    
    st.write("**■ ネットバランス (Net Balance)**")
    st.latex(r"\text{バランス} = \text{総IN} - \text{総OUT}")

    # 2. 各項目の推算根拠
    st.markdown(
        '<h4 class="report-header">2. 各項目の推算根拠</h4>',
        unsafe_allow_html=True
    )
    
    st.markdown("##### ① 代謝水 (Metabolic Water)")
    st.write("栄養素が体内で燃焼（酸化）される際に生成される水分です。")
    st.latex(r"\text{算出式: } 5\,\text{mL} \times \text{体重(kg)}")
    st.caption(
        "根拠: 通常、成人では1日あたり約200〜300mL（約5mL/kg）程度とされています。"
    )

    st.markdown("##### ② 不感蒸泄 (Insensible Water Loss)")
    st.write(
        "呼気や皮膚から自覚なしに失われる水分です。"
        "体温や周囲の温度によって変動します。"
    )
    st.latex(r"\text{基本式: } 15\,\text{mL} \times \text{体重(kg)}")
    
    st.write("**・発熱補正:** 体温が37℃を超える場合、1℃上昇につき15%増加させます。")
    st.latex(r"\text{補正係数} = 1.0 + 0.15 \times (\text{体温} - 37)")
    
    st.write("**・室温補正:** 室温が30℃を超える場合、1℃上昇につき17.5%増加させます。")
    st.latex(r"\text{補正係数} = 1.0 + 0.175 \times (\text{室温} - 30)")

    st.markdown("##### ③ 便中水分")
    st.write("便の性状（水分含有率）に基づき、重量から水分量を推定します。")
    st.write("- **普通便:** $重量(g) \\times 0.75$")
    st.write("- **軟便:** $重量(g) \\times 0.85$")
    st.write("- **下痢:** $重量(g) \\times 0.95$")

    st.markdown("##### ④ 推定体水分率 (Total Body Water %)")
    st.write("加齢に伴う細胞内液の減少を考慮した推算式です。")
    st.write("- **乳児(0-1歳):** 80%から月齢に応じて減少")
    st.write("- **幼児・学童(1-13歳):** 70%から年齢に応じて減少")
    st.write("- **成人(14-65歳):** 60%から年齢に応じて減少")
    st.write("- **高齢者(65歳以上):** 一律 50%")

    # 3. 判定基準
    st.markdown(
        '<h4 class="report-header">3. 2026年現在の臨床的判定基準</h4>',
        unsafe_allow_html=True
    )


    st.write(
        "本システムでは、24時間あたりのネットバランスに基づき以下の判定を行っています。"
    )
    
    st.table([
        {
            "バランス結果": "+500 mL 超",
            "判定": "体液過剰 (Overhydration)",
            "臨床的リスク": "心不全増悪、浮腫、肺水腫のリスク"
        },
        {
            "バランス結果": "-200 ～ +500 mL",
            "判定": "維持範囲 (Maintenance)",
            "臨床的リスク": "生理的許容範囲"
        },
        {
            "バランス結果": "-200 mL 未満",
            "判定": "脱水リスク (Dehydration)",
            "臨床的リスク": "腎不全（乏尿）、循環不全、血圧低下のリスク"
        }
    ])

    st.warning("""
**※これらの数値はあくまで目安です。**  
2026年1月9日現在の臨床ガイドラインに則り、実際の診断には
血清ナトリウム値、心エコー、皮膚緊張度（ツルゴール）等の
身体所見を併せて評価する必要があります。
""")


elif st.session_state.page == "usage":
    st.title("🧭 使い方（シーン別）")
    st.info("本アプリは医療・看護・生活・学校など、複数の現場で共通に利用できる水分出納整理ツールです。")

    usage_table = [
        {
            "利用シーン": "医療（病棟・外来）",
            "主な対象": "入院患者・発熱患者",
            "入力のポイント": "輸液量・尿量・発熱の有無を正確に",
            "判定の見方": "体液過剰／脱水リスクの傾向把握",
            "活用例": "回診前サマリー、PDF記録"
        },
        {
            "利用シーン": "看護",
            "主な対象": "水分管理が必要な患者",
            "入力のポイント": "概算入力でも可、傾向重視",
            "判定の見方": "前日との差・IN/OUT対照",
            "活用例": "申し送り、患者説明"
        },
        {
            "利用シーン": "生活・家庭",
            "主な対象": "高齢者・体調不良時",
            "入力のポイント": "飲水量・排尿回数を簡易入力",
            "判定の見方": "不足・過剰の気づき",
            "活用例": "受診判断の参考"
        },
        {
            "利用シーン": "学校（保健・授業）",
            "主な対象": "児童・生徒",
            "入力のポイント": "体重・室温・活動量",
            "判定の見方": "熱中症リスクの可視化",
            "活用例": "保健指導、教材"
        },
        {
            "利用シーン": "運動・部活動",
            "主な対象": "競技者・部活動生徒",
            "入力のポイント": "運動前後の水分量",
            "判定の見方": "補給不足の確認",
            "活用例": "飲水計画の立案"
        },
    ]

    st.subheader("📋 利用シーン別一覧")
    st.table(usage_table)



# ================================
# 引用・参考文献ページ
# ================================
elif st.session_state.page == "refs":
    st.title("📚 引用・参考文献")
    
    st.info(
        "本システムの計算式および判定基準は、以下の公的機関・学会等の資料に基づき作成されています。"
    )

    # 1. 公的ガイドライン・基準
    st.markdown(
        '<h4 class="report-header">1. 公的ガイドライン・基準</h4>',
        unsafe_allow_html=True
    )

    
    st.markdown("""
- **[厚生労働省：日本人の食事摂取基準（2025年版）](https://www.mhlw.go.jp)**  
  *水分の必要量や代謝水の生成根拠となる栄養素の酸化プロセスに関する標準的な数値が記載されています。*

- **[環境省：熱中症環境保健マニュアル](https://www.wbgt.env.go.jp)**  
  *室温・外気温上昇に伴う不感蒸泄および発汗量の増加に関する知見がまとめられています。*
    """)

    # 2. 臨床医学的エビデンス
    st.markdown(
        '<h4 class="report-header">2. 臨床医学的エビデンス</h4>',
        unsafe_allow_html=True
    )

    
    st.markdown("""
- **[MSDマニュアル プロフェッショナル版：水分平衡](https://www.msdmanuals.com)**  
  *世界共通の臨床基準として、不感蒸泄（10〜15mL/kg/day）や、体温上昇に伴う損失増（1℃につき10〜15%）の根拠となります。*

- **[一般社団法人 日本臨床栄養代謝学会（JSPEN）：ガイドライン](https://www.jspen.or.jp)**  
  *臨床現場における水・電解質管理の最新の国内ガイドラインを確認できます。*
    """)

    # 3. 文献検索（最新知見）
    st.markdown(
        '<h4 class="report-header">3. 文献検索（最新知見）</h4>',
        unsafe_allow_html=True
    )

    
    st.markdown("""
- **[CiNii Research（日本の論文検索：水分出納）](https://cinii.clear.ndl.go.jp)**  
  *本システムで採用している各係数（15mL/kg/day 等）の妥当性を検証した最新の論文を検索可能です。*
    """)

    st.warning("""
**臨床現場での利用にあたって**  
2026年現在の医学的知見に基づき構成されていますが、臨床的な最終判断は  
患者個別の身体所見（血圧、浮腫、血清Na値等）に基づき、医師が行ってください。
""")












