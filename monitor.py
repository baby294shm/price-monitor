import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 파일 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- 에러 방지용 안전한 스타일링 ---
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .product-card {
        background-color: white; padding: 15px; border-radius: 10px;
        border: 1px solid #E9ECEF; margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .badge-blue { background-color: #0D6EFD; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-gray { background-color: #F1F3F5; color: #495057; padding: 4px 10px; border-radius: 5px; font-size: 13px; }
    .diff-up { color: #DC3545; font-weight: bold; }
    .diff-down { color: #0D6EFD; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 기능 함수 ---
def get_live_price(url):
    try:
        u = str(url).strip()
        if not u.startswith('http'): u = 'https://' + u
        res = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        p_tag = soup.select_one("#product_content_2_price")
        return int(''.join(filter(str.isdigit, p_tag.get_text()))) if p_tag else None
    except: return None

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_excel(DB_FILE)
        cols = ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]
        for c in cols:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()

# --- 메인 화면 ---
st.title("🍁 가을 가전 통합 관리자")

# 1. 신규 등록
with st.expander("➕ 신규 상품 등록"):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리 등록", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL")
    
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", step=1000)
    r_cp = c5.number_input("컴퓨존기준가", step=1000)
    r_memo = c6.text_input("메모(비고)")
    if c7.button("목록에 추가", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 2. 필터 및 검색
st.write("---")
f1, f2 = st.columns([7, 3])
with f1: search_q = st.text_input("🔍 상품명 또는 메모 검색", placeholder="무엇을 찾으시나요?")
with f2: category_q = st.selectbox("📂 카테고리 필터", CATEGORY_LIST)

tabs = st.tabs(["전체보기", "가격비교", "자주구매"])
sel_tab = "전체보기" if tabs[0] else "가격비교" if tabs[1] else "자주구매"

# 데이터 필터링
disp_df = st.session_state.df.copy()
if sel_tab != "전체보기": disp_df = disp_df[disp_df['구분'] == sel_tab]
if category_q != "전체보기": disp_df = disp_df[disp_df['카테고리'] == category_q]
if search_q: 
    disp_df = disp_df[disp_df['상품명'].str.contains(search_q, case=False) | disp_df['메모'].astype(str).str.contains(search_q, case=False)]

# 3. 액션 버튼
act_c1, act_c2, act_c3 = st.columns([7, 1.5, 1.5])
with act_c2: refresh_btn = st.button("🔄 가격 업데이트", use_container_width=True)
with act_c3: delete_btn = st.button("🗑️ 선택 삭제", use_container_width=True)

# 4. 리스트 출력 (가장 안전한 방식)
selected_indices = []
for idx, row in disp_df.iterrows():
    # 체크박스 + 내용
    col_check, col_content = st.columns([0.05, 0.95])
    with col_check:
        if st.checkbox("", key=f"sel_{idx}"): selected_indices.append(idx)
    
    with col_content:
        # 가격 정보 계산
        diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
        diff_str = f"▲{diff:,}" if diff > 0 else f"▼{abs(diff):,}" if diff < 0 else "-"
        diff_color = "diff-up" if diff > 0 else "diff-down" if diff < 0 else ""

        # 실제 카드 내용 구성
        # 탭이 '가격비교'일 때는 가을판매가 칸을 비웁니다.
        fall_price_display = f'<span class="badge-blue">{int(row["가을판매가"]):,}</span>' if sel_tab != "가격비교" else ""
        
        st.markdown(f"""
            <div class="product-card">
                <div style="flex:1;">
                    <div style="font-size:12px; color:gray;">[{row['카테고리']}]</div>
                    <div style="font-weight:bold; font-size:15px;">{row['상품명']}</div>
                    <div style="font-size:13px; color:#666;">📝 {row['메모'] if str(row['메모']) != 'nan' else '비고 없음'}</div>
                </div>
                <div style="display:flex; gap:20px; align-items:center; text-align:center;">
                    <div style="width:100px;"><span style="font-size:10px; color:gray;">가을판매가</span><br>{fall_price_display}</div>
                    <div style="width:90px;"><span style="font-size:10px; color:gray;">컴퓨존기준</span><br>{int(row['컴퓨존판매가']):,}</div>
                    <div style="width:90px;"><span style="font-size:10px; color:gray;">실시간가</span><br><b>{int(row['실시간가']):,}</b></div>
                    <div style="width:80px;"><span style="font-size:10px; color:gray;">변동액</span><br><span class="{diff_color}">{diff_str}</span></div>
                    <div style="width:60px;"><a href="{row['リンク']}" target="_blank" style="text-decoration:none; color:white; background:#198754; padding:5px 10px; border-radius:5px; font-size:12px;">열기</a></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# 5. 하단 가격 수정 기능 (체크 시 활성화)
if selected_indices:
    st.write("---")
    st.subheader("🛠️ 가격 및 메모 빠르게 수정")
    e_idx = selected_indices[0]
    target = st.session_state.df.loc[e_idx]
    
    with st.container():
        ec1, ec2, ec3, ec4 = st.columns([1, 1, 2, 1])
        new_f = ec1.number_input("가을판매가", value=int(target['가을판매가']), step=1000)
        new_c = ec2.number_input("컴퓨존기준가", value=int(target['컴퓨존판매가']), step=1000)
        new_m = ec3.text_input("메모수정", value=str(target['메모']))
        if ec4.button("💾 저장하기", use_container_width=True):
            st.session_state.df.at[e_idx, '가을판매가'] = new_f
            st.session_state.df.at[e_idx, '컴퓨존판매가'] = new_c
            st.session_state.df.at[e_idx, '메모'] = new_m
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.success("수정 완료!")
            st.rerun()

# 6. 삭제/갱신 로직
if delete_btn and selected_indices:
    st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
    st.session_state.df.to_excel(DB_FILE, index=False)
    st.rerun()

if refresh_btn:
    with st.spinner("가격을 가져오고 있습니다..."):
        for i in disp_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
