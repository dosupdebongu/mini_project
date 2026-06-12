import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# .env 파일 로드
load_dotenv()

# ----------------------------------------------------
# 1. Pydantic 스키마 수정 (능력치 급변 방지 밸런스 패치)
# ----------------------------------------------------
class StatChange(BaseModel):
    money: int = Field(
        ..., 
        description="돈 변화량. 일반적인 선택은 -10 ~ +10 내외, 리스크가 큰 결정(투자, 대박 등)만 극단적으로 -25 ~ +25 범위 내에서 조절하세요."
    )
    health: int = Field(
        ..., 
        description="체력 변화량. 밤샘이나 과로는 -10 ~ -15, 휴식은 +5 ~ +10 범위 내에서 정밀하게 조절하세요. 절대 한 번에 30 이상 깎지 마세요."
    )
    mental: int = Field(
        ..., 
        description="멘탈 변화량. 일상적 스트레스는 -5 ~ -10, 극심한 충격은 -15 ~ -20 범위 내에서 조절하세요."
    )
    relationship: int = Field(
        ..., 
        description="인간관계 변화량. 전반적인 소통에 따라 -10 ~ +10 범위 내에서 조절하세요."
    )
    career: int = Field(
        ..., 
        description="커리어 변화량. 성장은 +5 ~ +15, 실수나 퇴보는 -5 ~ -10 범위 내에서 조절하세요."
    )
    luck: int = Field(
        ..., 
        description="운 변화량. 상황에 따라 소폭으로 -5 ~ +5 범위 내에서 조절하세요."
    )
class GameTurnResponse(BaseModel):
    result_story: str = Field(..., description="사용자가 고른 선택지에 대한 결과 스토리 (재미있고 실감 나게 기술)")
    stat_change: StatChange = Field(..., description="이번 선택으로 인한 능력치 변화 수치")
    next_event: str = Field(..., description="다음에 벌어질 새로운 상황이나 사건 설명")
    next_choices: List[str] = Field(..., description="사용자가 고를 수 있는 다음 선택지 4개", min_items=4, max_items=4)
    is_ending: bool = Field(..., description="게임이 종료되는 엔딩 조건(성공 혹은 파산/사망 등)에 도달했는지 여부")
    ending_title: Optional[str] = Field(None, description="엔딩인 경우 엔딩의 제목 (예: '벼락부자 CEO', '과로사로 인한 돌연사')")
    ending_description: Optional[str] = Field(None, description="엔딩인 경우 최종 엔딩 스토리 및 요약")

class FinalReportResponse(BaseModel):
    title: str = Field(..., description="이 사람의 인생을 한마디로 요약하는 타이틀 명칭")
    summary: str = Field(..., description="선택 기록들을 바탕으로 복기하는 종합 인생 요약 리포트 (스토리텔링 형식)")
    best_moment: str = Field(..., description="인생의 가장 찬란했던 전성기나 최고의 순간")
    worst_moment: str = Field(..., description="인생의 가장 위태로웠던 위기 순간")

# ----------------------------------------------------
# 2. LLM 초기화
# ----------------------------------------------------
model = ChatOpenAI(model='gpt-4o-mini', temperature=0.8) # 스토리의 다채로움을 위해 0.8 설정
structured_game_model = model.with_structured_output(GameTurnResponse)
structured_report_model = model.with_structured_output(FinalReportResponse)

# ----------------------------------------------------
# 3. Streamlit 화면 기본 설정
# ----------------------------------------------------
st.set_page_config(page_title="인생 선택지 시뮬레이터", layout="wide")
st.title("🌱 선택장애 구출작전: 마이 라이프 (My Life: Choose Wisely) 🌱")
st.caption("당신의 선택이 곧 당신의 인생이 됩니다. 어떤 삶을 살아가시겠습니까?")

# ----------------------------------------------------
# 4. Streamlit session_state (상태 관리) 초기화
# ----------------------------------------------------
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "current_turn" not in st.session_state:
    st.session_state.current_turn = 0
if "stats" not in st.session_state:
    st.session_state.stats = {"money": 50, "health": 50, "mental": 50, "relationship": 50, "career": 10, "luck": 50}
if "history" not in st.session_state:
    st.session_state.history = []
if "current_situation" not in st.session_state:
    st.session_state.current_situation = ""
if "current_choices" not in st.session_state:
    st.session_state.current_choices = []
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "ending_data" not in st.session_state:
    st.session_state.ending_data = None
if "report" not in st.session_state:
    st.session_state.report = None
