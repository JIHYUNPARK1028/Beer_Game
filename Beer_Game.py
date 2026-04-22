# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt
import random

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game Board", layout="wide")

# --- 스타일 정의 (사진의 보드판 느낌 재현) ---
st.markdown("""
    <style>
    .board-node {
        border: 5px solid #444;
        border-radius: 15px;
        padding: 20px;
        background-color: #fdfdfd;
        min-height: 400px;
        box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
    }
    .order-box {
        border: 2px dashed #ff4b4b;
        background-color: #fff5f5;
        padding: 10px;
        margin-bottom: 15px;
        border-radius: 5px;
    }
    .inventory-box {
        border: 3px solid #1f77b4;
        background-color: #e7f3ff;
        padding: 20px;
        margin: 15px 0;
        border-radius: 10px;
        font-size: 2.5em;
        font-weight: bold;
        color: #1f77b4;
    }
    .shipment-box {
        border: 2px solid #2ca02c;
        background-color: #f0fff0;
        padding: 10px;
        border-radius: 5px;
    }
    .role-title {
        font-size: 1.8em;
        font-weight: bold;
        margin-bottom: 10px;
        text-transform: uppercase;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 상수 및 로직 (동일) ---
CUSTOMER_ORDERS = [4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 8, 7, 8, 10, 7, 7, 8, 7, 10, 9]
MAX_WEEKS = len(CUSTOMER_ORDERS)

if "chain" not in st.session_state:
    from Beer_Game_Logic import BeerGameChain # 로직 클래스 분리 가정 혹은 기존 클래스 사용
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1

# --- 보드판 렌더링 함수 (사진 레이아웃 적용) ---
def render_physical_board(chain, user_role, is_finished):
    cols = st.columns(4)
    colors = {"Retailer": "#0056b3", "Wholesaler": "#28a745", "Distributor": "#333", "Factory": "#dc3545"}
    
    for i, role in enumerate(chain.roles):
        node = chain.nodes[role]
        color = colors[role]
        is_me = (role == user_role) or is_finished
        
        with cols[i]:
            # 데이터 보안 처리
            stock = node.inventory if node.backorder == 0 else -node.backorder
            inv_display = f"{stock}" if is_me else "???"
            
            # Incoming Order (사진 상단 포스트잇 구역)
            if role == "Retailer":
                inc_order = CUSTOMER_ORDERS[st.session_state.week-1] if st.session_state.week <= MAX_WEEKS else "END"
            else:
                inc_order = chain.order_delay[role][0] if is_me else "???"

            # Shipments (사진 하단 칩 구역)
            truck = chain.supply_delay[role][1] if is_me else "?"
            train = chain.supply_delay[role][0] if is_me else "?"

            st.markdown(f"""
                <div class="board-node" style="border-color: {color if (role == user_role) else '#ddd'};">
                    <div class="role-title" style="color: {color};">{role}</div>
                    <div style="color: gray; font-size: 0.8em; margin-bottom: 20px;">
                        {"(YOU - PLAYER)" if role == user_role else "(COMPUTER)"}
                    </div>
                    
                    <div class="order-box">
                        <small style="color: #ff4b4b;">INCOMING ORDERS</small><br>
                        <span style="font-size: 1.5em; font-weight: bold;">{inc_order}</span>
                    </div>
                    
                    <div class="inventory-box">
                        <small style="font-size: 0.3em; color: #555; display: block;">CURRENT INVENTORY</small>
                        {inv_display}
                    </div>
                    
                    <div class="shipment-box">
                        <small style="color: #2ca02c;">INCOMING SHIPMENTS</small>
                        <div style="display: flex; justify-content: space-around; margin-top: 5px;">
                            <div><small>Truck</small><br><b>{truck}</b></div>
                            <div style="border-left: 1px solid #ccc;"></div>
                            <div><small>Train</small><br><b>{train}</b></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- 메인 실행부 ---
st.title("🍺 Beer Game: Physical Board Interface")

user_role = st.sidebar.selectbox("역할 선택", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("리셋"):
    st.session_state.week = 1; st.session_state.history = []; st.rerun()

is_finished = st.session_state.week > MAX_WEEKS

# 1. 보드판 구역
render_physical_board(st.session_state.chain, user_role, is_finished)

st.write("") # 간격

# 2. 제어 및 장부 구역
if not is_finished:
    c1, c2 = st.columns([1, 3])
    with c1:
        st.subheader("🕹️ Decision")
        order_val = st.number_input(f"Week {st.session_state.week} 발주량:", min_value=0, value=4)
        if st.button("확정 (Confirm)", type="primary", use_container_width=True):
            res = st.session_state.chain.proceed_week(st.session_state.week, user_role, order_val, CUSTOMER_ORDERS[st.session_state.week-1])
            st.session_state.history.append(res)
            st.session_state.week += 1
            st.rerun()
    
    with c2:
        st.subheader("📋 Accounting Sheet")
        if st.session_state.history:
            my_data = [w[user_role] for w in st.session_state.history]
            df = pd.DataFrame(my_data)[['Week', 'C1_Initial', 'C2_Arrived', 'C3_NewOrder', 'C4_Final', 'C5_OrderDec']]
            df.columns = ['주차', '기초재고', '입고', '주문수량', '기말재고', '발주결정']
            st.dataframe(df.sort_values('주차', ascending=False), use_container_width=True)

else:
    st.success("게임이 종료되었습니다. 상단 보드에서 모든 데이터가 공개되었습니다.")
    # (그래프 및 비용 분석 로직 추가...)
