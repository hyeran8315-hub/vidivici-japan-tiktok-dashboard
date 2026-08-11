
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path


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
        "ツヤ", "艶", "つや", "透明感", "仕上がり", "肌", "肌綺麗",
        "ナチュラル", "マット", "メイク", "トーンアップ",
        "発光", "水光", "陶器肌", "血色", "うるおい",
        "もちもち", "もちっ", "うるうる", "つるつる"
    ],
    "구매·문의": [
        "欲しい", "欲しかった", "買う", "買った", "買いたい",
        "買お", "買っちゃ", "ポチ", "再販",
        "購入", "注文", "メガ割", "Qoo10", "どこで買える",
        "どこで売ってる", "気になる", "何色", "何番",
        "おすすめ", "使ったことある", "教えて"
    ],
}



# 기존 "기타"를 해석 가능한 소비자 관심으로 세분화합니다.
# 순서가 우선순위입니다. 위에서부터 먼저 일치하는 카테고리로 분류됩니다.
CATEGORY_REFINEMENT = {
    "호감·감탄": [
        "最高", "すご", "素敵", "好き", "かわい", "可愛",
        "美しい", "綺麗", "きれい", "キレイ", "神", "尊い",
        "良い", "いい", "憧れ", "結婚したい"
    ],
    "사용 후기·경험": [
        "使ってみた", "使用感", "レビュー", "リピート", "愛用",
        "使い続けて", "使った感想", "感想", "使ってから", "リピ買い"
    ],
    "정보·질문": [
        "どこで買える", "どこで売ってる", "いくら", "値段",
        "何色", "何番", "サイズ", "って何",
        "知りたい", "ませんか"
    ],
    "제품 관심·탐색": [
        "気になる", "使ってみたい", "試したい", "欲しい",
        "何", "どこの", "どれ", "教えて", "おすすめ"
    ],
    "메이크업 룩": [
        "メイク", "ベースメイク", "仕上がり", "ツヤ", "艶",
        "透明感", "肌", "ビジュ"
    ],
    "콘텐츠·소통": [
        "動画", "投稿", "配信", "面白", "楽しい", "シェア",
        "保存", "コメント", "チャンネル", "フォロー",
        "ライブ", "イベント", "ワロタ"
    ],
}

def refine_interest_category(row):
    current = str(row.get("category", ""))
    if current != "기타":
        return current

    text = str(row.get("text", ""))
    reaction = str(row.get("reaction_target", ""))

    # 반응 대상이 이미 구체적이면 우선 활용
    if reaction == "모델·출연자 반응":
        return "출연자·비주얼"
    if reaction == "피부 표현·메이크업":
        return "메이크업 룩"
    if reaction == "제품 반응":
        return "제품 관심·탐색"
    if reaction == "구매·문의":
        return "제품 관심·탐색"

    for category, keywords in CATEGORY_REFINEMENT.items():
        if any(keyword in text for keyword in keywords):
            return category

    return "기타"

# 기존 반응 대상 "기타"를 세분화합니다.
# reaction_target이 이미 구체적인 값(제품 반응 등)이면 건드리지 않습니다.
REACTION_REFINEMENT = {
    "일반 호감·감탄": [
        "最高", "すご", "素敵", "好き", "神", "尊い", "良い", "いい",
        "かわい", "可愛", "憧れ", "結婚したい"
    ],
    "정보·질문": [
        "教えて", "どこで買える", "どこで売ってる", "いくら",
        "値段", "何色", "何番",
        "知りたい", "ませんか"
    ],
    "콘텐츠 반응": [
        "動画", "投稿", "配信", "面白", "楽しい", "シェア",
        "保存", "コメント", "チャンネル", "フォロー",
        "ライブ", "イベント", "ワロタ"
    ],
}


# -----------------------------
# 모델 피부 칭찬 보정
# "肌"(피부)라는 단어 때문에 모델 칭찬이 제품 반응으로 새는 것을 막습니다.
# 예: "쥬리짱 피부 갖고 싶어요"는 제품이 아니라 출연자에 대한 반응입니다.
# 단, 메이크업·제품 단어가 함께 있으면 제품 관련으로 그대로 둡니다.
# -----------------------------
MODEL_SKIN_HINTS = [
    "ちゃんの肌", "さんの肌", "羨ましい", "うらやましい",
    "肌になりたい", "肌目指す", "肌綺麗すぎ", "肌きれいすぎ",
    "肌がきれいすぎ", "肌が綺麗すぎ",
]