if "job" not in st.session_state:
    st.session_state.job = ""

# 게임 리셋 함수
def reset_game():
    st.session_state.game_started = False
    st.session_state.current_turn = 0
    st.session_state.stats = {"money": 50, "health": 50, "mental": 50, "relationship": 50, "career": 10, "luck": 50}
    st.session_state.history = []
    st.session_state.current_situation = ""
    st.session_state.current_choices = []
    st.session_state.game_over = False
    st.session_state.ending_data = None
    st.session_state.report = None
    st.session_state.job = ""

st.sidebar.button("🔄 게임 처음부터 다시 시작", on_click=reset_game)
st.sidebar.header("🎭 게임 버전 선택")
game_version = st.sidebar.selectbox(
    "어떤 인생의 분위기를 원하시나요?",
    [
        "🎨 평범한 오리지널 버전 (기본 밸런스)",
        "🖤 매운맛 우울 버전 (냉혹한 현실, 시니컬하고 씁쓸한 전개)",
        "🌈 행복 버전 (모든 게 해피엔딩, 긍정 가득하고 따뜻한 전개)",
        "🎬 막장 드라마 버전 (예상치 못한 출생의 비밀, 배신, 파격적인 반전)"
    ]
)
st.sidebar.header("⏱️ 게임 길이 설정")
# 5턴부터 30턴까지 선택 가능, 기본값은 10턴
max_turns = st.sidebar.slider("목표 인생 턴 수", min_value=5, max_value=30, value=10, step=1)

# 프로프터 주입용 텍스트 정제
version_mode = game_version.split(" ")[1]
# ----------------------------------------------------
# 5. 프롬프트 템플릿 정의
# ----------------------------------------------------
# 다음 턴 생성 프롬프트 (위기/보너스 조건 포함)
turn_prompt = ChatPromptTemplate.from_template(
    "당신은 인생 시뮬레이터 게임의 마스터 AI입니다.\n\n"
    "★ [현재 게임 버전]: {version_mode} ★\n"
    "- '우울 버전'인 경우: 현실은 시니컬하고 잔인합니다. 결과 스토리와 다음 사건을 다소 씁쓸하고 냉혹하게 묘사하세요.\n"
    "- '행복 버전'인 경우: 세상은 따뜻하고 희망찹니다. 결과와 상황을 긍정적이고 유쾌하며 힐링되는 톤으로 묘사하세요.\n"
    "- '막장 드라마 버전'인 경우: 자극적이고 황당무계한 반전(배신, 출생의 비밀, 우연한 대박 등)을 적극적으로 가미하세요.\n\n"
    "[플레이어 정보]\n"
    "- 직업: {job}\n"
    "- 현재 턴수: {turn}번째 선택\n"
    "- 현재 능력치: 돈={money}, 체력={health}, 멘탈={mental}, 인간관계={relationship}, career={career}, luck={luck}\n\n"
    "[이전 상황 및 플레이어의 선택]\n"
    "- 직전 상황: {last_situation}\n"
    "- 플레이어의 선택: {player_choice}\n\n"
    "[시스템 규칙]\n"
    "- 현재 턴수({turn})가 사용자가 지정한 총 목표 턴수({max_turns})에 도달하면, 이번 턴을 끝으로 게임을 종료해야 합니다. 반드시 'is_ending'을 true로 설정하고 감동적이거나 파격적인 최종 엔딩 제목과 설명을 작성하세요.\n\n"
    "위 조건과 현재 게임 버전에 완벽히 부합하는 결과 스토리와 변동 능력치, 다음 상황을 JSON 스키마로 반환하세요."
)

# 최종 요약 리포트 프롬프트
report_prompt = ChatPromptTemplate.from_template(
    "당신은 플레이어의 인생을 정밀 분석하는 커리어/라이프 코치 AI입니다.\n"
    "플레이어가 선택한 직업: {job}\n"
    "최종 능력치: 돈={money}, 체력={health}, 멘탈={mental}, 인간관계={relationship}, 커리어={career}, 운={luck}\n\n"
    "--- 플레이어의 전체 선택 일지 ---\n"
    "{history_text}\n"
    "----------------------------------\n"
    "이 기록을 바탕으로 이 사람의 성향을 분석하고, 인생 요약 리포트를 격조 있고 통찰력 있게 작성해 주세요."
)

# ----------------------------------------------------
# 6. 게임 흐름 제어 로직
# ----------------------------------------------------

