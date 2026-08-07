
import pandas as pd
import streamlit as st
import altair as alt

# Optional automatic translation.
# If deep-translator is unavailable or the external service fails,
# the dashboard still runs and shows the original Japanese text.
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except Exception:
    TRANSLATOR_AVAILABLE = False


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

# -----------------------------
# 데이터 보완용 반응 대상 분류
# -----------------------------
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

    # 일본 시장 전용
    df = df[df["language"] == "Japanese"].copy()

    return df


df = load_data()

# -----------------------------
# 번역
# -----------------------------
@st.cache_data(show_spinner=False)
def translate_batch_to_korean(texts):
    texts = [str(x) for x in texts]

    if not TRANSLATOR_AVAILABLE:
        return [""] * len(texts)

    translator = GoogleTranslator(source="ja", target="ko")
    translated = []

    # 실패해도 대시보드 전체가 멈추지 않도록 한 줄씩 안전 처리
    for text in texts:
        if not text.strip():
            translated.append("")
            continue

        try:
            translated.append(translator.translate(text))
        except Exception:
            translated.append("")

    return translated


# -----------------------------
# 브랜드 스타일
# -----------------------------
BLACK = "#141414"
CREAM = "#F7F3EE"
BEIGE = "#B9AA9A"
ROSE = "#C48C8C"
GRAY = "#77716B"
LIGHT_GRAY = "#EEE9E4"
OTHER = "#E8E1D9"

