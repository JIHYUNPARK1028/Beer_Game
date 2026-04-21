# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game Simulator", layout="wide")

# --- 로직 클래스: 개별 노드 (재고 관리 전용) ---
class BeerGameNode:
    def __init__(self, role_name):
        self.role_name = role_name
        self.inventory = 12  # 초기 재고
        self.backorder = 0

    def calculate_step(self, incoming_order, arrived_supply):
        """재고 및 배송 계산 (C1~C5 로직)"""
        # 기초 재고 기록
        beg_inv = self.inventory
        
        # 물량 입고
        self.inventory += arrived_supply
        
        # 배송 계산 (이월주문 포함)
        total_demand = incoming_order + self.backorder
        actual_ship = min(self.inventory, total_demand)
        
        # 재고 및 이월주문 업데이트
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

# --- 로직 클래스: 공급망 체인 (연동 및 지연 관리) ---
class BeerGameChain:
    def __init__(self):
        self.roles = ["Retailer", "Wholesaler", "Distributor", "Factory"]
        self.nodes = {role: BeerGameNode(role) for role in self.roles}
        
        # 정보 지연 (2주): 하위 단계 주문이 상위로 도달하는 시간
        self.order_delay = {
            "Wholesaler": [4, 4], # Retailer -> Wholesaler
            "Distributor": [4, 4], # Wholesaler -> Distributor
            "Factory": [4, 4]      # Distributor -> Factory
        }
        # 물류 지연 (2주): 상위 단계 배송이 하위로 도달하는 시간
        self.supply_delay = {
            "Retailer": [4, 4],    # Wholesaler -> Retailer
            "Wholesaler": [4, 4],  # Distributor -> Wholesaler
            "Distributor": [4, 4], # Factory -> Distributor
            "Factory": [4, 4]      # Production -> Factory (생산 리드타임)
        }

    def proceed_week(self, week, user_role, user_order, consumer_demand):
        results = {}
        
        # 1. 각 단계별 이번 주 실제 입력값(수요/공급) 확정
        current_inputs = {
            "Retailer": {"demand": consumer_demand, "supply": self.supply_delay["Retailer"].pop(0)},
            "Wholesaler": {"demand": self.order_delay["Wholesaler"].pop(0), "supply": self.supply_delay["Wholesaler"].pop(0)},
            "Distributor": {"demand": self.order_delay["Distributor"].pop(0), "supply": self.supply_delay["Distributor"].pop(0)},
            "Factory": {"demand": self.order_delay["Factory"].pop(0), "supply": self.supply_delay["Factory"].pop(0)}
        }

        # 2. 모든 노드 계산 실행
        for role in self.roles:
            inputs = current_inputs[role]
            node_res = self.nodes[role].calculate_step(inputs["demand"], inputs["supply"])
            
            # 3. 발주 결정 (C6)
            if role == user_role:
                order_decision = user_order
            else:
                # AI 로직: 받은 주문량만큼 그대로 발주 (추종 전략)
                order_decision = inputs["demand"]
            
            node_res["C6_Order"] = order_decision
            node_res["Role"] = role
            node_res["Week"] = week
            results[role] = node_res

            # 4. 결과물을 지연 버퍼에 전달 (다음 주를 위한 준비)
            if role == "Retailer":
                self.order_delay["Wholesaler"].append(order_decision)
            elif role == "Wholesaler":
                self.order_delay["Distributor"].append(order_decision)
                self.supply_delay["Retailer"].append(node_res["C4_Shipment"])
            elif role == "Distributor":
                self.order_delay["Factory"].append(order_decision)
                self.supply_delay["Wholesaler"].append(node_res["C4_Shipment"])
            elif role == "Factory":
                self.supply_delay["Distributor"].append(node_res["C4_Shipment"])
                self.supply_delay["Factory"].append(order_decision) # 공장 생산물 진입

        return results

# 2. 세션 상태 초기화
if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1

# 3. 사이드바 및 환경 설정
st.sidebar.title("🎮 Game Setting")
user_role = st.sidebar.selectbox("플레이어 역할", ["Retailer", "Wholesaler", "Distributor", "Factory"])
role_colors = {"Retailer": "#D1E7DD", "Wholesaler": "#FFF3CD", "Distributor": "#CFE2FF", "Factory": "#F8D7DA"}

st.markdown(f"<style>.stApp {{ background-color: {role_colors[user_role]}; }}</style>", unsafe_allow_html=True)

# 4. 메인 대시보드
st.title(f"🍺 Beer Game: {user_role} Dashboard")

chain = st.session_state.chain
my_node = chain.nodes[user_role]

# 상단 지표
col1, col2, col3, col4 = st.columns(4)
col1.metric("현재 창고 재고", f"{my_node.inventory} PKG")
col2.metric("미납 주문 (Backorder)", f"{my_node.backorder} PKG", delta_color="inverse")
col3.metric("입고 대기 물량", f"{sum(chain.supply_delay[user_role])} PKG")
col4.metric("현재 주차", f"Week {st.session_state.week}")

# 5. 의사결정 입력
st.divider()
c_demand = 4 if st.session_state.week < 5 else 8  # 5주차부터 수요 급증 (채찍효과 유도)

with st.form("order_form"):
    st.write(f"📢 이번 주 고객 주문(C3): **{c_demand if user_role == 'Retailer' else chain.order_delay.get(user_role, [0,0])[0]}** PKG")
    order_val = st.number_input("이번 주 발주량 결정 (C6)", min_value=0, value=4)
    submit = st.form_submit_button("주문 확정 및 다음 주로 이동")

if submit:
    week_res = chain.proceed_week(st.session_state.week, user_role, order_val, c_demand)
    st.session_state.history.append(week_res)
    st.session_state.week += 1
    st.rerun()

# 6. 결과 시각화
if st.session_state.history:
    # 데이터 변환 (차트용)
    history_data = []
    for week_map in st.session_state.history:
        for r_name, r_val in week_map.items():
            history_data.append(r_val)
    
    df = pd.DataFrame(history_data)
    my_df = df[df['Role'] == user_role]

    st.subheader("📊 시뮬레이션 분석")
    tab1, tab2, tab3 = st.tabs(["내 역할 추이", "전체 공급망 비교 (Bullwhip)", "상세 장부"])

    with tab1:
        # 내 재고 및 주문 그래프
        base = alt.Chart(my_df).encode(x='Week:O')
        line1 = base.mark_line(color='#1f77b4', point=True).encode(y='Inventory:Q', tooltip=['Week', 'Inventory'])
        line2 = base.mark_line(color='#ff7f0e', strokeDash=[5,5]).encode(y='C6_Order:Q', tooltip=['Week', 'C6_Order'])
        st.altair_chart((line1 + line2).properties(height=300, title="재고(실선) vs 주문(점선)"), use_container_width=True)

    with tab2:
        # 채찍효과 확인 (모든 역할의 주문량 비교)
        bw_chart = alt.Chart(df).mark_line(point=True).encode(
            x='Week:O',
            y='C6_Order:Q',
            color='Role:N',
            tooltip=['Role', 'Week', 'C6_Order']
        ).properties(height=400, title="공급망 단계별 주문 변동 (채찍효과)")
        st.altair_chart(bw_chart, use_container_width=True)
        st.caption("공장(Factory)으로 갈수록 주문의 진폭이 커지는 것을 확인해보세요.")

    with tab3:
        st.write("회계 장부 (전체 기록)")
        st.dataframe(my_df[['Week', 'C1_BegInv', 'C2_Arrived', 'C3_NewOrder', 'C4_Shipment', 'C5_EndInv', 'C6_Order']])
