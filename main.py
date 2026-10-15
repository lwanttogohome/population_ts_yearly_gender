import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


# ============================================================
# 기본 설정
# ============================================================

st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

# 따뜻한 느낌을 주기 위한 간단한 CSS입니다.
st.markdown(
    """
    <style>
    .stApp {
        background-color: #fffaf5;
    }

    h1 {
        color: #8b4513;
    }

    h2, h3 {
        color: #a0522d;
    }

    .description {
        padding: 15px;
        border-radius: 10px;
        background-color: #fff1e6;
        margin-bottom: 20px;
    }

    .warning-badge {
        display: inline-block;
        margin-left: 8px;
        padding: 4px 10px;
        border-radius: 999px;
        background-color: #ffe0b2;
        color: #8b4513;
        font-weight: 700;
        font-size: 0.85rem;
        vertical-align: middle;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 데이터 불러오기
# ============================================================

DATA_URL = (
    "https://raw.githubusercontent.com/first2022-cyber/contents/"
    "main/population_ts_yearly_gender.zip"
)


@st.cache_data
def load_data():
    """GitHub의 ZIP 압축 CSV를 pandas로 직접 읽습니다."""
    df = pd.read_csv(DATA_URL, compression="zip")
    return df


try:
    df = load_data()
except Exception as e:
    st.error("데이터를 불러오는 중 문제가 발생했습니다.")
    st.exception(e)
    st.stop()


# ============================================================
# 최신 연도만 사용
# ============================================================

# 연도를 숫자로 바꿔 가장 최신 연도를 찾습니다.
df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
df = df.dropna(subset=["연도"])

latest_year = int(df["연도"].max())

# 최신 연도에 해당하는 데이터만 남깁니다.
latest_df = df[df["연도"] == latest_year].copy()


# ============================================================
# 제목
# ============================================================

st.title("🏘️ 동네별 인구 피라미드")

st.markdown(
    f"""
    <div class="description">
    <b>{latest_year}년 최신 인구 데이터</b>를 이용해
    원하는 시도 → 시군구 → 동을 선택하고,
    해당 지역의 연령별 남녀 인구와 인구 구조를 확인해 보세요.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 지역 선택
# ============================================================

st.subheader("📍 지역을 선택하세요")

# 첫 번째 드롭다운: 시도
sido_list = sorted(
    latest_df["시도"].dropna().astype(str).unique().tolist()
)

selected_sido = st.selectbox(
    "① 시도",
    sido_list,
)

# 선택한 시도에 해당하는 데이터만 남깁니다.
sido_df = latest_df[
    latest_df["시도"].astype(str) == selected_sido
].copy()


# 두 번째 드롭다운: 시군구
sigungu_list = sorted(
    sido_df["시군구"].dropna().astype(str).unique().tolist()
)

selected_sigungu = st.selectbox(
    "② 시군구",
    sigungu_list,
)

# 선택한 시도 + 시군구에 해당하는 데이터만 남깁니다.
sigungu_df = sido_df[
    sido_df["시군구"].astype(str) == selected_sigungu
].copy()


# 세 번째 드롭다운: 동
dong_list = sorted(
    sigungu_df["동"].dropna().astype(str).unique().tolist()
)

selected_dong = st.selectbox(
    "③ 동",
    dong_list,
)


# ============================================================
# 선택한 동네 데이터 추출
# ============================================================

selected_df = sigungu_df[
    sigungu_df["동"].astype(str) == selected_dong
].copy()

if selected_df.empty:
    st.warning("선택한 지역의 데이터를 찾을 수 없습니다.")
    st.stop()


# ============================================================
# 나이 목록
# ============================================================

# 나이는 0세부터 100세 이상까지 순서대로 고정합니다.
ages = [f"{age}세" for age in range(101)]
ages[-1] = "100세 이상"


# ============================================================
# 남녀 인구 열 이름
# ============================================================

male_columns = [f"남_{age}" for age in ages]
female_columns = [f"여_{age}" for age in ages]

# 필요한 열이 데이터에 모두 있는지 확인합니다.
missing_columns = [
    col
    for col in male_columns + female_columns
    if col not in selected_df.columns
]

if missing_columns:
    st.error(
        "인구 데이터 열 이름을 찾을 수 없습니다.\n\n"
        + ", ".join(missing_columns)
    )
    st.stop()


# ============================================================
# 연령별 인구 계산
# ============================================================

# 같은 동네에 여러 행이 있을 가능성을 고려해 연령별로 합산합니다.
male_population = (
    selected_df[male_columns]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
    .sum(axis=0)
)

female_population = (
    selected_df[female_columns]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
    .sum(axis=0)
)


# ============================================================
# 지표 계산
# ============================================================

# 남자 인구는 그래프에서 왼쪽에 놓기 위해 음수로 만들었지만,
# 실제 인구 계산에서는 절댓값을 사용합니다.
male_counts = male_population.to_numpy(dtype=float)
female_counts = female_population.to_numpy(dtype=float)

male_counts = np.nan_to_num(male_counts, nan=0.0)
female_counts = np.nan_to_num(female_counts, nan=0.0)

total_by_age = male_counts + female_counts

# 총인구
total_population = float(total_by_age.sum())

# 평균연령
# 각 연령별 인구에 해당 나이를 곱해 가중평균을 계산합니다.
# 100세 이상은 100세로 계산합니다.
age_values = np.arange(101, dtype=float)

if total_population > 0:
    average_age = float(
        np.sum(age_values * total_by_age) / total_population
    )
else:
    average_age = 0.0

# 고령화율 = 65세 이상 인구 / 전체 인구 × 100
# 65세 이상은 65세~100세 이상을 포함합니다.
age_65_plus_population = float(total_by_age[65:].sum())

if total_population > 0:
    aging_rate = age_65_plus_population / total_population * 100
else:
    aging_rate = 0.0


# ============================================================
# 지표 카드 3개
# ============================================================

st.subheader(
    f"📌 {selected_sido} · {selected_sigungu} · {selected_dong}"
)

card1, card2, card3 = st.columns(3)

with card1:
    st.metric(
        "총인구",
        f"{int(round(total_population)):,}명",
    )

with card2:
    st.metric(
        "평균연령",
        f"{average_age:.1f}세",
    )

with card3:
    # 고령화율이 20%를 넘으면 카드 제목 옆에 주의 표시를 붙입니다.
    if aging_rate > 20:
        card_title = "고령화율 ⚠️"
    else:
        card_title = "고령화율"

    st.metric(
        card_title,
        f"{aging_rate:.1f}%",
    )

    if aging_rate > 20:
        st.caption("⚠️ 고령화율 20% 초과")


# ============================================================
# 그래프용 데이터
# ============================================================

# 나이 순서를 절대로 정렬하지 않고
# 0세 → 1세 → ... → 100세 이상 순서 그대로 사용합니다.
chart_df = pd.DataFrame(
    {
        "나이": ages,
        "남자": -male_counts,
        "여자": female_counts,
    }
)


# ============================================================
# 인구 피라미드 그래프
# ============================================================

fig = go.Figure()

# 남자: 음수 값으로 만들어 왼쪽에 표시합니다.
fig.add_trace(
    go.Bar(
        y=chart_df["나이"],
        x=chart_df["남자"],
        name="남자",
        orientation="h",
        hovertemplate=(
            "나이: %{y}<br>"
            "남자: %{customdata:,}명"
            "<extra></extra>"
        ),
        customdata=np.abs(chart_df["남자"]),
    )
)

# 여자: 양수 값으로 만들어 오른쪽에 표시합니다.
fig.add_trace(
    go.Bar(
        y=chart_df["나이"],
        x=chart_df["여자"],
        name="여자",
        orientation="h",
        hovertemplate=(
            "나이: %{y}<br>"
            "여자: %{x:,}명"
            "<extra></extra>"
        ),
    )
)


# ============================================================
# 그래프 레이아웃
# ============================================================

# 중요:
# categoryarray에 0세부터 100세 이상까지의 순서를 직접 넣습니다.
# 따라서 값 크기순 정렬을 하지 않습니다.
# 또한 y축 전체를 뒤집는 autorange="reversed"도 사용하지 않습니다.
#
# 결과:
# 맨 아래 = 0세
# 맨 위   = 100세 이상
fig.update_layout(
    title=f"{selected_dong} 연령별 남녀 인구",
    barmode="relative",

    xaxis=dict(
        title="인구 수 (명)",
        tickformat=",",
        zeroline=True,
        zerolinewidth=2,
    ),

    yaxis=dict(
        title="나이",
        categoryorder="array",
        categoryarray=ages,
    ),

    height=1000,

    legend=dict(
        title="성별",
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5,
    ),

    margin=dict(
        l=80,
        r=80,
        t=100,
        b=60,
    ),

    plot_bgcolor="#fffaf5",
    paper_bgcolor="#fffaf5",
)


# ============================================================
# 그래프 표시
# ============================================================

st.plotly_chart(
    fig,
    width="stretch",
    config={
        "displayModeBar": True,
        "scrollZoom": False,
    },
)


# ============================================================
# 인구 구조 한 줄 설명
# ============================================================

# 아이(0~14세)와 어르신(65세 이상)의 인구를 비교합니다.
child_population = float(total_by_age[:15].sum())

if child_population > age_65_plus_population:
    population_comment = (
        "👶 이 동네는 어르신보다 아이 인구가 많은 편이에요."
    )
elif child_population < age_65_plus_population:
    population_comment = (
        "👵 이 동네는 아이보다 어르신 인구가 많은 편이에요."
    )
else:
    population_comment = (
        "⚖️ 이 동네는 아이와 어르신 인구가 비슷한 편이에요."
    )

st.info(
    f"**이 동네는 아이가 많은 편인가요, 어르신이 많은 편인가요?** "
    f"{population_comment}"
)


# ============================================================
# 나이 축 순서 최종 확인
# ============================================================

# 실제 그래프에 전달한 나이 목록의 첫 번째와 마지막을 확인합니다.
if (
    chart_df["나이"].iloc[0] == "0세"
    and chart_df["나이"].iloc[-1] == "100세 이상"
):
    st.success(
        "✅ 나이 축 확인 완료: 맨 아래 0세 → 맨 위 100세 이상"
    )
else:
    st.error("나이 축 순서에 문제가 있습니다.")


st.caption(
    "※ 남자 인구는 그래프에서 왼쪽으로 보이도록 음수로 표시했으며, "
    "실제 인구 수를 계산할 때는 절댓값을 사용했습니다."
)
