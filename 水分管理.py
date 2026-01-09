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
.section-header-in {
    background-color: rgba(30, 60, 100, 0.85); /* Blue-ish */
    color: #F0F8FF !important;
    padding: 0.6em 0.8em;
    border-radius: 0.6em;
    font-weight: 700;
    font-size: 1.05rem;
    text-align: center;
    border: 1px solid rgba(135, 206, 250, 0.25);
}

.section-header-out {
    background-color: rgba(100, 30, 30, 0.85); /* Red-ish */
    color: #FFF0F0 !important;
    padding: 0.6em 0.8em;
    border-radius: 0.6em;
    font-weight: 700;
    font-size: 1.05rem;
    text-align: center;
    border: 1px solid rgba(250, 128, 114, 0.25);
}

/* ライトモード補正 */
@media (prefers-color-scheme: light) {
    .section-header-in {
        background-color: #E3F2FD;
        color: #0d47a1 !important;
        border: 1px solid #BBDEFB;
    }
    .section-header-out {
        background-color: #FFEBEE;
        color: #b71c1c !important;
        border: 1px solid #FFCDD2;
    }
}
</style>
""", unsafe_allow_html=True)


# ================================
# 1. ダイアログ関数定義（最初に）
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
    est_u_vol = std_urine / max(st.session_state.get("u_times", 5), 1)

    st.info(f"推算24時間尿量：{std_urine:.0f} mL/day\n1回尿量：約 {est_u_vol:.0f} mL")

    c_ok, c_ng = st.columns(2)
    if c_ok.button("✅ 入力に反映"):
        # ウィジェットのキー("out_uvol")を更新してUIに反映させる
        st.session_state["out_uvol"] = int(est_u_vol)
        st.session_state.u_vol = int(est_u_vol)
        st.session_state.show_urine_dialog = False
        st.rerun()
    if c_ng.button("❌ キャンセル"):
        st.session_state.show_urine_dialog = False
        st.rerun()


# ================================
# 便量推算ダイアログ（定義だけ）
# ================================
@st.dialog("🚽 標準便量の推算（体重・状態別）")
def stool_dialog():
    # 体重取得（未設定なら60kg）
    weight = st.session_state.get("weight", 60.0)

    # 体調選択
    condition = st.selectbox(
        "状態・疾患区分",
        ["標準（健康時）", "軟便", "下痢", "発熱・感染症", "経腸栄養中", "便秘傾向"]
    )

    # 体調補正係数
    factor_table = {
        "標準（健康時）": 1.0,
        "軟便": 1.5,
        "下痢": 3.0,
        "発熱・感染症": 1.3,
        "経腸栄養中": 1.8,
        "便秘傾向": 0.6
    }

    # 推算便量計算
    base_stool_per_kg = 2.0  # kgあたり便量の基準(g/kg/day)
    est_stool = weight * base_stool_per_kg * factor_table[condition]

    # 表示
    st.metric("推算便重量（1日）", f"{est_stool:.0f} g")

    # 入力反映ボタン
    c_ok, c_ng = st.columns(2)
    if c_ok.button("✅ 入力に反映"):
        # ウィジェットのキー("out_svol")を更新してUIに反映させる
        st.session_state["out_svol"] = int(est_stool)
        st.session_state.s_vol = int(est_stool)
        st.session_state.show_stool_dialog = False
        st.rerun()
    if c_ng.button("❌ キャンセル"):
        st.session_state.show_stool_dialog = False
        st.rerun()

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

if "recorder" not in st.session_state:
    st.session_state.recorder = "本人"

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
    c.drawString(70 * mm, y, f"・性別：{data.get('gender', '不明')}")
    y -= 5 * mm
    c.drawString(25 * mm, y, f"・体重：{data['weight']:.1f} kg")
    c.drawString(70 * mm, y, f"・摂取エネルギー：{data.get('kcal', 0)} kcal")
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

    # 追加：詳細分析（TBW, 損失率）
    c.setFont("HeiseiMin-W3", 10)
    tbw_text = f"推算TBW: {data.get('tbw', 0):.0f} mL"
    loss_text = f"損失率: {data.get('loss_rate', 0):.2f} %"
    
    # 損失率による警告
    loss_rate = data.get('loss_rate', 0)
    warn_msg = ""
    if loss_rate >= 3.0:
        warn_msg = "【危険】熱中症リスク・パフォーマンス著効低下"
        c.setFillColor(colors.red)
    elif loss_rate >= 2.0:
        warn_msg = "【注意】運動パフォーマンス低下の懸念"
        c.setFillColor(colors.orange)
    else:
        c.setFillColor(colors.black)

    c.drawString(25 * mm, y, f"{tbw_text}   /   {loss_text}   {warn_msg}")
    c.setFillColor(colors.black) # 色を戻す
    
    y -= 6 * mm

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


# =========================================================
# 5. メイン計算ページ（2026/01/09 最終安定版）
# =========================================================
if st.session_state.page == "main":
    st.title("🏥 水分出納バランス記録")

    # --- 1. 変数の初期化 ---
    weight_init = st.session_state.get("weight", 60.0)
    u_vol_init = st.session_state.get("u_vol", 250)
    s_vol_init = st.session_state.get("s_vol", 150)
    u_times_init = st.session_state.get("u_times", 5)

    # --- 2. 基本情報入力エリア ---
    st.markdown('<div class="report-header-box"><h4>📋 基本パラメータ設定</h4></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    age = c1.number_input("年齢", 0, 120, 20, key="main_age")
    gender = c2.selectbox("性別", ["男性", "女性"], key="main_gender")
    weight = c3.number_input("体重(kg)", 1.0, 200.0, value=weight_init, step=0.1, key="main_weight")
    st.session_state.weight = weight
    temp = c4.number_input("体温(℃)", 34.0, 42.0, 36.5, 0.1, key="main_temp")
    r_temp = c5.number_input("室温(℃)", 10.0, 40.0, 24.0, 0.5, key="main_rtemp")
    recorder = c6.text_input("記録者", value=st.session_state.recorder, key="main_recorder")
    st.session_state.recorder = recorder

    # --- 3. IN / OUT 入力エリア ---
    st.divider()
    col_in, col_out = st.columns(2)

    with col_in:
        st.markdown('<p class="section-header-in">📥 IN (摂取・流入)</p>', unsafe_allow_html=True)
        oral = st.number_input(
            ":blue[経口摂取(mL)] ※代謝水除く", 
            0, 10000, 1500, 50, 
            key="in_oral",
            help="水、お茶、ジュース、スープ、飲み薬の水など。\n食事中の水分（ご飯、野菜など）を含めるかどうかは方針に従ってください。"
        )
        
        # 代謝水計算用カロリー入力
        ck1, ck2 = st.columns([2, 1])
        kcal = ck1.number_input(
            ":blue[摂取エネルギー(kcal)] ※代謝水推算用", 
            0, 5000, 2000, 100, 
            key="in_kcal",
            help="1日の食事・補食の総カロリー。\n(例) おにぎり1個:約180kcal, 一般的な定食:約700kcal"
        )
        meta_coef = ck2.number_input(
            ":blue[係数]", 
            0.10, 0.20, 0.13, 0.01, 
            format="%.2f", 
            key="in_meta_coef",
            help="代謝水産生係数（通常 0.12 〜 0.15）"
        )
        
        iv = st.number_input(
            ":blue[静脈輸液(mL)]", 
            0, 10000, 0, 50, 
            key="in_iv",
            help="点滴（輸液製剤、抗生剤の溶解液など）。"
        )
        blood = st.number_input(
            ":blue[輸血(mL)]", 
            0, 5000, 0, 50, 
            key="in_blood",
            help="赤血球製剤(RBC)、新鮮凍結血漿(FFP)などの輸血量。"
        )
        
        # 代謝水計算
        # 代謝水計算
        # 代謝水計算
        metabolic = kcal * meta_coef
        st.session_state["disp_metabolic"] = float(metabolic)
        st.number_input(
            ":blue[代謝水(自動計算) mL]", 
            value=float(metabolic), 
            disabled=True, 
            key="disp_metabolic",
            help="食事や栄養が体内でエネルギーに変わるときに作られる水。\n摂取エネルギー × 係数 で算出されます。"
        )

    with col_out:
        st.markdown('<p class="section-header-out">📤 OUT (排出・喪失)</p>', unsafe_allow_html=True)
        u_times = st.number_input(
            ":red[排尿回数]", 
            0, 20, value=u_times_init, 
            key="out_utimes",
            help="24時間でトイレに行った回数。"
        )
        st.session_state.u_times = u_times

        ucol_l, ucol_r = st.columns([3, 2])
        with ucol_l:
            u_vol = st.number_input(
                ":red[1回尿量(mL)]", 
                0, 1000, value=u_vol_init, 
                key="out_uvol",
                help="1回あたりの平均的な量。\n・紙コップ1杯: 約200mL\n・尿器の目盛りなどを参考に。"
            )
            st.session_state.u_vol = u_vol
        with ucol_r:
            st.markdown("###### ")
            if st.button("📐 尿量推算", use_container_width=True, key="btn_u_calc"):
                urine_dialog()

        bleeding = st.number_input(
            ":red[出血・ドレーン等(mL)]", 
            0, 5000, 0, 
            key="out_bleed",
            help="手術痕からの出血、ドレーン排液、嘔吐物など、尿・便以外の喪失。"
        )

        scol_l, scol_r = st.columns([3, 2])
        with scol_l:
            s_vol = st.number_input(
                ":red[便重量(g)]", 
                0, 1000, value=s_vol_init, 
                key="out_svol",
                help="便の重さ。\n・バナナ1本分: 約100g〜150g\n・卵1個分: 約50g"
            )
            st.session_state.s_vol = s_vol
        with scol_r:
            st.markdown("###### ")
            if st.button("📐 便量推算", use_container_width=True, key="btn_s_calc"):
                stool_dialog()
        
        # 入力項目の最後
        s_type = st.selectbox(
            ":red[便性状]", 
            ["普通", "軟便", "下痢"], 
            key="out_stype_main",
            help="便の水分量補正に使用します。\n・普通: ×0.75\n・軟便: ×0.85\n・下痢: ×0.95"
        )
        
        # 不感蒸泄の計算と表示（これまで下部で行っていた計算をここでも行う）
        insensible_calc = 15.0 * weight
        if temp > 37.0: 
            insensible_calc *= (1 + 0.15 * (temp - 37.0))
        if r_temp > 30.0: 
            insensible_calc *= (1 + 0.175 * (r_temp - 30.0))
            
        if r_temp > 30.0: 
            insensible_calc *= (1 + 0.175 * (r_temp - 30.0))
            
        st.session_state["disp_insensible"] = float(insensible_calc)
        st.number_input(
            ":red[不感蒸泄(自動計算) mL]", 
            value=float(insensible_calc), 
            disabled=True, 
            key="disp_insensible",
            help="発汗とは別に、皮膚や呼吸から自然に失われる水分。\n体重・体温・室温から算出され、熱や暑さで増加します。"
        )

    # =========================================================
    # 【完結】これより下は計算と表示。重複コードはすべて消去してください
    # =========================================================
    
    # 1. 確定計算
    urine_total = st.session_state.u_times * st.session_state.u_vol
    s_factor = 0.75 if s_type == "普通" else 0.85 if s_type == "軟便" else 0.95
    stool_total = st.session_state.s_vol * s_factor
    
    insensible_total = 15.0 * weight
    if temp > 37.0: 
        insensible_total *= (1 + 0.15 * (temp - 37.0))
    if r_temp > 30.0: 
        insensible_total *= (1 + 0.175 * (r_temp - 30.0))

    total_in = oral + iv + blood + metabolic
    total_out = urine_total + bleeding + stool_total + insensible_total
    net_balance = total_in - total_out

    # 2. 結果表示（1回のみ実行）
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("総流入 (IN)", f"{total_in:.0f} mL")
    m2.metric("総流出 (OUT)", f"{total_out:.0f} mL")
    m3.metric("バランス", f"{net_balance:+.0f} mL")

    # 3. 判定メッセージ（status_funcなどの変数を使わず直接表示）
    # 3. 判定メッセージ（status_funcなどの変数を使わず直接表示）
    if net_balance > 500:
        judg = "体液過剰の傾向"
        st.error(f"判定：{judg}")
    elif net_balance < -200:
        judg = "脱水リスク"
        st.warning(f"判定：{judg}")
    else:
        judg = "維持範囲"
        st.success(f"判定：{judg}")

    # --- 追加: 体内全水分量と損失率の計算 ---
    # 係数決定
    if age < 1:
        tbw_ratio = 0.8
    elif age < 14:
        tbw_ratio = 0.7
    elif age >= 65:
        tbw_ratio = 0.5
    else:
        # 成人(14-64)
        if gender == "男性":
            tbw_ratio = 0.6
        else:
            tbw_ratio = 0.55
            
    tbw_val = weight * tbw_ratio * 1000  # mL換算
    
    # 損失量の計算（マイナスバランスの場合のみ）
    loss_ml = abs(net_balance) if net_balance < 0 else 0
    loss_rate = (loss_ml / tbw_val) * 100 if tbw_val > 0 else 0
    
    st.markdown("### 💧 水分状態の詳細分析")
    c_res1, c_res2 = st.columns(2)
    c_res1.metric("推算体内全水分量 (TBW)", f"{tbw_val:,.0f} mL", help=f"年齢・性別・体重から推算（係数: {tbw_ratio*100:.0f}%）")
    
    # 損失率の表示（色分け）
    loss_color = "normal"
    if loss_rate >= 2.0:
        loss_color = "off" # inverse logic usually, but here checking threshold
    
    c_res2.metric("水分損失率 (対 TBW)", f"{loss_rate:.2f} %", delta=None)

    # パフォーマンス低下警告
    if loss_rate >= 3.0:
        st.error(f"⚠️ 水分損失率が {loss_rate:.1f}% です。運動パフォーマンスの著しい低下や熱中症のリスクがあります。直ちに水分補給を行ってください。")
    elif loss_rate >= 2.0:
        st.warning(f"⚠️ 水分損失率が {loss_rate:.1f}% です。運動パフォーマンスの低下（2〜3%）が懸念されます。早めの水分補給を推奨します。")
    elif loss_rate > 0:
        st.info(f"水分損失率は {loss_rate:.1f}% です。こまめな水分補給を心がけましょう。")

    # 4. PDF生成ボタン（一つに集約）
    st.markdown("---")
    if st.button("📄 PDFレポートを生成・保存", use_container_width=True, key="btn_final_unified"):
        report_data = {
            "age": age, "gender": gender, "weight": weight, "temp": temp, "room_temp": r_temp,
            "kcal": kcal,
            "oral": oral, "iv": iv, "blood": blood, "metabolic": metabolic,
            "urine": urine_total, "bleeding": bleeding, "stool": stool_total,
            "insensible": insensible_total, "net": net_balance, "judgment": judg,
            "tbw": tbw_val, "loss_rate": loss_rate,
            "recorder": recorder
        }
        pdf_buf = generate_medical_report(report_data)
        st.download_button(
            label="📥 PDFをダウンロード",
            data=pdf_buf,
            file_name=f"FluidBalance_20260109.pdf",
            mime="application/pdf",
            key="btn_download_unified"
        )





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
    st.latex(r"\text{算出式: } \text{摂取エネルギー(kcal)} \times 0.12 \sim 0.15")
    st.caption(
        "根拠: 一般的に摂取エネルギー 1kcal あたり 0.12mL 〜 0.15mL の代謝水が生成されると推定されています。"
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

    st.subheader("① 水分出納とは その重要性")
    st.write("""
    **水分出納（Water Balance）**とは、体に入ってくる水分（IN）と体から出ていく水分（OUT）のバランスのことです。
    私たちの体は成人で約60%が水分で構成されており、このバランスが崩れると生命維持に支障をきたします。
    
    - **脱水（IN < OUT）**: 循環不全、腎機能低下、意識障害などのリスク
    - **体液過剰（IN > OUT）**: 浮腫（むくみ）、心不全、呼吸困難などのリスク
    
    このバランスを日々把握し、適切に管理・補正することが健康維持の第一歩です。
    """)

    st.subheader("② IN（摂取・流入）の項目")
    st.markdown("""
    水分出納において、体内に水分が入ってくるルートは主に以下の通りです。
    
    - **経口摂取水 (Oral Intake)**  
      飲み物や食事に含まれる水分です。食事にも多くの水分が含まれているため、これらも重要な水分源となります。
    
    - **代謝水 (Metabolic Water)**  
      体内で栄養素（糖質・脂質・タンパク質）がエネルギーとして燃焼される際に化学反応で生成される水分です。
      飲まなくても体内で自然に作られる「見えない水分」です。
    
    - **静脈輸液 (Intravenous Fluids)**  
      点滴によって血管内に直接水分や電解質、薬剤を投与することです。医療現場で最も確実な水分補給手段です。
    
    - **輸血 (Transfusion)**  
      血液製剤の投与です。これも水分量としてカウントされますが、循環血液量の増加という点で輸液とは異なる慎重な管理が必要です。
    """)

    st.subheader("③ OUT（排出・喪失）の項目")
    st.markdown("""
    体から水分が出ていくルートは、生理的なものと病的なものに分けられます。
    
    - **排尿 (Urine Output)**  
      腎臓で血液が濾過され、不要な老廃物とともに水分が排出される生理現象です。
      体内の水分量調節・電解質バランスの維持に最も重要な役割を果たします。
    
    - **便中水分 (Stool Water)**  
      便として排出される水分です。通常は少量ですが、下痢の場合は大量の水分喪失となり得ます。
    
    - **出血・ドレーン排液 (Bleeding / Drainage)**  
      手術や怪我による出血、または体内に溜まった液体を管（ドレーン）で外に出す場合の水分です。
      これらは「異常な喪失」として、INを増やして補う必要があります。
      
    - **不感蒸泄 (Insensible Water Loss)**  
      発汗とは別に、皮膚や呼気から自然に蒸発して失われる水分です。発熱時などは増加します。
    """)

    st.divider()


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















