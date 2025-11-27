# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import openai
from optimize import optimize_keyword_ranks, DEFAULT_SCALE

# Load API key from Streamlit Secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

def parse_user_intent(user_input: str):
    system_prompt = """
    당신은 광고 예산 최적화 도구의 입력 파서를 돕는 AI입니다.
    사용자가 자연어로 입력한 문장을 다음 JSON 형식으로 변환하세요.

    {
        "budget": 숫자 (원 단위),
        "forced_keywords": [키워드 리스트]
    }

    - budget이 없으면 null
    - 강제 키워드가 없으면 빈 배열
    - JSON만 출력하세요.
    """

    completion = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0
    )
    text = completion.choices[0].message.content
    return json.loads(text)

st.title("키워드-순위 최적화 (자연어 버전 포함)")

uploaded_file = st.file_uploader("엑셀 업로드 (.xlsx)", type=["xlsx"])

scale = st.number_input("비용 단위 (DEFAULT_SCALE)", value=DEFAULT_SCALE, step=1000)

natural_input = st.text_area(
    "자연어로 조건을 입력하세요",
    placeholder="예: 예산 2000만원, 국제배송은 1순위 고정"
)

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.dataframe(df.head())

    if st.button("자연어 기반 최적화 실행"):
        try:
            parsed = parse_user_intent(natural_input)
            budget = parsed["budget"]
            forced = parsed["forced_keywords"]

            st.write("🔍 해석 결과:", parsed)

            for kw in forced:
                mask = (df["키워드"] == kw) & (df["순위"] == 1)
                df.loc[mask, ["비용", "클릭"]] = 0

            result, total_cost, total_clicks = optimize_keyword_ranks(
                df, budget, scale
            )

            st.success("최적화 완료!")
            st.dataframe(result)
            st.write(f"총 비용: {total_cost:,} 원")
            st.write(f"총 클릭수: {total_clicks:,}")

        except Exception as e:
            st.error(f"오류: {e}")
