import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 1. 기본 설정 및 데이터 로드 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        # 필수 컬럼 확인 및 생성 (에러 방지)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns:
                df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 실시간 가격 크롤링 함수 ---
def get_live_price(url):
    try:
        u = str(url).strip()
        if not u.startswith('http'): u = 'https://' + u
        res = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        p_tag = soup.select_one("#product_content_2_price")
        if p_tag:
            return int(''.join(filter(str.isdigit, p_tag.get_text())))
    except:
        return None
    return None

# --- 3. 메인 화면 레이아웃 ---
st.title("🍁 가을 가전 통합 관리자")

# 상품 등록 창
with st.expander("➕ 신규 상품 등록", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리 등록", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL (주소를 그대로 복사해서 넣으세요)")
    
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", value=0, step=1000)
    r_cp = c5.number_input("컴퓨존판매가", value=0, step=1000)
    r_memo = c6.text_input("메모(비고)")
    if c7.button("목록에 추가", use_container_width=True):
        if r_name and r_link:
            new_row = {
                "구분": r_type, "카테고리": r_cat, "상품명": r_name, 
                "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, 
                "메모": r_memo, "링크": r_link.strip()
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 필터링 섹션
st.write("")
f1, f2 = st.columns([7, 3])
with f1: search_q = st.text_input("🔍 상품명 또는 메모 검색", placeholder="검색어를 입력하세요...")
with f2: category_q = st.selectbox("📂 카테고리 필터", CATEGORY_LIST)

tabs = st.tabs(["전체보기", "가격비교", "자주구매"])
selected_tab = "전체보기" if tabs[0] else "가격비교" if tabs[1] else "자주구매"

# 데이터 필터링 로직
display_df = st.session_state.df.copy()
if selected_tab != "전체보기":
    display_df = display_df[display_df['구분'] == selected_tab]
if category_q != "전체보기":
    display_df = display_df[display_df['카테고리'] == category_q]
if search_q:
    display_df = display_df[display_df['상품명'].str.contains(search_q, case=False) | 
                            display_df['메모'].astype(str).str.contains(search_q, case=False)]

# 상단 버튼들
st.write("")
btn_c1, btn_c2, btn_c3 = st.columns([7, 1.5, 1.5])
refresh_clicked = btn_c2.button("🔄 가격 업데이트", use_container_width=True)
delete_clicked = btn_c3.button("🗑️ 선택 삭제", use_container_width=True)

# --- 4. 상품 리스트 출력 (안전한 카드 방식) ---
selected_indices = []

for idx, row in display_df.iterrows():
    # 테두리가 있는 카드 박스 형태
    with st.container(border=True):
        col_chk, col_info, col_price, col_link = st.columns([0.05, 0.45, 0.4, 0.1])
        
        with col_chk:
            if st.checkbox("", key=f"check_{idx}"):
                selected_indices.append(idx)
        
        with col_info:
            st.caption(f"[{row['카테고리']}]")
            st.markdown(f"**{row['상품명']}**")
            st.markdown(f"<small style='color:gray;'>📝 {row['메모']}</small>", unsafe_allow_html=True)
            
        with col_price:
            p1, p2, p3, p4 = st.columns(4)
            # 가격비교 탭일 때는 가을판매가 제외
            if selected_tab != "가격비교":
                p1.metric("가을가", f"{int(row['가을판매가']):,}")
            
            p2.metric("기준가", f"{int(row['컴퓨존판매가']):,}")
            p3.metric("실시간", f"{int(row['실시간가']):,}")
            
            diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
            p4.metric("변동액", f"{diff:,}", delta=diff, delta_color="inverse")
            
        with col_link:
            st.write("") # 정렬용
            st.link_button("열기", row['링크'], type="primary")

# --- 5. 가격/메모 수정 기능 (체크박스 선택 시 활성화) ---
if selected_indices:
    st.divider()
    st.subheader("🛠️ 선택한 상품 정보 수정")
    edit_idx = selected_indices[0] # 첫 번째 선택 항목 수정
    target = st.session_state.df.loc[edit_idx]
    
    with st.form("edit_panel"):
        st.write(f"수정 중: **{target['상품명']}**")
        ec1, ec2, ec3 = st.columns([1, 1, 2])
        new_fall = ec1.number_input("가을판매가 수정", value=int(target['가을판매가']), step=1000)
        new_comp = ec2.number_input("컴퓨존기준가 수정", value=int(target['컴퓨존판매가']), step=1000)
        new_memo = ec3.text_input("메모(비고) 수정", value=str(target['메모']))
        
        if st.form_submit_button("💾 정보 저장하기"):
            st.session_state.df.at[edit_idx, '가을판매가'] = new_fall
            st.session_state.df.at[edit_idx, '컴퓨존판매가'] = new_comp
            st.session_state.df.at[edit_idx, '메모'] = new_memo
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.success("정보가 업데이트되었습니다!")
            st.rerun()

# --- 6. 삭제 및 갱신 로직 ---
if delete_clicked and selected_indices:
    st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
    st.session_state.df.to_excel(DB_FILE, index=False)
    st.rerun()

if refresh_clicked:
    with st.spinner("최신 가격 데이터를 가져오는 중입니다..."):
        for i in display_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p:
                st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
