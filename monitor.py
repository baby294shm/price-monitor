import shutil
import time
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

st.set_page_config(page_title="컴퓨존 가격모니터", layout="wide")
st.caption("컴퓨존 가격모니터")


# --- [유틸] ---
def safe_int(val):
    try:
        return int(float(str(val).replace(",", "").strip()))
    except Exception:
        return 0


def extract_first_price(text: str) -> int | None:
    """텍스트에서 첫 번째 유효한 가격 추출 (1,000 ~ 30,000,000원)"""
    for m in re.findall(r"[\d,]+", text):
        try:
            num = int(m.replace(",", ""))
            if 1_000 <= num <= 30_000_000:
                return num
        except Exception:
            pass
    return None


# --- [크롤링: 공통 파싱] ---
def _parse_price_from_soup(soup) -> int | None:
    """BeautifulSoup 객체에서 가격 추출.

    우선순위:
    1. 판매가/할인가 레이블 텍스트 (실제 판매 금액, 정가 제외)
    2. DOM 레이블 → 인접 셀 탐색
    3. JSON-LD / og: 메타태그
    4. CSS 셀렉터 (정가 레이블 없는 경우 fallback)
    5. JS 인라인 변수
    """
    # ── 1단계: 판매가/할인가 레이블 텍스트 우선 (정가·권장소비자가 제외)
    # 정가 레이블이 붙은 금액은 건너뜀
    SKIP_RE = re.compile(r'정가|권장소비자가|시중가|소비자가|원가')
    SALE_RE = re.compile(
        r'(?:판매가|할인가|최종가|구매가|현재가|특가)[^\d]{0,6}([\d,]{4,})\s*원',
        re.S,
    )
    text = soup.get_text(" ", strip=True)
    # 정가 금액 먼저 수집해서 제외 목록 만들기
    skip_prices: set[int] = set()
    for m in re.finditer(
        r'(?:정가|권장소비자가|시중가|소비자가|원가)[^\d]{0,6}([\d,]{4,})\s*원', text
    ):
        v = extract_first_price(m.group(1))
        if v:
            skip_prices.add(v)

    # 모든 매칭 수집 후 최솟값 반환 (판매가 행에 정가+할인가 같이 표시될 때 대응)
    sale_candidates = []
    for m in SALE_RE.finditer(text):
        price = extract_first_price(m.group(1))
        if price and price not in skip_prices:
            sale_candidates.append(price)
    if sale_candidates:
        return min(sale_candidates)

    # ── 2단계: DOM 테이블에서 레이블 셀 → 값 셀 탐색
    LABEL_TEXTS = ["판매가", "할인가", "최종가", "구매가", "현재가", "특가"]
    for th in soup.find_all(["th", "td", "dt", "span", "label"]):
        if any(lbl in (th.get_text(strip=True) or "") for lbl in LABEL_TEXTS):
            # 같은 행(tr) 또는 바로 다음 형제에서 숫자 추출
            tr = th.find_parent("tr")
            if tr:
                for td in tr.find_all("td"):
                    price = extract_first_price(td.get_text())
                    if price and price not in skip_prices:
                        return price
            for sib in th.find_next_siblings()[:3]:
                price = extract_first_price(sib.get_text())
                if price and price not in skip_prices:
                    return price

    # ── 3단계: JSON-LD Schema.org
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            offers = data.get("offers", data.get("Offers", {}))
            if isinstance(offers, list):
                offers = offers[0]
            raw = offers.get("price", offers.get("Price", ""))
            if raw:
                price = extract_first_price(str(raw))
                if price and price not in skip_prices:
                    return price
        except Exception:
            pass

    # ── 4단계: og: 메타태그
    for prop in ["og:price:amount", "product:price:amount"]:
        meta = soup.find("meta", property=prop)
        if meta:
            price = extract_first_price(meta.get("content", ""))
            if price and price not in skip_prices:
                return price

    # ── 5단계: CSS 선택자 (정가가 없거나 위에서 못 찾은 경우 fallback)
    for selector in [
        "#prd_sale_price", "#sell_price", "#sale_price", "#final_price",
        "#salePrice", "#realPrice", "#dispPrice",
        ".sell_price", ".sale_price", ".final_price",
        ".selling_price", ".goods_price", ".product_price",
        ".salePrice", ".sale-price", ".real-price",
        "span.price", "strong.price", ".price_num",
        "#priceStd", ".priceStd",
        ".item_price strong", ".price_wrap strong",
        "em.price", "b.price",
        "#product_content_2_price",  # 컴퓨존 (정가 가능성 있어 후순위)
        "#prd_price",
    ]:
        el = soup.select_one(selector)
        if el:
            price = extract_first_price(el.get_text())
            if price and price not in skip_prices:
                return price

    # ── 6단계: data-* 속성
    for attr in ["data-price", "data-sale-price", "data-sell-price", "data-final-price"]:
        el = soup.find(attrs={attr: True})
        if el:
            price = extract_first_price(el[attr])
            if price and price not in skip_prices:
                return price

    # ── 7단계: JavaScript 인라인 변수
    for script in soup.find_all("script"):
        js = script.string or ""
        if not js.strip():
            continue
        for pattern in [
            r'["\']?(?:sell_price|sale_price|final_price|real_price|'
            r'selling_price|goods_price|product_price|salePrice|'
            r'realPrice|dispPrice|prd_price)["\']?\s*[=:]\s*["\']?([\d,]+)',
            r'"price"\s*:\s*"?([\d,]+)"?',
            r"'price'\s*:\s*'?([\d,]+)'?",
            r'var\s+price\s*=\s*([\d,]+)',
        ]:
            m2 = re.search(pattern, js, re.IGNORECASE)
            if m2:
                price = extract_first_price(m2.group(1))
                if price and price not in skip_prices:
                    return price

    return None


