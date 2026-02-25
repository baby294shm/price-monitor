import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 1. 설정 및 데이터 로드 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        # 필수 컬럼 강제 생성
        for c in ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# --- 2. 메인 화면 구성 ---
st.title("🍁 가을 가전 통합 관리자")

# 상품 등록 (필요할 때만 열어서 사용)
with st.expander("➕ 신규 상품 등록"):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL")
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", value=0)
    r_cp = c5.number_input("기준가", value=0)
    r_memo = c6.text_input("메모")
    if c7.button("추가하기", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False); st.rerun()

# 3. 검색 및 필터링 (탭 기능과 연동)
st.write("---")
f1, f2 = st.columns([7, 3])
search_q = f1.text_input("🔍 상품명 또는 메모 검색", key="search_bar")
cat_q = f2.selectbox("📂 카테고리 필터", CATEGORY_LIST)

# [핵심] 탭을 변수에 할당하여 현재 어떤 탭이 선택되었는지 확실히 체크
tab1, tab2, tab3 = st.tabs(["전체보기", "가격비교", "자주구매"])

# 데이터 필터링 로직 (탭 선택에 따라 변수 분리)
df = st.session_state.df.copy()

# 검색/카테고리 필터 우선 적용
if cat_q != "전체보기": df = df[df['카테고리'] == cat_q]
if search_q: df = df[df['상품명'].str.contains(search_q, case=False) | df['메모'].astype(str).str.contains(search_q, case=False)]

# 탭별 데이터 최종 출력
def display_list(target_df, current_tab):
    if target_df.empty:
        st.info("표시할 상품이 없습니다.")
        return
    
    selected_indices = []
    
    # 리스트 상단 버튼
    act_c1, act_c2, act_c3 = st.columns([7, 1.5, 1.5])
    refresh_btn = act_c2.button("🔄 가격 업데이트", key=f"re_{current_tab}", use_container_width=True)
    delete_btn = act_c3.button("🗑️ 선택 삭제", key=f"del_{current_tab}", use_container_width=True)

    for idx, row in target_df.iterrows():
        with st.container(border=True):
            c_chk, c_info, c_price, c_link = st.columns([0.05, 0.45, 0.4, 0.1])
            with c_chk:
                if st.checkbox("", key=f"sel_{current_tab}_{idx}"): selected_indices.append(idx)
            with c_info:
                st.caption(f"[{row['카테고리']}]")
                st.markdown(f"**{row['상품명']}**")
                st.markdown(f"<small style='color:gray;'>📝 {row['메모']}</small>", unsafe_allow_html=True)
            with c_price:
                p1, p2, p3, p4 = st.columns(4)
                # '가격비교' 탭에서는 가을판매가 숨김
                if current_tab != "가격비교":
                    p1.metric("가을가", f"{int(row['가을판매가']):,}")
                p2.metric("기준가", f"{int(row['컴퓨존판매가']):,}")
                p3.metric("실시간", f"{int(row['실시간가']):,}")
                diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
                p4.metric("변동액", f"{diff:,}", delta=diff, delta_color="inverse")
            with c_link:
                st.write("")
                st.link_button("열기", row['링크'])
    
    # 삭제/갱신 로직 처리
    if delete_btn and selected_indices:
        st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
        st.session_state.df.to_excel(DB_FILE, index=False); st.rerun()

    # 수정 기능 (체크박스 선택 시)
    if selected_indices:
        st.divider()
        e_idx = selected_indices[0]
        t = st.session_state.df.loc[e_idx]
        with st.form(f"edit_{current_tab}"):
            st.write(f"🛠️ **{t['상품명']}** 정보 수정")
            ec1, ec2, ec3 = st.columns([1, 1, 2])
            nf = ec1.number_input("가을판매가", value=int(t['가을판매가']))
            nc = ec2.number_input("기준가", value=int(t['컴퓨존판매가']))
            nm = ec3.text_input("메모", value=str(t['메모']))
            if st.form_submit_button("저장하기"):
                st.session_state.df.at[e_idx, '가을판매가'] = nf
                st.session_state.df.at[e_idx, '컴퓨존판매가'] = nc
                st.session_state.df.at[e_idx, '메모'] = nm
                st.session_state.df.to_excel(DB_FILE, index=False); st.rerun()

# 각 탭에 필터링된 데이터 뿌려주기
with tab1:
    display_list(df, "전체보기")
with tab2:
    display_list(df[df['구분'] == "가격비교"], "가격비교")
with tab3:
    display_list(df[df['구분'] == "자주구매"], "자주구매")
