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

# 모든 CSV 파일을 로드합니다.
df_moments_raw = load_data_from_s3(S3_PATH_MOMENTS)
df_conversations = load_data_from_s3(S3_PATH_CONVERSATIONS)
df_answers = load_data_from_s3(S3_PATH_ANSWERS)

# 파일 로드 성공 여부 확인 및 데이터 클린징
if df_moments_raw is not None and df_conversations is not None and df_answers is not None:
    # moments 파일 클린징 로직
    cols_start = ['Plan', 'MEP_Start', 'EUR_Price', 'EUR_Overage', 'KRW_Price', 'KRW_Overage', 'Partner_KRW_Price', 'Partner_KRW_Overage']
    cols_grow = ['Plan', 'MEP_Grow', 'EUR_Price_Grow', 'EUR_Overage_Grow', 'KRW_Price_Grow', 'KRW_Overage_Grow', 'Partner_KRW_Price_Grow', 'Partner_KRW_Overage_Grow']
    cols_scale = ['Plan', 'MEP_Scale', 'EUR_Price_Scale', 'EUR_Overage_Scale', 'KRW_Price_Scale', 'KRW_Overage_Scale', 'Partner_KRW_Price_Scale', 'Partner_KRW_Overage_Scale']
    final_cols = ['Plan', 'MEP', 'EUR_Price', 'EUR_Overage', 'KRW_Price', 'KRW_Overage', 'Partner_KRW_Price', 'Partner_KRW_Overage']

    df_start = df_moments_raw[df_moments_raw['Plan'] == 'Start'].copy()
    df_start = df_start[cols_start]
    df_start.columns = final_cols

    df_grow = df_moments_raw[df_moments_raw['Plan'] == 'Grow'].copy()
    df_grow = df_grow[cols_grow]
    df_grow.columns = final_cols

    df_scale = df_moments_raw[df_moments_raw['Plan'] == 'Scale'].copy()
    df_scale = df_scale[cols_scale]
    df_scale.columns = final_cols

    df_moments = pd.concat([df_start, df_grow, df_scale], ignore_index=True)

    for col in df_moments.columns[1:]:
        df_moments[col] = pd.to_numeric(df_moments[col], errors='coerce')

else:
    # 데이터 로드 실패 시 None으로 설정
    df_moments = None
    df_conversations = None
    df_answers = None

# --- 웹페이지 구성 ---
st.title("솔루션 파트너 매입가 계산기 📊")
st.markdown("---")

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
            primary_col = 'MEP'
            overage_col = 'Partner_KRW_Overage'
            price_col = 'Partner_KRW_Price'
        else: # Answers
            df = df_answers
            primary_col = 'mep'
            overage_col = 'overage_partner'
            price_col = 'price_partner'

        # 플랜 선택
        plan_options = sorted(df['Plan'].unique().tolist())
        selected_plan = st.selectbox("플랜을 선택하세요:", plan_options)
        
        # 필터링
        filtered_df = df[df['Plan'] == selected_plan].copy()
        
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
                    base_price = row[price_col]
                    overage_price = row[overage_col]
                    
                    # 총 매입가 계산
                    total_cost = base_price + (expected_usage * overage_price)

                    # 결과 표시
                    st.success("### 계산 결과")
                    st.metric("기준 매입가", f"{base_price:,.0f} KRW")
                    st.metric("예상 오버리지 비용", f"{expected_usage * overage_price:,.0f} KRW")
                    st.metric("총 예상 매입가", f"{total_cost:,.0f} KRW")
                except IndexError:
                    st.warning("선택한 플랜과 MEP에 대한 가격 정보를 찾을 수 없습니다. 다시 선택해주세요.")
                except Exception as e:
                    st.error(f"계산 중 오류가 발생했습니다: {e}")
        else:
            st.warning("선택한 플랜의 데이터가 없습니다. 다른 플랜을 선택해주세요.")

    # --- Conversations 솔루션 로직 ---
    elif solution_type == "Conversations":
        df = df_conversations
        primary_col = 'Agent'
        price_col = 'price_partner'
        
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
                    base_price = row[price_col]
                    
                    # 결과 표시
                    st.success("### 계산 결과")
                    st.metric("총 예상 매입가", f"{base_price:,.0f} KRW")
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