PRODUCT_CONTEXT_WORDS = [
    "メイク", "ファンデ", "クッション", "下地", "プライマー",
    "リップ", "チーク", "商品", "使っ", "何肌", "紹介",
]


def is_model_skin_praise(text):
    value = str(text)
    if not any(hint in value for hint in MODEL_SKIN_HINTS):
        return False
    if any(word in value for word in PRODUCT_CONTEXT_WORDS):
        return False
    return True


def refine_reaction_target(row):
    current = str(row.get("reaction_target", ""))
    text = str(row.get("text", ""))

    # 모델 피부 칭찬이 제품 관련으로 잡혀 있으면 모델 반응으로 되돌립니다.
    if current == "피부 표현·메이크업" and is_model_skin_praise(text):
        return "모델·출연자 반응"

    if current != "기타":
        return current

    # 기존 제품·피부·구매 키워드로 먼저 재확인 (키워드 보강분 반영)
    retry = classify_reaction_target(text)
    if retry != "기타":
        if retry == "피부 표현·메이크업" and is_model_skin_praise(text):
            return "모델·출연자 반응"
        return retry

    for target, keywords in REACTION_REFINEMENT.items():
        if any(keyword in text for keyword in keywords):
            return target

    return "기타"


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


# -----------------------------
# 반응 대상 그룹 (화면 표시용 큰 축)
# 관심 주제와 역할이 겹치지 않도록, 반응 대상은 "무엇에 반응했나"만 크게 나눕니다.
# 세부 값(reaction_target)은 제품 KPI 계산에 그대로 사용됩니다.
# -----------------------------
REACTION_GROUP_MAP = {
    "모델·출연자 반응": "모델·출연자",
    "제품 반응": "제품",
    "피부 표현·메이크업": "제품",
    "구매·문의": "제품",
    "콘텐츠 반응": "콘텐츠",
    "일반 호감·감탄": "일반 반응",
    "정보·질문": "일반 반응",
    "기타": "일반 반응",
}

REACTION_GROUP_ORDER = ["모델·출연자", "제품", "콘텐츠", "일반 반응"]


def to_reaction_group(value):
    return REACTION_GROUP_MAP.get(str(value), "일반 반응")


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

    # 기존 반응 대상 중 "기타"만 댓글 내용으로 추가 세분화
    df["reaction_target"] = df.apply(refine_reaction_target, axis=1)

    if "videoWebUrl" not in df.columns:
        df["videoWebUrl"] = ""

    # 기존 기타 관심 주제를 댓글 내용과 반응 대상으로 재분류
    df["category"] = df.apply(refine_interest_category, axis=1)

    # 화면 표시용 반응 대상 그룹 (세부 reaction_target은 KPI 계산에 그대로 사용)
    df["reaction_group"] = df["reaction_target"].apply(to_reaction_group)

    # 일본 시장 전용
    df = df[df["language"] == "Japanese"].copy()

    return df


df = load_data()