# 게임 시작 전: 초기 직업 선택 화면 (개선 과제)
# ----------------------------------------------------
# 6. 게임 흐름 제어 로직 (기존 직업 선택 + 커스텀 직접 입력 하이브리드)
# ----------------------------------------------------

# 게임 시작 전: 직업 선택 또는 직접 입력 화면
# ----------------------------------------------------
# 6. 게임 흐름 제어 로직 (직업 선택 + 커스텀 직접 입력 하이브리드 완벽 패치)
# ----------------------------------------------------

# 게임 시작 전: 직업 선택 또는 직접 입력 화면
if not st.session_state.game_started:
    st.markdown("### 🎭 초기 설정 및 세계관 선택")
    st.write("인생을 시작하기 전, 출발선이 될 직업을 선택해 주세요. 리스트에 없는 나만의 인생을 살고 싶다면 **'✍️ 내가 직접 입력하기'**를 선택하세요.")
    
    # 기본 제공 직업 리스트 및 직접 입력 옵션
    job_choice = st.radio(
        "원하는 직업을 선택하세요:",
        [
            "💻 AI 백엔드 개발자 (시작 능력치: 커리어 우세, 멘탈 취약)", 
            "🚀 스타트업 창업가 (시작 능력치: 돈 부족, 운/커리어 우세)", 
            "🎨 프리랜서 디자이너 (시작 능력치: 인간관계 부족, 자유도 우세)", 
            "🏢 대기업 신입사원 (시작 능력치: 돈 안정적, 체력 급감)",
            "📈 전업 주식 트레이더 (시작 능력치: 돈 변동성 극대, 멘탈 위험)",
            "🎬 100만 구독자 유튜버 (시작 능력치: 돈/인간관계 우세, 멘탈 취약)",
            "☕ 동네 카페 사장님 (시작 능력치: 체력 소진, 인간관계/운 우세)",
            "🎸 무명 인디밴드 보컬 (시작 능력치: 돈 파산 직전, 멘탈/운 우세)",
            "✍️ 내가 직접 입력하기 (AI가 당신이 입력한 키워드로 맞춤형 세계관 생성)"
        ]
    )
    
    # 💡 [패치] '내가 직접 입력하기' 글자가 포함되어 있다면 입력창을 화면에 동적으로 띄웁니다.
    custom_job_input = ""
    if "내가 직접 입력하기" in job_choice:
        custom_job_input = st.text_input(
            "원하는 직업이나 시작 상황을 자유롭게 적어보세요:",
            placeholder="예: 마법 학교 낙제생, 로또 1등 당첨된 백수, 조선시대 무사, 우주정비사 등"
        )
    
    if st.button("🚀 이 인생으로 시작하기", use_container_width=True):
        
        # 1. 💡 [핵심 패치] 사용자가 직접 입력을 선택한 경우 ('in' 키워드로 안전하게 체크)
        if "내가 직접 입력하기" in job_choice:
            if not custom_job_input.strip():
                st.warning("직업이나 상황을 입력해 주세요!")
            else:
                with st.spinner("AI가 당신만을 위한 맞춤형 세계관을 구축하는 중..."):
                    st.session_state.job = custom_job_input.strip()
                    
                    # 유저 입력 전용 초기화 프롬프트
                    init_prompt = ChatPromptTemplate.from_template(
                        "당신은 인생 시뮬레이터 게임의 마스터 AI입니다.\n"
                        "플레이어가 원하는 초기 직업/상황은 다음과 같습니다: [{user_job}]\n\n"
                        "이 조건에 딱 맞는 매우 흥미롭고 몰입감 넘치는 '첫 번째 시작 상황(next_event)'과 "
                        "그 상황에서 유저가 고를 수 있는 '독창적인 선택지 4개(next_choices)'를 작성해 주세요.\n"
                        "시작하는 턴이므로 초기 스탯 변화량(stat_change)은 전부 0으로 채우고, is_ending은 false로 설정하세요."
                    )
                    
                    init_chain = init_prompt | structured_game_model
                    init_response: GameTurnResponse = init_chain.invoke({"user_job": st.session_state.job})
                    
                    # 커스텀 인생은 모든 스탯 50 표준 밸런스로 출발
                    st.session_state.stats = {"money": 50, "health": 50, "mental": 50, "relationship": 50, "career": 10, "luck": 50}
                    st.session_state.current_situation = init_response.next_event
                    st.session_state.current_choices = init_response.next_choices
                    st.session_state.game_started = True
                    st.rerun()
                    
        # 2. 기존에 만들어진 고정 직업 시나리오를 선택한 경우
        else:
            # 괄호 앞의 텍스트만 추출해서 깔끔하게 직업 이름 저장
            st.session_state.job = job_choice.split(" (")[0].strip()
            
            # 이모지 예외 방지를 위해 'in' 키워드로 8개 고정 시나리오 매칭
            if "개발자" in job_choice:
                st.session_state.stats = {"money": 40, "health": 50, "mental": 30, "relationship": 40, "career": 30, "luck": 50}
                initial_situation = "당신은 밤샘 코딩 후 밀려오는 에러 메시지를 마주했습니다. 마침 사수로부터 '주문 API 트랜잭션 처리가 꼬였다'는 슬랙 메시지가 도착합니다."
                initial_choices = ["새벽을 새워서라도 원인을 차분히 분석한다", "모르는 척 슬랙을 읽지 않고 퇴근한다", "옆자리 시니어 개발자에게 기프티콘을 주며 도움을 요청한다", "팀장님에게 찾아가 일단 도망치듯 연차를 쓰겠다고 한다"]
            
            elif "창업가" in job_choice:
                st.session_state.stats = {"money": 15, "health": 50, "mental": 50, "relationship": 40, "career": 25, "luck": 70}
                initial_situation = "투자 유치 발표(IR)를 코앞에 두고 서비스 서버가 마비되었습니다. 팀원들은 전전긍긍하며 당신의 처분만 기다리고 있습니다."
                initial_choices = ["팀원들을 다독이며 밤샘 복구 작업을 지시한다", "투자자에게 전화를 걸어 미팅을 연기해 달라고 솔직히 고한다", "내가 직접 코드를 뜯어보며 원인을 차분히 분석한다", "스트레스로 두통이 몰려와 일단 도망치듯 담배를 피우러 나간다"]
            
            elif "디자이너" in job_choice:
                st.session_state.stats = {"money": 30, "health": 50, "mental": 50, "relationship": 20, "career": 20, "luck": 50}
                initial_situation = "악덕 클라이언트가 마감 당일, 기획을 통째로 뒤엎는 수정 요구를 메일로 보냈습니다. 심지어 단가 인하까지 요구합니다."
                initial_choices = ["전문가답게 요구사항에 맞춰 야근하며 전면 수정한다", "이런 무례한 계약은 파기하겠다며 전화를 걸어 소리친다", "수정 제안서의 모순점을 찾기 위해 원인을 차분히 분석한다", "멘탈이 붕괴되어 노트북을 덮고 일단 도망간다"]
            
            elif "대기업" in job_choice:
                st.session_state.stats = {"money": 50, "health": 30, "mental": 50, "relationship": 50, "career": 15, "luck": 50}
                initial_situation = "첫 출근 주간, 부서 전체 회식이 잡혔습니다. 부장님은 끊임없이 건배사를 요구하며 소맥을 말아주기 시작합니다."
                initial_choices = ["막내답게 분위기를 띄우며 주는 대로 다 마신다", "건강상 이유를 대며 정중하게 사이다만 마시겠다고 도움을 요청한다", "화장실에 간다고 한 뒤 그대로 집에 가기 위해 일단 도망간다", "부장님의 취향과 사내 정치를 차분히 분석하여 대처한다"]
            
            elif "트레이더" in job_choice:
                st.session_state.stats = {"money": 60, "health": 45, "mental": 20, "relationship": 30, "career": 15, "luck": 50}
                initial_situation = "미국 증시 개장 직후, 당신이 전재산의 50%를 레버리지로 태운 기술주가 어닝 쇼크로 15% 폭락하기 시작합니다. 계좌가 녹아내리는 중입니다."
                initial_choices = ["이건 일시적 공포다. 눈을 질질 감고 추가 매수(물타기)를 감행한다", "더 망가지기 전에 지금이라도 전량 손절하고 시장을 탈출한다", "멘탈이 터져 모니터를 끄고 방 구석으로 일단 도망간다", "시장 급락의 거시경제적 원인을 차분히 분석하며 숏(하락) 포지션 스위칭을 고려한다"]
            
            elif "유튜버" in job_choice:
                st.session_state.stats = {"money": 80, "health": 40, "mental": 25, "relationship": 60, "career": 35, "luck": 60}
                initial_situation = "어제 올린 영상 중 과거 발언이 짜깁기되어 커뮤니티에서 폭발적인 '온라인 폭로/저격 사태'가 터졌습니다. 실시간으로 구독자가 몇만 명씩 갈려 나갑니다."
                initial_choices = ["채널에 잘못을 인정하고 진정성 있는 5분짜리 해명 영상을 촬영해 올린다", "잘못이 없으니 허위사실 유포자들을 고소하겠다며 단호한 커뮤니티 공지글을 쓴다", "댓글창을 폐쇄하고 아무 일도 없었다는 듯 며칠간 잠수 타며 일단 도망간다", "여론의 유행과 댓글 민심의 원인을 차분히 분석하여 맞대응 콘텐츠를 기획한다"]
            
            elif "카페" in job_choice:
                st.session_state.stats = {"money": 35, "health": 20, "mental": 50, "relationship": 55, "career": 20, "luck": 50}
                initial_situation = "주말 아침, 오픈 준비를 하는데 메인 에스프레소 머신에서 정체 모를 연기가 나며 고장 났습니다. 10분 뒤면 단체 손님 20명이 들이닥칠 예정입니다."
                initial_choices = ["지인 카페 사장님들에게 연락해 다급하게 도움을 요청한다", "머신 매뉴얼을 펼치고 기계 고장의 원인을 차분히 분석하며 야매로 고쳐본다", "멘탈이 나가 가게 문을 걸어 잠그고 휴업 팻말을 붙인 뒤 일단 도망간다", "단체 손님들에게 양해를 구하고 비싼 드립 커피나 에이드 음료로 우회 유도한다"]
            
            # 마지막 무명 인디밴드는 매칭 예외를 완벽히 막기 위해 else 처리
            else:
                st.session_state.stats = {"money": 5, "health": 45, "mental": 60, "relationship": 40, "career": 10, "luck": 65}
                initial_situation = "다음 주 홍대 클럽 공연을 앞두고 베이스 멤버가 갑자기 '음악을 그만두겠다'며 잠수를 탔습니다. 대관료와 티켓 환불 비용이 머리를 스칩니다."
                initial_choices = ["인맥을 총동원해 대타를 뛰어줄 다른 밴드 세션에게 도움을 요청한다", "이참에 MR을 틀고 갈지, 어쿠스틱 편곡으로 갈지 원인을 차분히 분석하여 공연 형태를 바꾼다", "공연을 취소하고 위약금을 mu는 한이 있더라도 잠적한 멤버를 찾아 일단 도망간다", "밤을 새워서라도 내가 베이스 악보를 외워 베이스와 보컬을 동시에 소화하기로 결심한다"]

            # 세션 바인딩 및 화면 전환
            st.session_state.current_situation = initial_situation
            st.session_state.current_choices = initial_choices
            st.session_state.game_started = True
            st.rerun()

