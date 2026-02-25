import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 파일 및 기본 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- CSS (일렬 정렬, 메모 노출 디자인) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #F8F9FA; }
    
    .product-row {
        background: white; padding: 12px 15px; border-radius: 8px;
        border: 1px solid #E2E8F0; margin-bottom: 6px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .info-area { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .top-line { display: flex; align-items: center; margin-bottom: 4px; }
    .name-text { 
        font-size: 14px; font-weight: 600; color: #1E293B; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; 
    }
    /* 메모(비고) 스타일 */
    .memo-text { font-size: 12px; color: #64748B; font-weight: 400; }
    
    .price-area { display: flex; align-items: center; gap: 15px; flex-shrink: 0; }
    .price-box { text-align: center; width: 90px; }
    .fall-badge { background: #2563EB; color: white; padding: 5px 10px; border-radius: 6px; font-weight: 700; font-size: 15px; }
    
    .open-btn {
        text-decoration: none !important; background: #10B981; color: white !important;
        padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 700;
    }
    .open-btn:hover { background: #059669; }
    </style>
    """, unsafe_allow_html=True)

# --- 기능 함수 ---
def get_live_price(url):
    try:
        target_url = str(url).strip()
        if not target_url.startswith('http'): target_url = 'https://' + target_url
        res = requests.get(target_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        p_tag = soup.select_one("#product_content_2_price")
        return int(''.join(filter(str.isdigit, p_tag.get_text()))) if p_tag else None
    except: return None

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for col in cols:
            if col not in df.columns: df[col] = 0 if "가" in col else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()

# --- 메인 화면 ---
st.markdown('<div style="font-size:24px; font-weight:700; margin-bottom:20px;">🍁 가을 가전 통합 관리자</div>', unsafe_allow_html=True)

# 1. 신규 등록
with st.expander("➕ 신규 상품 등록"):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리 등록", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL (주소를 그대로 복사해서 넣으세요)")
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", step=1000)
    r_cp = c5.number_input("컴퓨존판매가", step=1000)
    r_memo = c6.text_input("메모(비고)")
    if c7.button("목록에 추가", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 2. 검색 및 카테고리 필터
col_s1, col_s2 = st.columns([7, 3])
with col_s1:
    search_q = st.text_input("🔍 상품명 또는 메모 검색", placeholder="찾으시는 상품을 입력하세요...")
with col_s2:
    category_q = st.selectbox("📂 카테고리 필터", CATEGORY_LIST)

t_all, t_price, t_fav = st.tabs(["전체보기", "가격비교", "자주구매"])
sel_tab = "전체보기" if t_all else "가격비교" if t_price else "자주구매"

# 데이터 필터링 (탭 + 검색어 + 카테고리)
disp_df = st.session_state.df.copy()
if sel_tab != "전체보기": disp_df = disp_df[disp_df['구분'] == sel_tab]
if category_q != "전체보기": disp_df = disp_df[disp_df['카테고리'] == category_q]
if search_q: disp_df = disp_df[disp_df['상품명'].str.contains(search_q, case=False) | disp_df['메모'].str.contains(search_q, case=False)]

# 3. 액션 바
st.write("")
col_act1, col_act2, col_act3 = st.columns([7, 1.5, 1.5])
with col_act2: refresh_btn = st.button("🔄 가격 갱신", use_container_width=True)
with col_act3: delete_btn = st.button("🗑️ 선택 삭제", use_container_width=True)

# 4. 리스트 출력
selected_indices = []
if disp_df.empty:
    st.info("검색 조건에 맞는 상품이 없습니다.")
else:
    for idx, row in disp_df.iterrows():
        c_chk, c_row = st.columns([0.03, 0.97])
        with c_chk:
            if st.checkbox("", key=f"del_{idx}"): selected_indices.append(idx)
        with c_row:
            raw_url = str(row['링크']).strip()
            st.markdown(f"""
            <div class="product-row">
                <div class="info-area">
                    <div class="top-line">
                        <span style="font-size:10px; color:#666; margin-right:8px; border:1px solid #CCC; padding:0 4px; border-radius:3px;">{row['카테고리']}</span>
                        <div class="name-text">{row['상품명']}</div>
                    </div>
                    <div class="memo-text">📝 {row['메모'] if row['메모'] != "-" else "메모 없음"}</div>
                </div>
                <div class="price-area">
                    <div class="price-box"><div class="fall-badge">{int(row['가을판매가']):,}</div></div>
                    <div class="price-box" style="color:#94A3B8; font-size:13px;">{int(row['컴퓨존판매가']):,}</div>
                    <div class="price-box" style="font-weight:700; color:#1E293B;">{int(row['실시간가']):,}</div>
                    <div style="width:60px; text-align:right;">
                        <a href="{raw_url}" target="_blank" class="open-btn">열기</a>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# 5. 로직 처리
if delete_btn:
    if not selected_indices: st.warning("삭제할 항목을 체크해주세요!")
    else:
        st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()

if refresh_btn:
    with st.spinner("가격을 업데이트 중..."):
        for i in disp_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