# -----------------------------
# 번역
# -----------------------------
# 실시간 번역 API를 사용하지 않습니다.
# CSV에 translation_ko 컬럼이 있으면 즉시 표시합니다.
HAS_TRANSLATION = "translation_ko" in df.columns

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
            background: #141414;
            border-right: 1px solid #141414;
        }}

        [data-testid="stSidebar"] * {{
            color: #F3EFE9;
        }}

        [data-testid="stSidebar"] input {{
            color: {BLACK};
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
            font-size: 2.9rem;
            line-height: 1.15;
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
            font-weight: 600;
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

        /* multiselect의 강한 빨간 태그 제거 → 베이지 톤 (여러 구조 대응) */
        [data-baseweb="tag"],
        span[data-baseweb="tag"],
        div[data-baseweb="tag"] {{
            background-color: {BEIGE} !important;
            color: {BLACK} !important;
            border-radius: 8px !important;
            border: none !important;
        }}

        [data-baseweb="tag"] svg,
        [data-baseweb="tag"] span {{
            fill: {BLACK} !important;
            color: {BLACK} !important;
        }}

        /* 체크박스 박스 자체 테두리 - 실제 구조(React Aria label > div) 기준 */
        [data-testid="stCheckbox"] label[data-rac] > div:nth-of-type(1),
        [data-testid="stSidebar"] label[data-rac] > div:nth-of-type(1) {{
            border: 2px solid #F3EFE9 !important;
            background-color: transparent !important;
            box-shadow: none !important;
        }}

        /* 체크된 상태는 베이지 톤으로 */
        [data-testid="stCheckbox"] label[data-rac]:has(input:checked) > div:nth-of-type(1),
        [data-testid="stSidebar"] label[data-rac]:has(input:checked) > div:nth-of-type(1) {{
            background-color: {BEIGE} !important;
            border-color: {BEIGE} !important;
        }}

        [data-testid="stCheckbox"] svg {{
            color: {BLACK} !important;
            fill: {BLACK} !important;
        }}

        /* 라디오 버튼(정렬 옵션 등) 선택 색상도 베이지 톤으로 통일 */
        [data-testid="stRadio"] input:checked + div:first-of-type {{
            background-color: {BEIGE} !important;
            border-color: {BEIGE} !important;
        }}

        /* 사이드바 버튼 */
        [data-testid="stSidebar"] button {{
            border-radius: 10px;
        }}

        /* 체크박스의 포인트 컬러를 중성적으로 */
        [data-testid="stCheckbox"] {{
            color: {BLACK};
        }}

        /* 멀티셀렉트 드롭다운(재선택 목록)이 안 보이는 문제 방지 */
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"] {{
            background-color: #FFFFFF !important;
        }}

        [role="option"] {{
            color: {BLACK} !important;
            background-color: #FFFFFF !important;
        }}

        [role="option"]:hover {{
            background-color: {LIGHT_GRAY} !important;
        }}

        /* 제목/서브헤더에 마우스를 올렸을 때 나타나는 연결고리(anchor) 아이콘 숨기기 */
        [data-testid="stHeaderActionElements"] {{
            display: none !important;
        }}

        h1 a, h2 a, h3 a, h4 a, h5 a, h6 a {{
            display: none !important;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand-kicker">VIDIVICI · JAPAN SOCIAL LISTENING</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">VIDIVICI Japan TikTok Consumer Insight</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">일본 TikTok 댓글의 콘텐츠 반응과 제품 인사이트를 확인합니다.</div>',
    unsafe_allow_html=True,
)

caption_parts = []

collected_file = Path("last_updated.txt")
if collected_file.exists():
    collected_at = collected_file.read_text(encoding="utf-8").strip()
    if collected_at:
        caption_parts.append(f"최근 수집일: {collected_at}")

if "createTimeISO" in df.columns and df["createTimeISO"].notna().any():
    latest_comment = df["createTimeISO"].max().strftime("%Y.%m.%d")
    caption_parts.append(f"최신 댓글: {latest_comment}")

if caption_parts:
    st.caption("📅 " + " · ".join(caption_parts))

# -----------------------------
# 사이드바 필터
# -----------------------------
st.sidebar.header("필터")
st.sidebar.caption("시장: Japan · 분석 언어: Japanese")

sentiment_options = sorted(df["sentiment"].dropna().unique().tolist())
category_options = sorted(df["category"].dropna().unique().tolist())
reaction_options = [g for g in REACTION_GROUP_ORDER if g in set(df["reaction_group"])]

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
st.sidebar.caption("댓글 원문에 포함된 단어로 검색합니다.")
search_text = st.sidebar.text_input(
    "검색어",
    placeholder="예: ファンデ / 毛穴 / かわいい",
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
if HAS_TRANSLATION:
    translation_enabled = st.sidebar.checkbox(
        "한국어 번역 표시",
        value=True,
        help="CSV에 저장된 한국어 번역을 즉시 표시합니다."
    )
else:
    translation_enabled = False
    st.sidebar.caption("한국어 번역: CSV에 translation_ko 컬럼을 추가하면 표시됩니다.")

filtered_df = df[
    df["sentiment"].isin(selected_sentiments)
    & df["category"].isin(selected_categories)
    & df["reaction_group"].isin(selected_reactions)
].copy()

if search_text:
    filtered_df = filtered_df[
        filtered_df["text"]
        .astype(str)
        .str.contains(search_text, case=False, na=False, regex=False)
    ]
    st.sidebar.caption(f"'{search_text}' 검색 결과: {len(filtered_df):,}건")

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
    '<div class="section-note">콘텐츠·출연자 반응을 확인합니다.</div>',
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

product_share = (product_related_count / total_comments * 100) if total_comments else 0

if model_share > product_share:
    st.caption(
        f"💡 이 기간 댓글은 제품({product_share:.1f}%)보다 "
        f"모델·출연자 반응({model_share:.1f}%)에 더 쏠려 있습니다."
    )
elif product_share > model_share:
    st.caption(
        f"💡 이 기간 댓글은 모델·출연자 반응({model_share:.1f}%)보다 "
        f"제품 관련 반응({product_share:.1f}%)이 더 큽니다."
    )

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------
# PRODUCT INSIGHT
# -----------------------------
st.markdown('<div class="section-eyebrow">PRODUCT INSIGHT</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">제품 인사이트</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-note">제품·메이크업·구매 관련 댓글을 집계합니다.</div>',
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

    # 항목이 많아지면 높이를 늘려서 라벨이 생략되지 않게 합니다.
    row_count = len(dataframe)
    computed_height = max(height, row_count * 34)

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
                    labelOverlap=False,
                    domain=False,
                    ticks=False,
                ),
            ),
            tooltip=[label_col, "댓글 수"],
        )
        .properties(height=computed_height)
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)


