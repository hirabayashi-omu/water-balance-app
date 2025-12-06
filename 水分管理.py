import streamlit as st

st.set_page_config(page_title="水分出納バランス管理アプリ", layout="wide")

st.markdown(
    """
    <meta name="google" content="notranslate">
    <style>
        html { notranslate: google; }
    </style>
    """,
    unsafe_allow_html=True
)
st.title("水分出納バランス管理アプリ")
st.write("生活・医療・看護で利用できる実用的な水分管理ツール")

# =========================================================
# 関数：年齢 → 体水分量（％）の線形近似
# =========================================================
def estimate_body_water(age):
    if age <= 1:
        return 80 - (age / 1) * 10          # 0〜1歳：80→70%
    elif age <= 13:
        return 70 - ((age - 1) / 12) * 10   # 1〜13歳：70→60%
    elif age <= 65:
        return 60 - ((age - 13) / 52) * 10  # 13〜65歳：60→50%
    else:
        return 50                           # 65歳以上：固定50%

# =========================================================
# 患者情報（年齢入力はここに一本化）
# =========================================================
st.header("人の情報（個人情報の保護：計算以外に利用・保存されません）")
col_p1, col_p2, col_p3, col_p4 = st.columns(4)

with col_p1:
    age = st.number_input("年齢 (歳)", min_value=0, max_value=120, value=35)

with col_p2:
    weight = st.number_input("体重 (kg)", min_value=1.0, value=50.0)

with col_p3:
    temp = st.number_input("体温 (℃)", min_value=30.0, max_value=42.0, value=36.5)

with col_p4:
    room_temp = st.number_input("室温 (℃)", min_value=10.0, max_value=40.0, value=25.0)

# 年齢に基づく体水分率
body_water_percent = estimate_body_water(age)
body_total_water = weight * (body_water_percent / 100)

st.info(f"推定体水分率：**{body_water_percent:.1f}%**")
st.info(f"推定総体水分量：**{body_total_water:.1f} L**")

# =========================================================
# 不感蒸泄・代謝水（自動計算）
# =========================================================
st.header("不感蒸泄・代謝水（自動計算）")

insensible = 15 * weight

# 発熱補正
if temp > 37:
    insensible *= 1 + 0.15 * (temp - 37)

# 高温環境補正
if room_temp > 30:
    insensible *= 1 + 0.175 * (room_temp - 30)

# 代謝水
metabolic_water = 5 * weight

col_i1, col_i2 = st.columns(2)
with col_i1:
    st.write(f"不感蒸泄量： **{insensible:.0f} mL/day**")
with col_i2:
    st.write(f"代謝水（Out から差し引く）： **{metabolic_water:.0f} mL/day**")

# =========================================================
# メインレイアウト：左右に In と Out
# =========================================================
col_in, col_out = st.columns(2)

# -----------------------------
# In（左）
# -----------------------------
with col_in:
    st.header("In（摂取量）")

    oral = st.number_input("経口摂取量(アルコール・カフェイン飲料を除く) (mL/day)", min_value=0, value=2500)
    iv = st.number_input("点滴・輸液量 (mL/day)", min_value=0, value=0)
    blood_transfusion = st.number_input("輸血量 (mL/day)", min_value=0, value=0)

    total_in = oral + iv + blood_transfusion

    st.markdown(f"### 合計 In： **{total_in:.0f} mL/day**")

# -----------------------------
# Out（右）
# -----------------------------
with col_out:
    st.header("Out（排泄量）")

    # 尿
    st.subheader("尿量")
    urine_times = st.number_input("排尿回数（回/日）", min_value=0, value=4)

    estimated_per_void = 200 + (weight / 10 * 20)
    estimated_per_void = min(max(estimated_per_void, 200), 400)

    per_void = st.number_input("1回あたりの尿量 (mL)", min_value=0, value=int(estimated_per_void))

    urine = urine_times * per_void
    st.write(f"1日尿量： **{urine:.0f} mL/day**")

    # 出血
    bleeding = st.number_input("出血量 (mL/day)", min_value=0, value=0)

    # 便
    st.subheader("便による水分損失")

    stool_weight = st.number_input("1日の便量 (g/day)", min_value=0, value=150)

    stool_type = st.selectbox(
        "便性状",
        ["正常便（成形）", "軟便（泥状）", "下痢（水様）"]
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

    st.markdown(f"### 合計 Out： **{total_out:.0f} mL/day**")

# =========================================================
# 結果（下段）
# =========================================================
st.markdown("---")
st.header("水分出納バランス結果（In - Out - 不感蒸泄 + 代謝水）")

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

if net_balance > 700:
    st.error("バランスが大きくプラス → 体液過剰の可能性")
elif net_balance > 300:
    st.warning("ややプラス（通常の成人では許容範囲）")
elif -200 <= net_balance <= 300:
    st.success("ほぼ適正範囲です")
else:
    st.error("マイナス → 脱水リスクあり")

# =========================================================
# 備考
# =========================================================
st.info("""
### 判定の目安
- 新生児：体水分量が多いため脱水進行が速い  
- 高齢者：体水分量が低く脱水リスクが高い  
- 健康成人：+500〜600 mL/day 程度で適正  
- 発熱・高温環境：不感蒸泄が増加  
- 心不全・腎不全：±0 〜 マイナスで管理  
""")



