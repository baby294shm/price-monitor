import streamlit as st
import pandas as pd
import os
import requests
from bs4 import BeautifulSoup

# --- 설정 및 데이터 로드 ---
DB_FILE = "product_db.xlsx"
CATEGORY_LIST = ["전체보기", "PC", "워크스테이션", "SSD", "HDD", "RAM", "VGA"]

st.set_page_config(page_title="가을 가전 관리자", layout="wide")

# --- CSS (사장님이 좋아하신 이미지 속 디자인 스타일) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #FDFDFD; }
    
    .product-row {
        background: white; padding: 12px 18px; border-radius: 12px;
        border: 1px solid #E5E7EB; margin-bottom: 8px;
        display: flex; align-items: center; justify-content: space-between;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .info-area { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .name-line { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
    .name-text { font-size: 14px; font-weight: 600; color: #334155; }
    .memo-text { font-size: 12px; color: #94A3B8; font-style: normal; }
    
    .price-area { display: flex; align-items: center; gap: 15px; flex-shrink: 0; }
    .price-box { text-align: center; width: 90px; }
    .label-txt { font-size: 10px; color: #94A3B8; margin-bottom: 2px; display: block; }
    
    /* 가을판매가 강조 배지 (파란색) */
    .fall-badge { background: #2563EB; color: white; padding: 5px 10px; border-radius: 6px; font-weight: 700; font-size: 14px; }
    
    /* 변동액 배지 (상승/하락) */
    .diff-badge { padding: 4px 8px; border-radius: 5px; font-weight: 700; font-size: 12px; min-width: 65px; text-align: center; }
    .up { background: #FEE2E2; color: #EF4444; }
    .down { background: #DBEAFE; color: #3B82F6; }
    .same { background: #F3F4F6; color: #94A3B8; }

    /* 열기 버튼 (초록색) */
    .open-btn {
        text-decoration: none !important; background: #10B981; color: white !important;
        padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 700;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 실시간 가격 함수 ---
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

# --- 메인 대시보드 ---
st.markdown('<div style="font-size:24px; font-weight:700; color:#1E293B; margin-bottom:20px;">🌸 가을 가전 통합 관리 대시보드</div>', unsafe_allow_html=True)

# 1. 등록 영역
with st.expander("➕ 상품 신규 등록", expanded=False):
    c1, c2, c3 = st.columns([1, 1, 2])
    r_type = c1.selectbox("구분", ["가격비교", "자주구매"])
    r_cat = c2.selectbox("카테고리", CATEGORY_LIST[1:])
    r_name = c3.text_input("상품명")
    r_link = st.text_input("컴퓨존 URL")
    c4, c5, c6, c7 = st.columns([1, 1, 1, 1])
    r_my = c4.number_input("가을판매가", step=1000)
    r_cp = c5.number_input("컴퓨존기준가", step=1000)
    r_memo = c6.text_input("비고(메모)")
    if c7.button("목록에 추가", use_container_width=True):
        if r_name and r_link:
            new_row = {"구분": r_type, "카테고리": r_cat, "상품명": r_name, "가을판매가": r_my, "컴퓨존판매가": r_cp, "실시간가": r_cp, "메모": r_memo, "링크": r_link.strip()}
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.df.to_excel(DB_FILE, index=False)
            st.rerun()

# 2. 필터 영역 (이미지와 동일 구성)
col_f1, col_f2 = st.columns([7, 3])
with col_f1: search_q = st.text_input("🔍 상품명/메모 검색")
with col_f2: category_q = st.selectbox("📂 카테고리 필터", CATEGORY_LIST)

t1, t2, t3 = st.tabs(["전체보기", "가격비교", "자주구매"])
sel_tab = "전체보기" if t1 else "가격비교" if t2 else "자주구매"

# 데이터 필터링
disp_df = st.session_state.df.copy()
if sel_tab != "전체보기": disp_df = disp_df[disp_df['구분'] == sel_tab]
if category_q != "전체보기": disp_df = disp_df[disp_df['카테고리'] == category_q]
if search_q: disp_df = disp_df[disp_df['상품명'].str.contains(search_q, case=False) | disp_df['메모'].str.contains(search_q, case=False)]

# 3. 버튼들
act_c1, act_c2, act_c3 = st.columns([7, 1.5, 1.5])
with act_c2: refresh_btn = st.button("🔄 실시간 가격 갱신", use_container_width=True)
with act_c3: delete_btn = st.button("🗑️ 선택 상품 삭제", use_container_width=True)

# 4. 리스트 출력
selected_indices = []
for idx, row in disp_df.iterrows():
    chk_c, row_c = st.columns([0.03, 0.97])
    with chk_c:
        if st.checkbox("", key=f"sel_{idx}"): selected_indices.append(idx)
    with row_c:
        diff = int(row['실시간가']) - int(row['컴퓨존판매가'])
        d_class = "up" if diff > 0 else "down" if diff < 0 else "same"
        d_txt = f"▲{diff:,}" if diff > 0 else f"▼{abs(diff):,}" if diff < 0 else "-"
        
        # 가격비교 탭 최적화: 가을판매가 숨기고 변동에 집중
        if sel_tab == "가격비교":
            price_box_html = f"""
                <div class="price-box"><span class="label-txt">기준가</span><div style="font-size:14px; color:#64748B;">{int(row['컴퓨존판매가']):,}</div></div>
                <div class="price-box"><span class="label-txt">실시간가</span><div style="font-size:14px; font-weight:700;">{int(row['실시간가']):,}</div></div>
                <div class="price-box"><span class="label-txt">변동액</span><div class="diff-badge {d_class}">{d_txt}</div></div>
            """
        else:
            price_box_html = f"""
                <div class="price-box"><span class="label-txt">가을판매가</span><div class="fall-badge">{int(row['가을판매가']):,}</div></div>
                <div class="price-box"><span class="label-txt">실시간가</span><div style="font-size:14px; font-weight:700;">{int(row['실시간가']):,}</div></div>
                <div class="price-box"><span class="label-txt">변동</span><div class="diff-badge {d_class}">{d_txt}</div></div>
            """

        st.markdown(f"""
        <div class="product-row">
            <div class="info-area">
                <div class="name-line">
                    <span style="font-size:10px; color:#3B82F6; background:#EFF6FF; padding:1px 5px; border-radius:4px; font-weight:700;">{row['카테고리']}</span>
                    <div class="name-text">{row['상품명']}</div>
                </div>
                <div class="memo-text">📝 {row['메모'] if str(row['메모']) != 'nan' else '메모 없음'}</div>
            </div>
            <div class="price-area">
                {price_box_html}
                <div style="width:50px; text-align:right;">
                    <a href="{row['링크']}" target="_blank" class="open-btn">열기</a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 5. 가격/정보 수정 (체크 시 활성화)
if selected_indices:
    st.divider()
    st.subheader("🛠️ 선택 상품 가격 및 메모 수정")
    e_idx = selected_indices[0]
    target = st.session_state.df.loc[e_idx]
    ec1, ec2, ec3, ec4 = st.columns([2, 2, 4, 2])
    new_fall = ec1.number_input("가을판매가", value=int(target['가을판매가']), step=1000)
    new_compu = ec2.number_input("컴퓨존기준가", value=int(target['컴퓨존판매가']), step=1000)
    new_memo = ec3.text_input("메모수정", value=target['메모'])
    if ec4.button("💾 수정내용 저장", use_container_width=True):
        st.session_state.df.at[e_idx, '가을판매가'] = new_fall
        st.session_state.df.at[e_idx, '컴퓨존판매가'] = new_compu
        st.session_state.df.at[e_idx, '메모'] = new_memo
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.success("정보가 수정되었습니다!")
        st.rerun()

# 6. 로직
if delete_btn and selected_indices:
    st.session_state.df = st.session_state.df.drop(selected_indices).reset_index(drop=True)
    st.session_state.df.to_excel(DB_FILE, index=False)
    st.rerun()

if refresh_btn:
    with st.spinner("최신 가격 정보 가져오는 중..."):
        for i in disp_df.index:
            p = get_live_price(st.session_state.df.at[i, '링크'])
            if p: st.session_state.df.at[i, '실시간가'] = p
        st.session_state.df.to_excel(DB_FILE, index=False)
        st.rerun()
