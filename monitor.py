import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 1. 기본 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# 데이터 로드 (컬럼명 에러 방지 포함)
def load_data():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
            for c in cols:
                if c not in df.columns:
                    df[c] = 0 if "가" in c else "-"
            return df
        except:
            pass
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 실시간 가격 크롤링
def get_live_price(url):
    try:
        u = str(url).strip()
        if not u.startswith('http'): u = 'https://' + u
        res = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        p_tag = soup.select_one("#product_content_2_price")
        return int(''.join(filter(str.isdigit, p_tag.get_text()))) if p_tag else None
    except: return None

# --- 2. 상단 레이아웃 ---
st.title("🌸 가을 가전 통합 관리자")

# 신규 등록
with st.expander("➕ 신규 상품 등록"):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분 선택", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리 선택", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명 입력")
    r_link = st.text_input("컴퓨존 URL 입력")
    
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", value=0)
    r_cp = c5.number_input("컴퓨존기준가", value=0)
    r_memo = c6.text_input("비고(메모)")
    if c7.button("목록에 추가", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 검색 및 필터링
st.write("---")
f1, f2 = st.columns([7, 3])
search_q = f1.text_input("🔍 상품명 또는 메모 검색")
category_q = f2.selectbox("📂 카테고리 필터", CATEGORY_LIST)

# 탭 구성 및 데이터 필터링 (핵심 수정)
tab1, tab2, tab3 = st.tabs(["전체보기", "가격비교", "자주구매"])

# 기본 데이터 준비
filtered_df = st.session_state.df.copy()

# 카테고리/검색 필터 먼저 적용
if category_q != "전체보기":
    filtered_df = filtered_df[filtered_df['카테고리'] == category_q]
if search_q:
    filtered_df = filtered_df[filtered_df['상품명'].str.contains(search_q, case=False) | 
                               filtered_df['메모'].astype(str).str.contains(search_q, case=False)]

# 탭별 최종 데이터 분리
with tab1: display_df = filtered_df.copy(); current_tab = "전체보기"
with tab2: display_df = filtered_df[filtered_df['구분'] == "가격비교"]; current_tab = "가격비교"
with tab3: display_df = filtered_df[filtered_df['구분'] == "자주구매"]; current_tab = "자주구매"

# 상단 공통 버튼
btn_c1, btn_c2, btn_c3 = st.columns([7, 1.5, 1.5])
refresh_clicked = btn_c2.button("🔄 실시간 가격 갱신", use_container_width=True)
delete_clicked = btn_c3.button("🗑️ 선택 항목 삭제", use_container_width=True)

# --- 3. 리스트 출력 ---
selected_indices = []

if display_df.empty:
    st.info("해당하는 상품이 없습니다.")
else:
    for idx, row in display_df.iterrows():
        # 깔끔한 카드형 디자인 (안전한 스트림릿 순정 위젯 사용)
        with st.container(border=True):
            c_check, c_info, c_prices, c_btn = st.columns([0.05, 0.45, 0.4, 0.1])
            
            with c_check:
                if st.checkbox("", key=f"chk_{idx}"):
                    selected_indices.append(idx)
            
            with c_info:
                st.caption(f"ID: {idx} | {row['카테고리']}")
                st.markdown(f"**{row['상품명']}**")
                st.markdown(f"*{row['메모'] if str(row['메모']) != 'nan' else '비고 없음'}*")
            
            with c_prices:
                p1, p2, p3, p4 = st.columns(4)
                # 가격비교 탭이 아닐 때만 가을가 표시
                if current_tab != "가격비교":
                    p1.write("가을가"); p1.info(f"{int(row['가을판매가']):,}")
                
                p2.write("기준가"); p2.write(f"{int(row['컴퓨존판매가']):,}")
                p3.write("실시간"); p3.write(f"**{int(row['실시간가']):,}**")
                
                diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
                p4.write("변동액")
                if diff > 0: p4.error(f"▲{diff:,}")
                elif diff < 0: p4.info(f"▼{abs(diff):,}")
                else: p4.write("-")
                
            with c_btn:
                st.write("")
                st.link_button("열기", row['リンク'] if 'リンク' in row else row['링크'])

# --- 4. 하단 수정/삭제 로직 ---
if selected_indices:
    st.divider()
    edit_idx = selected_indices[0]
    target = st.session_state.df.loc[edit_idx]
    with st.form("edit_form"):
        st.subheader(f"🛠️ [{target['상품명']}] 수정")
        e1, e2, e3 = st.columns([1, 1, 2])
        new_f = e1.number_input("가을판매가", value=int(target['가을판매가']))
        new_c = e2.number_input("컴퓨존기준가", value=int(target['컴퓨존판매가']))
        new_m = e3.text_input("메모수정", value=str(target['메모']))
        if st.form_submit_button("변경내용 저장"):
            st.session_state.df.at[edit_idx, '가을판매가'] = new_f
            st.session_state.df.at[edit_idx, '컴퓨존판매가'] = new_c
            st.session_state.df.at[edit_idx, '메모'] = new_m
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

if delete_clicked and selected_indices:
    st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
    st.session_state.df.to_excel(DB_FILE, index=False)
    st.rerun()

if refresh_clicked:
    with st.spinner("가격을 업데이트하고 있습니다..."):
        for i in display_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
