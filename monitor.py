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

# --- 강화된 디자인 CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #F1F5F9; }
    
    .main-title { font-size: 26px; font-weight: 700; color: #0F172A; margin: 20px 0; border-left: 5px solid #2563EB; padding-left: 15px; }
    
    /* 카드 디자인: 상품명 영역 확보 */
    .product-card {
        background: white;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #E2E8F0;
        margin-bottom: 12px;
        display: flex;
        flex-direction: column; /* 세로 배열로 변경하여 공간 확보 */
        gap: 15px;
    }
    
    /* 상단 영역: 태그 + 상품명 */
    .top-info { display: flex; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
    .tag { font-size: 11px; padding: 4px 10px; border-radius: 20px; font-weight: 600; }
    .tag-type { background: #475569; color: white; }
    .tag-cat { background: #E0F2FE; color: #0369A1; }
    
    /* 상품명: 가려지지 않게 줄바꿈 허용 */
    .product-name { font-size: 16px; font-weight: 600; color: #1E293B; line-height: 1.5; flex: 1; min-width: 300px; }
    
    /* 하단 가격 영역: 가로 정렬 */
    .bottom-bar { 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        background: #F8FAFC; 
        padding: 12px 20px; 
        border-radius: 10px; 
        flex-wrap: wrap;
        gap: 15px;
    }
    
    .price-group { display: flex; gap: 25px; align-items: center; }
    .price-item { text-align: center; }
    .price-label { font-size: 11px; color: #64748B; margin-bottom: 4px; font-weight: 500; }
    
    /* 가을판매가 강조 (더 진하게) */
    .fall-badge {
        background: #2563EB;
        color: white;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 18px;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
    }
    
    .val { font-weight: 700; color: #334155; font-size: 15px; }
    .status-badge { font-size: 12px; font-weight: 700; padding: 5px 12px; border-radius: 6px; }
    .up { background: #FEE2E2; color: #B91C1C; }
    .down { background: #DBEAFE; color: #1D4ED8; }
    .none { background: #F1F5F9; color: #94A3B8; }

    /* 체크박스 스타일 */
    .stCheckbox { margin-top: 5px; }
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

if 'df' not in st.session_state: st.session_state.df = load_data()

st.markdown('<div class="main-title">🍁 가을 가전 통합 가격 매니저</div>', unsafe_allow_html=True)

# 1. 등록 (색상 포인트 추가)
with st.expander("📝 새로운 상품 등록하기", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST)
    r_name = c3.text_input("상품명")
    c4, c5, c6, c7 = st.columns([2, 1, 1, 1])
    r_link = c4.text_input("컴퓨존 URL")
    r_my = c5.number_input("가을판매가", min_value=0, step=1000)
    r_cp = c6.number_input("컴퓨존판매가(기준)", min_value=0, step=1000)
    r_memo = c7.text_input("비고(메모)")
    if st.button("💾 이 상품을 리스트에 저장", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 2. 탭 및 액션
tabs = st.tabs(["전체보기", "가격비교", "자주구매"])
selected_mode = "전체보기" if tabs[0] else "가격비교" if tabs[1] else "자주구매"
disp_df = st.session_state.df if selected_mode == "전체보기" else st.session_state.df[st.session_state.df['구분'] == selected_mode]

col_btn1, col_btn2 = st.columns([7, 3])
with col_btn2:
    cc1, cc2 = st.columns(2)
    refresh = cc1.button("🔄 가격 업데이트")
    delete = cc2.button("🗑️ 선택 삭제")

# 3. 리스트 출력
selected_indices = []
if disp_df.empty:
    st.info("현재 등록된 상품이 없습니다.")
else:
    for idx, row in disp_df.iterrows():
        c_chk, c_card = st.columns([0.04, 0.96])
        with c_chk:
            if st.checkbox("", key=f"c_{idx}"): selected_indices.append(idx)
        
        with c_card:
            diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
            st_class = "up" if diff > 0 else "down" if diff < 0 else "none"
            diff_txt = f"▲ {diff:,}" if diff > 0 else f"▼ {abs(diff):,}" if diff < 0 else "변동없음"
            
            st.markdown(f"""
            <div class="product-card">
                <div class="top-info">
                    <span class="tag tag-type">{row['구분']}</span>
                    <span class="tag tag-cat">{row['카테고리']}</span>
                    <div class="product-name">{row['상품명']}</div>
                    <div style="font-size:13px; color:#94A3B8;">{row['메모']}</div>
                </div>
                <div class="bottom-bar">
                    <div class="price-group">
                        <div class="price-item">
                            <div class="price-label">가을판매가</div>
                            <div class="fall-badge">{int(row['가을판매가']):,}원</div>
                        </div>
                        <div class="price-item">
                            <div class="price-label">컴퓨존(기준)</div>
                            <div class="val">{int(row['컴퓨존판매가']):,}원</div>
                        </div>
                        <div class="price-item">
                            <div class="price-label">실시간 컴퓨존가</div>
                            <div class="val">{int(row['실시간가']):,}원</div>
                        </div>
                        <div class="price-item">
                            <div class="price-label">변동액</div>
                            <div class="status-badge {st_class}">{diff_txt}</div>
                        </div>
                    </div>
                    <a href="{row['링크']}" target="_blank" style="text-decoration:none; font-size:24px;">🔗</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# 4. 기능 로직
if refresh:
    with st.spinner("최신 가격 수집 중..."):
        for i in disp_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()

if delete:
    if not selected_indices: st.warning("삭제할 상품을 선택하세요!")
    else:
        st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
