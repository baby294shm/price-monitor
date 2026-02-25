import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 1. 기본 설정 및 데이터 로드 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- CSS (숫자 크기 및 디자인 미세 조정) ---
st.markdown("""
    <style>
    .product-card {
        background-color: white; padding: 12px 15px; border-radius: 10px;
        border: 1px solid #E5E7EB; margin-bottom: 8px;
        display: flex; align-items: center; justify-content: space-between;
    }
    .price-unit { text-align: center; width: 85px; }
    .price-label { font-size: 11px; color: #6B7280; margin-bottom: 2px; }
    .price-value { font-size: 14px; font-weight: 700; color: #1F2937; }
    .fall-price { color: white; background: #2563EB; padding: 3px 8px; border-radius: 5px; }
    .diff-up { color: #EF4444; font-size: 12px; font-weight: bold; }
    .diff-down { color: #3B82F6; font-size: 12px; font-weight: bold; }
    .diff-same { color: #9CA3AF; font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()

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

# 상품 등록 (생략 가능하지만 사장님 편의를 위해 유지)
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

# 검색 및 필터
f1, f2 = st.columns([7, 3])
search_q = f1.text_input("🔍 상품명 또는 메모 검색")
category_q = f2.selectbox("📂 카테고리 필터", CATEGORY_LIST)

# 탭 필터링 (가장 중요한 부분)
tab_names = ["전체보기", "가격비교", "자주구매"]
tabs = st.tabs(tab_names)

# 데이터 필터링 로직
display_df = st.session_state.df.copy()

# 탭 선택 상태 감지 및 필터링
selected_tab = "전체보기"
for i, tab in enumerate(tabs):
    with tab:
        if i == 1: display_df = display_df[display_df['구분'] == "가격비교"]; selected_tab = "가격비교"
        elif i == 2: display_df = display_df[display_df['구분'] == "자주구매"]; selected_tab = "자주구매"

if category_q != "전체보기": display_df = display_df[display_df['카테고리'] == category_q]
if search_q: display_df = display_df[display_df['상품명'].str.contains(search_q, case=False) | display_df['메모'].astype(str).str.contains(search_q, case=False)]

# 상단 버튼
btn_c1, btn_c2, btn_c3 = st.columns([7, 1.5, 1.5])
refresh_clicked = btn_c2.button("🔄 가격 업데이트", use_container_width=True)
delete_clicked = btn_c3.button("🗑️ 선택 삭제", use_container_width=True)

# --- 3. 리스트 출력 (가독성 최적화) ---
selected_indices = []

for idx, row in display_df.iterrows():
    diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
    diff_style = "diff-up" if diff > 0 else "diff-down" if diff < 0 else "diff-same"
    diff_text = f"▲{diff:,}" if diff > 0 else f"▼{abs(diff):,}" if diff < 0 else "-"

    col_chk, col_body = st.columns([0.04, 0.96])
    with col_chk:
        if st.checkbox("", key=f"c_{idx}"): selected_indices.append(idx)
    
    with col_body:
        # 가격비교 탭일 때는 가을가 제외
        fall_html = f'<div class="price-unit"><div class="price-label">가을가</div><div class="price-value"><span class="fall-price">{int(row["가을판매가"]):,}</span></div></div>' if selected_tab != "가격비교" else ""
        
        st.markdown(f"""
            <div class="product-card">
                <div style="flex:1;">
                    <div style="font-size:11px; color:#3B82F6; font-weight:700;">{row['카테고리']}</div>
                    <div style="font-size:14px; font-weight:600; color:#374151;">{row['상품명']}</div>
                    <div style="font-size:12px; color:#9CA3AF;">📝 {row['메모'] if str(row['메모']) != 'nan' else '비고 없음'}</div>
                </div>
                <div style="display:flex; gap:15px; align-items:center;">
                    {fall_html}
                    <div class="price-unit"><div class="price-label">기준가</div><div class="price-value" style="color:#6B7280;">{int(row['컴퓨존판매가']):,}</div></div>
                    <div class="price-unit"><div class="price-label">실시간</div><div class="price-value">{int(row['실시간가']):,}</div></div>
                    <div class="price-unit"><div class="price-label">변동액</div><div class="{diff_style}">{diff_text}</div></div>
                    <div style="margin-left:10px;"><a href="{row['링크']}" target="_blank" style="text-decoration:none; background:#10B981; color:white; padding:6px 12px; border-radius:6px; font-size:12px; font-weight:bold;">열기</a></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# --- 4. 정보 수정 (체크 시 하단 노출) ---
if selected_indices:
    st.divider()
    edit_idx = selected_indices[0]
    target = st.session_state.df.loc[edit_idx]
    with st.form("quick_edit"):
        st.subheader(f"🛠️ {target['상품명']} 수정")
        e1, e2, e3 = st.columns([1, 1, 2])
        new_f = e1.number_input("가을판매가", value=int(target['가을판매가']))
        new_c = e2.number_input("컴퓨존기준가", value=int(target['컴퓨존판매가']))
        new_m = e3.text_input("메모수정", value=str(target['메모']))
        if st.form_submit_button("💾 저장하기"):
            st.session_state.df.at[edit_idx, '가을판매가'] = new_f
            st.session_state.df.at[edit_idx, '컴퓨존판매가'] = new_c
            st.session_state.df.at[edit_idx, '메모'] = new_m
            st.session_state.df.to_excel(DB_FILE, index=False); st.success("저장되었습니다!"); st.rerun()

# 삭제 및 갱신 로직
if delete_clicked and selected_indices:
    st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
    st.session_state.df.to_excel(DB_FILE, index=False); st.rerun()

if refresh_clicked:
    with st.spinner("가격 갱신 중..."):
        for i in display_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False); st.rerun()
