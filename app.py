import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="VIDIVICI Japan TikTok Dashboard",
    page_icon="💬",
    layout="wide",
)

DATA_FILE = "vidivici_comments_final.csv"

TARGET_KEYWORDS = {
    "모델·출연자 반응": [
        "かわいい", "可愛い", "可愛すぎ", "美人", "綺麗", "きれい",
        "顔", "ビジュ", "ビジュアル", "似合う", "ちゃん", "女の子",
        "モデル", "推し", "好き", "最高", "神", "尊い", "美女",
        "イケメン", "美しい",
    ],
    "제품 반응": [
        "ファンデ", "ファンデーション", "クッション", "プライマー",
        "リップ", "ブラッシュ", "カバー", "カバー力", "崩れ",
        "崩れない", "崩れにくい", "毛穴", "乾燥", "保湿", "密着",
        "持ち", "テクスチャ", "伸び", "発色", "色味", "軽い",
        "しっとり", "サラサラ",
    ],
    "피부 표현·메이크업": [
        "ツヤ", "艶", "透明感", "仕上がり", "肌", "肌綺麗",
        "ナチュラル", "マット", "メイク", "トーンアップ", "発光",
        "水光", "陶器肌", "血色", "うるおい",
    ],
    "구매·문의": [
        "欲しい", "欲しかった", "買う", "買った", "買いたい", "購入",
        "注文", "メガ割", "qoo10", "どこで買える", "どこで売ってる",
        "気になる", "何色", "何番", "おすすめ", "使ったことある",
        "教えて",
    ],
}

REACTION_PRIORITY = [
    "제품 반응",
    "피부 표현·메이크업",
    "구매·문의",
    "모델·출연자 반응",
]

PRODUCT_RELATED_TARGETS = {
    "제품 반응",
    "피부 표현·메이크업",
    "구매·문의",
}


def classify_reaction_target(text: object) -> str:
    value = str(text).lower()
    matched = []

    for target, keywords in TARGET_KEYWORDS.items():
        if any(keyword.lower() in value for keyword in keywords):
            matched.append(target)

    for target in REACTION_PRIORITY:
        if target in matched:
            return target

    return "기타"



def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_FILE)

    required_columns = {
        "text",
        "diggCount",
        "language",
        "sentiment",
        "category",
        "videoWebUrl",
    }
    missing = required_columns.difference(df.columns)
    if missing:
        raise ValueError(f"CSV에 필요한 컬럼이 없습니다: {sorted(missing)}")

    df["text"] = df["text"].fillna("").astype(str)
    df["diggCount"] = pd.to_numeric(
        df["diggCount"], errors="coerce"
    ).fillna(0).astype(int)

    if "createTimeISO" in df.columns:
        df["createTimeISO"] = pd.to_datetime(
            df["createTimeISO"], errors="coerce", utc=True
        )

    # 최신 CSV에 reaction_target이 없더라도 앱에서 자동 생성합니다.
    if "reaction_target" not in df.columns:
        df["reaction_target"] = df["text"].apply(classify_reaction_target)
    else:
        df["reaction_target"] = (
            df["reaction_target"].fillna("기타").astype(str)
        )

    return df


def safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator * 100 if denominator else 0.0


try:
    df = load_data()
except Exception as exc:
    st.error(f"데이터를 불러오지 못했습니다: {exc}")
    st.stop()

st.title("VIDIVICI Japan TikTok Consumer Insight")
st.caption(
    "일본 TikTok 댓글의 감성, 관심 주제, 반응 대상을 구분한 소비자 반응 대시보드"
)

# 사이드바 필터
st.sidebar.header("필터")

language_options = sorted(df["language"].dropna().unique().tolist())
default_languages = (
    ["Japanese"] if "Japanese" in language_options else language_options
)
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
    placeholder="일본어 또는 키워드를 입력하세요",
)

