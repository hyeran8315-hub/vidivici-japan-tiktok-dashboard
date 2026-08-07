
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(
    page_title="VIDIVICI Japan TikTok Dashboard",
    page_icon="💬",
    layout="wide",
)

DATA_FILE = "vidivici_comments_final.csv"

PRODUCT_RELATED_TARGETS = [
    "제품 반응",
    "피부 표현·메이크업",
    "구매·문의",
]

# reaction_target 컬럼이 없는 구버전 CSV도 실행되도록 보완
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

# ---------- STYLE ----------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        .main-title {
            font-size: 2.15rem;
            font-weight: 800;
            margin-bottom: 0.15rem;
        }
        .sub-title {
            color: #666;
            margin-bottom: 1.4rem;
        }
        .metric-card {
            background: #ffffff;
            border: 1px solid #ececec;
            border-radius: 16px;
            padding: 18px 20px;
            min-height: 112px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        }
        .metric-label {
            color: #777;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 1.8rem;
            font-weight: 800;
            line-height: 1.2;
        }
        .section-note {
            color: #777;
            font-size: 0.9rem;
            margin-top: -8px;
            margin-bottom: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">VIDIVICI Japan TikTok Consumer Insight</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">일본 TikTok 소비자 댓글 감성 · 관심 주제 · 반응 대상 분석</div>',
    unsafe_allow_html=True,
)

# ---------- SIDEBAR ----------
st.sidebar.header("필터")

language_options = sorted(df["language"].dropna().unique().tolist())
default_languages = ["Japanese"] if "Japanese" in language_options else language_options

selected_languages = st.sidebar.multiselect(
    "언어",
    options=language_options,
    default=default_languages,
)

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
    df["language"].isin(selected_languages)
    & df["sentiment"].isin(selected_sentiments)
    & df["category"].isin(selected_categories)
    & df["reaction_target"].isin(selected_reactions)
].copy()

if search_text:
    filtered_df = filtered_df[
        filtered_df["text"]
        .astype(str)
        .str.contains(search_text, case=False, na=False, regex=False)
    ]

# ---------- KPI ----------
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

with k1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">일본어 댓글 수</div>
            <div class="metric-value">{total_comments:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">전체 콘텐츠 긍정률</div>
            <div class="metric-value">{positive_rate:.1f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">제품 관련 긍정률</div>
            <div class="metric-value">{product_positive_rate:.1f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">제품 관련 댓글</div>
            <div class="metric-value">{product_related_count:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# ---------- HELPERS ----------
def horizontal_bar_chart(dataframe, label_col, value_col="댓글 수", height=280):
    if dataframe.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    chart = (
        alt.Chart(dataframe)
        .mark_bar(cornerRadiusEnd=5)
        .encode(
            x=alt.X(f"{value_col}:Q", title=value_col),
            y=alt.Y(
                f"{label_col}:N",
                sort="-x",
                title=None,
                axis=alt.Axis(labelLimit=220),
            ),
            tooltip=[label_col, value_col],
        )
        .properties(height=height)
    )
    st.altair_chart(chart, use_container_width=True)


# ---------- CHARTS ----------
left, right = st.columns(2)

with left:
    st.subheader("감성 분포")
    sentiment_df = (
        filtered_df["sentiment"]
        .value_counts()
        .rename_axis("감성")
        .reset_index(name="댓글 수")
    )
    horizontal_bar_chart(sentiment_df, "감성", height=230)

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
    horizontal_bar_chart(product_sentiment_df, "감성", height=230)

left, right = st.columns(2)

with left:
    st.subheader("관심 주제 분포")
    category_df = (
        filtered_df["category"]
        .value_counts()
        .rename_axis("관심 주제")
        .reset_index(name="댓글 수")
    )
    horizontal_bar_chart(category_df, "관심 주제", height=320)

with right:
    st.subheader("반응 대상 분포")
    reaction_df = (
        filtered_df["reaction_target"]
        .value_counts()
        .rename_axis("반응 대상")
        .reset_index(name="댓글 수")
    )
    horizontal_bar_chart(reaction_df, "반응 대상", height=320)

st.divider()

# ---------- TOP COMMENTS ----------
st.subheader("좋아요 TOP 20 댓글")
st.markdown(
    '<div class="section-note">공감이 많이 발생한 댓글을 반응 대상과 함께 확인합니다.</div>',
    unsafe_allow_html=True,
)

top_comments = (
    filtered_df
    .sort_values(["diggCount", "createTimeISO"] if "createTimeISO" in filtered_df.columns else ["diggCount"],
                 ascending=False)
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
        "영상": st.column_config.LinkColumn(
            "TikTok",
            display_text="영상 열기",
        )
    },
)

# ---------- ALL COMMENTS ----------
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
        "TikTok": st.column_config.LinkColumn(
            "TikTok",
            display_text="영상 열기",
        )
    },
)

# ---------- DOWNLOAD ----------
csv_data = filtered_df.to_csv(
    index=False,
    encoding="utf-8-sig",
)

st.download_button(
    label="필터 적용 분석 결과 CSV 다운로드",
    data=csv_data,
    file_name="vidivici_filtered_analysis.csv",
    mime="text/csv",
    use_container_width=False,
)

st.caption(
    f"현재 필터 기준 평균 댓글 좋아요: {avg_likes:.1f} · "
    "감성은 콘텐츠 전체 반응과 제품 관련 반응을 구분해 해석하세요."
)
