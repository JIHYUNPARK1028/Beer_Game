# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game Simulator v2.1", layout="wide")

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
        self.inventory = 8  # PPT 기준 초기 재고 8박스
        self.backorder = 0

    def calculate_step(self, incoming_order, arrived_supply):
        beg_inv = self.inventory
        self.inventory += arrived_supply
        
        # 이월 주문을 포함한 총 수요 계산
        total_demand = incoming_order + self.backorder
        actual_ship = min(self.inventory, total_demand)
        
        # 재고 및 이월 주문 업데이트
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
        
        # 초기 지연 물량 (2주 리드타임 고려, 초기값 4)
        self.order_delay = {
            "Wholesaler": [4, 4], 
            "Distributor": [4, 4], 
            "Factory": [4, 4]
        }
        self.supply_delay = {
            "Retailer": [4, 4], 
            "Wholesaler": [4, 4], 
            "Distributor": [4, 4], 
            "Factory": [4, 4] # 생산 지연
        }

    def proceed_week(self, week, user_role, user_order, consumer_demand):
        results = {}
        
        # 1. 이번 주 입력값(수요/공급)을 큐에서 1회씩만 추출
        # 각 단계의 수요(demand)는 하위 단계가 보낸 '지연된 주문'입니다.
        current_inputs = {
            "Retailer": {
                "demand": consumer_demand, 
                "supply": self.supply_delay["Retailer"].pop(0)
            },
            "Wholesaler": {
                "demand": self.order_delay["Wholesaler"].pop(0), 
                "supply": self.supply_delay["Wholesaler"].pop(0)
            },
            "Distributor": {
                "demand": self.order_delay["Distributor"].pop(0), 
                "supply": self.supply_delay["Distributor"].pop(0)
            },
            "Factory": {
                "demand": self.order_delay["Factory"].pop(0), 
                "supply": self.supply_delay["Factory"].pop(0)
            }
        }

        # 2. 모든 노드 계산 실행
        for role in self.roles:
            inputs = current_inputs[role]
            node_res = self.nodes[role].calculate_step(inputs["demand"], inputs["supply"])
            
            # 발주 결정 (C6): 사용자 역할이면 입력값, AI면 이번 주 받은 주문량(추종 전략)
            order_decision = user_order if role == user_role else inputs["demand"]
            
            node_res.update({"C6_Order": order_decision, "Role": role, "Week": week})
            results[role] = node_res

            # 3. 발생한 결과(주문량, 배송량)를 다음 주 지연 버퍼에 추가
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
                self.supply_delay["Factory"].append(order_decision) # 공장 생산 투입
                
        return results

# 2. 세션 초기화
if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1

# 3. 사이드바 및 레이아웃
user_role = st.sidebar.selectbox("플레이어 역할 선택", ["Retailer", "Wholesaler", "Distributor", "Factory"])
if st.sidebar.button("게임 초기화"):
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1
    st.rerun()

role_colors = {"Retailer": "#D1E7DD", "Wholesaler": "#FFF3CD", "Distributor": "#CFE2FF", "Factory": "#F8D7DA"}
st.markdown(f"<style>.stApp {{ background-color: {role_colors[user_role]}; }}</style>", unsafe_allow_html=True)

# 4. 메인 화면
st.title(f"🍺 Beer Game: {user_role} Dashboard")

if st.session_state.week <= MAX_WEEKS:
    chain = st.session_state.chain
    my_node = chain.nodes[user_role]
    
    # 상단 지표 표시
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("현재 창고 재고", f"{my_node.inventory} PKG")
    col2.metric("미납 주문 (Backorder)", f"{my_node.backorder} PKG", delta_color="inverse")
    col3.metric("입고 대기 (물류 지연)", f"{sum(chain.supply_delay[user_role])} PKG")
    col4.metric("진행 상황", f"Week {st.session_state.week} / {MAX_WEEKS}")

    # 의사결정 섹션
    current_market_demand = CUSTOMER_ORDERS[st.session_state.week - 1]
    
    with st.form("order_form"):
        if user_role == "Retailer":
            st.info(f"📊 이번 주 소비자 주문(C3): **{current_market_demand}** PKG")
        else:
            # 상위 단계는 큐의 첫 번째 값(2주 전 하위 단계 주문)이 이번 주의 수요임
            incoming_demand = chain.order_delay[user_role][0]
            st.info(f"📦 이번 주 하위 단계로부터의 주문(C3): **{incoming_demand}** PKG")
            
        order_val = st.number_input("이번 주 발주 결정 (C6)", min_value=0, value=4)
        submit = st.form_submit_button("의사결정 완료")

    if submit:
        # 연동 로직 실행
        week_res = chain.proceed_week(st.session_state.week, user_role, order_val, current_market_demand)
        st.session_state.history.append(week_res)
        st.session_state.week += 1
        st.rerun()
else:
    st.success("🎉 모든 시뮬레이션(30주)이 완료되었습니다!")

# 5. 데이터 시각화
if st.session_state.history:
    # 차트용 데이터 평탄화
    flat_history = [data for week_data in st.session_state.history for data in week_data.values()]
    df = pd.DataFrame(flat_history)
    
    tab1, tab2 = st.tabs(["📉 공급망 변동 분석", "📋 상세 장부"])
    
    with tab1:
        st.subheader("채찍효과(Bullwhip Effect) 확인")
        # 모든 역할의 주문량 추이 비교
        bw_chart = alt.Chart(df).mark_line(point=True).encode(
            x='Week:O',
            y='C6_Order:Q',
            color='Role:N',
            tooltip=['Role', 'Week', 'C6_Order', 'Inventory']
        ).properties(height=400)
        st.altair_chart(bw_chart, use_container_width=True)
        st.caption("그래프의 진폭이 공장(Factory)으로 갈수록 커지는지 확인해보세요.")
        
    with tab2:
        st.write(f"### {user_role} 상세 기록")
        my_df = df[df['Role'] == user_role]
        st.dataframe(my_df[['Week', 'C1_BegInv', 'C2_Arrived', 'C3_NewOrder', 'C4_Shipment', 'C5_EndInv', 'C6_Order']])
