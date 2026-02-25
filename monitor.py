import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# --- 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]
VIEW_TYPES = ["가격비교", "자주구매"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- 모던 디자인 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F9FAFB; }
    
    .main-title { font-size: 28px; font-weight: 600; color: #111827; margin-bottom: 5px; }
    .sub-title { font-size: 14px; color: #6B7280; margin-bottom: 30px; }
    
    /* 카드 디자인 */
    .product-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        margin-bottom: 12px;
        transition: all 0.2s;
    }
    .product-card:hover { border-color: #3B82F6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    
    /* 가격 태그 */
    .price-label { font-size: 12px; color: #6B7280; margin-bottom: 4px; }
    .price-value { font-size: 16px; font-weight: 600; color: #111827; }
    
    /* 변동폭 디자인 */
    .status-up { color: #EF4444; background: #FEE2E2; padding: 2px 8px; border-radius: 4px; font-size: 13px; font-weight: 600; }
    .status-down { color: #3B82F6; background: #DBEAFE; padding: 2px 8px; border-radius: 4px; font-size: 13px; font-weight: 600; }
    .status-none { color: #9CA3AF; font-size: 13px; }
    
    /* 버튼 커스텀 */
    .stButton>button { border-radius: 8px; border: 1px solid #E5E7EB; background: white; color: #374151; font-weight: 500; }
    .stButton>button:hover { border-color: #3B82F6; color: #3B82F6; background: #F0F7FF; }
    
    /* 입력창 디자인 */
    div[data-testid="stExpander"] { background: white; border: 1px solid #E5E7EB; border-radius: 12px; }
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
        return None
    except: return None

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        # 컬럼명 보정 (기존 데이터 호환)
        mapping = {"우리판매가": "가을판매가", "컴퓨존등록가": "컴퓨존판매가"}
        df.rename(columns=mapping, inplace=True)
        for col in ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]:
            if col not in df.columns: df[col] = 0 if "가" in col else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

def save_data(df): df.to_excel(DB_FILE, index=False)

# --- 메인 화면 ---
st.markdown('<div class="main-title">가을 가전 가격 관리</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">실시간 컴퓨존 가격 추적 대시보드</div>', unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 1. 상단 등록 바
with st.expander("📦 신규 상품 등록", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    reg_type = c1.selectbox("구분", VIEW_TYPES)
    reg_cat = c2.selectbox("카테고리", CATEGORY_LIST)
    reg_name = c3.text_input("상품명")
    c4, c5, c6, c7 = st.columns([2, 1, 1, 1])
    reg_link = c4.text_input("URL")
    reg_my = c5.number_input("가을판매가", step=1000)
    reg_comp = c6.number_input("컴퓨존판매가", step=1000)
    reg_memo = c7.text_input("비고")
    if st.button("목록에 추가하기"):
        if reg_name and reg_link:
            new_row = {"구분": reg_type, "카테고리": reg_cat, "상품명": reg_name, "가을판매가": reg_my, "컴퓨존판매가": reg_comp, "실시간가": reg_comp, "메모": reg_memo, "링크": reg_link}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.rerun()

# 2. 필터 섹션
st.write("")
col_nav1, col_nav2 = st.columns([7, 3])
with col_nav1:
    selected_mode = st.radio("보기 모드", VIEW_TYPES, horizontal=True, label_visibility="collapsed")

with col_nav2:
    if st.button("🔄 실시간 가격 일괄 업데이트"):
        with st.spinner("가격을 업데이트 중..."):
            temp_df = st.session_state.df[st.session_state.df['구분'] == selected_mode]
            for i in temp_df.index:
                p = get_live_price(st.session_state.df.at[i, '링크'])
                if p: st.session_state.df.at[i, '실시간가'] = p
            save_data(st.session_state.df)
            st.rerun()

# 3. 리스트 출력 (카드 스타일)
display_df = st.session_state.df[st.session_state.df['구분'] == selected_mode]

if display_df.empty:
    st.info("해당 구분에 등록된 상품이 없습니다.")
else:
    for idx, row in display_df.iterrows():
        st.markdown(f"""
        <div class="product-card">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <span style="font-size: 11px; color: #3B82F6; font-weight: 600; text-transform: uppercase;">{row['카테고리']}</span>
                    <div style="font-size: 16px; font-weight: 600; color: #111827; margin-top: 4px;">{row['상품명']}</div>
                    <div style="font-size: 13px; color: #6B7280; margin-top: 4px;">{row['메모']}</div>
                </div>
                <div style="text-align: right; min-width: 120px;">
                    <a href="{row['링크']}" target="_blank" style="text-decoration: none; font-size: 13px; color: #3B82F6;">컴퓨존 바로가기 ↗</a>
                </div>
            </div>
            <div style="display: flex; margin-top: 20px; gap: 40px; border-top: 1px solid #F3F4F6; padding-top: 15px;">
                <div>
                    <div class="price-label">가을판매가</div>
                    <div class="price-value">{int(row['가을판매가']):,}원</div>
                </div>
                <div>
                    <div class="price-label">컴퓨존판매가 (기준)</div>
                    <div class="price-value" style="color: #9CA3AF;">{int(row['컴퓨존판매가']):,}원</div>
                </div>
                <div>
                    <div class="price-label">실시간 컴퓨존가</div>
                    <div class="price-value">{int(row['실시간가']):,}원</div>
                </div>
                <div style="margin-left: auto; align-self: end;">
                    {"<span class='status-up'>▲ "+format(int(row['실시간가'])-int(row['컴퓨존판매가']), ',')+"</span>" if int(row['실시간가']) > int(row['컴퓨존판매가']) else 
                      "<span class='status-down'>▼ "+format(abs(int(row['실시간가'])-int(row['컴퓨존판매가'])), ',')+"</span>" if int(row['실시간가']) < int(row['컴퓨존판매가']) else 
                      "<span class='status-none'>변동없음</span>"}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("상품 삭제", key=f"del_{idx}"):
            st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.df)
            st.rerun()
