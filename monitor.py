import streamlit as st
import pandas as pd
import os
import re
import json
import requests
from bs4 import BeautifulSoup

# --- [설정] ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="컴퓨존 비교표 및 구매링크", layout="wide")
st.title("🍁 컴퓨존 비교표 및 구매링크")


# --- [유틸] ---
def safe_int(val):
    try:
        return int(float(str(val).replace(",", "").strip()))
    except Exception:
        return 0


# --- [실시간 가격 크롤링] ---
def fetch_compuzone_price(url: str) -> int | None:
    """컴퓨존 상품 URL에서 판매가 크롤링. 실패 시 None 반환."""
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

        # 방법 1: CSS 선택자 (컴퓨존 전용 + 한국 쇼핑몰 공통)
        for selector in [
            "#product_content_2_price",
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

        # 방법 2: JSON-LD Schema.org
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
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

        # 방법 3: 텍스트 regex
        text = soup.get_text(" ", strip=True)
        for pattern in [
            r'판매가[^\d]*?([\d,]+)\s*원',
            r'할인가[^\d]*?([\d,]+)\s*원',
            r'최종가[^\d]*?([\d,]+)\s*원',
        ]:
            for m in re.findall(pattern, text):
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
            for c in cols:
                if c not in df.columns:
                    df[c] = "자주구매" if c == "구분" else 0
            return df.fillna("")
        except Exception:
            pass
    return pd.DataFrame(columns=cols)


# --- [세션 초기화] ---
if "df" not in st.session_state:
    st.session_state.df = load_data()


# --- [신규 상품 등록] ---
with st.expander("➕ 신규 상품 등록"):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat  = c2.selectbox("카테고리", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL")
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my   = c4.number_input("가을판매가", value=0, min_value=0, step=1000)
    r_cp   = c5.number_input("기준가",     value=0, min_value=0, step=1000)
    r_memo = c6.text_input("메모")

    if c7.button("추가하기", use_container_width=True):
        if r_name:
            with st.spinner("실시간 가격 조회 중..."):
                live_price = fetch_compuzone_price(r_link)
            if live_price is None:
                live_price = r_cp
            new_row = {
                "구분": r_type, "카테고리": r_cat, "상품명": r_name,
                "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": live_price,
                "메모": r_memo, "링크": r_link.strip(),
            }
            st.session_state.df = pd.concat(
                [st.session_state.df, pd.DataFrame([new_row])], ignore_index=True
            )
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()


# --- [검색 & 카테고리 필터] ---
st.write("---")
f1, f2 = st.columns([7, 3])
search_q = f1.text_input("🔍 상품명 또는 메모 검색")
cat_q    = f2.selectbox("📂 카테고리 필터", CATEGORY_LIST)

# --- [탭] ---
tab1, tab2, tab3 = st.tabs(["전체보기", "가격비교", "자주구매"])

# --- [기본 필터 적용] ---
df = st.session_state.df.copy()
if cat_q != "전체보기":
    df = df[df["카테고리"] == cat_q]
if search_q:
    df = df[
        df["상품명"].str.contains(search_q, case=False, na=False) |
        df["메모"].astype(str).str.contains(search_q, case=False, na=False)
    ]


# --- [리스트 렌더링] ---
def display_list(target_df: pd.DataFrame, current_tab: str):
    if target_df.empty:
        st.info("표시할 상품이 없습니다.")
        return

    # 상단 액션 버튼
    act_c1, act_c2, act_c3 = st.columns([7, 1.5, 1.5])
    refresh_btn = act_c2.button("🔄 가격 업데이트", key=f"re_{current_tab}", use_container_width=True)
    delete_btn  = act_c3.button("🗑️ 선택 삭제",   key=f"del_{current_tab}", use_container_width=True)

    selected_indices = []

    for idx, row in target_df.iterrows():
        with st.container(border=True):
            c_chk, c_info, c_price, c_btn = st.columns([0.05, 0.40, 0.45, 0.10])

            # 체크박스
            with c_chk:
                if st.checkbox("", key=f"sel_{current_tab}_{idx}"):
                    selected_indices.append(idx)

            # 상품 정보
            with c_info:
                st.caption(f"[{row['카테고리']}]")
                st.markdown(f"**{row['상품명']}**")
                memo = str(row["메모"]).strip()
                if memo and memo not in ("nan", "-", "0", ""):
                    st.markdown(
                        f"<small style='color:gray;'>📝 {memo}</small>",
                        unsafe_allow_html=True,
                    )

            # 가격
            with c_price:
                fall_price = safe_int(row["가을판매가"])
                base_price = safe_int(row["컴퓨존판매가"])
                live_price = safe_int(row["실시간가"])
                diff       = live_price - base_price

                p1, p2, p3, p4 = st.columns(4)
                if current_tab != "가격비교":
                    p1.metric("가을가", f"{fall_price:,}")
                p2.metric("기준가", f"{base_price:,}")
                p3.metric("실시간", f"{live_price:,}")
                p4.metric("변동액", f"{diff:,}", delta=diff, delta_color="inverse")

            # 링크 버튼
            with c_btn:
                st.write("")
                link = str(row["링크"]).strip()
                if link and link.startswith("http"):
                    st.link_button("열기", link)

    # ── 가격 업데이트
    if refresh_btn:
        progress_bar = st.progress(0, text="가격 조회 중...")
        total   = len(target_df)
        updated = 0
        for i, (idx, row) in enumerate(target_df.iterrows()):
            link = str(row.get("링크", "")).strip()
            if link:
                price = fetch_compuzone_price(link)
                if price:
                    st.session_state.df.at[idx, "실시간가"] = price
                    updated += 1
            progress_bar.progress((i + 1) / total, text=f"조회 중... ({i+1}/{total})")
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.success(f"{updated} / {total} 가격 갱신 완료")
        st.rerun()

    # ── 선택 삭제
    if delete_btn and selected_indices:
        st.session_state.df = (
            st.session_state.df.drop(selected_indices).reset_index(drop=True)
        )
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()

    # ── 수정 폼 (체크박스 선택 시 하단 표시)
    if selected_indices:
        st.divider()
        e_idx = selected_indices[0]
        t = st.session_state.df.loc[e_idx]
        with st.form(f"edit_form_{current_tab}"):
            st.write(f"🛠️ **{t['상품명']}** 수정")
            ec1, ec2, ec3, ec4 = st.columns([1, 1, 2, 2])
            nf = ec1.number_input("가을판매가", value=safe_int(t["가을판매가"]), min_value=0, step=1000)
            nc = ec2.number_input("기준가",     value=safe_int(t["컴퓨존판매가"]), min_value=0, step=1000)
            nl = ec3.text_input("URL", value=str(t["링크"]))
            nm = ec4.text_input("메모", value="" if str(t["메모"]) in ("nan", "0") else str(t["메모"]))
            if st.form_submit_button("저장하기", type="primary"):
                st.session_state.df.at[e_idx, "가을판매가"]   = nf
                st.session_state.df.at[e_idx, "컴퓨존판매가"] = nc
                st.session_state.df.at[e_idx, "링크"]         = nl
                st.session_state.df.at[e_idx, "메모"]         = nm
                st.session_state.df.to_excel(DB_FILE, index=False)
                st.rerun()


# --- [출력] ---
with tab1: display_list(df, "전체보기")
with tab2: display_list(df[df["구분"] == "가격비교"], "가격비교")
with tab3: display_list(df[df["구분"] == "자주구매"], "자주구매")
