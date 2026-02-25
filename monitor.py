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

if 'df' not in st.session_state:
    st.session_state.df = load_data()

def get_live_price(url):
    try:
        u = str(url).strip()
        if not u.startswith('http'): u = 'https://' + u
        res = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        p_tag = soup.select_one("#product_content_2_price")
        return int(''.join(filter(str.isdigit, p_tag.get_text()))) if p_tag else None
    except: return None

# --- 2. 메인 화면 ---
st.title("🍁 가을 가전 통합 관리자")

# 신규 등록
with st.expander("➕ 신규 상품 등록"):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리 등록", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL")
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", value=0)
    r_cp = c5.number_input("컴퓨존기준가", value=0)
    r_memo = c6.text_input("메모(비고)")
    if c7.button("목록에 추가", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False); st.rerun()

# 검색 및 필터링
f1, f2 = st.columns([7, 3])
search_q = f1.text_input("🔍 상품명 또는 메모 검색")
cat_q = f2.selectbox("📂 카테고리 필터", CATEGORY_LIST)

# 탭 설정
tab1, tab2, tab3 = st.tabs(["전체보기", "가격비교", "자주구매"])

# 데이터 필터링 (탭별로 정확하게 분리)
filtered_df = st.session_state.df.copy()
if cat_q != "전체보기": filtered_df = filtered_df[filtered_df['카테고리'] == cat_q]
if search_q: filtered_df = filtered_df[filtered_df['상품명'].str.contains(search_q, case=False) | filtered_df['메모'].astype(str).str.contains(search_q, case=False)]

# 출력 함수 (가독성 & 수정기능 포함)
def show_list(target_df, current_tab_name):
    if target_df.empty:
        st.info("표시할 상품이 없습니다.")
        return
    
    selected_indices = []
    
    # 상단 공통 버튼
    btn_c1, btn_c2, btn_c3 = st.columns([7, 1.5, 1.5])
    refresh_clicked = btn_c2.button("🔄 가격 업데이트", key=f"re_{current_tab_name}", use_container_width=True)
    delete_clicked = btn_c3.button("🗑️ 선택 삭제", key=f"del_{current_tab_name}", use_container_width=True)

    for idx, row in target_df.iterrows():
        with st.container(border=True):
            col_chk, col_info, col_price, col_link = st.columns([0.05, 0.45, 0.4, 0.1])
            with col_chk:
                if st.checkbox("", key=f"sel_{current_tab_name}_{idx}"): selected_indices.append(idx)
            with col_info:
                st.caption(f"[{row['카테고리']}]")
                st.markdown(f"**{row['상품명']}**")
                st.markdown(f"<small style='color:gray;'>📝 {row['메모'] if str(row['메모']) != 'nan' else '메모 없음'}</small>", unsafe_allow_html=True)
            with col_price:
                p1, p2, p3, p4 = st.columns(4)
                # 가격비교 탭에서는 가을가 제외
                if current_tab_name != "가격비교":
                    p1.metric("가을가", f"{int(row['가을판매가']):,}")
                p2.metric("기준가", f"{int(row['컴퓨존판매가']):,}")
                p3.metric("실시간", f"{int(row['실시간가']):,}")
                diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
                p4.metric("변동액", f"{diff:,}", delta=diff, delta_color="inverse")
            with col_link:
                st.write("")
                st.link_button("열기", row['링크'])

    # --- 3. 수정 기능 (체크 시 하단에 폼 노출) ---
    if selected_indices:
        st.divider()
        edit_idx = selected_indices[0] # 첫 번째 선택 항목 수정
        t = st.session_state.df.loc[edit_idx]
        with st.form(f"edit_form_{current_tab_name}"):
            st.subheader(f"🛠️ {t['상품명']} 수정")
            ec1, ec2, ec3 = st.columns([1, 1, 2])
            new_f = ec1.number_input("가을판매가 수정", value=int(t['가을판매가']))
            new_c = ec2.number_input("기준가 수정", value=int(t['컴퓨존판매가']))
            new_m = ec3.text_input("메모 수정", value=str(t['메모']))
            if st.form_submit_button("💾 수정 내용 저장"):
                st.session_state.df.at[edit_idx, '가을판매가'] = new_f
                st.session_state.df.at[edit_idx, '컴퓨존판매가'] = new_c
                st.session_state.df.at[edit_idx, '메모'] = new_m
                st.session_state.df.to_excel(DB_FILE, index=False)
                st.success("수정되었습니다!"); st.rerun()

    # 삭제 및 업데이트 로직
    if delete_clicked and selected_indices:
        st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
        st.session_state.df.to_excel(DB_FILE, index=False); st.rerun()
    if refresh_clicked:
        with st.spinner("가격 갱신 중..."):
            for i in target_df.index:
                p = get_live_price(st.session_state.df.at[i, '링크'])
                if p: st.session_state.df.at[i, '실시간가'] = p
            st.session_state.df.to_excel(DB_FILE, index=False); st.rerun()

# 탭별 출력 적용
with tab1: show_list(filtered_df, "전체보기")
with tab2: show_list(filtered_df[filtered_df['구분'] == "가격비교"], "가격비교")
with tab3: show_list(filtered_df[filtered_df['구분'] == "자주구매"], "자주구매")
