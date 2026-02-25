import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 기본 설정 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- CSS (이미지 디자인 복구 및 코드 노출 방지) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #F8F9FA; }
    
    /* 카드 디자인 */
    .product-row {
        background: white; padding: 15px 20px; border-radius: 12px;
        border: 1px solid #E2E8F0; margin-bottom: 10px;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .info-area { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .name-line { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .cat-tag { font-size: 10px; color: #2563EB; background: #EFF6FF; padding: 2px 6px; border-radius: 4px; font-weight: 700; }
    .name-text { font-size: 14px; font-weight: 600; color: #1E293B; }
    .memo-text { font-size: 12px; color: #94A3B8; }
    
    .price-area { display: flex; align-items: center; gap: 20px; flex-shrink: 0; }
    .price-box { text-align: center; width: 95px; }
    .label-txt { font-size: 10px; color: #94A3B8; margin-bottom: 4px; display: block; }
    
    /* 가을판매가 배지 */
    .fall-badge { background: #2563EB; color: white !important; padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 14px; }
    
    /* 변동 배지 */
    .diff-badge { padding: 4px 8px; border-radius: 5px; font-weight: 700; font-size: 12px; min-width: 65px; text-align: center; }
    .up { background: #FEE2E2; color: #EF4444; }
    .down { background: #DBEAFE; color: #2563EB; }
    .same { background: #F1F5F9; color: #94A3B8; }

    /* 열기 버튼 */
    .open-btn {
        text-decoration: none !important; background: #10B981; color: white !important;
        padding: 7px 15px; border-radius: 6px; font-size: 13px; font-weight: 700;
    }
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
        for c in ["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"]:
            if c not in df.columns: df[c] = 0 if "가" in c else "-"
        return df
    return pd.DataFrame(columns=["구분", "카테고리", "상품명", "가을판매가", "컴퓨존판매가", "실시간가", "메모", "링크"])

if 'df' not in st.session_state: st.session_state.df = load_data()

# --- 화면 출력 ---
st.markdown('<h2 style="color:#1E293B;">🌸 가을 가전 통합 관리자</h2>', unsafe_allow_html=True)

# 1. 신규 등록
with st.expander("➕ 상품 신규 등록"):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL (그대로 복사해서 넣으세요)")
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", step=1000)
    r_cp = c5.number_input("기준가(컴퓨존)", step=1000)
    r_memo = c6.text_input("메모")
    if c7.button("목록 추가", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 2. 필터 및 검색
f1, f2 = st.columns([7, 3])
with f1: s_name = st.text_input("🔍 검색 (상품명 또는 메모)")
with f2: s_cat = st.selectbox("📂 카테고리 필터", CATEGORY_LIST)

tabs = st.tabs(["전체보기", "가격비교", "자주구매"])
sel_tab = "전체보기" if tabs[0] else "가격비교" if tabs[1] else "자주구매"

df = st.session_state.df.copy()
if sel_tab != "전체보기": df = df[df['구분'] == sel_tab]
if s_cat != "전체보기": df = df[df['카테고리'] == s_cat]
if s_name: df = df[df['상품명'].str.contains(s_name, case=False) | df['메모'].str.contains(s_name, case=False)]

# 3. 액션 버튼
act_c1, act_c2, act_c3 = st.columns([7, 1.5, 1.5])
with act_c2: refresh_btn = st.button("🔄 가격 갱신", use_container_width=True)
with act_c3: delete_btn = st.button("🗑️ 선택 삭제", use_container_width=True)

# 4. 리스트 출력 (이미지 디자인 적용)
selected_indices = []
for idx, row in df.iterrows():
    chk, r_ui = st.columns([0.03, 0.97])
    with chk:
        if st.checkbox("", key=f"del_{idx}"): selected_indices.append(idx)
    with r_ui:
        diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
        d_class = "up" if diff > 0 else "down" if diff < 0 else "same"
        d_txt = f"▲{diff:,}" if diff > 0 else f"▼{abs(diff):,}" if diff < 0 else "-"
        
        # 가격비교 탭 최적화 레이아웃
        if sel_tab == "가격비교":
            price_html = f"""
                <div class="price-box"><span class="label-txt">컴퓨존 기준</span><div style="font-size:14px; color:#64748B;">{int(row['컴퓨존판매가']):,}</div></div>
                <div class="price-box"><span class="label-txt">실시간가</span><div style="font-size:14px; font-weight:700; color:#1E293B;">{int(row['실시간가']):,}</div></div>
                <div class="price-box"><span class="label-txt">변동액</span><div class="diff-badge {d_class}">{d_txt}</div></div>
            """
        else:
            price_html = f"""
                <div class="price-box"><span class="label-txt">가을판매가</span><div class="fall-badge">{int(row['가을판매가']):,}</div></div>
                <div class="price-box"><span class="label-txt">실시간가</span><div style="font-size:14px; font-weight:700; color:#1E293B;">{int(row['실시간가']):,}</div></div>
                <div class="price-box"><span class="label-txt">변동</span><div class="diff-badge {d_class}">{d_txt}</div></div>
            """

        st.markdown(f"""
        <div class="product-row">
            <div class="info-area">
                <div class="name-line">
                    <span class="cat-tag">{row['카테고리']}</span>
                    <div class="name-text">{row['상품명']}</div>
                </div>
                <div class="memo-text">📝 {row['메모'] if str(row['메모']) != 'nan' else '비고 없음'}</div>
            </div>
            <div class="price-area">
                {price_html}
                <div style="width:50px; text-align:right;">
                    <a href="{row['링크']}" target="_blank" class="open-btn">열기</a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 5. 하단 가격 수정 기능
if selected_indices:
    st.divider()
    st.subheader("🛠️ 선택 상품 가격/메모 수정")
    e_idx = selected_indices[0]
    target = st.session_state.df.loc[e_idx]
    e1, e2, e3, e4 = st.columns([2, 2, 4, 2])
    new_fall = e1.number_input("가을판매가 수정", value=int(target['가을판매가']), step=1000)
    new_compu = e2.number_input("컴퓨존기준가 수정", value=int(target['컴퓨존판매가']), step=1000)
    new_memo = e3.text_input("메모 수정", value=str(target['메모']))
    if e4.button("💾 저장하기", use_container_width=True):
        st.session_state.df.at[e_idx, '가을판매가'] = new_fall
        st.session_state.df.at[e_idx, '컴퓨존판매가'] = new_compu
        st.session_state.df.at[e_idx, '메모'] = new_memo
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.success("수정되었습니다!")
        st.rerun()

# 6. 삭제 및 갱신 로직
if delete_btn and selected_indices:
    st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
    st.session_state.df.to_excel(DB_FILE, index=False)
    st.rerun()

if refresh_btn:
    with st.spinner("최신 가격 정보 가져오는 중..."):
        for i in df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
