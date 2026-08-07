
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="VIDIVICI Japan TikTok Dashboard",
    page_icon="💬",
    layout="wide",
)

DATA_FILE = "vidivici_comments_final.csv"

# -----------------------------
# 분석 정의
# -----------------------------
PRODUCT_RELATED_TARGETS = [
    "제품 반응",
    "피부 표현·메이크업",
    "구매·문의",
]

TARGET_KEYWORDS = {
    "모델·출연자 반응": [
        "かわいい", "可愛い", "可愛すぎ", "美人", "綺麗", "きれい",
        "顔", "ビジュ", "ビジュアル", "似合う", "ちゃん", "女の子",
        "モデル", "推し", "好き", "最高", "神", "尊い", "美女",
        "イケメン", "美しい"
    ],
    "제품 반응": [
        "ファンデ", "ファンデーション", "クッション", "プライマー",
        "リップ", "ブラッシュ", "カバー", "カバー力", "崩れ",
        "崩れない", "崩れにくい", "毛穴", "乾燥", "保湿", "密着",
        "持ち", "テクスチャ", "伸び", "発色", "色味", "軽い",
        "しっとり", "サラサラ"
    ],
    "피부 표현·메이크업": [
        "ツヤ", "艶", "透明感", "仕上がり", "肌", "肌綺麗",
        "ナチュラル", "マット", "メイク", "トーンアップ",
        "発光", "水光", "陶器肌", "血色", "うるおい"
    ],
    "구매·문의": [
        "欲しい", "欲しかった", "買う", "買った", "買いたい",
        "購入", "注文", "メガ割", "Qoo10", "どこで買える",
        "どこで売ってる", "気になる", "何色", "何番",
        "おすすめ", "使ったことある", "教えて"
    ],
}


def classify_reaction_target(text):
    text = str(text).lower()

    matched = []
    for target, keywords in TARGET_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            matched.append(target)

    if not matched:
        return "기타"

    priority = [
        "제품 반응",
        "피부 표현·메이크업",
        "구매·문의",
        "모델·출연자 반응",
    ]

    for target in priority:
        if target in matched:
            return target

    return "기타"


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE)

    df["diggCount"] = pd.to_numeric(
        df.get("diggCount", 0),
        errors="coerce",
    ).fillna(0).astype(int)

    if "createTimeISO" in df.columns:
        df["createTimeISO"] = pd.to_datetime(
            df["createTimeISO"],
            errors="coerce",
        )

    for col in ["text", "language", "sentiment", "category"]:
        if col not in df.columns:
            df[col] = ""

    if "reaction_target" not in df.columns:
        df["reaction_target"] = df["text"].apply(classify_reaction_target)

    if "videoWebUrl" not in df.columns:
        df["videoWebUrl"] = ""

    return df


df = load_data()

# -----------------------------
# 브랜드 스타일
# -----------------------------
VIDIVICI_BLACK = "#111111"
VIDIVICI_BEIGE = "#F4EFE9"
VIDIVICI_TAUPE = "#B7A99A"
VIDIVICI_ROSE = "#C98E8E"
VIDIVICI_GRAY = "#6F6F6F"
VIDIVICI_GRID = "#EAE6E1"