filtered_df = df[
    df["language"].isin(selected_languages)
    & df["sentiment"].isin(selected_sentiments)
    & df["category"].isin(selected_categories)
    & df["reaction_target"].isin(selected_reactions)
].copy()

if search_text:
    filtered_df = filtered_df[
        filtered_df["text"].str.contains(
            search_text,
            case=False,
            na=False,
            regex=False,
        )
    ].copy()

# KPI
all_count = len(filtered_df)
all_positive_count = filtered_df["sentiment"].eq("Positive").sum()
all_positive_rate = safe_rate(all_positive_count, all_count)

product_df = filtered_df[
    filtered_df["reaction_target"].isin(PRODUCT_RELATED_TARGETS)
].copy()
product_count = len(product_df)
product_positive_count = product_df["sentiment"].eq("Positive").sum()
product_positive_rate = safe_rate(product_positive_count, product_count)

average_likes = filtered_df["diggCount"].mean() if all_count else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("표시 댓글 수", f"{all_count:,}")
col2.metric("전체 긍정 비율", f"{all_positive_rate:.1f}%")
col3.metric("제품 관련 긍정 비율", f"{product_positive_rate:.1f}%")
col4.metric("제품 관련 댓글 수", f"{product_count:,}")

st.caption(
    "제품 관련 지표는 제품 반응, 피부 표현·메이크업, 구매·문의 댓글을 합산합니다."
)
st.divider()

# 핵심 차트
col1, col2 = st.columns(2)

with col1:
    st.subheader("감성 분포")
    sentiment_chart = (
        filtered_df["sentiment"]
        .value_counts()
        .rename_axis("감성")
        .to_frame("댓글 수")
    )
    st.bar_chart(sentiment_chart)

with col2:
    st.subheader("반응 대상 분포")
    reaction_chart = (
        filtered_df["reaction_target"]
        .value_counts()
        .rename_axis("반응 대상")
        .to_frame("댓글 수")
    )
    st.bar_chart(reaction_chart)

col1, col2 = st.columns(2)

with col1:
    st.subheader("관심 주제 분포")
    category_chart = (
        filtered_df["category"]
        .value_counts()
        .rename_axis("관심 주제")
        .to_frame("댓글 수")
    )
    st.bar_chart(category_chart)

with col2:
    st.subheader("언어 분포")
    language_chart = (
        filtered_df["language"]
        .value_counts()
        .rename_axis("언어")
        .to_frame("댓글 수")
    )
    st.bar_chart(language_chart)

st.divider()

# 제품 관련 감성
st.subheader("제품 관련 댓글 감성")
if product_df.empty:
    st.info("현재 필터 조건에 해당하는 제품 관련 댓글이 없습니다.")
else:
    product_sentiment_chart = (
        product_df["sentiment"]
        .value_counts()
        .rename_axis("감성")
        .to_frame("댓글 수")
    )
    st.bar_chart(product_sentiment_chart)

# 좋아요 상위 댓글
st.subheader("좋아요 TOP 20 댓글")
top_comments = filtered_df.sort_values("diggCount", ascending=False).head(20)

display_columns = [
    "text",
    "diggCount",
    "sentiment",
    "category",
    "reaction_target",
    "videoWebUrl",
]

column_config = {
    "text": st.column_config.TextColumn("댓글", width="large"),
    "diggCount": st.column_config.NumberColumn("좋아요", format="%d"),
    "sentiment": "감성",
    "category": "관심 주제",
    "reaction_target": "반응 대상",
    "videoWebUrl": st.column_config.LinkColumn(
        "TikTok 영상",
        display_text="영상 열기",
    ),
}

st.dataframe(
    top_comments[display_columns],
    use_container_width=True,
    hide_index=True,
    column_config=column_config,
)

# 전체 데이터
st.subheader("전체 댓글 데이터")
st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
    column_config=column_config,
)

# CSV 다운로드
csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="현재 필터 결과 CSV 다운로드",
    data=csv_data,
    file_name="vidivici_filtered_analysis.csv",
    mime="text/csv",
)