# --- [크롤링: requests (빠름)] ---
def _fetch_with_requests(url: str) -> int | None:
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": "https://www.compuzone.co.kr/",
        }
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        # 한국어 쇼핑몰은 EUC-KR 또는 UTF-8
        if resp.encoding and resp.encoding.lower() in ("iso-8859-1", "latin-1"):
            resp.encoding = resp.apparent_encoding
        price = _parse_price_from_soup(BeautifulSoup(resp.text, "html.parser"))
        if price:
            return price
        # EUC-KR 인코딩 재시도 (컴퓨존 등 일부 한국 쇼핑몰)
        resp.encoding = "euc-kr"
        return _parse_price_from_soup(BeautifulSoup(resp.text, "html.parser"))
    except Exception:
        return None


# --- [크롤링: Selenium (JS 렌더링)] ---
def _get_chrome_driver():
    """헤드리스 Chrome 드라이버 생성. 설치 안 됐으면 None 반환."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,800")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        chrome_bin = (
            shutil.which("chromium") or
            shutil.which("chromium-browser") or
            shutil.which("google-chrome")
        )
        if chrome_bin:
            options.binary_location = chrome_bin

        driver_path = shutil.which("chromedriver") or "/usr/bin/chromedriver"
        service = Service(driver_path)
        return webdriver.Chrome(service=service, options=options)
    except Exception:
        return None


def fetch_compuzone_price(url: str) -> int | None:
    """단일 URL 가격 크롤링 (신규 등록 시 사용)"""
    if not url or not str(url).strip():
        return None
    url = str(url).strip()

    # 1차: requests (빠름)
    price = _fetch_with_requests(url)
    if price:
        return price

    # 2차: Selenium (JS 렌더링)
    driver = _get_chrome_driver()
    if not driver:
        return None
    try:
        driver.set_page_load_timeout(12)
        driver.get(url)
        time.sleep(1)
        return _parse_price_from_soup(BeautifulSoup(driver.page_source, "html.parser"))
    except Exception:
        return None
    finally:
        try:
            driver.quit()
        except Exception:
            pass


# --- [데이터 로드] ---
def load_data() -> pd.DataFrame:
    cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            for c in cols:
                if c not in df.columns:
                    df[c] = "자주구매" if c == "구분" else 0
            df = df.fillna("")
            # 비정상 가격(30,000,000원 초과) 자동 초기화
            fixed = False
            for price_col in ["가을판매가", "컴퓨존판매가", "실시간가"]:
                mask = df[price_col].apply(lambda v: safe_int(v) > 30_000_000)
                if mask.any():
                    df.loc[mask, price_col] = 0
                    fixed = True
            if fixed:
                df.to_excel(DB_FILE, index=False)
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=cols)


# --- [세션 초기화] ---
if "df" not in st.session_state:
    st.session_state.df = load_data()
if "editing_key" not in st.session_state:
    st.session_state.editing_key = None  # (current_tab, idx)
if "show_add_form" not in st.session_state:
    st.session_state.show_add_form = False


# --- [URL 파싱 진단] ---
with st.expander("🔧 URL 파싱 진단 (가격 조회 안 될 때)"):
    diag_url = st.text_input("테스트할 URL 입력", key="diag_url")
    if st.button("파싱 테스트", key="diag_btn"):
        if diag_url.strip().startswith("http"):
            with st.spinner("요청 중..."):
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Accept-Language": "ko-KR,ko;q=0.9",
                        "Referer": "https://www.compuzone.co.kr/",
                    }
                    resp = requests.get(diag_url.strip(), headers=headers, timeout=12)
                    st.write(f"**HTTP 상태코드:** {resp.status_code}")
                    st.write(f"**인코딩 감지:** {resp.apparent_encoding}")
                    if resp.encoding and resp.encoding.lower() in ("iso-8859-1", "latin-1"):
                        resp.encoding = resp.apparent_encoding
                    soup = BeautifulSoup(resp.text, "html.parser")
                    text_full = soup.get_text(" ", strip=True)

                    # ── 상세 진단 ──
                    st.write("**📋 가격 관련 텍스트 (앞 2000자):**")
                    # 가격 레이블 주변 텍스트 추출
                    price_context = []
                    for kw in ["정가", "판매가", "할인가", "특가", "현재가"]:
                        idx = text_full.find(kw)
                        if idx != -1:
                            price_context.append(f"[{kw} @ {idx}] " + text_full[idx:idx+60])
                    if price_context:
                        st.code("\n".join(price_context))
                    else:
                        st.warning("가격 레이블 텍스트 없음")

                    # skip_prices
                    SKIP_PATTERN = r'(?:정가|권장소비자가|시중가|소비자가|원가)[^\d]{0,6}([\d,]{4,})\s*원'
                    skip_prices: set[int] = set()
                    for sm in re.finditer(SKIP_PATTERN, text_full):
                        v = extract_first_price(sm.group(1))
                        if v:
                            skip_prices.add(v)
                    st.write(f"**제외 목록(정가 등):** {[f'{p:,}원' for p in skip_prices] or '없음'}")

                    # SALE_RE 매칭
                    SALE_PATTERN = re.compile(
                        r'(?:판매가|할인가|최종가|구매가|현재가|특가)[^\d]{0,6}([\d,]{4,})\s*원', re.S
                    )
                    sale_matches = []
                    for sm in SALE_PATTERN.finditer(text_full):
                        v = extract_first_price(sm.group(1))
                        if v:
                            sale_matches.append(v)
                    st.write(f"**판매가 패턴 매칭:** {[f'{p:,}원' for p in sale_matches] or '없음'}")

                    parsed = _parse_price_from_soup(soup)
                    if parsed:
                        st.success(f"✅ 최종 파싱 결과: **{parsed:,}원**")
                    else:
                        st.error("❌ 파싱 실패 — 페이지 텍스트 일부:")
                        st.code(text_full[:800])
                except Exception as e:
                    st.error(f"요청 오류: {e}")
        else:
            st.warning("http(s)://로 시작하는 URL을 입력해주세요.")


# --- [신규 상품 등록] ---
if st.button("➕ 신규 상품 등록"):
    st.session_state.show_add_form = not st.session_state.show_add_form
    st.rerun()

if st.session_state.show_add_form:
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat  = c2.selectbox("카테고리", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL")
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my   = c4.number_input("가을판매가", value=0, min_value=0, step=1000)
    r_cp   = c5.number_input("기준가",     value=0, min_value=0, step=1000)
    r_memo = c6.text_input("메모")

    add_clicked = c7.button("추가하기", use_container_width=True)
    if add_clicked:
        if not r_name.strip():
            st.warning("상품명을 입력해주세요.")
        else:
            with st.spinner("실시간 가격 조회 중..."):
                live_price = fetch_compuzone_price(r_link)
            if live_price is None:
                live_price = 0  # 조회 실패 시 0으로 저장 → "실시간 미조회" 표시
            new_row = {
                "구분": r_type, "카테고리": r_cat, "상품명": r_name.strip(),
                "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": live_price,
                "메모": r_memo, "링크": r_link.strip(),
            }
            st.session_state.df = pd.concat(
                [st.session_state.df, pd.DataFrame([new_row])], ignore_index=True
            )
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.session_state.show_add_form = False
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


# --- [가격 표시 HTML] ---
def price_html(row, show_fall: bool) -> str:
    fall_price = safe_int(row["가을판매가"])
    base_price = safe_int(row["컴퓨존판매가"])
    live_price = safe_int(row["실시간가"])

    sep = '<span style="color:#ddd;margin:0 3px;">·</span>'
    parts = []

    if show_fall and fall_price > 0:
        parts.append(
            f'<span style="color:#888;font-size:0.88em;">가을가</span>'
            f'<span style="font-size:1.0em;margin-left:3px;font-weight:500;">{fall_price:,}원</span>'
        )

    if base_price > 0:
        parts.append(
            f'<span style="color:#888;font-size:0.88em;">기준가</span>'
            f'<span style="font-size:1.0em;margin-left:3px;font-weight:500;">{base_price:,}원</span>'
        )

    if live_price == 0:
        parts.append('<span style="color:#aaa;font-size:0.85em;">실시간 미조회</span>')
    else:
        # 기준가가 있을 때만 델타 표시
        if base_price > 0:
            diff = live_price - base_price
            if diff > 0:
                delta = f'<span style="color:#e74c3c;font-weight:700;font-size:1.05em;margin-left:4px;">▲ {diff:,}원</span>'
            elif diff < 0:
                delta = f'<span style="color:#27ae60;font-weight:700;font-size:1.05em;margin-left:4px;">▼ {abs(diff):,}원</span>'
            else:
                delta = '<span style="color:#999;font-size:1.0em;margin-left:4px;">─ 동일</span>'
        else:
            delta = ''
        parts.append(
            f'<span style="color:#888;font-size:0.88em;">실시간</span>'
            f'<b style="font-size:1.0em;margin-left:3px;">{live_price:,}원</b>'
            f'{delta}'
        )

    return (
        f'<div style="white-space:nowrap;overflow:hidden;font-size:0.85em;">'
        + sep.join(parts)
        + '</div>'
    )


# --- [리스트 렌더링] ---
def display_list(target_df: pd.DataFrame, current_tab: str):
    if target_df.empty:
        st.info("표시할 상품이 없습니다.")
        return

    # 상단: 가격 업데이트 버튼
    _, btn_col = st.columns([8, 2])
    refresh_btn = btn_col.button(
        "🔄 가격 업데이트", key=f"re_{current_tab}", use_container_width=True
    )

    # ── 각 상품 카드
    for idx, row in target_df.iterrows():
        is_editing = st.session_state.editing_key == (current_tab, idx)

        with st.container(border=True):
            if not is_editing:
                # ── 일반 표시
                c_info, c_price, c_btns = st.columns([0.40, 0.47, 0.13])

                with c_info:
                    cat  = str(row["카테고리"]).strip()
                    name = str(row["상품명"]).strip()
                    memo = str(row["메모"]).strip()
                    info_parts = []
                    if cat and cat not in ("nan", ""):
                        info_parts.append(
                            f'<span style="font-size:0.72em;color:#888;background:#f0f0f0;'
                            f'padding:1px 5px;border-radius:3px;white-space:nowrap;">{cat}</span>'
                        )
                    info_parts.append(f'<span style="font-size:0.85em;font-weight:600;">{name}</span>')
                    if memo and memo not in ("nan", "-", "0", ""):
                        info_parts.append(
                            f'<span style="font-size:0.78em;color:#aaa;white-space:nowrap;">📝 {memo}</span>'
                        )
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:8px;overflow:hidden;">'
                        + " ".join(info_parts)
                        + "</div>",
                        unsafe_allow_html=True,
                    )

                with c_price:
                    show_fall = current_tab != "가격비교"
                    st.markdown(
                        f'<div style="padding:2px 0;">{price_html(row, show_fall)}</div>',
                        unsafe_allow_html=True,
                    )

                with c_btns:
                    link = str(row["링크"]).strip()
                    bc1, bc2, bc3 = st.columns([1, 1, 1])
                    if link.startswith("http"):
                        bc1.link_button("🔗", link, use_container_width=True)
                    if bc2.button("✏️", key=f"edit_{current_tab}_{idx}", use_container_width=True):
                        st.session_state.editing_key = (current_tab, idx)
                        st.rerun()
                    if bc3.button("🗑️", key=f"qdel_{current_tab}_{idx}", use_container_width=True):
                        st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
                        st.session_state.df.to_excel(DB_FILE, index=False)
                        st.rerun()

            else:
                # ── 수정 폼 (신규 등록과 동일한 레이아웃)
                st.caption("✏️ 상품 수정")
                fe1, fe2, fe3 = st.columns([1, 1, 2])
                n_type = fe1.selectbox(
                    "구분", ["가격비교", "자주구매"],
                    index=0 if str(row["구분"]) == "가격비교" else 1,
                    key=f"etype_{current_tab}_{idx}",
                )
                cat_options = CATEGORY_LIST[1:]
                cat_default = cat_options.index(str(row["카테고리"])) if str(row["카테고리"]) in cat_options else 0
                n_cat = fe2.selectbox(
                    "카테고리", cat_options,
                    index=cat_default,
                    key=f"ecat_{current_tab}_{idx}",
                )
                n_name = fe3.text_input("상품명", value=str(row["상품명"]), key=f"ename_{current_tab}_{idx}")

                n_link = st.text_input("컴퓨존 URL", value=str(row["링크"]), key=f"elink_{current_tab}_{idx}")

                fe4, fe5, fe6 = st.columns([1, 1, 2])
                n_fall = fe4.number_input(
                    "가을판매가", value=safe_int(row["가을판매가"]),
                    min_value=0, step=1000, key=f"efall_{current_tab}_{idx}",
                )
                n_base = fe5.number_input(
                    "기준가", value=safe_int(row["컴퓨존판매가"]),
                    min_value=0, step=1000, key=f"ebase_{current_tab}_{idx}",
                )
                memo_val = str(row["메모"])
                n_memo = fe6.text_input(
                    "메모",
                    value="" if memo_val in ("nan", "0", "") else memo_val,
                    key=f"ememo_{current_tab}_{idx}",
                )

                fb1, fb2, fb3 = st.columns([1, 1, 4])
                save_btn   = fb1.button("💾 저장", key=f"save_{current_tab}_{idx}", type="primary", use_container_width=True)
                delete_btn = fb2.button("🗑️ 삭제", key=f"del_{current_tab}_{idx}", use_container_width=True)
                cancel_btn = fb3.button("취소",    key=f"cancel_{current_tab}_{idx}")

                if save_btn:
                    st.session_state.df.at[idx, "구분"]        = n_type
                    st.session_state.df.at[idx, "카테고리"]    = n_cat
                    st.session_state.df.at[idx, "상품명"]      = n_name
                    st.session_state.df.at[idx, "링크"]        = n_link.strip()
                    st.session_state.df.at[idx, "가을판매가"]  = n_fall
                    st.session_state.df.at[idx, "컴퓨존판매가"] = n_base
                    st.session_state.df.at[idx, "메모"]        = n_memo
                    st.session_state.df.to_excel(DB_FILE, index=False)
                    st.session_state.editing_key = None
                    st.rerun()

                if delete_btn:
                    st.session_state.df = (
                        st.session_state.df.drop(idx).reset_index(drop=True)
                    )
                    st.session_state.df.to_excel(DB_FILE, index=False)
                    st.session_state.editing_key = None
                    st.rerun()

                if cancel_btn:
                    st.session_state.editing_key = None
                    st.rerun()

    # ── 가격 업데이트 (Selenium 우선, fallback: requests)
    if refresh_btn:
        progress_bar = st.progress(0, text="가격 조회 중...")
        total   = len(target_df)
        updated = 0
        failed  = 0

        # Chrome 드라이버 한 번만 생성 (JS 렌더링용)
        driver = _get_chrome_driver()
        selenium_ok = driver is not None

        for i, (idx, row) in enumerate(target_df.iterrows()):
            link = str(row.get("링크", "")).strip()
            price = None

            if link and link.startswith("http"):
                # 1차: Selenium (JS 렌더링)
                if selenium_ok:
                    try:
                        driver.set_page_load_timeout(12)
                        driver.get(link)
                        time.sleep(1)
                        price = _parse_price_from_soup(
                            BeautifulSoup(driver.page_source, "html.parser")
                        )
                    except Exception:
                        pass

                # 2차: requests fallback
                if not price:
                    price = _fetch_with_requests(link)

            if price:
                st.session_state.df.at[idx, "실시간가"] = price
                updated += 1
            else:
                failed += 1

            progress_bar.progress(
                (i + 1) / total,
                text=f"조회 중... ({i+1}/{total})",
            )

        if driver:
            try:
                driver.quit()
            except Exception:
                pass

        st.session_state.df.to_excel(DB_FILE, index=False)

        mode_note = "" if selenium_ok else " · Chrome 없음(requests 전용)"
        if updated:
            st.success(
                f"✅ {updated}개 갱신 완료"
                + (f" / {failed}개 조회 실패" if failed else "")
                + mode_note
            )
        else:
            st.warning(
                f"⚠️ 전체 조회 실패 ({failed}개){mode_note}\n\n"
                "URL이 올바른지 확인하거나, 해당 쇼핑몰이 크롤링을 차단 중일 수 있습니다."
            )
        st.rerun()


# --- [출력] ---
with tab1: display_list(df, "전체보기")
with tab2: display_list(df[df["구분"] == "가격비교"], "가격비교")
with tab3: display_list(df[df["구분"] == "자주구매"], "자주구매")
