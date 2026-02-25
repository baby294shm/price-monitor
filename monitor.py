import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 1. 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# 데이터 로드
def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()

# --- 2. 상단 헤더 ---
st.title("🌸 가을 가전 통합 관리자")

# 검색 및 카테고리 (가독성을 위해 필터 위치 조정)
f1, f2 = st.columns([7, 3])
search_q = f1.text_input("🔍 상품명 또는 메모 검색", placeholder="검색어를 입력하세요")
cat_q = f2.selectbox("📂 카테고리 필터", CATEGORY_LIST)

# 탭 설정
tab1, tab2, tab3 = st.tabs(["전체보기", "가격비교", "자주구매"])

# 데이터 필터링
df = st.session_state.df.copy()
if cat_q != "전체보기": df = df[df['카테고리'] == cat_q]
if search_q: df = df[df['상품명'].str.contains(search_q, case=False) | df['메모'].astype(str).str.contains(search_q, case=False)]

# --- 3. 리스트 출력 함수 ---
def render_list(target_df, tab_key):
    if target_df.empty:
        st.info("해당하는 상품이 없습니다.")
        return

    # 공통 버튼
    c1, c2, c3 = st.columns([7, 1.5, 1.5])
    refresh = c2.button("🔄 가격 업데이트", key=f"btn_ref_{tab_key}", use_container_width=True)
    delete = c3.button("🗑️ 선택 삭제", key=f"btn_del_{tab_key}", use_container_width=True)

    selected_idx = []
    
    for idx, row in target_df.iterrows():
        # 
        with st.container(border=True):
            col_chk, col_txt, col_pri, col_btn = st.columns([0.05, 0.45, 0.4, 0.1])
            
            with col_chk:
                if st.checkbox("", key=f"chk_{tab_key}_{idx}"):
                    selected_idx.append(idx)
            
            with col_txt:
                st.markdown(f"<span style='font-size:12px; color:blue; font-weight:bold;'>[{row['카테고리']}]</span>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:14px; font-weight:bold;'>{row['상품명']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:12px; color:gray;'>📝 {row['메모']}</div>", unsafe_allow_html=True)
                
            with col_pri:
                p1, p2, p3, p4 = st.columns(4)
                # '가격비교' 탭에서는 가을가 숨김
                if tab_key != "가격비교":
                    p1.caption("가을가")
                    p1.markdown(f"**{int(row['가을판매가']):,}**")
                
                p2.caption("기준가")
                p2.write(f"{int(row['컴퓨존판매가']):,}")
                
                p3.caption("실시간")
                p3.markdown(f"**{int(row['실시간가']):,}**")
                
                diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
                p4.caption("변동액")
                if diff > 0: p4.markdown(f"<span style='color:red;'>▲{diff:,}</span>", unsafe_allow_html=True)
                elif diff < 0: p4.markdown(f"<span style='color:blue;'>▼{abs(diff):,}</span>", unsafe_allow_html=True)
                else: p4.write("-")

            with col_btn:
                st.write("")
                st.link_button("열기", row['링크'])

    # --- 여기가 수정 칸! ---
    if selected_idx:
        st.write("---")
        st.subheader("🛠️ 선택 상품 정보 수정")
        target_idx = selected_idx[0]
        t_row = st.session_state.df.loc[target_idx]
        
        with st.form(f"edit_form_{tab_key}"):
            st.info(f"수정 중: {t_row['상품명']}")
            ec1, ec2, ec3 = st.columns([1, 1, 2])
            new_fall = ec1.number_input("가을판매가", value=int(t_row['가을판매가']))
            new_comp = ec2.number_input("기준가", value=int(t_row['컴퓨존판매가']))
            new_memo = ec3.text_input("메모", value=str(t_row['메모']))
            
            if st.form_submit_button("💾 수정 내용 저장"):
                st.session_state.df.at[target_idx, '가을판매가'] = new_fall
                st.session_state.df.at[target_idx, '컴퓨존판매가'] = new_comp
                st.session_state.df.at[target_idx, '메모'] = new_memo
                st.session_state.df.to_excel(DB_FILE, index=False)
                st.success("수정 완료!")
                st.rerun()

    # 삭제 로직
    if delete and selected_idx:
        st.session_state.df = st.session_state.df.drop(selected_idx).reset_index(drop=True)
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()

# 탭별 데이터 뿌리기
with tab1: render_list(df, "전체보기")
with tab2: render_list(df[df['구분'] == "가격비교"], "가격비교")
with tab3: render_list(df[df['구분'] == "자주구매"], "자주구매")
