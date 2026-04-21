# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 15:29:31 2026

@author: admir
"""

import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="Beer Game - Analysis Mode", layout="wide")

# --- 상수 데이터 ---
CUSTOMER_ORDERS = [4, 4, 10, 8, 9, 8, 8, 10, 4, 4, 5, 3, 8, 8, 9, 8, 7, 8, 10, 11, 8, 7, 8, 10, 7, 7, 8, 7, 10, 9]
MAX_WEEKS = len(CUSTOMER_ORDERS)

# --- 로직 클래스 ---
class BeerGameNode:
    def __init__(self, role_name):
        self.role_name = role_name
        self.inventory = 8
        self.backorder = 0

    def calculate_step(self, incoming_order, arrived_supply):
        self.inventory += arrived_supply
        total_demand = incoming_order + self.backorder
        actual_ship = min(self.inventory, total_demand)
        self.inventory -= actual_ship
        self.backorder = total_demand - actual_ship
        return {"Shipment": actual_ship, "Inv": self.inventory, "Back": self.backorder}

class BeerGameChain:
    def __init__(self):
        self.roles = ["Retailer", "Wholesaler", "Distributor", "Factory"]
        self.nodes = {role: BeerGameNode(role) for role in self.roles}
        self.order_delay = {"Wholesaler": [4, 4], "Distributor": [4, 4], "Factory": [4, 4]}
        self.supply_delay = {"Retailer": [4, 4], "Wholesaler": [4, 4], "Distributor": [4, 4], "Factory": [4, 4]}

    def proceed_week(self, week, user_role, user_order, consumer_demand):
        results = {}
        current_inputs = {
            "Retailer": {"demand": consumer_demand, "supply": self.supply_delay["Retailer"].pop(0)},
            "Wholesaler": {"demand": self.order_delay["Wholesaler"].pop(0), "supply": self.supply_delay["Wholesaler"].pop(0)},
            "Distributor": {"demand": self.order_delay["Distributor"].pop(0), "supply": self.supply_delay["Distributor"].pop(0)},
            "Factory": {"demand": self.order_delay["Factory"].pop(0), "supply": self.supply_delay["Factory"].pop(0)}
        }
        for role in self.roles:
            res = self.nodes[role].calculate_step(current_inputs[role]["demand"], current_inputs[role]["supply"])
            order_decision = user_order if role == user_role else current_inputs[role]["demand"]
            
            # 순수 재고/이월 상태 기록
            final_stock = res["Inv"] if res["Back"] == 0 else -res["Back"]
            # 비용 계산: 재고($1), 이월($2)
            weekly_cost = res["Inv"] * 1 + res["Back"] * 2
            
            res.update({
                "C6_Order": order_decision, "Role": role, "Week": week, 
                "C3_Demand": current_inputs[role]["demand"], "C2_Arrived": current_inputs[role]["supply"],
                "Stock_Level": final_stock, "Weekly_Cost": weekly_cost
            })
            results[role] = res
            
            if role == "Retailer": self.order_delay["Wholesaler"].append(order_decision)
            elif role == "Wholesaler":
                self.order_delay["Distributor"].append(order_decision); self.supply_delay["Retailer"].append(res["Shipment"])
            elif role == "Distributor":
                self.order_delay["Factory"].append(order_decision); self.supply_delay["Wholesaler"].append(res["Shipment"])
            elif role == "Factory":
                self.supply_delay["Distributor"].append(res["Shipment"]); self.supply_delay["Factory"].append(order_decision)
        return results

# --- 세션 초기화 ---
if "chain" not in st.session_state:
    st.session_state.chain = BeerGameChain()
    st.session_state.history = []
    st.session_state.week = 1

# --- 보드판 렌더링 (에러 방지 로직 포함) ---
def render_board(chain, user_role, is_finished=False):
    cols = st.columns(4)
    colors = {"Retailer": "#0056b3", "Wholesaler": "#28a745", "Distributor": "#333", "Factory": "#dc3545"}
    
    for i, role in enumerate(chain.roles):
        node = chain.nodes[role]
        color = colors[role]
        # 게임이 끝나면 모두 공개, 진행 중이면 나만 공개
        is_visible = True if is_finished else (role == user_role)
        
        with cols[i]:
            # Index Error 방지: 마지막 주차 이후에는 리스트 조회를 하지 않음
            if not is_finished:
                display_incoming = f"{CUSTOMER_ORDERS[st.session_state.week-1]}" if role == 'Retailer' else f"{chain.order_delay[role][0]}"
            else:
                display_incoming = "END"

            display_inv = f"{node.inventory if node.backorder == 0 else -node.backorder}" if is_visible else "???"
            display_inc = display_incoming if is_visible else "???"

            st.markdown(f"""
                <div style="border: 4px solid {color if is_visible else '#ddd'}; border-radius: 12px; padding: 20px; text-align: center; background-color: white;">
                    <h2 style="color: {color};">{role.upper()}</h2>
                    <hr>
                    <p>받은 주문: <b style="color:red;">{display_inc}</b></p>
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px;">
                        재고 현황<br><b style="font-size: 2.5em;">{display_inv}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- 메인 화면 ---
