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
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None # 수정 중인 인덱스 저장

# --- 2. 상단 등록/수정창 (사장님 요청사항) ---
st.title("🍁 가을 가전 통합 관리자")

# 수정 모드인지 등록 모드인지 판단
is_edit = st.session_state.edit_idx is not None
title = "📝 상품 정보 수정" if is_edit else "➕ 신규 상품 등록"
btn_label = "💾 수정 내용 저장" if is_edit else "목록에 추가"

with st.expander(title, expanded=is_edit):
    # 수정 모드라면 기존 데이터를 불러옴
    if is_edit:
        row = st.session_state.df.loc[st.session_state.edit_idx]
        v_type = row['구분']
        v_cat = row['카테고리']
        v_name = row['상품명']
        v_link = row['링크']
        v_my = int(row['가을판매가'])
        v_cp = int(row['컴퓨존판매가'])
        v_memo = str(row['메모'])
    else:
        v_type, v_cat, v_name, v_link, v_my, v_cp, v_memo = "가격비교", CATEGORY_LIST[1], "", "", 0, 0, ""

    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"], index=0 if v_type=="가격비교" else 1)
    r_cat = c2.selectbox("카테고리 등록", CATEGORY_LIST[1:], index=CATEGORY_LIST[1:].index(v_cat) if v_cat in CATEGORY_LIST else 0)
    r_name = c3.text_input("상품명", value=v_name)
    r_link = st.text_input("컴퓨존 URL", value=v_link)
    
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", value=v_my, step=1000)
    r_cp = c5.number_input("컴퓨존판매가", value=v_cp, step=1000)
    r_memo = c6.text_input("메모(비고)", value=v_memo)
    
    with c7:
        st.write("") # 간격 맞춤
        if st.button(btn_label, use_container_width=True, type="primary"):
            if is_edit:
                # 수정 로직
                idx = st.session_state.edit_idx
                st.session_state.df.at[idx, '구분'] = r_type
                st.session_state.df.at[idx, '카테고리'] = r_cat
                st.session_state.df.at[idx, '상품명'] = r_name
                st.session_state.df.at[idx, '링크'] = r_link
                st.session_state.df.at[idx, '가을판매가'] = r_my
                st.session_state.df.at[idx, '컴퓨존판매가'] = r_cp
                st.session_state.df.at[idx, '메모'] = r_memo
                st.session_state.edit_idx = None # 수정 완료 후 초기화
                st.success("수정 완료!")
            else:
                # 등록 로직
                new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                st.success("추가 완료!")
            
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()
            
    if is_edit:
        if st.button("❌ 수정 취소", use_container_width=True):
            st.session_state.edit_idx = None
            st.rerun()

# --- 3. 리스트 영역 ---
st.write("---")
f1, f2 = st.columns([7, 3])
search_q = f1.text_input("🔍 상품명 또는 메모 검색")
cat_q = f2.selectbox("📂 카테고리 필터", CATEGORY_LIST)

tabs = st.tabs(["전체보기", "가격비교", "자주구매"])

def show_data(target_df, tab_key):
    if target_df.empty:
        st.info("상품이 없습니다.")
        return

    # 공통 액션 버튼
    ac1, ac2, ac3 = st.columns([7, 1.5, 1.5])
    if ac2.button("🔄 가격 업데이트", key=f"up_{tab_key}", use_container_width=True):
        # 크롤링 로직 (생략 - 기존과 동일)
        st.rerun()
    
    selected_indices = []
    for idx, row in target_df.iterrows():
        with st.container(border=True):
            c_chk, c_info, c_price, c_btn = st.columns([0.05, 0.45, 0.4, 0.1])
            with c_chk:
                # 체크박스 클릭 시 세션 스테이트에 수정 인덱스 저장
                if st.checkbox("", key=f"chk_{tab_key}_{idx}"):
                    st.session_state.edit_idx = idx
                    st.rerun()
            with c_info:
                st.caption(f"[{row['카테고리']}]")
                st.markdown(f"**{row['상품명']}**")
                st.markdown(f"<small style='color:gray;'>📝 {row['메모']}</small>", unsafe_allow_html=True)
            with c_price:
                p1, p2, p3, p4 = st.columns(4)
                if tab_key != "가격비교": p1.metric("가을가", f"{int(row['가을판매가']):,}")
                p2.metric("기준가", f"{int(row['컴퓨존판매가']):,}")
                p3.metric("실시간", f"{int(row['실시간가']):,}")
                diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
                p4.metric("변동액", f"{diff:,}", delta=diff, delta_color="inverse")
            with c_btn:
                st.write("")
                st.link_button("열기", row['링크'])

# 필터링 적용
filtered = st.session_state.df.copy()
if cat_q != "전체보기": filtered = filtered[filtered['카테고리'] == cat_q]
if search_q: filtered = filtered[filtered['상품명'].str.contains(search_q, case=False)]

with tabs[0]: show_data(filtered, "전체보기")
with tabs[1]: show_data(filtered[filtered['구분'] == "가격비교"], "가격비교")
with tabs[2]: show_data(filtered[filtered['구분'] == "자주구매"], "자주구매")