# -----------------------------
# 감성 차트
# -----------------------------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("전체 반응")
    st.caption("전체 댓글의 긍정·중립·부정")
    sentiment_df = (
        filtered_df["sentiment"]
        .value_counts()
        .rename_axis("감성")
        .reset_index(name="댓글 수")
    )
    horizontal_bar_chart(sentiment_df, "감성", BLACK, height=220)

with right:
    st.subheader("제품 반응")
    st.caption("제품 관련 댓글의 긍정·중립·부정")
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
    st.subheader("관심 주제")
    st.caption("댓글이 무엇에 대해 이야기했는지")

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
    st.subheader("반응 대상")
    st.caption("댓글이 무엇에 반응했는지 (관심 주제와 다른 관점)")

    reaction_df = (
        filtered_df["reaction_group"]
        .value_counts()
        .rename_axis("반응 대상")
        .reset_index(name="댓글 수")
    )

    reaction_df["색상"] = reaction_df["반응 대상"].apply(
        lambda x: OTHER if x == "일반 반응" else BLACK
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
# 좋아요 TOP 20
# -----------------------------
st.subheader("인기 댓글")
if translation_enabled:
    st.caption("일본어 원문과 저장된 한국어 번역을 함께 표시합니다.")
else:
    st.caption("좋아요가 많은 댓글")

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

if translation_enabled and "translation_ko" in top_comments.columns:
    top_data["한국어 번역"] = top_comments["translation_ko"]

top_data.update({
    "좋아요": top_comments["diggCount"],
    "감성": top_comments["sentiment"],
    "반응 대상": top_comments["reaction_group"],
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

if translation_enabled and "한국어 번역" in top_display.columns:
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
st.subheader("전체 댓글")
st.caption("현재 필터에 해당하는 댓글")

sort_option = st.radio(
    "정렬",
    ["좋아요순", "최신순"],
    horizontal=True,
    label_visibility="collapsed",
)

if sort_option == "최신순" and "createTimeISO" in filtered_df.columns:
    sorted_filtered_df = filtered_df.sort_values("createTimeISO", ascending=False)
else:
    sorted_filtered_df = filtered_df.sort_values("diggCount", ascending=False)

all_data = {
    "댓글": sorted_filtered_df["text"],
}

if translation_enabled and "translation_ko" in sorted_filtered_df.columns:
    all_data["한국어 번역"] = sorted_filtered_df["translation_ko"]

all_data.update({
    "좋아요": sorted_filtered_df["diggCount"],
    "감성": sorted_filtered_df["sentiment"],
    "관심 주제": sorted_filtered_df["category"],
    "반응 대상": sorted_filtered_df["reaction_group"],
    "TikTok": sorted_filtered_df["videoWebUrl"],
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

if translation_enabled and "한국어 번역" in display_df.columns:
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