st.markdown(
    f"""
    <style>
        .stApp {{
            background: #FCFBFA;
        }}

        .block-container {{
            max-width: 1480px;
            padding-top: 4.2rem !important;
            padding-bottom: 3rem;
        }}

        [data-testid="stSidebar"] {{
            background: #F6F3F0;
            border-right: 1px solid #ECE7E2;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            padding-top: 2.2rem;
        }}

        .brand-kicker {{
            font-size: 0.78rem;
            letter-spacing: 0.16em;
            color: {BEIGE};
            font-weight: 700;
            margin-bottom: 0.4rem;
        }}

        .main-title {{
            color: {BLACK};
            font-size: 2.2rem;
            line-height: 1.2;
            font-weight: 800;
            margin-bottom: 0.35rem;
        }}

        .sub-title {{
            color: {GRAY};
            font-size: 0.96rem;
            margin-bottom: 1.6rem;
        }}

        .section-eyebrow {{
            color: {BEIGE};
            font-size: 0.78rem;
            letter-spacing: 0.12em;
            font-weight: 700;
            margin-bottom: 0.2rem;
        }}

        .section-title {{
            color: {BLACK};
            font-size: 1.55rem;
            line-height: 1.25;
            font-weight: 800;
            margin-bottom: 0.2rem;
        }}

        .section-note {{
            color: #8A837D;
            font-size: 0.88rem;
            margin-bottom: 0.9rem;
        }}

        .metric-card {{
            background: #FFFFFF;
            border: 1px solid {LIGHT_GRAY};
            border-radius: 18px;
            padding: 18px 20px;
            min-height: 108px;
            box-shadow: 0 4px 18px rgba(17,17,17,0.035);
        }}

        .metric-label {{
            color: {GRAY};
            font-size: 0.87rem;
            margin-bottom: 8px;
        }}

        .metric-value {{
            color: {BLACK};
            font-size: 1.78rem;
            font-weight: 800;
            line-height: 1.15;
        }}

        div[data-testid="stDataFrame"] {{
            border-radius: 14px;
            overflow: hidden;
        }}

        .stDownloadButton button {{
            border-radius: 12px;
            border: 1px solid #CFC6BD;
            background: #FFFFFF;
            color: {BLACK};
            font-weight: 700;
        }}

        /* multiselect의 강한 빨간 태그 제거 */
        [data-baseweb="tag"] {{
            background-color: #E8E1D9 !important;
            color: #2B2927 !important;
            border-radius: 8px !important;
        }}

        [data-baseweb="tag"] svg {{
            fill: #5F5953 !important;
        }}

        /* 사이드바 버튼 */
        [data-testid="stSidebar"] button {{
            border-radius: 10px;
        }}

        /* 체크박스의 포인트 컬러를 중성적으로 */
        [data-testid="stCheckbox"] {{
            color: {BLACK};
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand-kicker">VIDIVICI · JAPAN SOCIAL LISTENING</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">VIDIVICI Japan TikTok Consumer Insight</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">일본 TikTok 댓글에서 콘텐츠 반응과 제품 관련 인사이트를 분리해 확인합니다.</div>',
    unsafe_allow_html=True,
)

# -----------------------------
# 사이드바 필터
# -----------------------------
st.sidebar.header("필터")
st.sidebar.caption("시장: Japan · 분석 언어: Japanese")

sentiment_options = sorted(df["sentiment"].dropna().unique().tolist())
category_options = sorted(df["category"].dropna().unique().tolist())
reaction_options = sorted(df["reaction_target"].dropna().unique().tolist())

# 전체 선택 여부를 명확히 제공
sentiment_all = st.sidebar.checkbox("감성 전체 선택", value=True)
if sentiment_all:
    selected_sentiments = sentiment_options
else:
    selected_sentiments = st.sidebar.multiselect(
        "감성 선택",
        options=sentiment_options,
        default=sentiment_options,
    )

category_all = st.sidebar.checkbox("관심 주제 전체 선택", value=True)
if category_all:
    selected_categories = category_options
else:
    selected_categories = st.sidebar.multiselect(
        "관심 주제 선택",
        options=category_options,
        default=category_options,
        help="삭제한 항목도 이 목록에서 다시 선택할 수 있습니다.",
    )

reaction_all = st.sidebar.checkbox("반응 대상 전체 선택", value=True)
if reaction_all:
    selected_reactions = reaction_options
else:
    selected_reactions = st.sidebar.multiselect(
        "반응 대상 선택",
        options=reaction_options,
        default=reaction_options,
        help="삭제한 항목도 이 목록에서 다시 선택할 수 있습니다.",
    )

st.sidebar.markdown("---")
st.sidebar.markdown("**키워드 검색**")
st.sidebar.caption("일본어 댓글 원문에서 입력한 단어가 포함된 댓글만 찾습니다.")
search_text = st.sidebar.text_input(
    "검색어",
    placeholder="예: ファンデ / 毛穴 / かわいい",
    label_visibility="collapsed",
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

model_count = filtered_df["reaction_target"].eq("모델·출연자 반응").sum()
model_share = (model_count / total_comments * 100) if total_comments else 0
avg_likes = filtered_df["diggCount"].mean() if total_comments else 0

# -----------------------------
# CONTENT RESPONSE
# -----------------------------
st.markdown('<div class="section-eyebrow">CONTENT RESPONSE</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">콘텐츠 반응</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">댓글이 콘텐츠와 출연자에게 어떻게 반응했는지 확인합니다.</div>',
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
content_cards = [
    ("일본어 댓글 수", f"{total_comments:,}"),
    ("전체 콘텐츠 긍정률", f"{positive_rate:.1f}%"),
    ("모델·출연자 반응 비중", f"{model_share:.1f}%"),
]

for col, (label, value) in zip([c1, c2, c3], content_cards):
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

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# PRODUCT INSIGHT
# -----------------------------
st.markdown('<div class="section-eyebrow">PRODUCT INSIGHT</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">제품 인사이트</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">제품 반응 · 피부 표현/메이크업 · 구매/문의 댓글을 제품 관련 반응으로 집계합니다.</div>',
    unsafe_allow_html=True,
)

p1, p2 = st.columns(2)

for col, (label, value) in zip(
    [p1, p2],
    [
        ("제품 관련 긍정률", f"{product_positive_rate:.1f}%"),
        ("제품 관련 댓글 수", f"{product_related_count:,}"),
    ],
):
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
def horizontal_bar_chart(dataframe, label_col, color, height=240):
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
                "댓글 수:Q",
                title="댓글 수",
                axis=alt.Axis(
                    grid=True,
                    gridColor=LIGHT_GRAY,
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
            tooltip=[label_col, "댓글 수"],
        )
        .properties(height=height)
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)


# -----------------------------
# 감성 차트
# -----------------------------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("Sentiment Overview")
    st.caption("전체 댓글의 긍정 · 중립 · 부정 반응")
    sentiment_df = (
        filtered_df["sentiment"]
        .value_counts()
        .rename_axis("감성")
        .reset_index(name="댓글 수")
    )
    horizontal_bar_chart(sentiment_df, "감성", BLACK, height=220)

with right:
    st.subheader("Product Sentiment")
    st.caption("제품 관련 댓글의 긍정 · 중립 · 부정 반응")
    product_sentiment_df = (
        product_related_df["sentiment"]
        .value_counts()
        .rename_axis("감성")
        .reset_index(name="댓글 수")
    )
    horizontal_bar_chart(product_sentiment_df, "감성", ROSE, height=220)

# -----------------------------
# 관심 주제 / 반응 대상
# -----------------------------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("Consumer Interests")
    st.caption("모델·출연자 반응은 제외하고 제품·소비자 관심 주제만 표시")

    topic_df = filtered_df[
        filtered_df["category"] != "모델·출연자 반응"
    ].copy()

    category_df = (
        topic_df["category"]
        .value_counts()
        .rename_axis("관심 주제")
        .reset_index(name="댓글 수")
    )

    horizontal_bar_chart(category_df, "관심 주제", BEIGE, height=300)

with right:
    st.subheader("Reaction Focus")
    st.caption("댓글이 제품, 메이크업, 출연자, 구매 관심 중 어디에 반응했는지 표시")

    reaction_df = (
        filtered_df["reaction_target"]
        .value_counts()
        .rename_axis("반응 대상")
        .reset_index(name="댓글 수")
    )

    reaction_df["색상"] = reaction_df["반응 대상"].apply(
        lambda x: OTHER if x == "기타" else BLACK
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
                    gridColor=LIGHT_GRAY,
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
        .properties(height=300)
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)

st.divider()

# -----------------------------
# 번역 옵션
# -----------------------------
translation_enabled = st.toggle(
    "한국어 번역 보기",
    value=False,
    help="켜면 현재 필터 결과의 일본어 댓글을 한국어로 번역합니다. 처음 실행 시 시간이 조금 걸릴 수 있습니다.",
)

if translation_enabled:
    with st.spinner("일본어 댓글을 한국어로 번역하고 있습니다..."):
        translations = translate_batch_to_korean(filtered_df["text"].tolist())
        filtered_df = filtered_df.copy()
        filtered_df["translation_ko"] = translations

# -----------------------------
# 좋아요 TOP 20
# -----------------------------
st.subheader("Top Comments")
st.caption("좋아요가 많이 발생한 댓글을 우선 확인합니다.")

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

top_data = {
    "댓글": top_comments["text"],
}

if translation_enabled:
    top_data["한국어 번역"] = top_comments["translation_ko"]

top_data.update({
    "좋아요": top_comments["diggCount"],
    "감성": top_comments["sentiment"],
    "반응 대상": top_comments["reaction_target"],
    "관심 주제": top_comments["category"],
    "영상": top_comments["videoWebUrl"],
})

top_display = pd.DataFrame(top_data)

top_column_config = {
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
}

if translation_enabled:
    top_column_config["한국어 번역"] = st.column_config.TextColumn(
        "한국어 번역",
        width="large",
    )

st.dataframe(
    top_display,
    use_container_width=True,
    hide_index=True,
    column_config=top_column_config,
)

# -----------------------------
# 전체 댓글
# -----------------------------
st.subheader("All Comments")
st.caption("현재 필터 조건에 해당하는 댓글 전체")

all_data = {
    "댓글": filtered_df["text"],
}

if translation_enabled:
    all_data["한국어 번역"] = filtered_df["translation_ko"]

all_data.update({
    "좋아요": filtered_df["diggCount"],
    "감성": filtered_df["sentiment"],
    "관심 주제": filtered_df["category"],
    "반응 대상": filtered_df["reaction_target"],
    "TikTok": filtered_df["videoWebUrl"],
})

display_df = pd.DataFrame(all_data)

all_column_config = {
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
}

if translation_enabled:
    all_column_config["한국어 번역"] = st.column_config.TextColumn(
        "한국어 번역",
        width="large",
    )

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config=all_column_config,
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
    "전체 콘텐츠 반응과 제품 관련 반응은 별도 지표로 해석합니다."
)
