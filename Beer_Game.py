# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정 (반드시 최상단에 위치)
st.set_page_config(page_title="Beer Game Simulator", layout="wide")

# --- 비어게임 로직 클래스 ---
class BeerGameNode:
    def __init__(self, role_name, initial_inv=8, initial_delay=4):
        self.role_name = role_name
        self.shipment_delay = [initial_delay, initial_delay] 
        self.inventory = initial_inv
        self.backorder = 0

    def play_week(self, week, incoming_order, incoming_supply):
        arrived_supply = self.shipment_delay.pop(0)
        beg_inv = self.inventory
        self.inventory += arrived_supply
        self.shipment_delay.append(incoming_supply)
        
        total_demand = incoming_order + self.backorder
        actual_ship = min(self.inventory, total_demand)
        
        self.inventory -= actual_ship
        self.backorder = total_demand - actual_ship
        
        final_inv_val = self.inventory if self.backorder == 0 else -self.backorder
        
        return {
            "Week": week,
            "C1_BegInv": beg_inv,
            "C2_Arrived": arrived_supply,
            "C3_NewOrder": incoming_order,
            "C4_Shipment": actual_ship,
            "C5_EndInv": final_inv_val,
            "Inventory": self.inventory,
            "Backorder": self.backorder,
            "InTransit": sum(self.shipment_delay)
        }

# 2. 세션 상태 초기화 (게임 데이터 유지)
if "game_node" not in st.session_state:
    st.session_state.game_node = BeerGameNode("Retailer")
    st.session_state.history = []
    st.session_state.week = 1

# 3. 사이드바: 역할 선택 및 테마 적용
role_colors = {
    "Retailer": "#D1E7DD", "Wholesaler": "#FFF3CD", 
    "Distributor": "#CFE2FF", "Factory": "#F8D7DA"
}
selected_role = st.sidebar.selectbox(
    "본인의 역할을 선택하세요", 
    ["Retailer", "Wholesaler", "Distributor", "Factory"],
    key="role_select"
)

# 역할 변경 시 노드 초기화
if st.session_state.game_node.role_name != selected_role:
    st.session_state.game_node = BeerGameNode(selected_role)
    st.session_state.history = []
    st.session_state.week = 1

# 배경색 주입 (CSS)
st.markdown(f"""
    <style>
    .stApp {{ background-color: {role_colors[selected_role]}; }}
    </style>
    """, unsafe_allow_html=True)

# 4. 메인 화면 대시보드
st.title(f"🍺 Beer Game: {selected_role} Dashboard")

node = st.session_state.game_node

# 지표 계산
current_inv = node.inventory
current_backorder = node.backorder
incoming_total = sum(node.shipment_delay)
last_shipped = st.session_state.history[-1]['C4_Shipment'] if st.session_state.history else 0

# 지표 표시 (Metrics)
col1, col2, col3, col4 = st.columns(4)
col1.metric("현재 창고 재고", f"{current_inv} 박스")
col2.metric("도착 예정 (물류 지연)", f"{incoming_total} 박스")
col3.metric("최근 배송량", f"{last_shipped} 박스")
col4.metric("미납 주문 (Backorder)", f"{current_backorder} 박스", delta_color="inverse")

# 5. 입력 및 실행 (노란색 칸 역할)
st.divider()
st.subheader(f"Week {st.session_state.week}: 의사결정")
order_val = st.number_input("이번 주 발주 결정 (C6):", min_value=0, value=4)

if st.button("배송 지시 및 발주 완료"):
    # 무작위 수요 발생 (추후 멀티플레이어 시 다른 노드의 값으로 대체)
    simulated_demand = 4 if st.session_state.week < 5 else 8
    simulated_supply = 4
    
    # 로직 실행
    result = node.play_week(st.session_state.week, simulated_demand, simulated_supply)
    result["C6_Order"] = order_val
    
    st.session_state.history.append(result)
    st.session_state.week += 1
    st.rerun()

# 6. 시각화 (채찍효과 확인)
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    
    st.subheader("📊 데이터 추이")
    tab1, tab2 = st.tabs(["재고 그래프", "상세 기록표"])
    
    with tab1:
        chart = alt.Chart(df).mark_line(point=True).encode(
            x='Week:O',
            y='Inventory:Q',
            color=alt.value("blue"),
            tooltip=['Week', 'Inventory', 'C6_Order']
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    
    with tab2:
        st.dataframe(df)
