# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import pandas as pd

class BeerGameNode:
    def __init__(self, role_name, initial_inv=8, initial_delay=4):
        self.role_name = role_name
        # 물리적 물류 지연 (2주: 기차/트럭 혹은 구매/제조)
        self.shipment_delay = [initial_delay, initial_delay] 
        # 정보(발주) 지연 (2주)
        self.order_delay = [4, 4] 
        
        self.inventory = initial_inv
        self.backorder = 0
        self.ledger = [] # C1~C6 기록용

    def play_week(self, week, incoming_order, incoming_supply):
        # --- Timeline 1: 물량 이동 및 도착 ---
        arrived_supply = self.shipment_delay.pop(0) # 가장 오래된 지연 물량 도착
        self.inventory += arrived_supply
        self.shipment_delay.append(incoming_supply) # 상위 단계에서 보낸 새 물량 진입
        
        # 기초 재고 기록 (C1)
        beg_inv = self.inventory - arrived_supply
        
        # --- Timeline 2: 수요 확인 및 배송 (C5 계산) ---
        total_demand = incoming_order + self.backorder
        actual_ship = min(self.inventory, total_demand)
        
        self.inventory -= actual_ship
        self.backorder = total_demand - actual_ship
        
        # 기말 재고(C5): 양수면 재고, 음수면 이월주문(Backorder)
        final_inv_val = self.inventory if self.backorder == 0 else -self.backorder
        
        # --- Timeline 3: 발주 결정은 외부(학생)에서 입력 받음 ---
        return {
            "Week": week,
            "C1_BegInv": beg_inv,
            "C2_Arrived": arrived_supply,
            "C3_NewOrder": incoming_order,
            "C4_Shipment": actual_ship,
            "C5_EndInv": final_inv_val
        }

# --- 1주차 시뮬레이션 실행 ---
roles = ["Retailer", "Wholesaler", "Distributor", "Factory"]
game_nodes = {role: BeerGameNode(role) for role in roles}

# 1주차 외부 데이터 (예: 소비자 수요 4, 팩토리 공급 4)
external_demand = 4
factory_supply = 4

# 각 노드의 1주차 처리
results = []
for role in roles:
    # 실제 구현 시에는 상위/하위 노드와 연결하여 order/supply를 주고받음
    # 여기서는 1주차 작동 확인을 위해 기본값 4를 사용
    res = game_nodes[role].play_week(1, 4, 4)
    res['Role'] = role
    
    # 학생이 결정한 발주량(C6) 입력 예시
    res['C6_OrderDecision'] = 5 if role == "Retailer" else 8 # 예시 발주량
    results.append(res)

# 데이터프레임으로 결과 확인 (학생들에게 보여줄 엑셀 양식)
df_week1 = pd.DataFrame(results)
print(df_week1[['Role', 'Week', 'C1_BegInv', 'C2_Arrived', 'C3_NewOrder', 'C4_Shipment', 'C5_EndInv', 'C6_OrderDecision']])















# In[]: [Option A] Streamlit: 개인 연습용 UI (MVP)


import streamlit as st
import pandas as pd
import altair as alt # 시각화를 위한 라이브러리

# ... (기존 BeerGameNode 클래스 로직 포함) ...

st.set_page_config(layout="wide") # 화면을 넓게 사용
st.title(f"🍺 Beer Game: {st.session_state.role} Dashboard")

# 1. 핵심 지표 (PPT의 주요 수치들)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("현재 창고 재고 (C1+C2)", f"{current_inv} 박스")
with col2:
    st.metric("도착 예정 (Truck/Train)", f"{incoming_total} 박스", delta="In-transit")
with col3:
    st.metric("이번 주 배송량 (C4)", f"{last_shipped} 박스", delta_color="normal")
with col4:
    st.metric("미납 주문 (Backorder)", f"{current_backorder} 박스", delta="-", delta_color="inverse")

# 2. 시각적 차트 (재고 및 주문 흐름)
if st.session_state.history:
    df = pd.DataFrame(st.session_state.history)
    
    # 재고 변화 선 그래프
    chart = alt.Chart(df).mark_line(point=True).encode(
        x='Week:O',
        y='Inventory:Q',
        tooltip=['Week', 'Inventory', 'Order']
    ).properties(width=700, height=300, title="주차별 재고 추이")
    
    st.altair_chart(chart, use_container_width=True)

# 3. 입력 구간 (노란색 칸)
st.divider()
order_val = st.slider("이번 주 발주 결정 (C6):", 0, 50, 4)
if st.button("배송 지시 및 발주 완료"):
    # 게임 로직 실행 및 화면 갱신
    pass


