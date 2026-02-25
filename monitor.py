import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 파일 및 기본 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- CSS (간결하게 한 줄 정렬) ---
st.markdown("""
    <style>
    .product-row {
        background: white; padding: 12px; border-radius: 8px;
        border: 1px solid #E2E8F0; margin-bottom: 8px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .name-text { font-size: 14px; font-weight: 600; flex: 1; margin: 0 15px; }
    .price-box { width: 90px; text-align: center; font-size: 14px; }
    .fall-badge { background: #2563EB; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    /* 열기 버튼 디자인 */
    .open-btn {
        text-decoration: none !important;
        background: #10B981; color: white !important;
        padding: 8px 15px; border-radius: 5px;
        font-weight: bold; font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 실시간 가격 수집용 (여기서만 https를 임시로 체크합니다) ---
def get_live_price(url):
    try:
        # 가격 수집할 때만 주소가 필요하므로 최소한의 처리만 함
        target_url = str(url).strip()
        if not target_url.startswith('http'): target_url = 'https://' + target_url
        res = requests.get(target_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        p_tag = soup.select_one("#product_content_2_price")
        return int(''.join(filter(str.isdigit, p_tag.get_text()))) if p_tag else None
    except: return None

def load_data():
    if os.path.exists(DB_FILE): return pd.read_excel(DB_FILE)
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()

# --- 화면 구성 ---
st.title("🍁 가을 가전 관리자")

# 1. 등록 부분
with st.expander("➕ 상품 등록"):
    c1, c2, c3 = st.columns([1, 1, 4])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST)
    r_name = c3.text_input("상품명")
    
    r_link = st.text_input("여기에 주소를 그대로 복사해서 넣으세요 (https:// 포함)")
    
    c4, c5, c6 = st.columns(3)
    r_my = c4.number_input("가을판매가", step=1000)
    r_cp = c5.number_input("컴퓨존판매가", step=1000)
    r_memo = c6.text_input("메모")
    
    if st.button("저장하기"):
        new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()

# 2. 검색 및 탭
search = st.text_input("🔍 검색")
t1, t2, t3 = st.tabs(["전체보기", "가격비교", "자주구매"])
selected = "전체보기" if t1 else "가격비교" if t2 else "자주구매"

df = st.session_state.df.copy()
if selected != "전체보기": df = df[df['구분'] == selected]
if search: df = df[df['상품명'].str.contains(search, case=False)]

# 3. 리스트 출력
for idx, row in df.iterrows():
    # 주소에 아무런 가공을 하지 않고 그대로 링크에 박습니다.
    raw_link = str(row['링크'])
    
    st.markdown(f"""
    <div class="product-row">
        <div style="display:flex; align-items:center; flex:1;">
            <span style="font-size:11px; color:#666;">[{row['카테고리']}]</span>
            <div class="name-text">{row['상품명']}</div>
        </div>
        <div style="display:flex; align-items:center; gap:10px;">
            <div class="price-box"><span class="fall-badge">{int(row['가을판매가']):,}</span></div>
            <div class="price-box" style="color:#999;">{int(row['컴퓨존판매가']):,}</div>
            <div class="price-box" style="font-weight:bold;">{int(row['실시간가']):,}</div>
            <a href="{raw_link}" target="_blank" class="open-btn">링크열기</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 4. 하단 버튼
if st.button("🔄 전체 가격 업데이트"):
    for i in df.index:
        p = get_live_price(st.session_state.df.at[i, '링크'])
        if p: st.session_state.df.at[i, '실시간가'] = p
    st.session_state.df.to_excel(DB_FILE, index=False)
    st.rerun()
