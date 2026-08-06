
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="VIDIVICI Japan TikTok Dashboard",
    page_icon="💬",
    layout="wide",
)


@st.cache_data
def load_data():
    df = pd.read_csv("vidivici_comments_final.csv")

    df["diggCount"] = pd.to_numeric(
        df["diggCount"],
        errors="coerce",
    ).fillna(0).astype(int)

    df["createTimeISO"] = pd.to_datetime(
        df["createTimeISO"],
        errors="coerce",
    )

    return df


df = load_data()


st.title("VIDIVICI Japan TikTok Consumer Insight")
st.caption("일본 TikTok 소비자 댓글 감성 및 관심 주제 분석")


# 사이드바 필터
st.sidebar.header("필터")

language_options = sorted(df["language"].dropna().unique())

selected_languages = st.sidebar.multiselect(
    "언어",
    options=language_options,
    default=language_options,
)

sentiment_options = sorted(df["sentiment"].dropna().unique())

selected_sentiments = st.sidebar.multiselect(
    "감성",
    options=sentiment_options,
    default=sentiment_options,
)

category_options = sorted(df["category"].dropna().unique())

selected_categories = st.sidebar.multiselect(
    "관심 주제",
    options=category_options,
    default=category_options,
)

search_text = st.sidebar.text_input(
    "댓글 검색",
    placeholder="검색어를 입력하세요",
)


filtered_df = df[
    df["language"].isin(selected_languages)
    & df["sentiment"].isin(selected_sentiments)
    & df["category"].isin(selected_categories)
].copy()

if search_text:
    filtered_df = filtered_df[
        filtered_df["text"]
        .astype(str)
        .str.contains(search_text, case=False, na=False)
    ]


# KPI
total_comments = len(filtered_df)

positive_count = (
    filtered_df["sentiment"]
    .eq("Positive")
    .sum()
)

positive_rate = (
    positive_count / total_comments * 100
    if total_comments > 0
    else 0
)

average_likes = (
    filtered_df["diggCount"].mean()
    if total_comments > 0
    else 0
)

japanese_count = (
    filtered_df["language"]
    .eq("Japanese")
    .sum()
)

japanese_rate = (
    japanese_count / total_comments * 100
    if total_comments > 0
    else 0
)


col1, col2, col3, col4 = st.columns(4)

col1.metric("댓글 수", f"{total_comments:,}")
col2.metric("긍정 비율", f"{positive_rate:.1f}%")
col3.metric("평균 좋아요", f"{average_likes:.1f}")
col4.metric("일본어 비율", f"{japanese_rate:.1f}%")


st.divider()


# 감성 분포
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


# 언어 분포
with col2:
    st.subheader("언어 분포")

    language_chart = (
        filtered_df["language"]
        .value_counts()
        .rename_axis("언어")
        .to_frame("댓글 수")
    )

    st.bar_chart(language_chart)


# 관심 주제
st.subheader("관심 주제 분포")

category_chart = (
    filtered_df["category"]
    .value_counts()
    .rename_axis("관심 주제")
    .to_frame("댓글 수")
)

st.bar_chart(category_chart)


# 좋아요 상위 댓글
st.subheader("좋아요 TOP 20 댓글")

top_comments = (
    filtered_df
    .sort_values("diggCount", ascending=False)
    .head(20)
)

display_columns = [
    "text",
    "diggCount",
    "language",
    "sentiment",
    "category",
    "videoWebUrl",
]

st.dataframe(
    top_comments[display_columns],
    use_container_width=True,
    hide_index=True,
)


# 전체 데이터
st.subheader("전체 댓글 데이터")

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
)


# CSV 다운로드
csv_data = filtered_df.to_csv(
    index=False,
    encoding="utf-8-sig",
)

st.download_button(
    label="분석 결과 CSV 다운로드",
    data=csv_data,
    file_name="vidivici_filtered_analysis.csv",
    mime="text/csv",
)