st.markdown(
    f"""
    <style>
        .stApp {{
            background: #FCFBFA;
        }}

        .block-container {{
            max-width: 1480px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }}

        [data-testid="stSidebar"] {{
            background: #F6F3F0;
            border-right: 1px solid #ECE7E2;
        }}

        .brand-kicker {{
            font-size: 0.82rem;
            letter-spacing: 0.16em;
            color: {VIDIVICI_TAUPE};
            font-weight: 700;
            margin-bottom: 0.35rem;
        }}

        .main-title {{
            color: {VIDIVICI_BLACK};
            font-size: 2.25rem;
            line-height: 1.15;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }}

        .sub-title {{
            color: {VIDIVICI_GRAY};
            font-size: 0.96rem;
            margin-bottom: 1.5rem;
        }}

        .metric-card {{
            background: #FFFFFF;
            border: 1px solid #EEE9E4;
            border-radius: 18px;
            padding: 18px 20px;
            min-height: 112px;
            box-shadow: 0 4px 18px rgba(17,17,17,0.035);
        }}

        .metric-label {{
            color: {VIDIVICI_GRAY};
            font-size: 0.88rem;
            margin-bottom: 8px;
        }}

        .metric-value {{
            color: {VIDIVICI_BLACK};
            font-size: 1.85rem;
            font-weight: 800;
            line-height: 1.15;
        }}

        .section-note {{
            color: #89817A;
            font-size: 0.88rem;
            margin-top: -8px;
            margin-bottom: 12px;
        }}

        div[data-testid="stDataFrame"] {{
            border-radius: 14px;
            overflow: hidden;
        }}

        .stDownloadButton button {{
            border-radius: 12px;
            border: 1px solid #CFC6BD;
            background: #FFFFFF;
            color: {VIDIVICI_BLACK};
            font-weight: 700;
        }}

        .stDownloadButton button:hover {{
            border-color: {VIDIVICI_BLACK};
            color: {VIDIVICI_BLACK};
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand-kicker">VIDIVICI · JAPAN SOCIAL LISTENING</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">VIDIVICI Japan TikTok Consumer Insight</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">일본 TikTok 소비자 댓글의 감성, 제품 반응, 피부 표현, 구매 관심을 구분해 확인하는 대시보드</div>',
    unsafe_allow_html=True,
)

# -----------------------------
# 사이드바
# -----------------------------
st.sidebar.header("필터")
st.sidebar.caption("시장: Japan · 분석 언어: Japanese")

# 일본 시장 전용 대시보드: Japanese 댓글만 고정 사용
df = df[df["language"] == "Japanese"].copy()

sentiment_options = sorted(df["sentiment"].dropna().unique().tolist())
selected_sentiments = st.sidebar.multiselect(
    "감성",
    options=sentiment_options,
    default=sentiment_options,
)

category_options = sorted(df["category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "관심 주제",
    options=category_options,
    default=category_options,
)

reaction_options = sorted(df["reaction_target"].dropna().unique().tolist())
selected_reactions = st.sidebar.multiselect(
    "반응 대상",
    options=reaction_options,
    default=reaction_options,
)

search_text = st.sidebar.text_input(
    "댓글 검색",
    placeholder="일본어 키워드 또는 댓글 내용 검색",
)

filtered_df = df[
    df["sentiment"].isin(selected_sentiments)
    & df["category"].isin(selected_categories)
    & df["reaction_target"].isin(selected_reactions)
].copy()

if search_text:
    filtered_df = filtered_df[
        filtered_df["text"]
        .astype(str)
        .str.contains(search_text, case=False, na=False, regex=False)
    ]

# -----------------------------
# KPI
# -----------------------------
total_comments = len(filtered_df)
positive_count = filtered_df["sentiment"].eq("Positive").sum()
positive_rate = (positive_count / total_comments * 100) if total_comments else 0

product_related_df = filtered_df[
    filtered_df["reaction_target"].isin(PRODUCT_RELATED_TARGETS)
].copy()

product_related_count = len(product_related_df)
product_positive_count = product_related_df["sentiment"].eq("Positive").sum()
product_positive_rate = (
    product_positive_count / product_related_count * 100
    if product_related_count
    else 0
)

avg_likes = filtered_df["diggCount"].mean() if total_comments else 0

k1, k2, k3, k4 = st.columns(4)

cards = [
    ("일본어 댓글 수", f"{total_comments:,}"),
    ("전체 콘텐츠 긍정률", f"{positive_rate:.1f}%"),
    ("제품 관련 긍정률", f"{product_positive_rate:.1f}%"),
    ("제품 관련 댓글", f"{product_related_count:,}"),
]

for col, (label, value) in zip([k1, k2, k3, k4], cards):
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# -----------------------------
# 차트 헬퍼
# -----------------------------
def horizontal_bar_chart(
    dataframe,
    label_col,
    value_col="댓글 수",
    height=260,
    color=VIDIVICI_BLACK,
):
    if dataframe.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    chart = (
        alt.Chart(dataframe)
        .mark_bar(
            cornerRadiusEnd=7,
            color=color,
        )
        .encode(
            x=alt.X(
                f"{value_col}:Q",
                title=value_col,
                axis=alt.Axis(
                    grid=True,
                    gridColor=VIDIVICI_GRID,
                    domain=False,
                    tickColor="#D8D2CC",
                ),
            ),
            y=alt.Y(
                f"{label_col}:N",
                sort="-x",
                title=None,
                axis=alt.Axis(
                    labelLimit=230,
                    domain=False,
                    ticks=False,
                ),
            ),
            tooltip=[label_col, value_col],
        )
        .properties(height=height)
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)


# -----------------------------
# 감성 분석
# -----------------------------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("감성 분포")
    sentiment_df = (
        filtered_df["sentiment"]
        .value_counts()
        .rename_axis("감성")
        .reset_index(name="댓글 수")
    )
    horizontal_bar_chart(
        sentiment_df,
        "감성",
        height=230,
        color=VIDIVICI_BLACK,
    )

with right:
    st.subheader("제품 관련 댓글 감성")
    st.markdown(
        '<div class="section-note">제품 반응 · 피부 표현/메이크업 · 구매/문의 댓글만 집계</div>',
        unsafe_allow_html=True,
    )

    product_sentiment_df = (
        product_related_df["sentiment"]
        .value_counts()
        .rename_axis("감성")
        .reset_index(name="댓글 수")
    )

    horizontal_bar_chart(
        product_sentiment_df,
        "감성",
        height=230,
        color=VIDIVICI_ROSE,
    )

# -----------------------------
# 관심 주제 / 반응 대상
# -----------------------------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("관심 주제 분포")
    st.markdown(
        '<div class="section-note">모델·출연자 반응은 제외하고 제품/소비자 관심 주제만 표시</div>',
        unsafe_allow_html=True,
    )

    # 중요: 관심 주제 차트에서는 모델·출연자 반응을 제외
    topic_df = filtered_df[
        filtered_df["category"] != "모델·출연자 반응"
    ].copy()

    category_df = (
        topic_df["category"]
        .value_counts()
        .rename_axis("관심 주제")
        .reset_index(name="댓글 수")
    )

    horizontal_bar_chart(
        category_df,
        "관심 주제",
        height=320,
        color=VIDIVICI_TAUPE,
    )

with right:
    st.subheader("반응 대상 분포")
    st.markdown(
        '<div class="section-note">제품, 메이크업, 출연자, 구매 관심을 별도로 구분</div>',
        unsafe_allow_html=True,
    )

    reaction_df = (
        filtered_df["reaction_target"]
        .value_counts()
        .rename_axis("반응 대상")
        .reset_index(name="댓글 수")
    )

    # 기타를 제외한 핵심 반응만 시각적으로 강조
    reaction_df["색상"] = reaction_df["반응 대상"].apply(
        lambda x: VIDIVICI_BEIGE if x == "기타" else VIDIVICI_BLACK
    )

    chart = (
        alt.Chart(reaction_df)
        .mark_bar(cornerRadiusEnd=7)
        .encode(
            x=alt.X(
                "댓글 수:Q",
                title="댓글 수",
                axis=alt.Axis(
                    grid=True,
                    gridColor=VIDIVICI_GRID,
                    domain=False,
                ),
            ),
            y=alt.Y(
                "반응 대상:N",
                sort="-x",
                title=None,
                axis=alt.Axis(
                    labelLimit=230,
                    domain=False,
                    ticks=False,
                ),
            ),
            color=alt.Color(
                "색상:N",
                scale=None,
                legend=None,
            ),
            tooltip=["반응 대상", "댓글 수"],
        )
        .properties(height=320)
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)

st.divider()

# -----------------------------
# 좋아요 TOP 댓글
# -----------------------------
st.subheader("좋아요 TOP 20 댓글")
st.markdown(
    '<div class="section-note">공감이 많이 발생한 댓글을 반응 대상과 함께 확인합니다.</div>',
    unsafe_allow_html=True,
)

sort_cols = ["diggCount"]
ascending = [False]

if "createTimeISO" in filtered_df.columns:
    sort_cols.append("createTimeISO")
    ascending.append(False)

top_comments = (
    filtered_df
    .sort_values(sort_cols, ascending=ascending)
    .head(20)
    .copy()
)

top_display = pd.DataFrame({
    "댓글": top_comments["text"],
    "좋아요": top_comments["diggCount"],
    "감성": top_comments["sentiment"],
    "반응 대상": top_comments["reaction_target"],
    "관심 주제": top_comments["category"],
    "영상": top_comments["videoWebUrl"],
})

st.dataframe(
    top_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "댓글": st.column_config.TextColumn("댓글", width="large"),
        "좋아요": st.column_config.NumberColumn("좋아요", width="small"),
        "감성": st.column_config.TextColumn("감성", width="small"),
        "반응 대상": st.column_config.TextColumn("반응 대상", width="medium"),
        "관심 주제": st.column_config.TextColumn("관심 주제", width="medium"),
        "영상": st.column_config.LinkColumn(
            "TikTok",
            display_text="영상 열기",
            width="small",
        ),
    },
)

# -----------------------------
# 전체 댓글
# -----------------------------
st.subheader("전체 댓글 데이터")

display_df = pd.DataFrame({
    "댓글": filtered_df["text"],
    "좋아요": filtered_df["diggCount"],
    "감성": filtered_df["sentiment"],
    "관심 주제": filtered_df["category"],
    "반응 대상": filtered_df["reaction_target"],
    "TikTok": filtered_df["videoWebUrl"],
})

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "댓글": st.column_config.TextColumn("댓글", width="large"),
        "좋아요": st.column_config.NumberColumn("좋아요", width="small"),
        "감성": st.column_config.TextColumn("감성", width="small"),
        "관심 주제": st.column_config.TextColumn("관심 주제", width="medium"),
        "반응 대상": st.column_config.TextColumn("반응 대상", width="medium"),
        "TikTok": st.column_config.LinkColumn(
            "TikTok",
            display_text="영상 열기",
            width="small",
        ),
    },
)

# -----------------------------
# 다운로드
# -----------------------------
csv_data = filtered_df.to_csv(
    index=False,
    encoding="utf-8-sig",
)

st.download_button(
    label="필터 적용 분석 결과 CSV 다운로드",
    data=csv_data,
    file_name="vidivici_filtered_analysis.csv",
    mime="text/csv",
)

st.caption(
    f"현재 필터 기준 평균 댓글 좋아요 {avg_likes:.1f} · "
    "전체 콘텐츠 긍정률과 제품 관련 긍정률은 별도 지표로 해석합니다."
)
