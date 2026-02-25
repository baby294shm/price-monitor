import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# --- 설정 및 스타일 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]
VIEW_TYPES = ["가격비교", "자주구매"]

st.set_page_config(page_title="Price Master Pro", layout="wide", initial_sidebar_state="collapsed")

# 커스텀 CSS (세련된 디자인 입히기)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; border: none; }
    .stButton>button:hover { background-color: #0056b3; color: white; }
    div[data-testid="stExpander"] { background-color: white; border-radius: 10px; border: 1px solid #e0e0e0; }
    .price-up { color: #ff4b4b; font-weight: bold; }
    .price-down { color: #1c83e1; font-weight: bold; }
    .no-change { color: #6c757d; }
    </style>
    """, unsafe_allow_html=True)

# --- 함수부 (기능은 유지) ---
def get_live_price(product_url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(product_url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            price_tag = soup.select_one("#product_content_2_price")
            if price_tag:
                return int(''.join(filter(str.isdigit, price_tag.get_text())))
        return None
    except: return None

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        for col in ["구분", "카테고리", "상품명", "우리판매가", "컴퓨존등록가", "실시간가", "메모", "링크"]:
            if col not in df.columns: df[col] = 0 if "가" in col else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "우리판매가", "컴퓨존등록가", "실시간가", "메모", "링크"])

def save_data(df): df.to_excel(DB_FILE, index=False)

# --- 화면 구성 ---
st.title("🚀 PRICE MASTER PRO")
st.caption("컴퓨존 실시간 가격 비교 및 재고 관리 시스템")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 상단 요약 대시보드 (디자인 포인트)
if not st.session_state.df.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 등록 상품", f"{len(st.session_state.df)}개")
    m2.metric("자주구매", f"{len(st.session_state.df[st.session_state.df['구분']=='자주구매'])}개")
    m3.metric("가격비교", f"{len(st.session_state.df[st.session_state.df['구분']=='가격비교'])}개")
    m4.metric("오늘의 업데이트", pd.Timestamp.now().strftime('%m/%d %H:%M'))

st.write("")

# 신규 등록 섹션 (Expander 디자인)
with st.expander("➕ 새로운 상품 등록하기", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    reg_type = c1.selectbox("구분", VIEW_TYPES)
    reg_cat = c2.selectbox("카테고리", CATEGORY_LIST)
    reg_name = c3.text_input("상품명")
    
    c4, c5, c6, c7 = st.columns([2, 1, 1, 1])
    reg_link = c4.text_input("컴퓨존 URL")
    reg_my_price = c5.number_input("우리 판매가", min_value=0, step=1000)
    reg_comp_price = c6.number_input("컴퓨존가", min_value=0, step=1000)
    reg_memo = c7.text_input("메모")
    
    if st.button("신규 상품 저장"):
        if reg_name and reg_link:
            new_row = {"구분": reg_type, "카테고리": reg_cat, "상품명": reg_name, "우리판매가": reg_my_price, "컴퓨존등록가": reg_comp_price, "실시간가": reg_comp_price, "메모": reg_memo, "링크": reg_link}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df)
            st.rerun()

st.write("")

# 메인 리스트 컨트롤러
if not st.session_state.df.empty:
    ctrl_c1, ctrl_c2, ctrl_c3 = st.columns([3, 4, 3])
    with ctrl_c1:
        view_mode = st.segmented_control("모드 선택", VIEW_TYPES, default="가격비교")
    with ctrl_c2:
        view_cat = st.multiselect("카테고리 필터", CATEGORY_LIST, placeholder="전체보기")
    
    display_df = st.session_state.df[st.session_state.df['구분'] == view_mode]
    if view_cat:
        display_df = display_df[display_df['카테고리'].isin(view_cat)]

    with ctrl_c3:
        if st.button("🔄 실시간 가격 갱신"):
            with st.status("가격 정보를 수집 중입니다...", expanded=False) as status:
                for i in display_df.index:
                    new_p = get_live_price(st.session_state.df.at[i, '링크'])
                    if new_p: st.session_state.df.at[i, '실시간가'] = new_p
                save_data(st.session_state.df)
                status.update(label="업데이트 완료!", state="complete", expanded=False)
            st.rerun()

    # 테이블 디자인
    st.write("")
    for idx, row in display_df.iterrows():
        with st.container():
            t1, t2, t3, t4, t5, t6, t7 = st.columns([1, 3, 1.5, 1.5, 1.5, 1, 0.5])
            t1.caption(f"{row['카테고리']}")
            t2.markdown(f"**{row['상품명']}**")
            t3.write(f"우리: {int(row['우리판매가']):,}원")
            t4.write(f"컴퓨: {int(row['컴퓨존등록가']):,}원")
            
            # 실시간가 및 변동폭
            now_p = row['실시간가']
            if pd.notna(now_p) and now_p != 0:
                diff = int(now_p) - int(row['컴퓨존등록가'])
                t5.write(f"실시간: {int(now_p):,}원")
                if diff > 0: t6.markdown(f"<span class='price-up'>▲{diff:,}</span>", unsafe_allow_html=True)
                elif diff < 0: t6.markdown(f"<span class='price-down'>▼{abs(diff):,}</span>", unsafe_allow_html=True)
                else: t6.markdown("<span class='no-change'>-</span>", unsafe_allow_html=True)
            else:
                t5.write("연결확인")
                t6.write("-")
            
            if t7.button("🗑️", key=f"del_{idx}"):
                st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
                save_data(st.session_state.df)
                st.rerun()
            st.markdown("---")
