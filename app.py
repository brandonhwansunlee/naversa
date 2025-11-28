# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import openai
# optimize 모듈이 같은 폴더에 있어야 합니다.
from optimize import optimize_keyword_ranks, DEFAULT_SCALE

# Load API key from Streamlit Secrets
# Streamlit Cloud의 Secrets에 OPENAI_API_KEY가 설정되어 있어야 합니다.
openai.api_key = st.secrets["OPENAI_API_KEY"]

def parse_user_intent(user_input: str):
    system_prompt = """
    당신은 광고 예산 최적화 도구의 입력 파서를 돕는 AI입니다.
    사용자가 자연어로 입력한 문장을 다음 JSON 형식으로 변환하세요.

    {
        "budget": 숫자 (원 단위, 없으면 null),
        "forced_keywords": [키워드 리스트 (없으면 빈 배열)]
    }

    반드시 JSON 형식으로만 응답하세요.
    """

    try:
        # Client 인스턴스 생성 (최신 버전 OpenAI 라이브러리 대응)
        client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # [중요] 모델 이름 수정 (gpt-4.1-mini -> gpt-4o-mini)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0,
            response_format={"type": "json_object"} # [중요] JSON 모드 강제
        )
        
        text = completion.choices[0].message.content
        
        # 디버깅을 위해 텍스트가 비어있으면 예외 처리
        if not text:
            raise ValueError("API 응답이 비어있습니다.")

        return json.loads(text)

    except Exception as e:
        # 파싱 중 에러가 나면 원본 텍스트를 확인하기 위해 에러 메시지에 포함
        st.error(f"AI 응답 해석 실패: {e}")
        # 만약 text 변수가 정의되어 있다면 출력 (디버깅용)
        if 'text' in locals():
            st.warning(f"AI가 반환한 원본 텍스트: {text}")
        return {"budget": None, "forced_keywords": []}

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
        # 입력값이 없으면 실행 방지
        if not natural_input.strip():
            st.warning("조건을 입력해주세요.")
        else:
            try:
                parsed = parse_user_intent(natural_input)
                
                # 파싱 결과가 None이거나 에러일 경우 처리
                if not parsed:
                    st.error("조건 해석에 실패했습니다.")
                else:
                    budget = parsed.get("budget") # .get() 사용하여 안전하게 가져오기
                    forced = parsed.get("forced_keywords", [])

                    st.write("🔍 해석 결과:", parsed)

                    # 예산이 null인 경우 처리 (선택 사항)
                    if budget is None:
                        st.info("예산이 설정되지 않았습니다. 기본 로직을 따릅니다.")

                    for kw in forced:
                        # 키워드가 데이터프레임에 있는지 확인
                        if kw in df["키워드"].values:
                            mask = (df["키워드"] == kw) & (df["순위"] == 1)
                            df.loc[mask, ["비용", "클릭"]] = 0
                        else:
                            st.warning(f"경고: '{kw}' 키워드는 엑셀 파일에 없습니다.")

                    result, total_cost, total_clicks = optimize_keyword_ranks(
                        df, budget, scale
                    )

                    st.success("최적화 완료!")
                    st.dataframe(result)
                    st.write(f"총 비용: {total_cost:,.0f} 원") # 천단위 콤마 포맷팅 수정
                    st.write(f"총 클릭수: {total_clicks:,.0f}")

            except Exception as e:
                st.error(f"실행 중 오류 발생: {e}")
