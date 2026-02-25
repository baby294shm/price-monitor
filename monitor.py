import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# --- 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]
# '전체보기'를 리스트 맨 앞에 추가했습니다.
VIEW_TYPES = ["전체보기", "가격비교", "자주구매"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- 심플 모던 디자인 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #F8F9FA; }
    
    .main-title { font-size: 24px; font-weight: 700; color: #1A1A1A; margin: 20px 0; }
    
    /* 리스트 아이템 디자인 */
    .product-row {
        background-color: white;
        padding: 12px 20px;
        border-radius: 8px;
        border: 1px solid #E9ECEF;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .info-box { display: flex; align-items: center; flex: 1; min-width: 0; }
    .cat-tag { font-size: 10px; color: #495057; background: #E9ECEF; padding: 2px 6px; border-radius: 4px; margin-right: 12px; white-space: nowrap; }
    .type-tag { font-size: 10px; color: #ffffff; background: #6C757D; padding: 2px 6px; border-radius: 4px; margin-right: 8px; white-space: nowrap; }
    .name-text { font-size: 14px; font-weight: 500; color: #212529; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-right: 20px; }
    
    .price-group { display: flex; align-items: center; gap: 25px; white-space: nowrap; }
    .price-unit { text-align: center; width: 90px; }
    .price-label { font-size: 11px; color: #868E96; margin-bottom: 2px; }
    .price-value { font-size: 14px; font-weight: 600; }
    .fall-price { color: #007BFF; font-size: 15px; font-weight: 700; }
    
    .status-up { color: #FA5252; font-weight: 600; font-size: 12px; }
    .status-down { color: #228BE6; font-weight: 600; font-size: 12px; }
    .status-none { color: #ADB5BD; font-size: 12px; }
    
    /* 탭 디자인 커스텀 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #ffffff; border: 1px solid #E9ECEF; border-radius: 6px 6px 0 0; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 기능 함수 ---
def get_live_price(product_url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(product_url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            price_tag = soup.select_one("#product_content_2_price")
            if price_tag: return int(''.join(filter(str.isdigit, price_tag.get_text())))
    except: pass
    return None

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        df.rename(columns={"우리판매가": "가을판매가", "컴퓨존등록가": "컴퓨존판매가"}, inplace=True)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

def save_data(df): df.to_excel(DB_FILE, index=False)

# --- 메인 화면 ---
st.markdown('<div class="main-title">🍁 가을 가전 통합 관리 대시보드</div>', unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 1. 신규 등록 섹션
with st.expander("➕ 상품 신규 등록", expanded=False):
    c1, c2, c3, c4 = st.columns([1, 1, 3, 2])
    # 등록할 때는 '전체보기'가 아닌 실제 구분을 선택해야 합니다.
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"]) 
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST)
    r_name = c3.text_input("상품명")
    r_memo = c4.text_input("메모(비고)")
    
    c5, c6, c7, c8 = st.columns([3, 1, 1, 1])
    r_link = c5.text_input("컴퓨존 URL")
    r_my = c6.number_input("가을판매가", min_value=0, step=1000)
    r_cp = c7.number_input("컴퓨존판매가", min_value=0, step=1000)
    if c8.button("저장하기", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.rerun()

# 2. 탭 및 업데이트 버튼
st.write("")
tab_all, tab_comp, tab_fav = st.tabs(["📋 전체보기", "📊 가격비교", "⭐ 자주구매"])

# 선택된 탭에 따른 데이터 필터링
if tab_all:
    sel_mode = "전체보기"
    disp_df = st.session_state.df
elif tab_comp:
    sel_mode = "가격비교"
    disp_df = st.session_state.df[st.session_state.df['구분'] == "가격비교"]
else:
    sel_mode = "자주구매"
    disp_df = st.session_state.df[st.session_state.df['구분'] == "자주구매"]

# 업데이트 버튼 (탭 아래 배치)
col_up1, col_up2 = st.columns([8, 2])
with col_up2:
    if st.button("🔄 현재 목록 가격 갱신", use_container_width=True):
        with st.spinner("갱신 중..."):
            for i in disp_df.index:
                p = get_live_price(st.session_state.df.at[i, '링크'])
                if p: st.session_state.df.at[i, '실시간가'] = p
            save_data(st.session_state.df)
            st.rerun()

# 3. 리스트 헤더
st.markdown("""
    <div style="display: flex; padding: 10px 20px; font-size: 11px; color: #868E96; font-weight: 600;">
        <div style="flex: 1;">상품 정보 (구분 / 카테고리 / 명칭)</div>
        <div style="display: flex; gap: 25px; padding-right: 120px;">
            <div style="width: 90px; text-align: center;">가을판매가</div>
            <div style="width: 90px; text-align: center;">컴퓨존(기준)</div>
            <div style="width: 90px; text-align: center;">실시간가</div>
            <div style="width: 60px; text-align: center;">변동</div>
        </div>
    </div>
""", unsafe_allow_html=True)

# 4. 상품 리스트 출력
if disp_df.empty:
    st.info("등록된 상품이 없습니다.")
else:
    for idx, row in disp_df.iterrows():
        diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
        diff_html = f"<span class='status-up'>▲{diff:,}</span>" if diff > 0 else f"<span class='status-down'>▼{abs(diff):,}</span>" if diff < 0 else "<span class='status-none'>-</span>"
        
        # 전체보기일 때만 '구분' 태그 표시
        type_tag_html = f"<span class='type-tag'>{row['구분']}</span>" if sel_mode == "전체보기" else ""

        st.markdown(f"""
        <div class="product-row">
            <div class="info-box">
                {type_tag_html}
                <span class="cat-tag">{row['카테고리']}</span>
                <div class="name-text" title="{row['상품명']}">{row['상품명']}</div>
            </div>
            <div class="price-group">
                <div class="price-unit"><div class="fall-price">{int(row['가을판매가']):,}</div></div>
                <div class="price-unit"><div class="price-value" style="color:#868E96;">{int(row['컴퓨존판매가']):,}</div></div>
                <div class="price-unit"><div class="price-value">{int(row['실시간가']):,}</div></div>
                <div class="price-unit" style="width:60px;">{diff_html}</div>
                <div style="margin-left: 10px;"><a href="{row['링크']}" target="_blank" style="text-decoration:none; font-size:18px;">🔗</a></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 삭제 버튼 (초슬림 배치)
        c_del1, c_del2 = st.columns([0.97, 0.03])
        if c_del2.button("×", key=f"del_{idx}", help="삭제"):
            st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.df)
            st.rerun()