# 게임 진행 중 화면
else:
    # 좌측: 상단 대시보드 및 능력치 판넬 (개선 과제: 수치 시각화)
    st.markdown(f"### 💼 직업: **{st.session_state.job}** | ⏱️ 진행 상황: **{st.session_state.current_turn}턴째 살아가는 중**")
    
    cols = st.columns(6)
    stat_names = {"money": "💰 돈", "health": "💪 체력", "mental": "🧠 멘탈", "relationship": "🤝 인간관계", "career": "📈 커리어", "luck": "🍀 운"}
    for i, (key, value) in enumerate(st.session_state.stats.items()):
        with cols[i]:
            # 위기/보너스 수치 시각적 강조
            if value <= 20:
                st.metric(label=f"{stat_names[key]} (위기!)", value=value, delta="⚠️ 위험")
            elif value >= 80:
                st.metric(label=f"{stat_names[key]} (보너스!)", value=value, delta="🔥 우수")
            else:
                st.metric(label=stat_names[key], value=value)
            st.progress(max(0, min(100, value))) # 0~100 사이로 안전하게 프로그레스바 출력

    st.divider()

    # 게임 진행이 끝나지 않은 경우 상황판 출력
    if not st.session_state.game_over:
        st.markdown(f"#### 🚨 현재 상황")
        st.info(st.session_state.current_situation)
        
        st.markdown("#### 🖐️ 당신의 선택은?")
        
        # 선택지 버튼 4개 배치
        btn_cols = st.columns(2)
        choice_made = None
        
        for idx, choice in enumerate(st.session_state.current_choices):
            with btn_cols[idx % 2]:
                if st.button(f"{idx+1}. {choice}", use_container_width=True, key=f"btn_{idx}"):
                    choice_made = choice

        # 플레이어가 버튼을 클릭했을 때의 이벤트 처리
        if choice_made:
            with st.spinner("당신의 선택으로 미래가 바뀌는 중..."):
                # LLM 연동하여 결과 가져오기
                chain = turn_prompt | structured_game_model
                response: GameTurnResponse = chain.invoke({
                    "version_mode": version_mode,
                    "max_turns": max_turns,
                    "job": st.session_state.job,
                    "turn": st.session_state.current_turn + 1,
                    "money": st.session_state.stats["money"],
                    "health": st.session_state.stats["health"],
                    "mental": st.session_state.stats["mental"],
                    "relationship": st.session_state.stats["relationship"],
                    "career": st.session_state.stats["career"],
                    "luck": st.session_state.stats["luck"],
                    "last_situation": st.session_state.current_situation,
                    "player_choice": choice_made
                })
                
                # 능력치 누적 및 업데이트
                for key in st.session_state.stats.keys():
                    change_val = getattr(response.stat_change, key)
                    st.session_state.stats[key] = max(0, st.session_state.stats[key] + change_val)
                
                # 기록(History) 보관
                st.session_state.history.append({
                    "turn": st.session_state.current_turn + 1,
                    "situation": st.session_state.current_situation,
                    "choice": choice_made,
                    "result": response.result_story,
                    "change": response.stat_change
                })
                
                # 데이터 갱신
                st.session_state.current_turn += 1
                st.session_state.current_situation = response.next_event
                st.session_state.current_choices = response.next_choices
                
                # 엔딩 조건 체크
                if response.is_ending or st.session_state.current_turn >= max_turns:
                    st.session_state.game_over = True
                    st.session_state.ending_data = {
                        "title": response.ending_title if response.ending_title else "예상치 못한 결말",
                        "desc": response.ending_description if response.ending_description else "당신의 여정이 여기서 마무리되었습니다."
                    }
                
                st.rerun()

    # ----------------------------------------------------
    # 7. 엔딩 카드 및 최종 인생 요약 리포트 출력 (개선 과제)
    # ----------------------------------------------------
    else:
        st.error("🏁 게임이 종료되었습니다. 당신이 걸어온 인생의 종착지입니다.")
        
        # 엔딩 카드 출력
        st.markdown(f"## 🃏 엔딩 카드: {st.session_state.ending_data['title']}")
        st.warning(st.session_state.ending_data['desc'])
        
        # 최종 리포트 생성 버튼 생성
        if st.session_state.report is None:
            if st.button("📊 나의 인생 요약 리포트 발급받기", type="primary"):
                with st.spinner("AI가 당신이 내린 모든 결정의 발자취를 추적하고 있습니다..."):
                    # 히스토리 텍스트 변환
                    history_text = ""
                    for h in st.session_state.history:
                        history_text += f"[{h['turn']}턴] 상황: {h['situation']} -> 선택: {h['choice']} -> 결과: {h['result']}\n\n"
                    
                    report_chain = report_prompt | structured_report_model
                    report_res: FinalReportResponse = report_chain.invoke({
                        "job": st.session_state.job,
                        "money": st.session_state.stats["money"],
                        "health": st.session_state.stats["health"],
                        "mental": st.session_state.stats["mental"],
                        "relationship": st.session_state.stats["relationship"],
                        "career": st.session_state.stats["career"],
                        "luck": st.session_state.stats["luck"],
                        "history_text": history_text
                    })
                    st.session_state.report = report_res
                    st.rerun()
        else:
            # 리포트 출력
            st.divider()
            st.markdown(f"### 📋 인생 분석 리포트: <{st.session_state.report.title}>")
            st.info(st.session_state.report.summary)
            
            rep_col1, rep_col2 = st.columns(2)
            with rep_col1:
                st.success(f"🌟 **최고의 순간 (Best)**\n\n{st.session_state.report.best_moment}")
            with rep_col2:
                st.error(f"⚠️ **위기의 순간 (Worst)**\n\n{st.session_state.report.worst_moment}")

        # 여정 로그 펼치기 (기본 구현: 이전 선택 기록 확인)
        with st.expander("🔍 내가 살아온 인생 로그 전체 보기"):
            for h in st.session_state.history:
                st.markdown(f"**[{h['turn']}번째 선택]**")
                st.write(f"• **당면 상황:** {h['situation']}")
                st.write(f"• **내가 한 행동:** :blue[{h['choice']}]")
                st.write(f"• **결과 사건:** {h['result']}")
                st.caption(f"• **수치 변동:** {h['change']}")
                st.markdown("---")