import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]
VIEW_TYPES = ["전체보기", "가격비교", "자주구매"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- CSS (한 줄 유지 및 버튼 강조) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #F8F9FA; }
    
    .product-row {
        background: white; padding: 10px 15px; border-radius: 8px;
        border: 1px solid #E2E8F0; margin-bottom: 6px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .info-area { display: flex; align-items: center; flex: 1; min-width: 0; }
    .name-text { 
        font-size: 14px; font-weight: 500; color: #334155; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 20px;
    }
    .tag { font-size: 10px; padding: 2px 8px; border-radius: 4px; font-weight: 600; margin-right: 8px; white-space: nowrap; }
    .tag-type { background: #64748B; color: white; }
    .tag-cat { background: #DBEAFE; color: #1E40AF; }
    
    .price-area { display: flex; align-items: center; gap: 15px; flex-shrink: 0; }
    .price-box { text-align: center; width: 85px; }
    .fall-badge { background: #2563EB; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 15px; }
    .diff-badge { font-size: 11px; font-weight: 700; padding: 3px 6px; border-radius: 4px; min-width: 65px; text-align: center; }
    .up { background: #FEE2E2; color: #B91C1C; }
    .down { background: #DBEAFE; color: #1D4ED8; }
    
    /* 링크 버튼: 브라우저 기본 동작 강조 */
    .direct-link {
        text-decoration: none !important;
        background: #2563EB;
        color: white !important;
        padding: 6px 14px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 700;
        display: inline-block;
    }
    .direct-link:hover { background: #1D4ED8; }
    </style>
    """, unsafe_allow_html=True)

# URL 정제 함수
def clean_url(url):
    if not url: return ""
    url = str(url).strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def get_live_price(url):
    url = clean_url(url)
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        p_tag = soup.select_one("#product_content_2_price")
        return int(''.join(filter(str.isdigit, p_tag.get_text()))) if p_tag else None
    except: return None

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        df.rename(columns={"우리판매가": "가을판매가", "컴퓨존등록가": "컴퓨존판매가"}, inplace=True)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()

st.markdown('<div style="font-size:24px; font-weight:700; margin-bottom:20px;">🍁 가을 가전 가격 관리자</div>', unsafe_allow_html=True)

# 1. 신규 등록
with st.expander("➕ 신규 상품 등록 (주소 복사해서 넣어주세요)", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST)
    r_name = c3.text_input("상품명")
    c4, c5, c6, c7 = st.columns([2, 1, 1, 1])
    r_link = c4.text_input("컴퓨존 URL (정확히 입력)")
    r_my = c5.number_input("가을판매가", min_value=0, step=1000)
    r_cp = c6.number_input("컴퓨존판매가", min_value=0, step=1000)
    r_memo = c7.text_input("비고")
    if st.button("목록에 추가하기", use_container_width=True):
        if r_name and r_link:
            new_url = clean_url(r_link)
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": new_url}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 2. 검색 및 필터
search_q = st.text_input("🔍 상품명/메모 검색")
tabs = st.tabs(["전체보기", "가격비교", "자주구매"])
sel_tab = "전체보기" if tabs[0] else "가격비교" if tabs[1] else "자주구매"

disp_df = st.session_state.df.copy()
if sel_tab != "전체보기": disp_df = disp_df[disp_df['구분'] == sel_tab]
if search_q: disp_df = disp_df[disp_df['상품명'].str.contains(search_q, case=False) | disp_df['메모'].str.contains(search_q, case=False)]

# 3. 버튼
act1, act2, act3 = st.columns([7, 1.5, 1.5])
with act2: refresh = st.button("🔄 가격 갱신", use_container_width=True)
with act3: delete = st.button("🗑️ 선택 삭제", use_container_width=True)

# 4. 리스트 출력
selected_indices = []
for idx, row in disp_df.iterrows():
    c_chk, c_row = st.columns([0.03, 0.97])
    with c_chk:
        if st.checkbox("", key=f"c_{idx}"): selected_indices.append(idx)
    with c_row:
        diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
        st_class = "up" if diff > 0 else "down" if diff < 0 else "none"
        diff_txt = f"▲{diff:,}" if diff > 0 else f"▼{abs(diff):,}" if diff < 0 else "-"
        
        final_link = clean_url(row['링크']) # 주소 한 번 더 검증

        st.markdown(f"""
        <div class="product-row">
            <div class="info-area">
                <span class="tag tag-type">{row['구분']}</span>
                <span class="tag tag-cat">{row['카테고리']}</span>
                <div class="name-text" title="{row['상품명']}">{row['상품명']}</div>
            </div>
            <div class="price-area">
                <div class="price-box"><div class="fall-badge">{int(row['가을판매가']):,}</div></div>
                <div class="price-box"><div style="font-size:14px; color:#475569;">{int(row['컴퓨존판매가']):,}</div></div>
                <div class="price-box"><div style="font-size:14px; font-weight:600;">{int(row['실시간가']):,}</div></div>
                <div class="price-box"><div class="diff-badge {st_class}">{diff_txt}</div></div>
                <div style="width:60px; text-align:right;">
                    <a href="{final_link}" target="_blank" class="direct-link">구매이동</a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 5. 로직
if refresh:
    with st.spinner("가격 갱신 중..."):
        for i in disp_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()

if delete:
    if not selected_indices: st.warning("항목을 선택하세요!")
    else:
        st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
