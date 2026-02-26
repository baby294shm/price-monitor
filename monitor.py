import streamlit as st
import pandas as pd
import os
import re
import requests
from bs4 import BeautifulSoup

# --- [설정] ---
st.set_page_config(page_title="컴퓨존 비교표 및 구매링크", layout="wide")
st.title("🍁 컴퓨존 비교표 및 구매링크")

DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

# --- [스타일] ---
st.markdown("""
    <style>
    .stApp { background-color: #F9FAFB; }
    .price-label { font-size: 11px; color: #6B7280; margin: 0; }
    .price-value { font-size: 13px; font-weight: 600; color: #1F2937; margin: 0; }
    .prod-name { font-size: 13px; font-weight: 700; color: #374151; }
    .memo-txt { font-size: 11px; color: #9CA3AF; }
    </style>
""", unsafe_allow_html=True)


# --- [유틸] ---
def safe_int(val):
    try:
        return int(float(str(val).replace(",", "").strip()))
    except Exception:
        return 0


# --- [실시간 가격 크롤링] ---
def fetch_compuzone_price(url: str) -> int | None:
    """컴퓨존 상품 URL에서 판매가를 크롤링합니다. 실패 시 None 반환."""
    if not url or not str(url).strip():
        return None
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9",
            "Referer": "https://www.compuzone.co.kr/",
        }
        resp = requests.get(str(url).strip(), headers=headers, timeout=10)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        # 방법 1: 자주 쓰이는 한국 쇼핑몰 CSS 선택자
        for selector in [
            "#sell_price", "#sale_price", "#final_price",
            ".sell_price", ".sale_price", ".final_price",
            ".selling_price", ".goods_price", ".product_price",
            "span.price", "strong.price", ".price_num",
            "#priceStd", ".priceStd",
        ]:
            el = soup.select_one(selector)
            if el:
                num = re.sub(r"[^\d]", "", el.get_text())
                if num and int(num) > 1000:
                    return int(num)

        # 방법 2: JSON-LD 구조화 데이터 (Schema.org Product)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string or "")
                # 중첩 구조 처리
                if isinstance(data, list):
                    data = data[0]
                offers = data.get("offers", data.get("Offers", {}))
                if isinstance(offers, list):
                    offers = offers[0]
                price = offers.get("price", offers.get("Price", ""))
                if price:
                    num = re.sub(r"[^\d]", "", str(price))
                    if num and int(num) > 1000:
                        return int(num)
            except Exception:
                pass

        # 방법 3: 페이지 텍스트에서 판매가 패턴 regex
        text = soup.get_text(" ", strip=True)
        patterns = [
            r'판매가[^\d]*?([\d,]+)\s*원',
            r'할인가[^\d]*?([\d,]+)\s*원',
            r'최종가[^\d]*?([\d,]+)\s*원',
            r'소비자가[^\d]*?([\d,]+)\s*원',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                num = int(m.replace(",", ""))
                if num > 1000:
                    return num

        return None

    except Exception:
        return None


# --- [데이터 로드] ---
def load_data() -> pd.DataFrame:
    cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            for col in cols:
                if col not in df.columns:
                    df[col] = "자주구매" if col == "구분" else 0
            return df.fillna("")
        except Exception:
            pass
    return pd.DataFrame(columns=cols)


# --- [세션 초기화] ---
if "df" not in st.session_state:
    st.session_state.df = load_data()
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None


# --- [상품 등록/수정 폼] ---
is_edit = st.session_state.edit_idx is not None
expand_label = "📝 선택한 상품 수정하기" if is_edit else "➕ 신규 상품 등록"

with st.expander(expand_label, expanded=is_edit):
    if is_edit:
        curr = st.session_state.df.iloc[st.session_state.edit_idx]
        v_type  = curr["구분"]
        v_cat   = curr["카테고리"]
        v_name  = curr["상품명"]
        v_link  = curr["링크"]
        v_my    = safe_int(curr["가을판매가"])
        v_cp    = safe_int(curr["컴퓨존판매가"])
        v_memo  = str(curr["메모"])
    else:
        v_type, v_cat, v_name, v_link, v_my, v_cp, v_memo = "자주구매", "PC", "", "", 0, 0, ""

    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"],
                          index=0 if v_type == "가격비교" else 1)
    r_cat  = c2.selectbox("카테고리", CATEGORY_LIST[1:],
                          index=CATEGORY_LIST[1:].index(v_cat) if v_cat in CATEGORY_LIST[1:] else 0)
    r_name = c3.text_input("상품명", value=v_name)

    r_link = st.text_input("컴퓨존 URL", value=v_link)

    c4, c5, c6 = st.columns([1, 1, 1])
    r_my   = c4.number_input("가을판매가", value=v_my, min_value=0, step=1000)
    r_cp   = c5.number_input("기준가",     value=v_cp, min_value=0, step=1000)
    r_memo = c6.text_input("메모", value=v_memo)

    btn_save, btn_cancel = st.columns([3, 1])
    save_clicked   = btn_save.button("💾 저장", type="primary", use_container_width=True)
    cancel_clicked = btn_cancel.button("취소", use_container_width=True) if is_edit else False

    if cancel_clicked:
        st.session_state.edit_idx = None
        st.rerun()

    if save_clicked:
        with st.spinner("실시간 가격 조회 중..."):
            live_price = fetch_compuzone_price(r_link)
        if live_price is None:
            live_price = r_cp  # 크롤링 실패 시 기준가로 대체
            st.warning("실시간 가격 조회 실패 — 기준가로 대체되었습니다.")

        new_row = [r_type, r_cat, r_name, r_my, r_cp, live_price, r_memo, r_link]

        if is_edit:
            st.session_state.df.iloc[st.session_state.edit_idx] = new_row
            st.session_state.edit_idx = None
        else:
            new_df = pd.DataFrame([new_row], columns=st.session_state.df.columns)
            st.session_state.df = pd.concat(
                [st.session_state.df, new_df], ignore_index=True
            )
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.success("저장되었습니다.")
        st.rerun()


