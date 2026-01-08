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
# 3. ナビゲーション (3ページ構成に拡張)
# ================================
st.sidebar.title("メニュー")
page = st.sidebar.radio("画面切り替え", ["🏠 メイン計算", "📖 推算根拠", "📚 引用・参考文献"])

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
# 5. 推算根拠ページ (全文詳細版)
# ================================
else:
    st.title("📖 水分出納の推算根拠と判定基準")
    
    st.info("本プログラムで使用している各種推算式は以下の通りです。これらは臨床現場で一般的に用いられる指標に基づいています。")

    # 1. 入出量合計の算出式
    st.markdown('<div class="report-header-box"><h4>1. 入出量合計の算出式</h4></div>', unsafe_allow_html=True)
    st.write("**■ 総 Intake (総流入量)**")
    st.latex(r"\text{総IN} = \text{経口摂取(経管)} + \text{静脈輸液} + \text{輸血製剤} + \text{代謝水}")
    
    st.write("**■ 総 Output (総流出量)**")
    st.latex(r"\text{総OUT} = \text{尿量} + \text{出血・ドレーン等} + \text{便中水分} + \text{不感蒸泄}")
    
    st.write("**■ ネットバランス (Net Balance)**")
    st.latex(r"\text{バランス} = \text{総IN} - \text{総OUT}")

    # 2. 各項目の推算根拠
    st.markdown('<div class="report-header-box"><h4>2. 各項目の推算根拠</h4></div>', unsafe_allow_html=True)
    
    st.markdown("##### ① 代謝水 (Metabolic Water)")
    st.write("栄養素が体内で燃焼（酸化）される際に生成される水分です。")
    st.latex(r"\text{算出式: } 5\,\text{mL} \times \text{体重(kg)}")
    st.caption("根拠: 通常、成人では1日あたり約200〜300mL（約5mL/kg）程度とされています。")

    st.markdown("##### ② 不感蒸泄 (Insensible Water Loss)")
    st.write("呼気や皮膚から自覚なしに失われる水分です。体温や周囲の温度によって変動します。")
    st.latex(r"\text{基本式: } 15\,\text{mL} \times \text{体重(kg)}")
    
    st.write("**・発熱補正:** 体温が37℃を超える場合、1℃上昇につき15%増加させます。")
    st.latex(r"\text{補正係数} = 1.0 + 0.15 \times (\text{体温} - 37)")
    
    st.write("**・室温補正:** 室温が30℃を超える場合、1℃上昇につき17.5%増加させます。")
    st.latex(r"\text{補正係数} = 1.0 + 0.175 \times (\text{室温} - 30)")

    st.markdown("##### ③ 便中水分")
    st.write("便の性状（水分含有率）に基づき、重量から水分量を推定します。")
    st.write("- **普通便:** $重量(g) \times 0.75$")
    st.write("- **軟便:** $重量(g) \times 0.85$")
    st.write("- **下痢:** $重量(g) \times 0.95$")

    st.markdown("##### ④ 推定体水分率 (Total Body Water %)")
    st.write("加齢に伴う細胞内液の減少を考慮した推算式です。")
    st.write("- **乳児(0-1歳):** 80%から月齢に応じて減少")
    st.write("- **幼児・学童(1-13歳):** 70%から年齢に応じて減少")
    st.write("- **成人(14-65歳):** 60%から年齢に応じて減少")
    st.write("- **高齢者(65歳以上):** 一律 50%")

    # 3. 2026年現在の臨床的判定基準
    st.markdown('<div class="report-header-box"><h4>3. 2026年現在の臨床的判定基準</h4></div>', unsafe_allow_html=True)
    st.write("本システムでは、24時間あたりのネットバランスに基づき以下の判定を行っています。")
    
    st.table([
        {"バランス結果": "+500 mL 超", "判定": "体液過剰 (Overhydration)", "臨床的リスク": "心不全増悪、浮腫、肺水腫のリスク"},
        {"バランス結果": "-200 ～ +500 mL", "判定": "維持範囲 (Maintenance)", "臨床的リスク": "生理的許容範囲"},
        {"バランス結果": "-200 mL 未満", "判定": "脱水リスク (Dehydration)", "臨床的リスク": "腎不全（乏尿）、循環不全、血圧低下のリスク"}
    ])

    st.warning("""
    **※これらの数値はあくまで目安です。**  
    2026年1月9日現在の臨床ガイドラインに則り、実際の診断には血清ナトリウム値、心エコー、皮膚緊張度（ツルゴール）等の身体所見を併せて評価する必要があります。
    """)

    if st.sidebar.button("🏠 メイン画面へ戻る"):
        st.info("サイドメニューから「メイン計算」を選択してください。")


# ================================
# 6. 引用・参考文献ページ (新規追加)
# ================================
elif page == "📚 引用・参考文献":
    st.title("📚 引用・参考文献")
    st.info("本システムの計算式および判定基準は、以下の公的機関・学会等の資料に基づき作成されています。")

    st.markdown('<div class="report-header-box"><h4>1. 公的ガイドライン・基準</h4></div>', unsafe_allow_html=True)
    
    st.markdown("""
    - **[厚生労働省：日本人の食事摂取基準（2025年版）](www.mhlw.go.jp)**  
      *水分の必要量や代謝水の生成根拠となる栄養素の酸化プロセスに関する標準的な数値が記載されています。*
    
    - **[環境省：熱中症環境保健マニュアル](www.wbgt.env.go.jp)**  
      *室温・外気温上昇に伴う不感蒸泄および発汗量の増加に関する知見がまとめられています。*
    """)

    st.markdown('<div class="report-header-box"><h4>2. 臨床医学的エビデンス</h4></div>', unsafe_allow_html=True)
    
    st.markdown("""
    - **[MSDマニュアル プロフェッショナル版：水分平衡](www.msdmanuals.com)**  
      *世界共通の臨床基準として、不感蒸泄（10〜15mL/kg）や、体温上昇に伴う損失増（1℃につき10〜15%）の根拠となります。*
    
    - **[一般社団法人 日本臨床栄養代謝学会（JSPEN）：ガイドライン](www.jspen.or.jp)**  
      *臨床現場における水・電解質管理の最新の国内ガイドラインを確認できます。*
    """)

    st.markdown('<div class="report-header-box"><h4>3. 文献検索（最新知見）</h4></div>', unsafe_allow_html=True)
    
    st.markdown("""
    - **[CiNii Research（日本の論文検索：水分出納）](cinii.clear.ndl.go.jp)**  
      *本システムで採用している各係数（15mL/kg/day等）の妥当性を検証した最新の論文を検索可能です。*
    """)

    st.warning("""
    **臨床現場での利用にあたって**  
    2026年現在の医学的知見に基づき構成されていますが、臨床的な最終判断は患者個別の身体所見（血圧、浮腫、血清Na値等）に基づき、医師が行ってください。
    """)

