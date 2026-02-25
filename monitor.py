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
    
    .main-title { font-size: 26px; font-weight: 600; color: #111827; margin-bottom: 20px; }
    
    /* 카드 디자인 */
    .product-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        margin-bottom: 15px;
    }
    
    /* 한 줄 레이아웃 (상품명 + 가격) */
    .top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .product-title { font-size: 17px; font-weight: 600; color: #111827; }
    .main-price { font-size: 18px; font-weight: 700; color: #3B82F6; }
    
    /* 상세 정보 열 */
    .detail-row { display: flex; gap: 30px; border-top: 1px solid #F3F4F6; padding-top: 12px; }
    .detail-item { font-size: 13px; color: #6B7280; }
    .detail-value { font-size: 14px; font-weight: 600; color: #374151; margin-top: 2px; }

    /* 변동폭 배지 */
    .status-up { color: #EF4444; background: #FEE2E2; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .status-down { color: #3B82F6; background: #DBEAFE; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    
    .stButton>button { border-radius: 6px; }
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
        # 컬럼명 자동 매핑
        df.rename(columns={"우리판매가": "가을판매가", "컴퓨존등록가": "컴퓨존판매가"}, inplace=True)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

def save_data(df): df.to_excel(DB_FILE, index=False)

# --- 화면 구성 ---
st.markdown('<div class="main-title">🍁 가을 가전 가격 대시보드</div>', unsafe_allow_html=True)

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 1. 신규 등록
with st.expander("➕ 상품 신규 등록", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", VIEW_TYPES)
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST)
    r_name = c3.text_input("상품명")
    
    c4, c5, c6, c7 = st.columns([2, 1, 1, 1])
    r_link = c4.text_input("컴퓨존 URL")
    r_my = c5.number_input("가을판매가", min_value=0, step=1000)
    r_cp = c6.number_input("컴퓨존판매가", min_value=0, step=1000)
    r_memo = c7.text_input("메모")
    
    if st.button("목록에 추가하기", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.rerun()

# 2. 필터 및 업데이트
st.write("")
nav1, nav2 = st.columns([7, 3])
with nav1:
    sel_mode = st.radio("보기 모드", VIEW_TYPES, horizontal=True, label_visibility="collapsed")
with nav2:
    if st.button("🔄 전체 가격 업데이트", use_container_width=True):
        with st.spinner("갱신 중..."):
            for i in st.session_state.df[st.session_state.df['구분'] == sel_mode].index:
                p = get_live_price(st.session_state.df.at[i, '링크'])
                if p: st.session_state.df.at[i, '실시간가'] = p
            save_data(st.session_state.df)
            st.rerun()

# 3. 상품 리스트
disp_df = st.session_state.df[st.session_state.df['구분'] == sel_mode]

for idx, row in disp_df.iterrows():
    st.markdown(f"""
    <div class="product-card">
        <div class="top-row">
            <div>
                <span style="font-size:12px; color:#3B82F6;">{row['카테고리']}</span>
                <div class="product-title">{row['상품명']}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size:12px; color:#6B7280;">가을판매가</div>
                <div class="main-price">{int(row['가을판매가']):,}원</div>
            </div>
        </div>
        <div class="detail-row">
            <div class="detail-item">컴퓨존판매가(기준)<div class="detail-value">{int(row['컴퓨존판매가']):,}원</div></div>
            <div class="detail-item">실시간 컴퓨존가<div class="detail-value">{int(row['실시간가']):,}원</div></div>
            <div class="detail-item">비고<div class="detail-value">{row['메모']}</div></div>
            <div style="margin-left:auto;">
                {"<span class='status-up'>▲ "+format(int(row['실시간가'])-int(row['컴퓨존판매가']), ',')+"</span>" if int(row['실시간가']) > int(row['컴퓨존판매가']) else 
                  "<span class='status-down'>▼ "+format(abs(int(row['실시간가'])-int(row['컴퓨존판매가'])), ',')+"</span>" if int(row['실시간가']) < int(row['컴퓨존판매가']) else 
                  "<span style='color:#9CA3AF; font-size:12px;'>변동없음</span>"}
            </div>
            <div style="padding-top:5px;"><a href="{row['링크']}" target="_blank" style="text-decoration:none; font-size:13px; color:#3B82F6;">🔗 링크</a></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button(f"상품 삭제", key=f"del_{idx}"):
        st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
        save_data(st.session_state.df)
        st.rerun()