# --- [실시간가 전체 갱신] ---
if st.button("🔄 실시간가 전체 갱신", use_container_width=True):
    df = st.session_state.df
    total = len(df)
    if total == 0:
        st.info("등록된 상품이 없습니다.")
    else:
        progress_bar = st.progress(0, text="조회 중...")
        updated = 0
        for i, row in df.iterrows():
            link = str(row.get("링크", "")).strip()
            if link:
                price = fetch_compuzone_price(link)
                if price:
                    st.session_state.df.at[i, "실시간가"] = price
                    updated += 1
            progress_bar.progress((i + 1) / total, text=f"조회 중... ({i+1}/{total})")
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.success(f"{updated} / {total} 개 상품 실시간가 갱신 완료")
        st.rerun()


# --- [검색 & 탭] ---
search_q = st.text_input("🔍 검색")
t1, t2, t3 = st.tabs(["전체보기", "가격비교", "자주구매"])


def render(target_df: pd.DataFrame, tab_id: str):
    if tab_id == "가격비교":
        d_df = target_df[target_df["구분"] == "가격비교"]
    elif tab_id == "자주구매":
        d_df = target_df[target_df["구분"] == "자주구매"]
    else:
        d_df = target_df

    if d_df.empty:
        st.info("등록된 상품이 없습니다.")
        return

    for idx, row in d_df.iterrows():
        with st.container(border=True):
            col1, col2, col3 = st.columns([0.45, 0.45, 0.10])

            # ── 상품명 / 메모 / 구매링크
            with col1:
                st.markdown(
                    f"<div class='prod-name'>"
                    f"<span style='color:#2563EB'>[{row['카테고리']}]</span> {row['상품명']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if str(row["메모"]).strip():
                    st.markdown(
                        f"<div class='memo-txt'>{row['메모']}</div>",
                        unsafe_allow_html=True,
                    )
                link = str(row["링크"]).strip()
                if link:
                    st.markdown(
                        f"<a href='{link}' target='_blank' style='font-size:11px;color:#6B7280;'>🔗 구매링크</a>",
                        unsafe_allow_html=True,
                    )

            # ── 가격 4열
            with col2:
                fall_price = safe_int(row["가을판매가"])
                base_price = safe_int(row["컴퓨존판매가"])
                live_price = safe_int(row["실시간가"])
                diff       = live_price - base_price

                if diff > 0:
                    diff_txt = f"<span style='color:red'>▲{diff:,}</span>"
                elif diff < 0:
                    diff_txt = f"<span style='color:blue'>▼{abs(diff):,}</span>"
                else:
                    diff_txt = "<span style='color:#9CA3AF'>-</span>"

                p1, p2, p3, p4 = st.columns(4)
                p1.markdown(
                    f"<p class='price-label'>가을판매가</p>"
                    f"<p class='price-value'>{fall_price:,}</p>",
                    unsafe_allow_html=True,
                )
                p2.markdown(
                    f"<p class='price-label'>기준가</p>"
                    f"<p class='price-value'>{base_price:,}</p>",
                    unsafe_allow_html=True,
                )
                p3.markdown(
                    f"<p class='price-label'>실시간</p>"
                    f"<p class='price-value' style='color:#2563EB'>{live_price:,}</p>",
                    unsafe_allow_html=True,
                )
                p4.markdown(
                    f"<p class='price-label'>변동액</p>"
                    f"<p class='price-value'>{diff_txt}</p>",
                    unsafe_allow_html=True,
                )

            # ── 수정 / 삭제
            with col3:
                if st.button("수정", key=f"ed_{tab_id}_{idx}"):
                    st.session_state.edit_idx = idx
                    st.rerun()
                if st.button("삭제", key=f"del_{tab_id}_{idx}"):
                    st.session_state.df = (
                        st.session_state.df
                        .drop(index=idx)
                        .reset_index(drop=True)
                    )
                    st.session_state.df.to_excel(DB_FILE, index=False)
                    st.rerun()


# ── 필터 & 렌더링
f_df = st.session_state.df.copy()
if search_q:
    f_df = f_df[f_df["상품명"].str.contains(search_q, case=False, na=False)]

with t1: render(f_df, "전체")
with t2: render(f_df, "가격비교")
with t3: render(f_df, "자주구매")
