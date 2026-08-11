"""Monthly VIDIVICI Japan TikTok data updater.

1. Runs the saved Apify TikTok Scraper task.
2. Downloads the run's default dataset.
3. Cleans and analyzes comments (language / sentiment / category / reaction_target).
4. Merges them with the existing dashboard CSV.

기존 CSV의 모든 컬럼(translation_ko 포함)은 절대 삭제되지 않습니다.
기존 행의 값도 덮어쓰지 않고, 신규 댓글만 추가됩니다.

Required environment variables:
    APIFY_TOKEN
Optional environment variables:
    APIFY_TASK_ID (default: respectable_tabla_b2q~vidivici-japan)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from langdetect import DetectorFactory, LangDetectException, detect
from transformers import pipeline

API_BASE = "https://api.apify.com/v2"
TASK_ID = os.getenv(
    "APIFY_TASK_ID",
    "respectable_tabla_b2q~vidivici-japan",
)
TOKEN = os.getenv("APIFY_TOKEN", "").strip()
OUTPUT_PATH = Path("vidivici_comments_final.csv")
POLL_INTERVAL_SECONDS = 15
RUN_TIMEOUT_SECONDS = 45 * 60

# 중복 판단 기준 (이 3개가 같으면 같은 댓글로 봅니다)
KEY_COLUMNS = ["text", "uniqueId", "videoWebUrl"]

REQUIRED_COLUMNS = [
    "text",
    "diggCount",
    "uniqueId",
    "createTimeISO",
    "videoWebUrl",
]
ANALYSIS_COLUMNS = ["language", "sentiment", "category", "reaction_target"]
OUTPUT_COLUMNS = REQUIRED_COLUMNS + ANALYSIS_COLUMNS

DetectorFactory.seed = 42


# -----------------------------
# 반응 대상 분류 (app.py와 동일한 기준)
# -----------------------------
TARGET_KEYWORDS = {
    "모델·출연자 반응": [
        "かわい", "可愛", "美人", "綺麗", "きれい", "キレイ",
        "顔", "ビジュ", "ビジュアル", "似合う", "ちゃん", "女の子",
        "モデル", "推し", "好き", "最高", "神", "尊い", "美女",
        "イケメン", "美しい", "憧れ", "結婚したい",
    ],
    "제품 반응": [
        "ファンデ", "ファンデーション", "クッション", "プライマー",
        "リップ", "ブラッシュ", "カバー", "カバー力", "崩れ",
        "崩れない", "崩れにくい", "毛穴", "乾燥", "保湿", "密着",
        "持ち", "テクスチャ", "伸び", "発色", "色味", "軽い",
        "しっとり", "サラサラ",
    ],
    "피부 표현·메이크업": [
        "ツヤ", "艶", "つや", "透明感", "仕上がり", "肌", "肌綺麗",
        "ナチュラル", "マット", "メイク", "トーンアップ",
        "発光", "水光", "陶器肌", "血色", "うるおい",
        "もちもち", "もちっ", "うるうる", "つるつる",
    ],
    "구매·문의": [
        "欲しい", "欲しかった", "買う", "買った", "買いたい",
        "買お", "買っちゃ", "ポチ", "再販",
        "購入", "注文", "メガ割", "Qoo10", "どこで買える",
        "どこで売ってる", "気になる", "何色", "何番",
        "おすすめ", "使ったことある", "教えて",
    ],
}

TARGET_PRIORITY = [
    "제품 반응",
    "피부 표현·메이크업",
    "구매·문의",
    "모델·출연자 반응",
]


# 모델 피부 칭찬이 제품 반응으로 새는 것을 막는 보정 규칙 (app.py와 동일)
MODEL_SKIN_HINTS = [
    "ちゃんの肌", "さんの肌", "羨ましい", "うらやましい",
    "肌になりたい", "肌目指す", "肌綺麗すぎ", "肌きれいすぎ",
    "肌がきれいすぎ", "肌が綺麗すぎ",
]

PRODUCT_CONTEXT_WORDS = [
    "メイク", "ファンデ", "クッション", "下地", "プライマー",
    "リップ", "チーク", "商品", "使っ", "何肌", "紹介",
]


def is_model_skin_praise(text: str) -> bool:
    value = str(text)
    if not any(hint in value for hint in MODEL_SKIN_HINTS):
        return False
    if any(word in value for word in PRODUCT_CONTEXT_WORDS):
        return False
    return True


def classify_reaction_target(text: str) -> str:
    value = str(text)
    matched = [
        target
        for target, keywords in TARGET_KEYWORDS.items()
        if any(keyword in value for keyword in keywords)
    ]
    if not matched:
        return "기타"
    for target in TARGET_PRIORITY:
        if target in matched:
            if target == "피부 표현·메이크업" and is_model_skin_praise(value):
                return "모델·출연자 반응"
            return target
    return "기타"


# -----------------------------
# 관심 주제 분류 (app.py의 기존 카테고리 체계와 동일)
# app.py가 "기타"를 다시 세분화하므로, 여기서는 기본 분류만 합니다.
# -----------------------------
CATEGORY_KEYWORDS = {
    "가격": ["値段", "いくら", "価格", "高い", "安い", "コスパ", "セール", "メガ割"],
    "구매 의도": [
        "買う", "買った", "買いたい", "買お", "買っちゃ", "購入", "注文", "欲しい",
        "欲しかった", "ポチった", "予約",
    ],
    "사용 방법·문의": [
        "使い方", "どうやって", "順番", "何色", "何番", "どこで買える",
        "どこで売ってる", "教えて", "知りたい", "ませんか",
    ],
    "패키지·디자인": ["パッケージ", "容器", "デザイン", "見た目", "ケース", "ボトル"],
    "피부 표현·광채": [
        "ツヤ", "艶", "つや", "透明感", "肌", "陶器肌", "発光",
        "水光", "血色", "うるおい", "もちもち", "つるつる",
    ],
    "제품력·효과": [
        "カバー力", "崩れ", "崩れない", "崩れにくい", "毛穴", "乾燥",
        "保湿", "密着", "持ち", "発色", "効果", "肌荒れ",
        "テクスチャ", "伸び",
    ],
    "모델·출연자 반응": [
        "かわい", "可愛", "美人", "綺麗", "きれい", "キレイ", "美しい",
        "ビジュ", "似合う", "モデル", "推し", "美女", "憧れ", "結婚したい",
    ],
}

CATEGORY_PRIORITY = [
    "가격",
    "구매 의도",
    "사용 방법·문의",
    "패키지·디자인",
    "제품력·효과",
    "피부 표현·광채",
    "모델·출연자 반응",
]


def classify_category(text: str) -> str:
    value = str(text)
    matched = [
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in value for keyword in keywords)
    ]
    if not matched:
        return "기타"
    for category in CATEGORY_PRIORITY:
        if category in matched:
            return category
    return "기타"


# -----------------------------
# Apify
# -----------------------------
def api_request(method: str, endpoint: str, **kwargs: Any) -> requests.Response:
    params = dict(kwargs.pop("params", {}) or {})
    params["token"] = TOKEN
    response = requests.request(
        method,
        f"{API_BASE}{endpoint}",
        params=params,
        timeout=60,
        **kwargs,
    )
    response.raise_for_status()
    return response


def run_task_and_get_dataset_id() -> str:
    if not TOKEN:
        raise RuntimeError("APIFY_TOKEN environment variable is missing.")

    print(f"Starting Apify task: {TASK_ID}")
    response = api_request("POST", f"/actor-tasks/{TASK_ID}/runs")
    run = response.json()["data"]
    run_id = run["id"]
    print(f"Apify run started: {run_id}")

    deadline = time.monotonic() + RUN_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        run = api_request("GET", f"/actor-runs/{run_id}").json()["data"]
        status = run.get("status", "UNKNOWN")
        print(f"Run status: {status}")

        if status == "SUCCEEDED":
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                raise RuntimeError("Run succeeded but no default dataset was returned.")
            return dataset_id

        if status in {"FAILED", "ABORTED", "TIMED-OUT"}:
            message = run.get("statusMessage") or "No status message"
            raise RuntimeError(f"Apify run ended with {status}: {message}")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError("Apify run did not finish within 45 minutes.")


def download_dataset(dataset_id: str) -> list[dict[str, Any]]:
    print(f"Downloading dataset: {dataset_id}")
    response = api_request(
        "GET",
        f"/datasets/{dataset_id}/items",
        params={"clean": "true", "format": "json"},
    )
    items = response.json()
    if not isinstance(items, list):
        raise RuntimeError("Unexpected dataset response format.")
    print(f"Downloaded items: {len(items)}")
    return items


# -----------------------------
# 정규화 / 정리
# -----------------------------
def first_present(row: pd.Series, candidates: list[str], default: Any = "") -> Any:
    for name in candidates:
        if name in row.index:
            value = row[name]
            if pd.notna(value) and str(value).strip() != "":
                return value
    return default


def normalize_raw_items(items: list[dict[str, Any]]) -> pd.DataFrame:
    raw = pd.json_normalize(items)
    if raw.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    records: list[dict[str, Any]] = []
    for _, row in raw.iterrows():
        text = first_present(row, ["text", "commentText", "comment", "description"])
        if not str(text).strip():
            continue

        records.append(
            {
                "text": text,
                "diggCount": first_present(
                    row,
                    ["diggCount", "likes", "likeCount", "commentLikeCount"],
                    0,
                ),
                "uniqueId": first_present(
                    row,
                    [
                        "uniqueId",
                        "authorMeta.name",
                        "author.uniqueId",
                        "user.uniqueId",
                    ],
                    "unknown",
                ),
                "createTimeISO": first_present(
                    row,
                    ["createTimeISO", "createTime", "createdAt"],
                    pd.NaT,
                ),
                "videoWebUrl": first_present(
                    row,
                    ["videoWebUrl", "webVideoUrl", "url", "videoUrl"],
                    "",
                ),
            }
        )

    return pd.DataFrame(records, columns=REQUIRED_COLUMNS)


def clean_comments(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    cleaned = df.copy()
    cleaned["text"] = cleaned["text"].fillna("").astype(str).str.strip()
    cleaned = cleaned[cleaned["text"] != ""]
    cleaned["uniqueId"] = cleaned["uniqueId"].fillna("unknown").astype(str)
    cleaned["videoWebUrl"] = cleaned["videoWebUrl"].fillna("").astype(str)
    cleaned["diggCount"] = (
        pd.to_numeric(cleaned["diggCount"], errors="coerce").fillna(0).astype(int)
    )
    cleaned["createTimeISO"] = pd.to_datetime(
        cleaned["createTimeISO"], errors="coerce", utc=True
    )
    cleaned = cleaned.drop_duplicates(subset=KEY_COLUMNS, keep="last").reset_index(
        drop=True
    )
    return cleaned


def detect_language(text: str) -> str:
    value = str(text).strip()
    if len(value) < 3:
        return "unknown"
    try:
        lang = detect(value)
    except LangDetectException:
        return "unknown"

    if lang == "ja":
        return "Japanese"
    if lang == "ko":
        return "Korean"
    if lang == "en":
        return "English"
    return "Other"


def add_analysis(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    analyzed = df.copy()
    analyzed["language"] = analyzed["text"].apply(detect_language)
    analyzed["category"] = analyzed["text"].apply(classify_category)
    analyzed["reaction_target"] = analyzed["text"].apply(classify_reaction_target)

    print("Loading multilingual sentiment model...")
    sentiment_model = pipeline(
        "text-classification",
        model="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        tokenizer="cardiffnlp/twitter-xlm-roberta-base-sentiment",
        device=-1,
    )
    label_map = {
        "negative": "Negative",
        "neutral": "Neutral",
        "positive": "Positive",
        "LABEL_0": "Negative",
        "LABEL_1": "Neutral",
        "LABEL_2": "Positive",
    }

    texts = analyzed["text"].astype(str).str.slice(0, 512).tolist()
    print(f"Analyzing sentiment for {len(texts)} comments...")
    results = sentiment_model(texts, truncation=True, batch_size=16)
    analyzed["sentiment"] = [
        label_map.get(str(result.get("label", "neutral")), "Neutral")
        for result in results
    ]
    return analyzed


# -----------------------------
# 한국어 번역
# -----------------------------
# DEEPL_API_KEY 시크릿이 등록되어 있으면 DeepL을 사용하고,
# 없으면 무료 번역기를 사용합니다.
# 번역에 실패해도 해당 댓글만 비워두고 나머지는 정상 저장됩니다.
DEEPL_KEY = os.getenv("DEEPL_API_KEY", "").strip()
TRANSLATE_SLEEP_SECONDS = 0.4


def translate_with_deepl(texts: list[str]) -> list[str]:
    endpoint = (
        "https://api-free.deepl.com/v2/translate"
        if DEEPL_KEY.endswith(":fx")
        else "https://api.deepl.com/v2/translate"
    )
    results: list[str] = []
    # DeepL은 한 번에 여러 문장을 보낼 수 있습니다 (50개씩 나눠서 호출)
    for start in range(0, len(texts), 50):
        chunk = texts[start : start + 50]
        response = requests.post(
            endpoint,
            data=[("text", t) for t in chunk]
            + [("source_lang", "JA"), ("target_lang", "KO")],
            headers={"Authorization": f"DeepL-Auth-Key {DEEPL_KEY}"},
            timeout=60,
        )
        response.raise_for_status()
        results.extend(
            item.get("text", "") for item in response.json().get("translations", [])
        )
    return results


def translate_with_free_service(texts: list[str]) -> list[str]:
    from deep_translator import GoogleTranslator

    translator = GoogleTranslator(source="ja", target="ko")
    results: list[str] = []
    for text in texts:
        try:
            results.append(translator.translate(text) or "")
        except Exception as exc:
            print(f"  translation failed, left blank: {exc}")
            results.append("")
        time.sleep(TRANSLATE_SLEEP_SECONDS)
    return results


def add_translations(df: pd.DataFrame) -> pd.DataFrame:
    """번역이 비어 있는 일본어 댓글만 번역합니다. 기존 번역은 건드리지 않습니다."""
    if "translation_ko" not in df.columns:
        df["translation_ko"] = ""

    needs = (
        (df["language"] == "Japanese")
        & (df["translation_ko"].isna() | (df["translation_ko"].astype(str).str.strip() == ""))
    )
    targets = df.loc[needs, "text"].astype(str).tolist()

    if not targets:
        print("No comments need translation.")
        return df

    print(f"Translating {len(targets)} new comments to Korean...")
    try:
        if DEEPL_KEY:
            print("Using DeepL API.")
            translated = translate_with_deepl(targets)
        else:
            print("Using free translation service.")
            translated = translate_with_free_service(targets)
    except Exception as exc:
        print(f"WARNING: translation step failed entirely ({exc}).")
        print("Comments will be saved without Korean translation.")
        return df

    if len(translated) != len(targets):
        print("WARNING: translation count mismatch. Skipping translation.")
        return df

    df.loc[needs, "translation_ko"] = translated
    filled = sum(1 for t in translated if str(t).strip())
    print(f"Translated {filled} / {len(targets)} comments.")
    return df


# -----------------------------
# 병합 / 저장
# -----------------------------
def load_existing() -> pd.DataFrame:
    """기존 CSV를 있는 그대로 읽습니다. 컬럼을 잘라내지 않습니다."""
    if not OUTPUT_PATH.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    existing = pd.read_csv(OUTPUT_PATH, low_memory=False)
    for column in OUTPUT_COLUMNS:
        if column not in existing.columns:
            existing[column] = ""
    return existing


def write_last_updated() -> None:
    """수집이 정상 실행된 날짜를 기록합니다 (대시보드 표시용)."""
    from datetime import datetime, timezone, timedelta

    kst = timezone(timedelta(hours=9))
    stamp = datetime.now(kst).strftime("%Y.%m.%d")
    Path("last_updated.txt").write_text(stamp, encoding="utf-8")
    print(f"Recorded collection date: {stamp}")


def merge_and_save(new_data: pd.DataFrame) -> None:
    existing = load_existing()

    # 기존 컬럼 전체를 유지합니다 (translation_ko 등 포함)
    all_columns = list(existing.columns)
    for column in OUTPUT_COLUMNS:
        if column not in all_columns:
            all_columns.append(column)

    for column in all_columns:
        if column not in new_data.columns:
            new_data[column] = ""

    def make_key(frame: pd.DataFrame) -> pd.Series:
        return (
            frame["text"].fillna("").astype(str).str.strip()
            + "||"
            + frame["uniqueId"].fillna("unknown").astype(str)
            + "||"
            + frame["videoWebUrl"].fillna("").astype(str)
        )

    existing_keys = set(make_key(existing))
    new_keys = make_key(new_data)

    # 이미 있는 댓글은 건드리지 않고, 새 댓글만 추가합니다.
    fresh = new_data[~new_keys.isin(existing_keys)].copy()
    print(f"New comments to append: {len(fresh)}")

    if fresh.empty:
        print("No new comments. CSV left unchanged.")
        write_last_updated()
        return

    combined = pd.concat(
        [existing[all_columns], fresh[all_columns]], ignore_index=True
    )

    combined["text"] = combined["text"].fillna("").astype(str).str.strip()
    combined = combined[combined["text"] != ""]
    combined["diggCount"] = (
        pd.to_numeric(combined["diggCount"], errors="coerce").fillna(0).astype(int)
    )
    combined["createTimeISO"] = pd.to_datetime(
        combined["createTimeISO"], errors="coerce", utc=True
    )
    combined = combined.sort_values(
        "createTimeISO", ascending=False, na_position="last"
    )
    combined["createTimeISO"] = combined["createTimeISO"].dt.strftime(
        "%Y-%m-%dT%H:%M:%S%z"
    )
    combined = combined.reset_index(drop=True)

    # 번역이 비어 있는 신규 일본어 댓글만 번역합니다.
    combined = add_translations(combined)

    # 안전장치: 기존 행 수보다 줄어들면 저장하지 않습니다.
    if len(combined) < len(existing):
        raise RuntimeError(
            f"Row count would shrink ({len(existing)} -> {len(combined)}). Aborting save."
        )

    combined.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Saved {len(combined)} total comments to {OUTPUT_PATH}")

    # 대시보드에 "최근 수집일"을 표시하기 위해 실행 날짜를 기록합니다.
    write_last_updated()

    missing_translation = (
        combined["translation_ko"].isna() | (combined["translation_ko"] == "")
    ).sum() if "translation_ko" in combined.columns else 0
    if missing_translation:
        print(f"NOTE: {missing_translation} comments still need Korean translation.")


def main() -> int:
    try:
        dataset_id = run_task_and_get_dataset_id()
        items = download_dataset(dataset_id)
        raw_comments = normalize_raw_items(items)
        cleaned = clean_comments(raw_comments)
        print(f"Valid comments in this run: {len(cleaned)}")
        if cleaned.empty:
            raise RuntimeError(
                "No valid comment rows were found. "
                "Check the Apify task's TikTok comments settings."
            )
        analyzed = add_analysis(cleaned)
        merge_and_save(analyzed)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
