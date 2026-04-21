# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game Simulator v2", layout="wide")

# --- 상수: 교수님이 제공하신 30주간의 소비자 수요 데이터 ---
CUSTOMER_ORDERS = [
    4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 
    5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 
    8, 7, 8, 10, 7, 7, 8, 7, 10, 9
]
MAX_WEEKS = len(CUSTOMER_ORDERS)

# --- 로직 클래스: 개별 노드 ---
class BeerGameNode:
    def __init__(self, role_name):
        self.role_name = role_name
        self.inventory = 12
        self.backorder = 0

    def calculate_step(self, incoming_order, arrived_supply):
        beg_inv = self.inventory
        self.inventory += arrived_supply
        total_demand = incoming_order + self.backorder
        actual_ship = min(self.inventory, total_demand)
        self.inventory -= actual_ship
        self.backorder = total_demand - actual_ship
        
        return {
            "C1_BegInv": beg_inv,
            "C2_Arrived": arrived_supply,
            "C3_NewOrder": incoming_order,
            "C4_Shipment": actual_ship,
            "C5_EndInv": self.inventory if self.backorder == 0 else -self.backorder,
            "Inventory": self.inventory,
            "Backorder": self.backorder
        }

# --- 로직 클래스: 공급망 체인 ---
class BeerGameChain:
    def __init__(self):
        self.roles = ["Retailer", "Wholesaler", "Distributor", "Factory"]
        self.nodes = {role: BeerGameNode(role) for role in self.roles}
        self.order_delay = {"Wholesaler": [4, 4], "Distributor": [4, 4], "Factory": [4, 4]}
        self.supply_delay = {"Retailer": [4, 4], "Wholesaler": [4, 4], "Distributor": [4, 4], "Factory": [4, 4]}

    def proceed_week(self, week, user_role, user_order, consumer_demand):
        results = {}
        # 1. 입력값 확정
        current_inputs = {
            "Retailer": {"demand": consumer_demand, "supply": self.supply_delay["Retailer"].pop(0)},
            "Wholesaler": {"demand": self.order_delay["Wholesaler"].pop(0), "supply": self.supply_delay["Wholesaler"].pop(0)},
            "Distributor": {"demand": self.order_delay["Wholesaler"].pop(0), "supply": self.supply_delay["Distributor"].pop(0)}, # 오타수정: Wholesaler의 주문이 Distributor의 수요
            "Factory": {"demand": self.order_delay["Distributor"].pop(0), "supply": self.supply_delay["Factory"].pop(0)}
        }
        # Wholesaler와 Distributor 수요 로직 보정
        current_inputs["Wholesaler"]["demand"] = self.order_delay["Wholesaler"].pop(0)
        current_inputs["Distributor"]["demand"] = self.order_delay["Distributor"].pop(0)
        current_inputs["Factory"]["demand"] = self.order_delay["Factory"].pop(0)

        for role in self.roles:
            inputs = current_inputs[role]
            node_res = self.nodes[role].calculate_step(inputs["demand"], inputs["supply"])
            
            order_decision = user_order if role == user_role else inputs["demand"]
            node_res.update({"C6_Order": order_decision, "Role": role, "Week": week})
            results[role] = node_res

            # 다음 주 지연 버퍼 업데이트
            if role == "Retailer": self.order_delay["Wholesaler"].append(order_decision)
            elif role == "Wholesaler":
                self.order_delay["Distributor"].append(order_decision)
                self.supply_delay["Retailer"].append(node_res["C4_Shipment"])
            elif role == "Distributor":
                self.order_delay["Factory"].append(order_decision)
                self.supply_delay["Wholesaler"].append(node_res["C4_Shipment"])
            elif role == "Factory":
                self.supply_delay["Distributor"].append(node_res["C4_Shipment"])
                self.supply_delay["Factory"].append(order_decision)
        return results

# 2. 세션 초기화
if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1

# 3. 사이드바
user_role = st.sidebar.selectbox("플레이어 역할", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("게임 초기화"):
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1
    st.rerun()

# 4. 메인 화면
st.title(f"🍺 Beer Game: {user_role} Dashboard")

if st.session_state.week <= MAX_WEEKS:
    chain = st.session_state.chain
    my_node = chain.nodes[user_role]
    
    # 지표
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재 재고", f"{my_node.inventory} PKG")
    col2.metric("미납 주문", f"{my_node.backorder} PKG", delta_color="inverse")
    col3.metric("입고 대기", f"{sum(chain.supply_delay[user_role])} PKG")
    col4.metric("진행 상황", f"{st.session_state.week} / {MAX_WEEKS} 주")

    # 의사결정
    current_market_demand = CUSTOMER_ORDERS[st.session_state.week - 1]
    
    with st.form("order_form"):
        if user_role == "Retailer":
            st.info(f"📢 이번 주 소비자 주문: **{current_market_demand}** PKG")
        else:
            # 상위 노드(Wholesaler 등)는 하위 노드가 2주 전 보낸 주문을 이번 주의 수요로 받음
            incoming_demand = chain.order_delay[user_role][0] if user_role in chain.order_delay else 0
            st.info(f"📢 이번 주 하위 단계 주문: **{incoming_demand}** PKG")
            
        order_val = st.number_input("이번 주 발주량 결정 (C6)", min_value=0, value=4)
        submit = st.form_submit_button("주문 확정")

    if submit:
        res = chain.proceed_week(st.session_state.week, user_role, order_val, current_market_demand)
        st.session_state.history.append(res)
        st.session_state.week += 1
        st.rerun()
else:
    st.success("🎉 30주간의 시뮬레이션이 종료되었습니다!")

# 5. 시각화 로직
if st.session_state.history:
    history_data = [val for week in st.session_state.history for val in week.values()]
    df = pd.DataFrame(history_data)
    
    tab1, tab2 = st.tabs(["공급망 분석 (Bullwhip)", "상세 데이터"])
    
    with tab1:
        # 채찍효과 차트
        chart = alt.Chart(df).mark_line(point=True).encode(
            x='Week:O',
            y='C6_Order:Q',
            color='Role:N',
            tooltip=['Role', 'Week', 'C6_Order', 'Inventory']
        ).properties(height=400, title="주차별 발주량 추이 (공급망 단계별)")
        st.altair_chart(chart, use_container_width=True)
        st.caption("소비자 수요의 작은 변화가 상류(Factory)로 갈수록 어떻게 증폭되는지 확인하세요.")
        
    with tab2:
        st.dataframe(df[df['Role'] == user_role])
