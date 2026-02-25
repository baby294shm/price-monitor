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

# --- 디자인 입히기 (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #F0F2F5; }
    
    /* 제목 부분 */
    .main-title { font-size: 28px; font-weight: 700; color: #1E293B; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
    
    /* 리스트 카드 디자인 */
    .product-card {
        background: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        transition: transform 0.1s;
    }
    .product-card:hover { border-color: #3B82F6; background-color: #F8FAFC; }
    
    /* 태그 디자인 */
    .tag { font-size: 11px; padding: 3px 8px; border-radius: 6px; font-weight: 600; margin-right: 5px; }
    .tag-type { background: #64748B; color: white; }
    .tag-cat { background: #DBEAFE; color: #1E40AF; }
    
    /* 상품명 */
    .product-name { font-size: 15px; font-weight: 500; color: #334155; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    
    /* 가격 섹션 */
    .price-container { display: flex; align-items: center; gap: 20px; flex-shrink: 0; }
    .price-box { text-align: center; width: 100px; }
    .price-label { font-size: 11px; color: #94A3B8; margin-bottom: 2px; }
    
    /* 핵심: 가을판매가 강조 */
    .fall-price-badge {
        background: #2563EB;
        color: white;
        padding: 6px 12px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 16px;
        box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
    }
    
    .normal-price { font-weight: 600; color: #475569; font-size: 14px; }
    
    /* 변동 배지 */
    .status-badge { font-size: 12px; font-weight: 700; padding: 4px 8px; border-radius: 6px; min-width: 70px; text-align: center; }
    .up { background: #FEE2E2; color: #DC2626; }
    .down { background: #DBEAFE; color: #2563EB; }
    .none { background: #F1F5F9; color: #94A3B8; }

    /* 버튼 스타일 */
    .stButton>button { border-radius: 8px; font-weight: 600; }
    div[data-testid="stExpander"] { background: white; border-radius: 12px; border: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- 기능 함수 ---
def get_live_price(url):
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
        for c in ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

# --- 데이터 준비 ---
if 'df' not in st.session_state: st.session_state.df = load_data()

st.markdown('<div class="main-title">🍁 가을 가전 통합 관리 매니저</div>', unsafe_allow_html=True)

# 1. 상품 등록
with st.expander("✨ 신규 상품 추가하기", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST)
    r_name = c3.text_input("상품명 (예: 삼성 DDR5 8G)")
    
    c4, c5, c6, c7 = st.columns([2, 1, 1, 1])
    r_link = c4.text_input("컴퓨존 URL")
    r_my = c5.number_input("가을판매가", min_value=0, step=1000)
    r_cp = c6.number_input("컴퓨존판매가(기준)", min_value=0, step=1000)
    r_memo = c7.text_input("메모")
    
    if st.button("🚀 목록에 저장", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 2. 탭 선택
tabs = st.tabs(["전체보기", "가격비교", "자주구매"])
selected_mode = "전체보기"
if tabs[1]: selected_mode = "가격비교"
if tabs[2]: selected_mode = "자주구매"

# 필터링
if selected_mode == "전체보기": disp_df = st.session_state.df
else: disp_df = st.session_state.df[st.session_state.df['구분'] == selected_mode]

# 3. 조작 버튼
col_btn1, col_btn2 = st.columns([7, 3])
with col_btn2:
    cc1, cc2 = st.columns(2)
    refresh = cc1.button("🔄 가격 갱신")
    delete = cc2.button("🗑️ 선택 삭제")

# 4. 리스트 출력
st.markdown("<br>", unsafe_allow_html=True)
selected_indices = []

if disp_df.empty:
    st.info("등록된 상품이 없습니다.")
else:
    for idx, row in disp_df.iterrows():
        # 카드 한 줄 구성
        col_check, col_card = st.columns([0.05, 0.95])
        
        with col_check:
            st.write("") # 간격 맞춤
            if st.checkbox("", key=f"chk_{idx}"):
                selected_indices.append(idx)
        
        with col_card:
            diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
            status_class = "up" if diff > 0 else "down" if diff < 0 else "none"
            diff_text = f"▲{diff:,}" if diff > 0 else f"▼{abs(diff):,}" if diff < 0 else "변동없음"
            
            st.markdown(f"""
            <div class="product-card">
                <div class="info-box">
                    <span class="tag tag-type">{row['구분']}</span>
                    <span class="tag tag-cat">{row['카테고리']}</span>
                    <div class="product-name">{row['상품명']}</div>
                </div>
                <div class="price-container">
                    <div class="price-box">
                        <div class="price-label">가을판매가</div>
                        <div class="fall-price-badge">{int(row['가을판매가']):,}</div>
                    </div>
                    <div class="price-box">
                        <div class="price-label">컴퓨존(기준)</div>
                        <div class="normal-price">{int(row['컴퓨존판매가']):,}</div>
                    </div>
                    <div class="price-box">
                        <div class="price-label">실시간가</div>
                        <div class="normal-price">{int(row['실시간가']):,}</div>
                    </div>
                    <div class="price-box">
                        <div class="price-label">가격변동</div>
                        <div class="status-badge {status_class}">{diff_text}</div>
                    </div>
                    <div style="margin-left:10px;"><a href="{row['링크']}" target="_blank" style="text-decoration:none; font-size:20px;">🔗</a></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# 5. 로직 처리
if refresh:
    with st.spinner("최신 가격 확인 중..."):
        for i in disp_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()

if delete:
    if not selected_indices:
        st.warning("삭제할 항목을 먼저 체크해주세요!")
    else:
        st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
