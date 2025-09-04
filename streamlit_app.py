import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO

# S3 퍼블릭 URL 설정 (YOUR_BUCKET_NAME과 REGION을 실제 값으로 변경하세요)
S3_BUCKET = "infobip-partner-price"
S3_REGION = "ap-northeast-2"  # 실제 버킷의 리전으로 변경하세요
S3_BASE_URL = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com"

S3_PATH_MOMENTS = f"{S3_BASE_URL}/moments_price.csv"
S3_PATH_CONVERSATIONS = f"{S3_BASE_URL}/conversations_price.csv"
S3_PATH_ANSWERS = f"{S3_BASE_URL}/answers_price.csv"

# S3에서 데이터를 로드하는 함수 (자격 증명 없이)
@st.cache_data
def load_data_from_s3(url):
    """S3 퍼블릭 URL에서 CSV 파일을 읽어 DataFrame으로 반환합니다."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # HTTP 오류가 발생하면 예외를 발생시킵니다.
        
        # StringIO를 사용하여 텍스트 데이터를 파일처럼 다룹니다.
        data = StringIO(response.text)
        df = pd.read_csv(data)
        return df

    except requests.exceptions.RequestException as e:
        st.error(f"S3 URL에서 파일을 불러오는 중 네트워크 오류가 발생했습니다: {url}")
        st.error(f"오류 메시지: {e}")
        return None
    except Exception as e:
        st.error(f"파일을 읽는 중 알 수 없는 오류가 발생했습니다: {url}")
        st.error(f"오류 메시지: {e}")
        return None

# --- 웹페이지 구성 ---
st.title("솔루션 파트너 매입가 계산기 📊")
st.markdown("---")

# 데이터 캐시를 수동으로 지우는 버튼 추가
if st.button("데이터 새로고침 (캐시 비우기)"):
    st.cache_data.clear()
    st.rerun()

# 모든 CSV 파일을 로드합니다.
df_moments = load_data_from_s3(S3_PATH_MOMENTS)
df_conversations = load_data_from_s3(S3_PATH_CONVERSATIONS)
df_answers = load_data_from_s3(S3_PATH_ANSWERS)

if df_moments is not None and df_conversations is not None and df_answers is not None:
    # 사이드바에서 솔루션 선택
    solution_type = st.sidebar.selectbox(
        "솔루션을 선택하세요:",
        ("Moments", "Conversations", "Answers")
    )
    
    st.header(f"{solution_type} 솔루션 계산기")
    
    # --- Moments/Answers 솔루션 로직 ---
    if solution_type in ["Moments", "Answers"]:
        if solution_type == "Moments":
            df = df_moments
            primary_col = 'mep'
            price_eur_col = 'price_eur'
            price_krw_col = 'price_krw'
            price_partner_col = 'price_partner'
            overage_eur_col = 'overage_eur'
            overage_krw_col = 'overage_krw'
            overage_partner_col = 'overage_partner'
        else: # Answers
            df = df_answers
            primary_col = 'mep'
            price_eur_col = 'price_eur'
            price_krw_col = 'price_krw'
            price_partner_col = 'price_partner'
            overage_eur_col = 'overage_eur'
            overage_krw_col = 'overage_krw'
            overage_partner_col = 'overage_partner'

        # 플랜 선택
        plan_options = sorted(df['plan'].unique().tolist())
        selected_plan = st.selectbox("플랜을 선택하세요:", plan_options)
        
        # 필터링
        filtered_df = df[df['plan'] == selected_plan].copy()
        
        if not filtered_df.empty:
            mep_options = sorted(filtered_df[primary_col].unique().tolist())
            
            # 사용자 입력
            input_mep = st.selectbox(f"{selected_plan} 플랜의 기준 MEP를 선택하세요:", mep_options)
            expected_usage = st.number_input(f"예상 사용량을 입력하세요 (기준 MEP 초과분):", min_value=0, value=0)

            if st.button("계산하기"):
                try:
                    # 해당 MEP 값의 행 찾기
                    row = filtered_df[filtered_df[primary_col] == input_mep].iloc[0]
                    
                    # 가격 정보 추출
                    base_price_eur = row[price_eur_col]
                    overage_price_eur = row[overage_eur_col]
                    base_price_krw = row[price_krw_col]
                    overage_price_krw = row[overage_krw_col]
                    base_price_partner = row[price_partner_col]
                    overage_price_partner = row[overage_partner_col]

                    # 총 매입가 계산
                    total_cost_eur = base_price_eur + (expected_usage * overage_price_eur)
                    total_cost_krw = base_price_krw + (expected_usage * overage_price_krw)
                    total_cost_partner = base_price_partner + (expected_usage * overage_price_partner)

                    # 결과 표시
                    st.success("### 계산 결과")
                    result_df = pd.DataFrame({
                        "구분": ["기준 매입가", "예상 오버리지 비용", "총 예상 매입가"],
                        "EUR": [f"{base_price_eur:,.2f}", f"{expected_usage * overage_price_eur:,.2f}", f"{total_cost_eur:,.2f}"],
                        "KRW": [f"{base_price_krw:,.0f}", f"{expected_usage * overage_price_krw:,.0f}", f"{total_cost_krw:,.0f}"],
                        "Partner KRW": [f"{base_price_partner:,.0f}", f"{expected_usage * overage_price_partner:,.0f}", f"{total_cost_partner:,.0f}"]
                    })
                    st.table(result_df)

                except IndexError:
                    st.warning("선택한 플랜과 MEP에 대한 가격 정보를 찾을 수 없습니다. 다시 선택해주세요.")
                except Exception as e:
                    st.error(f"계산 중 오류가 발생했습니다: {e}")
        else:
            st.warning("선택한 플랜의 데이터가 없습니다. 다른 플랜을 선택해주세요.")

    # --- Conversations 솔루션 로직 ---
    elif solution_type == "Conversations":
        df = df_conversations
        price_eur_col = 'price_eur'
        price_krw_col = 'price_krw'
        price_partner_col = 'price_partner'
        
        # 플랜 선택
        plan_options = sorted(df['plan'].unique().tolist())
        selected_plan = st.selectbox("플랜을 선택하세요:", plan_options)
        
        # 필터링
        filtered_df = df[df['plan'] == selected_plan].copy()

        if not filtered_df.empty:
            agent_number = st.number_input("예상 에이전트 수를 입력하세요:", min_value=1, value=1)
            
            if st.button("계산하기"):
                try:
                    # 해당 에이전트 수의 행 찾기
                    if selected_plan == 'Start':
                            row = filtered_df.iloc[0] # Start 플랜은 ALL이므로 첫 행을 가져옴
                    else:
                        row = filtered_df[(filtered_df['agent_min'] <= agent_number) & (filtered_df['agent_max'] >= agent_number)].iloc[0]

                    # 가격 정보 추출
                    base_price_eur = row[price_eur_col]
                    base_price_krw = row[price_krw_col]
                    base_price_partner = row[price_partner_col]
                    
                    # 결과 표시
                    st.success("### 계산 결과")
                    result_df = pd.DataFrame({
                        "구분": ["총 예상 매입가"],
                        "EUR": [f"{base_price_eur:,.2f}"],
                        "KRW": [f"{base_price_krw:,.0f}"],
                        "Partner KRW": [f"{base_price_partner:,.0f}"]
                    })
                    st.table(result_df)
                    st.warning("Conversations의 경우 오버리지 가격 정보가 없어 기본 매입가만 표시됩니다.")
                except IndexError:
                    st.warning("입력한 에이전트 수에 대한 가격 정보를 찾을 수 없습니다. 다시 입력해주세요.")
                except Exception as e:
                    st.error(f"계산 중 오류가 발생했습니다: {e}")
        else:
            st.warning("선택한 플랜의 데이터가 없습니다. 다른 플랜을 선택해주세요.")
else:
    st.warning("S3에서 파일을 불러오지 못했습니다. S3 파일이 퍼블릭으로 설정되었는지 확인해주세요.")
    
    # 디버깅용 URL 표시
    with st.expander("디버깅 정보"):
        st.write("접근하려는 URL들:")
        st.write(f"- Moments: {S3_PATH_MOMENTS}")
        st.write(f"- Conversations: {S3_PATH_CONVERSATIONS}")
        st.write(f"- Answers: {S3_PATH_ANSWERS}")
        st.write("\n브라우저에서 위 URL들이 직접 접근 가능한지 확인해보세요.")