st.title("🍺 Beer Game Dashboard")
is_finished = st.session_state.week > MAX_WEEKS

if not is_finished:
    st.sidebar.header("🕹️ PLAY")
    user_role = st.sidebar.radio("역할 선택", ["Retailer", "Wholesaler", "Distributor", "Factory"])
    st.info(f"📅 **Week {st.session_state.week}** / {MAX_WEEKS}")
else:
    st.sidebar.success("🎮 GAME OVER")
    user_role = "Retailer" # 종료 시 기본값

# 보드판 출력
render_board(st.session_state.chain, user_role, is_finished)

st.divider()

if not is_finished:
    # 진행 중 입력창
    with st.expander("이번 주 주문하기", expanded=True):
        order_val = st.number_input(f"{user_role}의 발주량 결정:", min_value=0, value=4)
        if st.button("주문 확정"):
            res = st.session_state.chain.proceed_week(st.session_state.week, user_role, order_val, CUSTOMER_ORDERS[st.session_state.week-1])
            st.session_state.history.append(res)
            st.session_state.week += 1
            st.rerun()
else:
    # 종료 후 분석창
    st.header("📊 공급망 성적표 (Final Results)")
    
    # 데이터 정리
    flat_data = [d for w in st.session_state.history for d in w.values()]
    df = pd.DataFrame(flat_data)
    
    # 1. 비용 요약 테이블
    cost_summary = df.groupby('Role')['Weekly_Cost'].sum().reset_index()
    cost_summary.columns = ['역할', '총 비용 ($)']
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("💰 누적 비용")
        st.table(cost_summary)
        total_chain_cost = cost_summary['총 비용 ($)'].sum()
        st.metric("공급망 전체 비용", f"${total_chain_cost}")
        st.caption("※ 비용 산정 기준: 재고($1/개), 이월주문($2/개)")

    with c2:
        st.subheader("📈 주문 및 재고 추이")
        metric_choice = st.selectbox("그래프 선택", ["C6_Order", "Stock_Level"])
        label = "주문량" if metric_choice == "C6_Order" else "재고 수준"
        
        chart = alt.Chart(df).mark_line(point=True).encode(
            x='Week:O',
            y=alt.Y(f'{metric_choice}:Q', title=label),
            color='Role:N',
            tooltip=['Week', 'Role', metric_choice]
        ).properties(height=350).interactive()
        st.altair_chart(chart, use_container_width=True)

    # 상세 데이터 다운로드
    st.download_button("상세 기록(CSV) 다운로드", df.to_csv(index=False), "beer_game_result.csv")

if st.sidebar.button("게임 리셋"):
    st.session_state.chain = BeerGameChain(); st.session_state.history = []; st.session_state.week = 1; st.rerun()
