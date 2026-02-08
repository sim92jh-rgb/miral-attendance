import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
import io
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import os
import time
import random
import base64
import streamlit.components.v1 as components 

def close_keyboard_focus():
    """
    드롭박스를 확실하게 닫기 위해
    1. 현재 포커스 해제 (blur)
    2. ESC 키 이벤트 전송
    3. 화면 빈 공간 클릭 시뮬레이션
    이 3가지를 동시에 수행합니다.
    """
    components.html(
        """
        <script>
            var doc = window.parent.document;
            
            // Streamlit이 화면을 다 그린 뒤 실행되도록 300ms 대기
            setTimeout(function() {
                var active = doc.activeElement;
                
                if (active) {
                    // 1. 포커스 해제 시도
                    active.blur();
                    
                    // 2. ESC 키 누름 효과 (드롭박스 닫기 명령)
                    var escEvent = new KeyboardEvent('keydown', {
                        key: 'Escape',
                        code: 'Escape',
                        keyCode: 27,
                        bubbles: true,
                        cancelable: true
                    });
                    active.dispatchEvent(escEvent);
                }
                
                // 3. 최후의 수단: 화면의 최상위 body를 강제로 클릭하여 열린 메뉴 닫기
                doc.body.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                doc.body.click();
            }, 300);
        </script>
        """,
        height=0, width=0
    )

# -----------------------------------------------------------------------------
# 1. 환경 설정 및 데이터 준비
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="헬렌켈러 이용자관리",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded" # ⭐ 시작할 때 사이드바 강제 열림 (CSS로 버튼을 숨겨서 고정 효과)
)

COLOR_PRIMARY = "#2E7D32"
SIDEBAR_COLOR = "#2E7D32"

BUSINESS_CATEGORIES = [
    '의사소통기술교육사업', 
    '정보화교육사업', 
    '이동교육사업', 
    '발굴 및 개별화지원사업', 
    '권익옹호 및 인식개선사업', 
    '시청각장애 전문인력 역량강화사업',
    '일상생활 및 사회활동지원사업'
]

# ✅ 성경구절
BIBLE_VERSES = [
    "태초에 하나님이 천지를 창조하시니라 (창세기 1:1)",
    "너는 너의 본토 친척 아비 집을 떠나 내가 네게 지시할 땅으로 가라 (창세기 12:1)",
    "여호와는 나의 목자시니 내게 부족함이 없으리로다 (시편 23:1)",
    "그가 나를 푸른 초장에 누이시며 쉴 만한 물 가로 인도하시는도다 (시편 23:2)",
    "내 영혼을 소생시키시고 자기 이름을 위하여 의의 길로 인도하시는도다 (시편 23:3)",
    "내가 사망의 음침한 골짜기로 다닐지라도 해를 두려워하지 않을 것은 주께서 나와 함께 하심이라 (시편 23:4)",
    "주께서 내 원수의 목전에서 내게 상을 차려 주시고 기름을 내 머리에 부으셨으니 내 잔이 넘치나이다 (시편 23:5)",
    "내 평생에 선하심과 인자하심이 반드시 나를 따르리니 내가 여호와의 집에 영원히 살리로다 (시편 23:6)",
    "너의 행사를 여호와께 맡기라 그리하면 네가 경영하는 것이 이루어지리라 (잠언 16:3)",
    "사람이 마음으로 길을 계획할지라도 그의 걸음을 인도하시는 이는 여호와시니라 (잠언 16:9)",
    "두려워하지 말라 내가 너와 함께 함이라 놀라지 말라 나는 네 하나님이 됨이라 (이사야 41:10)",
    "내가 너를 굳세게 하리라 참으로 너를 도와 주리라 (이사야 41:10)",
    "참으로 나의 의로운 오른손으로 너를 붙들리라 (이사야 41:10)",
    "오직 여호와를 앙망하는 자는 새 힘을 얻으리니 (이사야 40:31)",
    "풀은 마르고 꽃은 시드나 우리 하나님의 말씀은 영원히 서리라 (이사야 40:8)",
    "일어나라 빛을 발하라 이는 네 빛이 이르렀고 여호와의 영광이 네 위에 임하였음이니라 (이사야 60:1)",
    "너희는 세상의 소금이니 소금이 만일 그 맛을 잃으면 무엇으로 짜게 하리요 (마태복음 5:13)",
    "너희는 세상의 빛이라 산 위에 있는 동네가 숨겨지지 못할 것이요 (마태복음 5:14)",
    "이같이 너희 빛이 사람 앞에 비치게 하여 (마태복음 5:16)",
    "구하라 그리하면 너희에게 주실 것이요 찾으라 그리하면 찾아낼 것이요 (마태복음 7:7)",
    "문을 두드리라 그리하면 너희에게 열릴 것이니 (마태복음 7:7)",
    "좁은 문으로 들어가라 멸망으로 인도하는 문은 크고 그 길이 넓어 (마태복음 7:13)",
    "수고하고 무거운 짐 진 자들아 다 내게로 오라 내가 너희를 쉬게 하리라 (마태복음 11:28)",
    "나는 마음이 온유하고 겸손하니 나의 멍에를 메고 내게 배우라 (마태복음 11:29)",
    "사람이 떡으로만 살 것이 아니요 하나님의 입으로부터 나오는 모든 말씀으로 살 것이라 (마태복음 4:4)",
    "하나님이 세상을 이처럼 사랑하사 독생자를 주셨으니 (요한복음 3:16)",
    "이는 그를 믿는 자마다 멸망하지 않고 영생을 얻게 하려 하심이라 (요한복음 3:16)",
    "내 계명은 곧 내가 너희를 사랑한 것 같이 너희도 서로 사랑하라 하는 이것이니라 (요한복음 15:12)",
    "너희가 내 안에 거하고 내 말이 너희 안에 거하면 무엇이든지 원하는 대로 구하라 (요한복음 15:7)",
    "진리를 알지니 진리가 너희를 자유롭게 하리라 (요한복음 8:32)",
    "내가 곧 길이요 진리요 생명이니 나로 말미암지 않고는 아버지께로 올 자가 없느니라 (요한복음 14:6)",
    "평안을 너희에게 끼치노니 곧 나의 평안을 너희에게 주노라 (요한복음 14:27)",
    "너희는 마음에 근심하지도 말고 두려워하지도 말라 (요한복음 14:27)",
    "마음의 즐거움은 양약이라도 심령의 근심은 뼈를 마르게 하느니라 (잠언 17:22)",
    "철이 철을 날카롭게 하는 것 같이 사람이 그의 친구를 빛나게 하느니라 (잠언 27:17)",
    "죽고 사는 것이 혀의 힘에 달렸나니 (잠언 18:21)",
    "믿음은 바라는 것들의 실상이요 보이지 않는 것들의 증거니 (히브리서 11:1)",
    "믿음이 없이는 하나님을 기쁘시게 하지 못하나니 (히브리서 11:6)",
    "예수 그리스도는 어제나 오늘이나 영원토록 동일하시니라 (히브리서 13:8)",
    "사랑은 오래 참고 사랑은 온유하며 시기하지 아니하며 (고린도전서 13:4)",
    "사랑은 자기의 유익을 구하지 아니하며 성내지 아니하며 (고린도전서 13:5)",
    "모든 것을 참으며 모든 것을 믿으며 모든 것을 바라며 모든 것을 견디느니라 (고린도전서 13:7)",
    "그런즉 믿음, 소망, 사랑, 이 세 가지는 항상 있을 것인데 그 중의 제일은 사랑이라 (고린도전서 13:13)",
    "너희 모든 일을 사랑으로 행하라 (고린도전서 16:14)",
    "누구든지 그리스도 안에 있으면 새로운 피조물이라 이전 것은 지나갔으니 보라 새 것이 되었도다 (고린도후서 5:17)",
    "내 은혜가 네게 족하도다 이는 내 능력이 약한 데서 온전하여짐이라 (고린도후서 12:9)",
    "우리가 선을 행하되 낙심하지 말지니 포기하지 아니하면 때가 이르매 거두리라 (갈라디아서 6:9)",
    "오직 성령의 열매는 사랑과 희락과 화평과 오래 참음과 자비와 양선과 충성과 온유와 절제니 (갈라디아서 5:22-23)",
    "너희가 짐을 서로 지라 그리하여 그리스도의 법을 성취하라 (갈라디아서 6:2)",
    "아무 것도 염려하지 말고 다만 모든 일에 기도와 간구로 너희 구할 것을 감사함으로 하나님께 아뢰라 (빌립보서 4:6)",
    "그리하면 모든 지각에 뛰어난 하나님의 평강이 그리스도 예수 안에서 너희 마음과 생각을 지키시리라 (빌립보서 4:7)",
    "내게 능력 주시는 자 안에서 내가 모든 것을 할 수 있느니라 (빌립보서 4:13)",
    "나의 하나님이 그리스도 예수 안에서 영광 가운데 그 풍성한 대로 너희 모든 쓸 것을 채우시리라 (빌립보서 4:19)",
    "항상 기뻐하라 (데살로니가전서 5:16)",
    "쉬지 말고 기도하라 (데살로니가전서 5:17)",
    "범사에 감사하라 이것이 그리스도 예수 안에서 너희를 향하신 하나님의 뜻이니라 (데살로니가전서 5:18)",
    "하나님의 말씀은 살아 있고 활력이 있어 좌우에 날선 어떤 검보다도 예리하며 (히브리서 4:12)",
    "너희 중에 누구든지 지혜가 부족하거든 모든 사람에게 후히 주시고 꾸짖지 아니하시는 하나님께 구하라 (야고보서 1:5)",
    "행함이 없는 믿음은 그 자체가 죽은 것이라 (야고보서 2:17)",
    "하나님은 사랑이심이라 (요한일서 4:8)",
    "사랑 안에 두려움이 없고 온전한 사랑이 두려움을 내쫓나니 (요한일서 4:18)",
    "볼지어다 내가 문 밖에 서서 두드리노니 누구든지 내 음성을 듣고 문을 열면 내가 그에게로 들어가 그와 더불어 먹고 (요한계시록 3:20)",
    "나는 알파와 오메가요 처음과 마지막이라 (요한계시록 22:13)",
    "여호와는 나의 빛이요 나의 구원이시니 내가 누구를 두려워하리요 (시편 27:1)",
    "너는 범사에 그를 인정하라 그리하면 네 길을 지도하시리라 (잠언 3:6)",
    "지혜는 그 얻은 자에게 생명 나무라 지혜를 가진 자는 복되도다 (잠언 3:18)",
    "무릇 지킬만한 것보다 더욱 네 마음을 지키라 생명의 근원이 이에서 남이니라 (잠언 4:23)",
    "여호와를 경외하는 것이 지식의 근본이거늘 미련한 자는 지혜와 훈계를 멸시하느니라 (잠언 1:7)",
    "교만은 패망의 선봉이요 거만한 마음은 넘어짐의 앞잡이니라 (잠언 16:18)",
    "선한 말은 꿀송이 같아서 마음에 달고 뼈에 양약이 되느니라 (잠언 16:24)",
    "마땅히 행할 길을 아이에게 가르치라 그리하면 늙어도 그것을 떠나지 아니하리라 (잠언 22:6)",
    "네 원수가 배고파하거든 먹이고 목말라하거든 마시게 하라 (잠언 25:21)",
    "사람이 친구를 위하여 자기 목숨을 버리면 이보다 더 큰 사랑이 없나니 (요한복음 15:13)",
    "내가 너희를 고아와 같이 버려두지 아니하고 너희에게로 오리라 (요한복음 14:18)",
    "너희는 마음에 근심하지 말라 하나님을 믿으니 또 나를 믿으라 (요한복음 14:1)",
    "온유한 자는 복이 있나니 그들이 땅을 기업으로 받을 것임이요 (마태복음 5:5)",
    "화평하게 하는 자는 복이 있나니 그들이 하나님의 아들이라 일컬음을 받을 것임이요 (마태복음 5:9)",
    "의를 위하여 박해를 받은 자는 복이 있나니 천국이 그들의 것임이라 (마태복음 5:10)",
    "너희는 먼저 그의 나라와 그의 의를 구하라 그리하면 이 모든 것을 너희에게 더하시리라 (마태복음 6:33)",
    "내일 일을 위하여 염려하지 말라 내일 일은 내일이 염려할 것이요 한 날의 괴로움은 그 날로 족하니라 (마태복음 6:34)",
    "비판을 받지 아니하려거든 비판하지 말라 (마태복음 7:1)",
    "무엇이든지 남에게 대접을 받고자 하는 대로 너희도 남을 대접하라 (마태복음 7:12)",
    "나더러 주여 주여 하는 자마다 다 천국에 들어갈 것이 아니요 (마태복음 7:21)",
    "나의 힘이신 여호와여 내가 주를 사랑하나이다 (시편 18:1)",
    "눈물을 흘리며 씨를 뿌리는 자는 기쁨으로 거두리로다 (시편 126:5)",
    "여호와께서 집을 세우지 아니하시면 세우는 자의 수고가 헛되며 (시편 127:1)",
    "호흡이 있는 자마다 여호와를 찬양할지어다 (시편 150:6)",
    "주의 말씀은 내 발에 등이요 내 길에 빛이니이다 (시편 119:105)",
    "젊은이가 무엇으로 그의 행실을 깨끗하게 하리이까 주의 말씀만 지킬 따름이니이다 (시편 119:9)",
    "내가 주께 범죄하지 아니하려 하여 주의 말씀을 내 마음에 두었나이다 (시편 119:11)",
    "고난 당한 것이 내게 유익이라 이로 말미암아 내가 주의 율례들을 배우게 되었나이다 (시편 119:71)",
    "형제가 연합하여 동거함이 어찌 그리 선하고 아름다운고 (시편 133:1)",
    "우리가 알거니와 하나님을 사랑하는 자 곧 그의 뜻대로 부르심을 입은 자들에게는 모든 것이 합력하여 선을 이루느니라 (로마서 8:28)",
    "누가 우리를 그리스도의 사랑에서 끊으리요 환난이나 곤고나 박해나 기근이나 적신이나 위험이나 칼이랴 (로마서 8:35)",
    "너희 몸을 하나님이 기뻐하시는 거룩한 산 제물로 드리라 (로마서 12:1)",
    "소망의 하나님이 모든 기쁨과 평강을 믿음 안에서 너희에게 충만하게 하사 (로마서 15:13)",
    "십자가의 도가 멸망하는 자들에게는 미련한 것이요 구원을 받는 우리에게는 하나님의 능력이라 (고린도전서 1:18)",
    "너희 몸은 너희가 하나님께로부터 받은 바 너희 가운데 계신 성령의 전인 줄을 알지 못하느냐 (고린도전서 6:19)",
    "그런즉 선 줄로 생각하는 자는 넘어질까 조심하라 (고린도전서 10:12)",
    "모든 일을 원망과 시비가 없이 하라 (빌립보서 2:14)",
    "주 안에서 항상 기뻐하라 내가 다시 말하노니 기뻐하라 (빌립보서 4:4)",
    "너희 관용을 모든 사람에게 알게 하라 주께서 가까우시니라 (빌립보서 4:5)",
    "돈을 사랑함이 일만 악의 뿌리가 되나니 (디모데전서 6:10)",
    "오직 너 하나님의 사람아 이것들을 피하고 의와 경건과 믿음과 사랑과 인내와 온유를 따르며 (디모데전서 6:11)",
    "믿음의 선한 싸움을 싸우라 생명을 취하라 (디모데전서 6:12)",
    "모든 성경은 하나님의 감동으로 된 것으로 교훈과 책망과 바르게 함과 의로 교육하기에 유익하니 (디모데후서 3:16)",
    "너는 말씀을 전파하라 때를 얻든지 못 얻든지 항상 힘쓰라 (디모데후서 4:2)"
]

# 🎨 UI/UX 디자인 커스텀 CSS
st.markdown(f"""
<style>
    /* ========================================
       헤더 및 푸터 숨김
       ======================================== */
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    footer {{
        display: none !important;
    }}
    .block-container {{
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
    }}

    /* ========================================
       사이드바 고정 및 스크롤 제거
       ======================================== */
    
    /* 사이드바 접기/펼치기 버튼 숨김 */
    [data-testid="stSidebarCollapseButton"] {{
        display: none !important;
    }}
    [data-testid="stSidebarCollapsedControl"] {{
        display: none !important;
    }}

    /* 사이드바 메인 컨테이너 */
    section[data-testid="stSidebar"] {{
        background-color: {SIDEBAR_COLOR} !important;
        min-width: 250px !important;
        max-width: 350px !important;
        overflow: hidden !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: relative !important;
        z-index: 999999 !important;
        height: 100vh !important;
    }}
    
    /* 사이드바 내부 스크롤바 제거 */
    section[data-testid="stSidebar"] > div {{
        background-color: {SIDEBAR_COLOR} !important;
        overflow: hidden !important;
    }}
    
    /* 사이드바 내부 콘텐츠 여백 최소화 */
    section[data-testid="stSidebar"] .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        margin-top: 0rem !important;
        margin-bottom: 0rem !important;
        overflow: hidden !important;
    }}
    
    /* ========================================
       메뉴 버튼 스타일
       ======================================== */
    
    /* 라디오 버튼 제목 숨김 */
    .stRadio > label {{
        display: none !important;
        height: 0px !important;
        margin: 0px !important;
        visibility: hidden !important;
    }}
    
    /* 동그라미 체크박스 숨김 */
    .stRadio div[role='radiogroup'] > label > div:first-child {{
        display: none !important;
    }}
    
    /* 첫 번째 버튼('메인') 숨김 */
    .stRadio div[role='radiogroup'] > label:nth-child(1) {{
        display: none !important;
    }}

    /* 메뉴 버튼 박스 디자인 */
    .stRadio div[role='radiogroup'] > label {{
        background-color: rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px !important;
        padding: 15px 0px !important;
        margin-bottom: 12px !important;
        transition: all 0.3s ease !important;
        border: none !important;
        width: 200% !important;
        margin-left: 17px !important;
        margin-right: auto !important;
        display: flex !important;
        justify-content: center !important;
        cursor: pointer !important;
    }}
    
    /* 메뉴 버튼 호버 효과 */
    .stRadio div[role='radiogroup'] > label:hover {{
        background-color: rgba(255, 255, 255, 0.4) !important;
        transform: translateX(0px) scale(1.02) !important;
    }}
    
    /* 메뉴 버튼 선택 상태 */
    .stRadio div[role='radiogroup'] > label[data-checked="true"] {{
        background-color: {SIDEBAR_COLOR} !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
    }}
    
    /* 메뉴 텍스트 스타일 */
    .stRadio label p {{
        color: #FFFFFF !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        margin: 0 !important;
    }}

    /* ========================================
       기타 UI 요소
       ======================================== */
    
    /* Streamlit 장식 요소 숨김 */
    [data-testid="stDecoration"] {{
        display: none !important;
    }}
    [data-testid="stToolbar"] {{
        display: none !important;
    }}

    /* ========================================
       우측 하단 GitHub 프로필 & Streamlit 로고 숨김 (추가)
       ======================================== */
    
    /* GitHub 프로필 아바타 숨기기 */
    [data-testid="appCreatorAvatar"] {{
        display: none !important;
    }}

    /* 프로필 프리뷰 전체 컨테이너 숨기기 */
    ._profilePreview_gzau3_63 {{
        display: none !important;
    }}

    /* Streamlit 로고 링크 숨기기 */
    ._link_gzau3_10 {{
        display: none !important;
    }}

    /* 클래스명이 바뀔 수 있으니 보험용 - 프로필 관련 모두 숨김 */
    div[class*="_profilePreview"] {{
        display: none !important;
    }}

    div[class*="_profileImage"] {{
        display: none !important;
    }}

    /* Streamlit 로고 SVG가 포함된 링크 모두 숨김 */
    div[class*="_link_"] svg {{
        display: none !important;
    }}

    /* "Created by" 텍스트가 포함된 모든 요소 숨김 */
    [class*="viewerBadge"] {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        height: 0 !important;
        width: 0 !important;
    }}
    
    /* Streamlit 배지 전체 영역 숨김 */
    div[class*="styles_viewerBadge"] {{
        display: none !important;
    }}
    
    /* iframe 내부의 배지 숨김 */
    iframe[title*="streamlit"] {{
        display: none !important;
    }}
    
    /* footer 영역 안의 모든 하위 요소 숨김 */
    footer * {{
        display: none !important;
    }}
    
    /* 우측 하단 고정 요소 전체 제거 */
    [data-testid="stBottom"] {{
        display: none !important;
    }}
    
    /* GitHub 아바타 이미지 직접 타겟 */
    img[alt="App Creator Avatar"] {{
        display: none !important;
    }}
    
    /* "Hosted with Streamlit" 버튼 */
    a[href*="streamlit.io"] {{
        display: none !important;
    }}

    /* 버전 텍스트 스타일 */
    .version-text {{
        color: #FFFFFF !important;
        font-size: 0.8em !important;
        font-weight: normal !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }}

    /* 메인 제목 상단 라인 */
    section[data-testid="stMain"] h1::before {{
        content: "" !important;
        display: block !important;
        width: 100% !important;
        height: 8px !important;
        background-color: {SIDEBAR_COLOR} !important;
        margin-bottom: 20px !important;
        border-radius: 4px !important;
    }}
    
    /* 기본 버튼 스타일 */
    .stButton > button {{
        background-color: {SIDEBAR_COLOR} !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
    }}

    /* Primary 버튼 스타일 */
    button[kind="primary"] {{
        background-color: {SIDEBAR_COLOR} !important;
        border-color: {SIDEBAR_COLOR} !important;
    }}

    /* Form 제출 버튼 스타일 (기본) */
    [data-testid="stFormSubmitButton"] button {{
        background-color: {SIDEBAR_COLOR} !important;
        border-color: {SIDEBAR_COLOR} !important;
    }}

    .stFormSubmitButton button[kind="primary"] {{
        background-color: {SIDEBAR_COLOR} !important;
        border-color: {SIDEBAR_COLOR} !important;
    }}
    
    /* 정보 라벨 스타일 */
    .info-label {{
        font-size: 0.9em !important;
        color: #666 !important;
        margin-bottom: 0px !important;
    }}
    
    /* 정보 값 스타일 */
    .info-value {{
        font-size: 1.2em !important;
        color: #000 !important;
        font-weight: 500 !important;
        margin-bottom: 10px !important;
    }}
        
    /* Webkit 브라우저 최적화 */
    @supports (-webkit-appearance:none) {{
        section[data-testid="stSidebar"] {{
            -webkit-transform: translateZ(0) !important;
            transform: translateZ(0) !important;
        }}
    }}

    /* ========================================
       이용자 관리 - 수정/삭제 버튼 색상 (수정됨)
       ======================================== */
    
    /* 1. 수정하기 버튼 (뒤에서 2번째 컬럼 = 왼쪽 버튼) */
    [data-testid="stForm"] [data-testid="column"]:nth-last-of-type(2) [data-testid="stFormSubmitButton"] button {{
        background-color: #1E88E5 !important;
        color: white !important;
        border: none !important;
    }}
    [data-testid="stForm"] [data-testid="column"]:nth-last-of-type(2) [data-testid="stFormSubmitButton"] button:hover {{
        background-color: #1565C0 !important;
    }}

    /* 2. 삭제하기 버튼 (뒤에서 1번째 컬럼 = 오른쪽 버튼) */
    [data-testid="stForm"] [data-testid="column"]:nth-last-of-type(1) [data-testid="stFormSubmitButton"] button {{
        background-color: #E53935 !important;
        color: white !important;
        border: none !important;
    }}
    [data-testid="stForm"] [data-testid="column"]:nth-last-of-type(1) [data-testid="stFormSubmitButton"] button:hover {{
        background-color: #C62828 !important;
    }}
    
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 데이터베이스 연결
# -----------------------------------------------------------------------------
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MRKhJYjuTp8dgAOndRzc9b0ztNHGPOMa2rK46Eb9q5E/edit"

@st.cache_resource
def connect_db():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = None
    if os.path.exists("service_account.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    else:
        try:
            if "gcp_service_account" in st.secrets:
                creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
        except:
            pass
    if not creds: return None
    client = gspread.authorize(creds)
    try:
        return client.open_by_url(SHEET_URL)
    except Exception as e:
        return None

def get_worksheet(sh, name):
    if sh is None: return None
    try:
        existing = [ws.title for ws in sh.worksheets()]
        if name in existing:
            return sh.worksheet(name)
        else:
            # 시트가 없으면 새로 생성 (기본 100행, 20열)
            ws = sh.add_worksheet(title=name, rows=100, cols=20)
            
            # [핵심 변경] '==' 대신 'in'을 써야 '_26'이 붙어도 인식합니다!
            
            if "users" in name:
                ws.append_row(["user_id", "name", "birth_date", "gender", "phone", "emergency_contact", "address", "family", "registration date", "is_disabled", "is_beneficiary", "is_seoul_resident", "is_school_age"])
            
            elif "classes" in name:
                ws.append_row(["class_id", "class_name", "business_category", "education_category", "instructor_name", "start_date"])
            
            elif "education_categories" in name:
                ws.append_row(["category_id", "business_category", "category_name", "class_type"])
            
            elif "attendance" in name:
                ws.append_row(["attendance_id", "user_id", "class_id", "attendance_date", "attendance_time"])
            
            # [추가하신 부분] external 시트 헤더 정의
            elif "external" in name:
                # external_id, class_id, 날짜, 시간, 실인원, 연인원
                ws.append_row(["external_id", "class_id", "attendance_date", "attendance_time", "external_member", "external_count"])
            
            return ws
    except Exception as e:
        st.toast(f"⚠️ 구글 시트({name}) 로딩 지연: 잠시 후 다시 시도됩니다.", icon="⏳")
        return None

@st.cache_data(ttl=300)  # 5분간 캐싱
def load_sheet_data(sheet_id):
    """구글 시트 데이터를 캐싱하여 로드"""
    sh = connect_db()
    if not sh:
        return None
    
    ws = None
    try:
        for worksheet in sh.worksheets():
            if worksheet.id == sheet_id:
                ws = worksheet
                break
        
        if ws:
            return pd.DataFrame(ws.get_all_records())
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_cached_users():
    """users 시트 캐싱"""
    sh = connect_db()
    ws = get_worksheet(sh, "users")
    if ws:
        return pd.DataFrame(ws.get_all_records())
    return pd.DataFrame()

@st.cache_data(ttl=300)
def get_cached_attendance(year_suffix):
    """attendance 시트 캐싱"""
    sh = connect_db()
    ws = get_worksheet(sh, f"attendance_{year_suffix}")
    if ws:
        return pd.DataFrame(ws.get_all_records())
    return pd.DataFrame()

@st.cache_data(ttl=300)
def get_cached_classes(year_suffix):
    """classes 시트 캐싱"""
    sh = connect_db()
    ws = get_worksheet(sh, f"classes_{year_suffix}")
    if ws:
        return pd.DataFrame(ws.get_all_records())
    return pd.DataFrame()

@st.cache_data(ttl=300)
def get_cached_external(year_suffix):
    """external 시트 캐싱"""
    sh = connect_db()
    ws = get_worksheet(sh, f"external_{year_suffix}")
    if ws:
        return pd.DataFrame(ws.get_all_records())
    return pd.DataFrame()

@st.cache_data(ttl=300)
def get_cached_edu_categories():
    """education_categories 시트 캐싱"""
    sh = connect_db()
    ws = get_worksheet(sh, "education_categories")
    if ws:
        return pd.DataFrame(ws.get_all_records())
    return pd.DataFrame()
# ========== 여기까지 추가 ==========

# ✅ 로컬 이미지 Base64 인코딩 함수 (HTML 삽입용)
def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        return f"data:image/png;base64,{encoded}"
    return None

# ✅ 날짜/시간 포맷 자동 변환 함수
def format_date_input(val):
    nums = "".join(filter(str.isdigit, val))
    if len(nums) == 8:
        return f"{nums[:4]}/{nums[4:6]}/{nums[6:]}"
    return val

def format_date_short_input(val):
    nums = "".join(filter(str.isdigit, val))
    if len(nums) == 6:
        return f"{nums[:2]}/{nums[2:4]}/{nums[4:]}"
    return val

def format_time_input(val):
    nums = "".join(filter(str.isdigit, val))
    if len(nums) == 4:
        return f"{nums[:2]}:{nums[2:]}"
    return val
# -----------------------------------------------------------------------------
# [추가] 4가지 인원 산출 로직 함수
# -----------------------------------------------------------------------------
def calculate_stat_metrics(df_target):
    if df_target.empty:
        return 0, 0, 0, 0

    # 데이터 복사 (원본 보존)
    temp_df = df_target.copy()
    
    # 날짜 컬럼이 datetime 형식이 아닐 경우 변환
    if not pd.api.types.is_datetime64_any_dtype(temp_df['attendance_date']):
        temp_df['attendance_date'] = pd.to_datetime(temp_df['attendance_date'])

    # 1. 실인원 (이름/ID 기준 고유 인원)
    cnt_real = temp_df['user_id'].nunique()

    # 2. 연인원 (단순 출석 횟수 총합)
    cnt_cumulative = len(temp_df)

    # 3. 과목합산 실인원 (이름 + 과목명 고유 건수)
    # user_id와 class_name이 모두 같은 경우 중복 제거 후 카운트
    cnt_subject_sum = temp_df[['user_id', 'class_name']].drop_duplicates().shape[0]

    # 4. 과목반기합산 실인원 (이름 + 과목명 + 반기 고유 건수)
    # 반기 구분 컬럼 생성 (1~6월: 상반기, 7~12월: 하반기)
    temp_df['half_year'] = temp_df['attendance_date'].dt.month.apply(lambda x: '상반기' if x <= 6 else '하반기')
    # user_id, class_name, half_year가 모두 같은 경우 중복 제거 후 카운트
    cnt_subject_period_sum = temp_df[['user_id', 'class_name', 'half_year']].drop_duplicates().shape[0]

    return cnt_real, cnt_cumulative, cnt_subject_sum, cnt_subject_period_sum

# -----------------------------------------------------------------------------
# 3. 메인 로직
# -----------------------------------------------------------------------------
def main():
    sh = connect_db()
    if not sh:
        st.error("🚨 구글 시트 서버에 연결할 수 없습니다. (503 오류 등)")
        st.warning("잠시 후 페이지를 새로고침(F5) 해주세요.")
        st.stop()

    if 'prev_menu' not in st.session_state:
        st.session_state['prev_menu'] = None

    # 🔄 사이드바 구성
    with st.sidebar:
        # 1. 로고 & 타이틀 박스 (클릭 시 메인으로 이동 - 링크 방식)
        logo_data = get_image_base64("logo.png")
        img_html = f"<img src='{logo_data}' style='width: 60%; margin-bottom: 10px;'>" if logo_data else ""
        
        # ✅ 로고 전체를 <a> 태그로 감싸서 클릭 시 새로고침(메인 이동) 유도
        st.markdown(f"""
        <a href="." target="_self" style="text-decoration: none; color: inherit;">
            <div class="logo-box" style='
                background-color: white; 
                border-radius: 15px; 
                padding: 20px 10px; 
                text-align: center; 
                margin-top: -30px;    
                margin-bottom: 10px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border-bottom: 7px solid {SIDEBAR_COLOR}; 
                width: 100%;
                cursor: pointer;
            '>
                {img_html}
                <p style='
                    color: #555 !important; 
                    margin: 0; 
                    padding-top: 10px; 
                    font-weight: 700; 
                    font-size: 0.7em;
                    line-height: 1.2;
                    display: block;
                    border-top: 1px solid #ccc;
                '>
                    헬렌켈러 시청각장애인 학습지원센터
                </p>
            </div>
        </a>
        """, unsafe_allow_html=True)

        # 2. 메뉴 (라벨 숨김, 메인 페이지 추가)
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        
        # ✅ "메인" 추가 (로고 클릭 시 이 항목이 기본 선택됨)
        menu_items = ["메인", "이용자 조회", "수업 조회", "출석 등록", "운영 현황", "이용자 관리", "수업 관리"]
        menu = st.radio("메뉴", menu_items, label_visibility="collapsed")
        
        # =========================================================
        # [수정] 1단계: 연도 선택 (2025 ~ 현재 연도)
        # =========================================================
                
        # 현재 연도 가져오기 (예: 2026)
        this_year = datetime.now().year
        
        # 2025년부터 올해까지의 리스트 생성 (예: [2025, 2026])
        year_options = list(range(2025, this_year + 1))
        
        # 기본값을 '올해'로 설정하기 위해 리스트의 마지막 인덱스 계산
        default_idx = len(year_options) - 1
        
        # 연도 선택박스
        selected_year = st.selectbox(
            "📅 작업 연도", 
            year_options, 
            index=default_idx,
            label_visibility="collapsed"
        )
        
        # [중요] 선택된 연도의 뒤 2자리만 추출 (예: 2026 -> "26")
        # 이 변수(yy)를 다음 단계(시트 연결)에서 사용합니다.
        yy = str(selected_year)[2:]

        # 3. 버전 정보 (여백 최소화, 흰색 강제)
        st.markdown(
            """
            <div style='text-align: center; margin-top:-89px;'>
                <p class='version-text'>
                    ver.26.02-1
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # -------------------------------------------------------------------------
    # [2단계] 시트 이름 동적 정의 (여기서 시트 이름을 연도별로 확정합니다)
    # -------------------------------------------------------------------------
    # users와 education_categories는 연도 구분 없이 고정
    # 나머지 3개는 뒤에 연도(_26 등)가 붙습니다.
    
    sheet_att = f"attendance_{yy}"  # 결과: attendance_26
    sheet_cls = f"classes_{yy}"     # 결과: classes_26
    sheet_ext = f"external_{yy}"    # 결과: external_26

    # 메뉴 이동 감지 및 로딩
    should_show_loading = False
    if st.session_state['prev_menu'] != menu:
        should_show_loading = True
        st.session_state['prev_menu'] = menu 

    loading_placeholder = st.empty()
    
    if should_show_loading:
        verse = random.choice(BIBLE_VERSES)
        loading_html = f"<div style='position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: #ffffff; z-index: 99999; display: flex; flex-direction: column; align-items: center; justify-content: center; padding-left: 300px;'><h1 style='color: #2E7D32; font-size: 3em; margin-bottom: 5px; font-weight: bold;'>🌿 잠시만 기다려주세요...</h1><div style='width: 550px; height: 8px; background-color: #2E7D32; margin-bottom: 40px; border-radius: 5px;'></div><div style='width: 80%; max-width: 1000px; text-align: center; margin: 0 auto;'><h3 style='color: #555; font-size: 1.5em; font-weight: normal; font-style: italic; line-height: 1.6; word-break: keep-all; white-space: normal;'>\"{verse}\"</h3></div></div>"
        with loading_placeholder.container():
            st.markdown(loading_html, unsafe_allow_html=True)

    def finish_loading():
        if should_show_loading:
            time.sleep(0.5)
            loading_placeholder.empty()
    main_container = st.empty()

    with main_container.container():

        # =========================================================================
        # 0. 메인 페이지 (초기 화면)
        # =========================================================================
        if menu == "메인":        
            
            # 1. 타이틀 영역 (수정됨: h1, h2 태그를 div로 변경하여 링크 제거)
            st.markdown("---")
            
            # 2. 생일 알림 로직
            df_u = get_cached_users()
        
            if not df_u.empty:
                try:
                    # 날짜 처리 준비
                    today = date.today()
                    today_birthdays = []    # (이름, 날짜)
                    upcoming_birthdays = [] # (이름, 날짜, D-Day)
                    past_birthdays = []     # (이름, 날짜)

                    if not df_u.empty and 'birth_date' in df_u.columns:
                        for idx, row in df_u.iterrows():
                            b_str = str(row.get('birth_date', '')).strip()
                            name = row.get('name', '이름없음')
                            
                            # 날짜 파싱 (YYYY/MM/DD 형식에서 숫자만 추출)
                            b_date = None
                            try:
                                nums = "".join(filter(str.isdigit, b_str))
                                if len(nums) == 8:
                                    b_date = date(int(nums[:4]), int(nums[4:6]), int(nums[6:]))
                            except:
                                continue # 날짜 형식이 올바르지 않으면 패스

                            if b_date:
                                try:
                                    # 올해 생일 계산 (올해 연도 + 생일 월/일)
                                    this_year_bday = date(today.year, b_date.month, b_date.day)
                                except ValueError:
                                    # 2월 29일 생일자 등 처리 (올해가 윤년 아니면 28일로)
                                    this_year_bday = date(today.year, 2, 28)

                                # 날짜 차이 계산
                                diff = (this_year_bday - today).days

                                # 연말/연초 보정 (예: 오늘 12/31, 생일 1/1 -> 차이는 -364지만 실제론 내년 +1일)
                                if diff < -300: # 올해 생일이 지났는데 차이가 너무 크면(작년취급) -> 내년 생일로 계산
                                    try:
                                        next_bday = date(today.year + 1, b_date.month, b_date.day)
                                    except:
                                        next_bday = date(today.year + 1, 2, 28)
                                    diff = (next_bday - today).days
                                elif diff > 300: # 내년 생일로 잡혔는데 너무 멀면(내년말) -> 작년 생일로 계산(지난 생일 확인용)
                                    try:
                                        prev_bday = date(today.year - 1, b_date.month, b_date.day)
                                    except:
                                        prev_bday = date(today.year - 1, 2, 28)
                                    diff = (prev_bday - today).days

                                # 화면 표시용 날짜 (MM/DD)
                                bday_display = f"{b_date.month}/{b_date.day}"

                                # 리스트 분류
                                if diff == 0:
                                    today_birthdays.append(f"{name} ({bday_display})")
                                elif 0 < diff <= 14: # 2주 이내 다가오는 생일
                                    upcoming_birthdays.append(f"{name} ({bday_display}, D-{diff})")
                                elif -7 <= diff < 0: # 1주 이내 지난 생일
                                    past_birthdays.append(f"{name} ({bday_display})")
                    
                    # 정렬 (다가오는 생일은 D-Day 순, 지난 생일은 최근 순)
                    upcoming_birthdays.sort(key=lambda x: int(x.split('D-')[1].replace(')', '')))
                    finish_loading()
                    st.markdown(f"""
                    <div style='
                        display: flex; 
                        flex-direction: column; 
                        justify-content: center; 
                        align-items: center; 
                        margin-top: 20px;
                        margin-bottom: 30px;
                        text-align: center;
                    '>
                        <div style='color: {COLOR_PRIMARY}; font-size: 2.5em; font-weight: 800; margin-bottom: 10px;'>
                            밀알복지재단
                        </div>
                        <div style='color: #555; font-size: 1.5em; font-weight: 600;'>
                            헬렌켈러 시청각장애인 학습지원센터
                        </div>
                    </div>
                    """, unsafe_allow_html=True)                
                    
                    # 3. 생일 현황 UI 표시 (3단 컬럼 & 카드 디자인)
                    st.markdown("---")
                    col_b1, col_b2, col_b3 = st.columns(3)

                    # HTML 카드 생성 함수
                    def birthday_card(title, data_list, icon, bg_color, title_color):
                        html_content = f"""
                        <div style='
                            background-color: {bg_color}; 
                            padding: 20px; 
                            border-radius: 12px; 
                            height: 250px; 
                            overflow-y: auto;
                            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                            border: 1px solid rgba(0,0,0,0.05);
                        '>
                            <h4 style='
                                color: {title_color}; 
                                margin-top: 0; 
                                margin-bottom: 15px; 
                                font-weight: 700;
                                border-bottom: 1px solid rgba(0,0,0,0.1); 
                                padding-bottom: 10px;
                                font-size: 1.1em;
                            '>
                                {icon} {title}
                            </h4>
                            <ul style='list-style-type: none; padding-left: 0; margin: 0; color: #333;'>
                        """
                        if data_list:
                            for item in data_list:
                                html_content += f"<li style='margin-bottom: 8px; font-weight: 500; font-size: 1em;'>• {item}</li>"
                        else:
                            html_content += f"<li style='color: #999; font-size: 0.9em; font-style: italic;'>없습니다</li>"
                        
                        html_content += "</ul></div>"
                        return html_content

                    with col_b1:
                        st.markdown(birthday_card(f"오늘 생일 ({today.strftime('%m/%d')})", today_birthdays, "🎂", "#FFF8E1", "#F57F17"), unsafe_allow_html=True)
                    
                    with col_b2:
                        st.markdown(birthday_card("다가오는 생일 (2주)", upcoming_birthdays, "🎉", "#E8F5E9", "#2E7D32"), unsafe_allow_html=True)
                    
                    with col_b3:
                        st.markdown(birthday_card("지난 생일 (1주)", past_birthdays, "🎁", "#F5F5F5", "#616161"), unsafe_allow_html=True)

                except Exception as e:
                    finish_loading()                
                    st.error(f"생일 정보를 불러오는 중 문제가 발생했습니다.")
                    # st.error(e) # 디버깅 시 주석 해제

        # =========================================================================
        # 1. 이용자 조회
        # =========================================================================
        elif menu == "이용자 조회":
            df_u = get_cached_users()
            df_a = get_cached_attendance(yy)
            df_c = get_cached_classes(yy)
        
            if df_u.empty or df_a.empty or df_c.empty:
                finish_loading()
                st.warning("데이터를 불러올 수 없습니다.")
                st.stop()
            
            st.title("🔍 이용자 조회")
            
            if not df_u.empty:
                search_name = st.text_input("조회할 이용자의 이름을 입력하고, 엔터를 눌러주세요", placeholder="예: 홍길동")
                
                finish_loading()

                if search_name:
                    found_users = df_u[df_u['name'].astype(str).str.contains(search_name)]
                    
                    if found_users.empty:
                        st.warning("검색된 이용자가 없습니다.")
                    else:
                        user_opts = [f"{row['name']} ({str(row['user_id'])})" for i, row in found_users.iterrows()]
                        selected_user_str = st.selectbox("이용자를 선택하세요", user_opts)
                        
                        if selected_user_str:
                            target_user_id = selected_user_str.split('(')[-1].replace(')', '')
                            
                            df_u['user_id'] = df_u['user_id'].astype(str)
                            user_info = df_u[df_u['user_id'] == target_user_id].iloc[0]
                            
                            st.markdown("---")
                            st.markdown("### 👤 이용자 상세 정보")
                            with st.container():
                                st.markdown(f"<h2 style='margin-bottom: 5px; color:#2E7D32;'>{user_info['name']} 님</h2>", unsafe_allow_html=True)
                                
                                def info_html(label, value):
                                    return f"""
                                    <div style='margin-bottom: 10px; background-color: #f5f5f5; padding: 10px; border-radius: 8px;'>
                                        <span style='color: grey; font-size: 0.9em;'>{label}</span>
                                        <br>
                                        <span style='color: black; font-size: 1.2em; font-weight: 500;'>{value if value else '-'}</span>
                                    </div>
                                    """

                                fam_val = user_info.get('family', '')
                                fam_txt = fam_val if fam_val else "해당없음"

                                c1, c2, c3 = st.columns(3)
                                c1.markdown(info_html("생년월일", user_info.get('birth_date', '-')), unsafe_allow_html=True)
                                c2.markdown(info_html("성별", user_info.get('gender', '-')), unsafe_allow_html=True)
                                c3.markdown(info_html("최초등록일", user_info.get('registration date', '-')), unsafe_allow_html=True)                            
                                                                                    
                                c4, c5, c6 = st.columns(3)
                                c4.markdown(info_html("연락처", user_info.get('phone', '-')), unsafe_allow_html=True)
                                c5.markdown(info_html("보호자", user_info.get('family', '-')), unsafe_allow_html=True)
                                c6.markdown(info_html("보호자 연락처", user_info.get('emergency_contact', '-')), unsafe_allow_html=True)                            
                                
                                
                                c7 = st.columns(1)[0]
                                c7.markdown(info_html("주소", user_info.get('address', '-')), unsafe_allow_html=True)
                                

                                flags = []
                                if str(user_info.get('is_disabled')).upper() == "TRUE": flags.append("장애")
                                if str(user_info.get('is_beneficiary')).upper() == "TRUE": flags.append("수급자")
                                if str(user_info.get('is_seoul_resident')).upper() == "TRUE": flags.append("서울거주")
                                if str(user_info.get('is_school_age')).upper() == "TRUE": flags.append("학령기")
                                flag_str = ", ".join(flags) if flags else "특이사항 없음"
                                
                                st.markdown(f"""
                                <div style='margin-bottom: 10px; background-color: #f5f5f5; padding: 10px; border-radius: 8px;'>
                                    <span style='color: grey; font-size: 0.9em;'>특이사항</span>
                                    <br>
                                    <span style='color: black; font-size: 1.2em; font-weight: 500;'>{flag_str}</span>
                                </div>
                                """, unsafe_allow_html=True)

                            st.markdown("---")

                            if not df_a.empty and not df_c.empty:
                                df_a['user_id'] = df_a['user_id'].astype(str)
                                user_attend = df_a[df_a['user_id'] == target_user_id].copy()
                                
                                if user_attend.empty:
                                    st.info("아직 출석 등록이 없습니다.")
                                else:
                                    df_c['class_id'] = df_c['class_id'].astype(str)
                                    user_attend['class_id'] = user_attend['class_id'].astype(str)
                                    merged_df = user_attend.merge(df_c, on='class_id', how='left')
                                    
                                    merged_df['attendance_date'] = pd.to_datetime(merged_df['attendance_date'])
                                    merged_df = merged_df.sort_values(by=['attendance_date', 'attendance_time'], ascending=False)

                                    st.subheader("📋 수강 이력 조회")
                                    fc1, fc2 = st.columns([1, 2])
                                    
                                    month_options = ["전체"] + [f"{i}월" for i in range(1, 13)]
                                    sel_month = fc1.selectbox("월별 조회", month_options)
                                    
                                    range_input = fc2.text_input("기간 상세 조회 (YYMMDD~YYMMDD)", placeholder="예: 240101~240228")
                                    
                                    filtered_df = merged_df.copy()
                                    
                                    if range_input and '~' in range_input:
                                        try:
                                            start_s, end_s = range_input.split('~')
                                            start_dt = datetime.strptime(start_s.strip(), "%y%m%d")
                                            end_dt = datetime.strptime(end_s.strip(), "%y%m%d")
                                            filtered_df = filtered_df[
                                                (filtered_df['attendance_date'] >= start_dt) & 
                                                (filtered_df['attendance_date'] <= end_dt)
                                            ]
                                        except:
                                            st.error("기간 형식이 올바르지 않습니다.")
                                    
                                    elif sel_month != "전체":
                                        target_month = int(sel_month.replace("월", ""))
                                        filtered_df = filtered_df[filtered_df['attendance_date'].dt.month == target_month]

                                    display_cols = ['attendance_date', 'attendance_time', 'class_name', 'instructor_name', 'business_category', 'education_category']
                                    existing_cols = [c for c in display_cols if c in filtered_df.columns]
                                    
                                    display_df = filtered_df[existing_cols].copy()
                                    display_df.rename(columns={
                                        'attendance_date': '출석 날짜', 
                                        'attendance_time': '출석 시간', 
                                        'class_name': '수업명',
                                        'instructor_name': '강사명',
                                        'business_category': '사업 구분',
                                        'education_category': '교육 구분'
                                    }, inplace=True)
                                    
                                    if '출석 날짜' in display_df.columns:
                                        display_df['출석 날짜'] = display_df['출석 날짜'].dt.strftime('%Y-%m-%d')
                                    
                                    st.caption(f"총 {len(display_df)}건의 기록이 있습니다.")
                                    # 엑셀 다운로드 버튼
                                    import io
                                    excel_buffer = io.BytesIO()
                                    display_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                                    excel_buffer.seek(0)

                                    st.download_button(
                                        label="📥 엑셀 다운로드",
                                        data=excel_buffer,
                                        file_name=f"{user_info['name']}_수강이력.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )    
                                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                            else:
                                st.info("출석 또는 수업 데이터가 아직 없습니다.")
            else:
                finish_loading()
                st.warning("등록된 이용자가 없습니다.")

        # =========================================================================
        # 1-2. 수업 조회 (외부수업/내부수업 분기 처리 적용)
        # =========================================================================
        elif menu == "수업 조회":
            # 1. 필요한 모든 시트 로드
            df_u = get_cached_users().astype(str)
            df_a = get_cached_attendance(yy).astype(str)
            df_c = get_cached_classes(yy).astype(str)
            df_edu = get_cached_edu_categories().astype(str)
            df_ext = get_cached_external(yy).astype(str)
        
            finish_loading()

            # [추가] 초록색 카드 디자인 함수
            def style_metric_card(label, value):
                return f"""
                <div style="background-color: #E8F5E9; padding: 15px; border-radius: 12px; border: 1px solid #C8E6C9; text-align: center;">
                    <p style="margin:0; color: #555; font-size: 0.9em; font-weight: bold;">{label}</p>
                    <h3 style="margin: 5px 0; color: #2E7D32; font-weight: 800;">{value}</h3>
                </div>
                """

            st.title("📚 수업 조회")

            if not df_c.empty:
                # -----------------------------------------------------------------
                # [A] 수업 검색 및 선택
                # -----------------------------------------------------------------
                search_class = st.text_input("조회할 수업명을 입력하고 엔터를 눌러주세요", placeholder="예: 점자")
                finish_loading()

                if search_class:
                    found_classes = df_c[df_c['class_name'].str.contains(search_class)]

                    if found_classes.empty:
                        st.warning("검색된 수업이 없습니다.")
                    else:
                        class_opts = [f"{row['class_name']} - {row['instructor_name']} ({row['class_id']})" for i, row in found_classes.iterrows()]
                        selected_class_str = st.selectbox("수업을 선택하세요", class_opts)

                        if selected_class_str:
                            target_class_id = selected_class_str.split('(')[-1].replace(')', '')
                            
                            # 수업 상세 정보 가져오기
                            class_info = df_c[df_c['class_id'] == target_class_id].iloc[0]
                            edu_cat_name = class_info['education_category']
                            
                            # -----------------------------------------------------
                            # [B] 수업 유형 판별 (내부 vs 외부)
                            # -----------------------------------------------------
                            class_type = "내부수업" # 기본값
                            if not df_edu.empty:
                                edu_match = df_edu[df_edu['category_name'] == edu_cat_name]
                                if not edu_match.empty:
                                    class_type = edu_match.iloc[0]['class_type']

                            # -----------------------------------------------------
                            # [C] 수업 정보 표시 (공통)
                            # -----------------------------------------------------
                            st.markdown("---")
                            st.markdown("### 📖 수업 상세 정보")
                            
                            # 배지 표시
                            if class_type == "외부수업":
                                st.markdown(f"<span style='background-color:#FFF3E0; color:#EF6C00; padding:4px 8px; border-radius:4px; font-weight:bold;'>🚩 외부수업</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<span style='background-color:#E8F5E9; color:#2E7D32; padding:4px 8px; border-radius:4px; font-weight:bold;'>🏠 내부수업</span>", unsafe_allow_html=True)
                            
                            def info_html(label, value):
                                return f"""
                                <div style='margin-bottom: 10px; background-color: #f5f5f5; padding: 10px; border-radius: 8px;'>
                                    <span style='color: grey; font-size: 0.9em;'>{label}</span><br>
                                    <span style='color: black; font-size: 1.2em; font-weight: 500;'>{value if value else '-'}</span>
                                </div>
                                """

                            c1, c2, c3, c4 = st.columns(4)
                            c1.markdown(info_html("강사명", class_info.get('instructor_name', '-')), unsafe_allow_html=True)
                            c2.markdown(info_html("사업구분", class_info.get('business_category', '-')), unsafe_allow_html=True)
                            c3.markdown(info_html("교육구분", class_info.get('education_category', '-')), unsafe_allow_html=True)
                            c4.markdown(info_html("강의 시작일", class_info.get('start_date', '-')), unsafe_allow_html=True)

                            st.markdown("---")

                            # -----------------------------------------------------
                            # [D] 데이터 조회 로직 (분기 처리)
                            # -----------------------------------------------------
                            
                            # === CASE 1: 외부수업 ===
                            if class_type == "외부수업":
                                st.subheader("📋 수강 내역 조회")
                                
                                # 해당 수업의 외부 데이터 필터링
                                target_ext_df = df_ext[df_ext['class_id'] == target_class_id].copy()
                                
                                if target_ext_df.empty:
                                    st.info("등록된 외부 수업 일지가 없습니다.")
                                else:
                                    # 날짜 형변환
                                    target_ext_df['attendance_date'] = pd.to_datetime(target_ext_df['attendance_date'])
                                    target_ext_df = target_ext_df.sort_values(by='attendance_date', ascending=False)
                                    
                                    # 필터링 UI (월별 / 기간별)
                                    fc1, fc2 = st.columns([1, 2])
                                    month_options = ["전체"] + [f"{i}월" for i in range(1, 13)]
                                    sel_month = fc1.selectbox("월별 조회", month_options)
                                    range_input = fc2.text_input("기간 상세 조회 (YYMMDD~YYMMDD)", placeholder="예: 240101~240228")
                                    
                                    # 필터링 적용
                                    filtered_df = target_ext_df.copy()
                                    if range_input and '~' in range_input:
                                        try:
                                            start_s, end_s = range_input.split('~')
                                            start_dt = datetime.strptime(start_s.strip(), "%y%m%d")
                                            end_dt = datetime.strptime(end_s.strip(), "%y%m%d")
                                            filtered_df = filtered_df[
                                                (filtered_df['attendance_date'] >= start_dt) & 
                                                (filtered_df['attendance_date'] <= end_dt)
                                            ]
                                        except:
                                            st.error("기간 형식이 올바르지 않습니다.")
                                    elif sel_month != "전체":
                                        target_month = int(sel_month.replace("월", ""))
                                        filtered_df = filtered_df[filtered_df['attendance_date'].dt.month == target_month]
                                    
                                    # 통계 계산 (외부실인원/외부연인원 합계)
                                    # 주의: 문자열로 저장되어 있을 수 있으므로 숫자로 변환
                                    filtered_df['external_member'] = pd.to_numeric(filtered_df['external_member'], errors='coerce').fillna(0)
                                    filtered_df['external_count'] = pd.to_numeric(filtered_df['external_count'], errors='coerce').fillna(0)
                                    
                                    total_mem = filtered_df['external_member'].sum()
                                    total_cnt = filtered_df['external_count'].sum()
                                    
                                    # 통계 표시
                                    # [수정] 통계 표시 (초록색 배경 적용)
                                m1, m2 = st.columns(2)
                                with m1: 
                                    st.markdown(style_metric_card("외부수업 실인원 합계", f"{int(total_mem)}명"), unsafe_allow_html=True)
                                with m2: 
                                    st.markdown(style_metric_card("외부수업 연인원 합계", f"{int(total_cnt)}명"), unsafe_allow_html=True)
                                    
                                st.markdown("<br>", unsafe_allow_html=True)
                                    
                                # 표 표시용 컬럼 정리
                                display_df = filtered_df[['attendance_date', 'attendance_time', 'external_member', 'external_count']].copy()
                                display_df.columns = ['날짜', '시간', '외부수업 실인원', '외부수업 연인원']
                                display_df['날짜'] = display_df['날짜'].dt.strftime('%Y-%m-%d')
                                    
                                # 엑셀 다운로드
                                import io
                                excel_buffer = io.BytesIO()
                                display_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                                st.download_button(
                                    label="📥 엑셀 다운로드",
                                    data=excel_buffer.getvalue(),
                                    file_name=f"{class_info['class_name']}_외부일지.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                                    
                                st.dataframe(display_df, use_container_width=True, hide_index=True)

                            # === CASE 2: 내부수업 (기존 로직 유지) ===
                            else:
                                st.subheader("📋 수강 내역 조회")
                                
                                class_attend = df_a[df_a['class_id'] == target_class_id].copy()

                                if class_attend.empty:
                                    st.info("아직 출석 등록이 없습니다.")
                                else:
                                    merged_df = class_attend.merge(df_u, on='user_id', how='left')
                                    merged_df['class_name'] = class_info['class_name'] # 통계 함수용
                                    
                                    merged_df['attendance_date'] = pd.to_datetime(merged_df['attendance_date'])
                                    merged_df = merged_df.sort_values(by=['attendance_date', 'attendance_time'], ascending=False)

                                    # 필터링 UI
                                    fc1, fc2 = st.columns([1, 2])
                                    month_options = ["전체"] + [f"{i}월" for i in range(1, 13)]
                                    sel_month = fc1.selectbox("월별 조회", month_options)
                                    range_input = fc2.text_input("기간 상세 조회 (YYMMDD~YYMMDD)", placeholder="예: 240101~240228")

                                    filtered_df = merged_df.copy()

                                    if range_input and '~' in range_input:
                                        try:
                                            start_s, end_s = range_input.split('~')
                                            start_dt = datetime.strptime(start_s.strip(), "%y%m%d")
                                            end_dt = datetime.strptime(end_s.strip(), "%y%m%d")
                                            filtered_df = filtered_df[
                                                (filtered_df['attendance_date'] >= start_dt) & 
                                                (filtered_df['attendance_date'] <= end_dt)
                                            ]
                                        except:
                                            st.error("기간 형식이 올바르지 않습니다.")
                                    elif sel_month != "전체":
                                        target_month = int(sel_month.replace("월", ""))
                                        filtered_df = filtered_df[filtered_df['attendance_date'].dt.month == target_month]

                                    # 4가지 인원 통계 (함수 활용)
                                    c_real, c_cum, c_sub, c_sub_per = calculate_stat_metrics(filtered_df)
                                    
                                    # 통계 카드 표시
                                    def style_metric(label, value, sub_text):
                                        return f"""
                                        <div style="background-color: #E8F5E9; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #C8E6C9;">
                                            <p style="margin:0; color: #555; font-size: 0.9em; font-weight: bold;">{label}</p>
                                            <h3 style="margin: 5px 0; color: #2E7D32; font-weight: 800;">{value}</h3>
                                            <p style="margin:0; color: #888; font-size: 0.75em;">{sub_text}</p>
                                        </div>
                                        """
                                    m1, m2, m3, m4 = st.columns(4)
                                    with m1: st.markdown(style_metric("실인원", f"<span style='margin-left: 20px;'>{c_real}명</span>", "순수 이용자 수"), unsafe_allow_html=True)
                                    with m2: st.markdown(style_metric("연인원", f"<span style='margin-left: 20px;'>{c_cum}명</span>", "총 출석 횟수"), unsafe_allow_html=True)
                                    with m3: st.markdown(style_metric("과목구분 실인원", f"<span style='margin-left: 20px;'>{c_sub}명</span>", "동일인이라도 수강과목이 다르면 따로 집계"), unsafe_allow_html=True)
                                    with m4: st.markdown(style_metric("과목반기구분 실인원", f"<span style='margin-left: 20px;'>{c_sub_per}명</span>", "수강과목, 기간(반기)이 다르면 따로 집계"), unsafe_allow_html=True)

                                    st.markdown("<br>", unsafe_allow_html=True)

                                    # 표 표시
                                    display_cols = ['attendance_date', 'attendance_time', 'name', 'gender', 'is_disabled', 'is_school_age', 'registration date']
                                    existing_cols = [c for c in display_cols if c in filtered_df.columns]
                                    display_df = filtered_df[existing_cols].copy()

                                    # 표 데이터 가공 (신규/기존, 장애/비장애 등 한글화)
                                    current_year = datetime.now().year
                                    def check_new_user(reg_date):
                                        try:
                                            nums = "".join(filter(str.isdigit, str(reg_date)))
                                            if len(nums) >= 4 and int(nums[:4]) == current_year: return '신규'
                                        except: pass
                                        return '기존'

                                    if 'registration date' in display_df.columns:
                                        display_df['registration date'] = display_df['registration date'].apply(check_new_user)
                                    if 'is_disabled' in display_df.columns:
                                        display_df['is_disabled'] = display_df['is_disabled'].apply(lambda x: '장애' if str(x).upper() == 'TRUE' else '비장애')
                                    if 'is_school_age' in display_df.columns:
                                        display_df['is_school_age'] = display_df['is_school_age'].apply(lambda x: '학령기' if str(x).upper() == 'TRUE' else '성인기')

                                    display_df.rename(columns={
                                        'attendance_date': '출석 날짜', 'attendance_time': '출석 시간', 'name': '이용자명',
                                        'gender': '성별', 'is_disabled': '장애', 'is_school_age': '학령기', 'registration date': '신규'
                                    }, inplace=True)

                                    if '출석 날짜' in display_df.columns:
                                        display_df['출석 날짜'] = display_df['출석 날짜'].dt.strftime('%Y-%m-%d')

                                    # 엑셀 다운로드
                                    import io
                                    excel_buffer = io.BytesIO()
                                    display_df.to_excel(excel_buffer, index=False, engine='openpyxl')
                                    st.download_button(
                                        label="📥 엑셀 다운로드",
                                        data=excel_buffer.getvalue(),
                                        file_name=f"{class_info['class_name']}_수강자목록.xlsx",
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                                    st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                st.warning("등록된 수업이 없습니다.")  

    # =========================================================================
        # 2. 출석 등록 (이용자 선택 시 자동 닫힘 제거, 연속 선택 가능)
        # =========================================================================
        elif menu == "출석 등록":
            # [초기 설정] Session State
            # 수업 선택용 키는 유지 (하나 고르면 딱 닫히는 게 깔끔하므로)
            if "att_cls_key" not in st.session_state:
                st.session_state.att_cls_key = 0
            if "att_cls_val" not in st.session_state:
                st.session_state.att_cls_val = []
                
            # [수정] 이용자 선택용 키/값 저장소는 제거함 (일반적인 멀티셀렉트로 복귀)

            # [CSS] 드롭박스 높이 제한 & 태그 색상
            st.markdown(
                """
                <style>
                ul[data-testid="stSelectboxVirtualDropdown"],
                ul[data-testid="stMultiSelectVirtualDropdown"] {
                    max-height: 150px !important;
                }
                span[data-baseweb="tag"] {
                    background-color: var(--primary-color) !important;
                    color: black !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # 데이터 로드
            ws_u = get_worksheet(sh, "users")
            ws_c = get_worksheet(sh, sheet_cls)
            ws_edu = get_worksheet(sh, "education_categories") 
            ws_a = get_worksheet(sh, sheet_att)
            ws_ext = get_worksheet(sh, sheet_ext)

            if None in [ws_u, ws_c, ws_edu, ws_a, ws_ext]:
                finish_loading()
                st.error("구글 시트 로드 실패.")
                st.stop()
                
            st.title("✅ 출석등록")
            
            df_u = pd.DataFrame(ws_u.get_all_records()).astype(str)
            df_c = pd.DataFrame(ws_c.get_all_records()).astype(str)
            df_edu = pd.DataFrame(ws_edu.get_all_records()).astype(str)

            finish_loading()

            # ---------------------------------------------------------------------
            # [UI Fragment] 입력창 부분만 따로 렌더링
            # ---------------------------------------------------------------------
            @st.fragment
            def render_attendance_ui():
                if df_u.empty or df_c.empty:
                    st.warning("이용자와 수업을 먼저 등록하세요.")
                    return

                # -----------------------------------------------------------------
                # [A] 수업 선택 (단일 선택이므로 자동 닫힘 유지)
                # -----------------------------------------------------------------
                current_cls = st.multiselect(
                    "1. 수업명", 
                    options=df_c['class_name'].unique(),
                    placeholder="수업명을 입력하거나 선택하세요",
                    key=f"cls_w_{st.session_state.att_cls_key}", 
                    default=st.session_state.att_cls_val
                )

                # 수업은 1개만 선택하면 자동으로 닫히게 처리 (깔끔함 유지)
                if len(current_cls) > 1:
                    st.session_state.att_cls_val = [current_cls[-1]]
                    st.session_state.att_cls_key += 1
                    st.rerun()
                elif len(current_cls) == 1 and current_cls != st.session_state.att_cls_val:
                    st.session_state.att_cls_val = current_cls
                    st.session_state.att_cls_key += 1
                    st.rerun()

                if not st.session_state.att_cls_val:
                    st.info("👆 수업을 먼저 선택해주세요.")
                    return 

                sel_class_name = st.session_state.att_cls_val[0]
                
                # 2. 강사명 선택
                filtered_classes = df_c[df_c['class_name'] == sel_class_name]
                instructor_list = filtered_classes['instructor_name'].unique()
                sel_instructor = st.selectbox("2. 강사명", instructor_list)
                
                # 상세 정보
                target_class_row = filtered_classes[filtered_classes['instructor_name'] == sel_instructor].iloc[0]
                real_class_id = target_class_row['class_id']
                edu_cat_name = target_class_row['education_category']
                
                # 3. 수업 유형 판별
                class_type = "내부수업"
                if not df_edu.empty:
                    edu_match = df_edu[df_edu['category_name'] == edu_cat_name]
                    if not edu_match.empty:
                        class_type = edu_match.iloc[0]['class_type']

                if class_type == "외부수업":                
                    st.markdown(f"<div style='margin-left: 50px; margin-top: -180px;'><span style='background-color:#FFF3E0; color:#EF6C00; padding:4px 8px; border-radius:4px; font-size:0.8em; font-weight:bold;'>🚩 외부수업 </span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='margin-left: 50px; margin-top: -180px;'><span style='background-color:#E8F5E9; color:#2E7D32; padding:4px 8px; border-radius:4px; font-size:0.8em; font-weight:bold;'>🏠 내부수업 </span></div>", unsafe_allow_html=True)

                # -----------------------------------------------------------------
                # [B] 상세 입력
                # -----------------------------------------------------------------
                
                sel_users = []
                ext_member_cnt = 0
                ext_total_cnt = 0
                
                if class_type == "내부수업":
                    
                    user_opts = [f"{r['name']} ({str(r['user_id'])})" for i, r in df_u.iterrows()]
                    
                    # [수정] 일반적인 Multiselect로 변경 (자동 닫힘 제거)
                    # 이제 선택해도 드롭박스가 닫히지 않고 연속 선택이 가능합니다.
                    sel_users = st.multiselect(
                        "이용자명", 
                        options=user_opts,
                        placeholder="예: 홍길동",
                        key="attendance_user_select" # 고정 키 사용
                    )
                    
                    st.markdown("---")

                # -----------------------------------------------------------------
                # [C] 폼 입력
                # -----------------------------------------------------------------
                with st.form("attendance_form"):
                    st.write("📝 날짜 및 시간 입력")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    
                    now_date_str = datetime.now().strftime("%y%m%d")
                    now_time_start = "10:00"
                    now_time_end = "12:00"
                    
                    input_date = col_d1.text_input("출석 일자 (YYMMDD)", value="", placeholder=f"예: {now_date_str}")
                    input_start_time = col_d2.text_input("시작 시간 (HH:MM)", value="", placeholder=f"예: {now_time_start}")
                    input_end_time = col_d3.text_input("종료 시간 (HH:MM)", value="", placeholder=f"예: {now_time_end}")

                    if class_type == "외부수업":
                        st.markdown("<br>", unsafe_allow_html=True)
                        c_ext1, c_ext2 = st.columns(2)
                        ext_member_cnt = c_ext1.number_input("외부 실인원 (명)", min_value=0, step=1)
                        ext_total_cnt = c_ext2.number_input("외부 연인원 (명)", min_value=0, step=1)

                    st.markdown("<br>", unsafe_allow_html=True)
                    submitted = st.form_submit_button("등록하기", type="primary", use_container_width=True)

                    if submitted:
                        # 1. [검증] 시간 입력값이 비어있는지 먼저 확인 (수정됨)
                        # 하나라도 비어있으면 경고를 띄우고 함수를 종료(return)해서 밑으로 못 가게 막습니다.
                        if not input_start_time or not input_end_time:
                            st.warning("⚠️ 출석 시간을 입력해주세요.")
                            return 
                        
                        # 2. 날짜/시간 포맷팅
                        # 날짜: 입력이 없으면 오늘 날짜(now_date_str)를 그대로 씁니다 (이건 유지)
                        final_date = format_date_short_input(input_date) if input_date else now_date_str
                        
                        # [수정된 부분] 시간: 위에서 입력 여부를 확인했으니, 'else' 없이 바로 변환합니다.
                        final_start = format_time_input(input_start_time)
                        final_end = format_time_input(input_end_time)
                        
                        # ---------------------------------------------------------
                        # 아래부터는 기존 저장 로직과 동일
                        # ---------------------------------------------------------
                        save_date_str = ""
                        try:
                            date_nums = "".join(filter(str.isdigit, final_date))
                            if len(date_nums) == 6:
                                save_date_str = datetime.strptime(date_nums, "%y%m%d").strftime("%Y-%m-%d")
                            else:
                                st.error(f"날짜 형식이 올바르지 않습니다. ({final_date})")
                                return
                        except ValueError:
                            st.error("날짜 형식이 올바르지 않습니다.")
                            return
                        
                        save_time_str = f"{final_start} ~ {final_end}"

                        # 저장 실행 (외부/내부 분기)
                        if class_type == "외부수업":
                            if ext_member_cnt == 0 and ext_total_cnt == 0:
                                st.warning("인원수를 입력해주세요.")
                            else:
                                new_ext_id = f"EXT{int(time.time())}"
                                ws_ext.append_row([
                                    new_ext_id, real_class_id, save_date_str, save_time_str, 
                                    int(ext_member_cnt), int(ext_total_cnt)
                                ])
                                st.toast(f"🚩 외부수업 등록 완료! (실인원 {ext_member_cnt}명)", icon="✅")
                                time.sleep(1)
                                st.rerun()
                                
                        else:
                            if not sel_users:
                                st.error("참여자를 최소 1명 이상 선택해주세요.")
                            else:
                                rows = []
                                for u_str in sel_users:
                                    try:
                                        target_uid = u_str.split('(')[-1].replace(')', '')
                                    except:
                                        target_uid = ""
                                    
                                    if target_uid:
                                        rows.append([f"A{int(time.time())}_{random.randint(100,999)}", target_uid, real_class_id, save_date_str, save_time_str])
                                
                                if rows:
                                    ws_a.append_rows(rows)
                                    # 저장 성공 시 선택 값 초기화
                                    st.session_state.att_cls_val = [] 
                                    st.session_state.att_cls_key += 1
                                    
                                    st.toast(f"🏠 내부수업 {len(rows)}명 등록 완료!", icon="✅")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("이용자 ID를 찾을 수 없습니다.")

            # [실행]
            render_attendance_ui()

        # =========================================================================
        # 3. 운영 현황 (대대적 개편: 세부 통계, 누적 비교, 그래프 시각화)
        # =========================================================================
        elif menu == "운영 현황":
            st.title("📊 운영 현황")
        
            df_u = get_cached_users()
            df_c = get_cached_classes(yy)
            df_a = get_cached_attendance(yy)
            df_ext = get_cached_external(yy)
            df_edu = get_cached_edu_categories()
        
            finish_loading()
        
            if not df_u.empty and not df_c.empty and not df_a.empty:

                if not df_a.empty and not df_c.empty and not df_u.empty:
                    # 데이터 타입 통일
                    df_u['user_id'] = df_u['user_id'].astype(str)
                    df_a['user_id'] = df_a['user_id'].astype(str)
                    df_a['class_id'] = df_a['class_id'].astype(str)
                    df_c['class_id'] = df_c['class_id'].astype(str)
                    df_a['attendance_date'] = pd.to_datetime(df_a['attendance_date'])
                    df_ext['external_count'] = pd.to_numeric(df_ext['external_count'], errors='coerce').fillna(0)
                    df_ext['external_member'] = pd.to_numeric(df_ext['external_member'], errors='coerce').fillna(0)
                    df_ext['class_id'] = df_ext['class_id'].astype(str)
                    df_ext_merged = df_ext.merge(df_c[['class_id', 'business_category', 'education_category']], on='class_id', how='left')

                    # 메인 병합 데이터프레임 (출석 + 수업 + 이용자)
                    df_m = df_a.merge(df_c, on='class_id', how='left').merge(df_u, on='user_id', how='left')
                    
                    # -------------------------------------------------------------
                    # [0] 종합 인원 집계 (기존 유지)
                    # -------------------------------------------------------------
                    st.markdown("### 📈 종합 인원 집계")
                    c_real, c_cum, c_sub, c_sub_per = calculate_stat_metrics(df_m)

                    def style_metric(label, value, sub_text):
                        return f"""
                        <div style="background-color: #E8F5E9; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #C8E6C9; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                            <p style="margin:0; color: #555; font-size: 0.9em; font-weight: bold;">{label}</p>
                            <h3 style="margin: 5px 0; color: #2E7D32; font-weight: 800; padding-left: 20px;">{value}</h3>
                            <p style="margin:0; color: #888; font-size: 0.75em;">{sub_text}</p>
                        </div>
                        """

                    m1, m2, m3, m4 = st.columns(4)
                    with m1: st.markdown(style_metric("① 실인원", f"{c_real:,}명", "순수 이용자 수"), unsafe_allow_html=True)
                    with m2: st.markdown(style_metric("② 연인원", f"{c_cum:,}명", "총 출석 횟수"), unsafe_allow_html=True)
                    with m3: st.markdown(style_metric("③ 과목구분 실인원", f"{c_sub:,}명", "동일인이라도 수강과목이 다르면 따로 집계"), unsafe_allow_html=True)
                    with m4: st.markdown(style_metric("④ 과목반기구분 실인원", f"{c_sub_per:,}명", "수강과목, 기간(반기)이 다르면 따로 집계"), unsafe_allow_html=True)
                    
                    st.markdown("---")

                    # 엑셀 다운로드용 헬퍼 함수 (import io 필요)
                    import io
                    def make_excel_download(df_in, file_label):
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_in.to_excel(writer, index=False)
                        return st.download_button(
                            label=f"📥 {file_label} 엑셀 다운로드",
                            data=output.getvalue(),
                            file_name=f"{file_label}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    # -------------------------------------------------------------
                    # [1] 대분류(business_category)별 인원수 4가지
                    # -------------------------------------------------------------
                    st.subheader("1. 사업구분(대분류)별 인원 현황")
                    
                    biz_stats = []
                    # 데이터에 있는 사업구분만 추출하거나, 미리 정의된 카테고리 전체를 순회
                    unique_biz = sorted(df_m['business_category'].dropna().unique())
                    
                    # [수정] 1. 사업구분별 현황 로직 교체
                    biz_stats = []
                    # df_m에 없는 사업구분이라도 외부수업에는 있을 수 있으므로 전체 목록 사용
                    for biz in BUSINESS_CATEGORIES:
                        # 1) 내부 데이터 계산
                        sub_df = df_m[df_m['business_category'] == biz]
                        r, c, s, sp = calculate_stat_metrics(sub_df)
                        
                        # 2) 외부 데이터 계산 (아까 만든 df_ext_merged 활용)
                        sub_ext = df_ext_merged[df_ext_merged['business_category'] == biz]
                        ext_r = sub_ext['external_member'].sum() # 외부 실인원 합계
                        ext_c = sub_ext['external_count'].sum()  # 외부 연인원 합계
                        
                        # 데이터가 하나라도 있으면 리스트에 추가 (내부/외부 모두 0이면 제외하고 싶으면 if문 추가 가능)
                        # 여기서는 0이라도 표시되도록 함
                        biz_stats.append({
                            "사업구분": biz, 
                            "실인원": r + ext_r,       # 내부 + 외부
                            "연인원": c + ext_c,       # 내부 + 외부
                            "과목구분실인원": s + ext_r,     # 내부 과목합산 + 외부 실인원(단순합산)
                            "과목반기구분실인원": sp + ext_r # 내부 과목반기 + 외부 실인원(단순합산)
                        })
                    
                    # [수정] 1번 표 출력 (열 넓이 균등 설정)
                    df_biz_stats = pd.DataFrame(biz_stats)
                    st.dataframe(
                        df_biz_stats, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "사업구분": st.column_config.Column(width="small"),
                            "실인원": st.column_config.Column(width="small"),
                            "연인원": st.column_config.Column(width="small"),
                            "과목구분실인원": st.column_config.Column(width="small"),
                            "과목반기구분실인원": st.column_config.Column(width="small")
                        }
                    )
                    make_excel_download(df_biz_stats, "사업구분별_인원현황")
                    
                    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

                    # -------------------------------------------------------------
                    # [2] 분류(category_name)별 인원수 4가지
                    # -------------------------------------------------------------
                    st.subheader("2. 교육구분(중분류)별 인원 현황")
                    
                    edu_stats = []
                    unique_edu = sorted(df_m['education_category'].dropna().unique()) # 혹은 education_category 컬럼명 확인
                    unique_edu_all = df_edu['category_name'].unique() if not df_edu.empty else []

                    for edu in unique_edu_all:
                        # 1) 내부 데이터 계산
                        sub_df = df_m[df_m['education_category'] == edu]
                        r, c, s, sp = calculate_stat_metrics(sub_df)
                        
                        # 2) 외부 데이터 계산
                        sub_ext = df_ext_merged[df_ext_merged['education_category'] == edu]
                        ext_r = sub_ext['external_member'].sum()
                        ext_c = sub_ext['external_count'].sum()
                        
                        # 상위 사업구분명 찾기 (df_edu에서 조회)
                        parent_biz = "-"
                        match_row = df_edu[df_edu['category_name'] == edu]
                        if not match_row.empty:
                            parent_biz = match_row.iloc[0]['business_category']
                        
                        edu_stats.append({
                            "사업구분": parent_biz, 
                            "교육구분": edu, 
                            "실인원": r + ext_r,       # 합산
                            "연인원": c + ext_c,       # 합산
                            "과목구분실인원": s + ext_r,     # 합산
                            "과목반기구분실인원": sp + ext_r # 합산
                        })
                        
                    df_edu_stats = pd.DataFrame(edu_stats)
                    st.dataframe(
                        df_edu_stats, 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            "사업구분": st.column_config.Column(width="small"),
                            "교육구분": st.column_config.Column(width="small"),
                            "실인원": st.column_config.Column(width="small"),
                            "연인원": st.column_config.Column(width="small"),
                            "과목구분실인원": st.column_config.Column(width="small"),
                            "과목반기구분실인원": st.column_config.Column(width="small")
                        }
                    )
                    make_excel_download(df_edu_stats, "교육구분별_인원현황")

                    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

                    # -------------------------------------------------------------
                    # [3] 장애/비장애/기타 별 인원수 4가지
                    # -------------------------------------------------------------
                    st.subheader("3. 장애 유형별 인원 현황")
                    
                    # 장애 유형 컬럼 생성 (기타 포함 로직)
                    # 현재는 TRUE/FALSE만 있지만, 추후 확장성을 위해 처리
                    def get_disability_type(val):
                        val_str = str(val).strip().upper()
                        if val_str == "TRUE": return "장애"
                        elif val_str == "FALSE": return "비장애"
                        else: return "기타"
                    
                    df_m['disability_status'] = df_m['is_disabled'].apply(get_disability_type)
                    
                    dis_stats = []
                    unique_dis = ["장애", "비장애", "기타"] # 순서 고정
                    
                    for d_type in unique_dis:
                        sub_df = df_m[df_m['disability_status'] == d_type]
                        if sub_df.empty and d_type == "기타": continue # 기타가 없으면 생략 가능
                        
                        r, c, s, sp = calculate_stat_metrics(sub_df)
                        dis_stats.append({
                            "구분": d_type, "실인원": r, "연인원": c, "과목구분실인원": s, "과목반기구분실인원": sp
                        })
                        
                    df_dis_stats = pd.DataFrame(dis_stats)
                    st.dataframe(df_dis_stats, use_container_width=True, hide_index=True)
                    make_excel_download(df_dis_stats, "장애유형별_인원현황")

                    st.markdown("---")

                    # -------------------------------------------------------------
                    # [4] 월말 기준 누적 실인원 수 비교
                    # -------------------------------------------------------------
                    st.subheader("4. 월말 기준 누적 실인원 상세 비교")
                    
                    months = [f"{i}월" for i in range(1, 13)]
                    col_sel, col_empty = st.columns([1, 3])
                    target_month_str = col_sel.selectbox("기준 월 선택", months, index=datetime.now().month - 1)
                    
                    target_month = int(target_month_str.replace("월", ""))
                    
                    # [로직] 선택한 월의 '말일'까지 출석한 기록이 있는 모든 고유 이용자 추출
                    # 1. 날짜 필터링
                    current_year_val = datetime.now().year
                    # 해당 월의 마지막 날짜 계산이 복잡하므로, 그냥 해당 월에 포함되거나 이전인 데이터 필터링
                    filtered_m = df_m[df_m['attendance_date'].dt.month <= target_month]
                    
                    # 2. 고유 ID 추출 (이게 누적 실인원)
                    active_user_ids = filtered_m['user_id'].unique()
                    
                    # 3. 해당 ID들의 상세 정보만 뽑아서 분석용 DF 생성 (User Info merge 된 df_m 활용하되 중복 제거)
                    # df_m은 출석 건수만큼 행이 있으므로, user_id로 drop_duplicates 해야 사람 기준이 됨
                    df_active_users = df_m[df_m['user_id'].isin(active_user_ids)].drop_duplicates(subset=['user_id']).copy()
                    
                    if df_active_users.empty:
                        st.warning(f"{target_month_str}까지의 실인원 데이터가 없습니다.")
                    else:
                        st.info(f"📅 **{target_month_str}말 기준** 누적 실인원: **{len(df_active_users)}명**")
                        
                        # 분석을 위한 전처리
                        # 성별
                        df_active_users['gender_clean'] = df_active_users['gender'].apply(lambda x: x if x in ['남', '여'] else '기타')
                        # 장애여부 (위에서 만든 disability_status 사용)
                        # 학령기여부
                        def get_age_type(val):
                            return "학령기" if str(val).upper() == "TRUE" else "성인기"
                        df_active_users['age_type'] = df_active_users['is_school_age'].apply(get_age_type)
                        # 신규/기존 여부
                        def get_reg_type(reg_date):
                            try:
                                # 숫자만 추출해서 연도 확인
                                nums = "".join(filter(str.isdigit, str(reg_date)))
                                if len(nums) >= 4:
                                    year = int(nums[:4])
                                    return "신규" if year == current_year_val else "기존"
                            except:
                                pass
                            return "기존" # 날짜 없으면 보통 기존으로 간주하거나 예외처리
                        df_active_users['reg_type'] = df_active_users['registration date'].apply(get_reg_type)

                        # ---------------------------------------------------------
                        # 4-a ~ 4-f 테이블 생성 함수 (Pivot Table 활용)
                        # ---------------------------------------------------------
                        def make_crosstab(index_col, columns_col, index_name, col_name_map):
                            ct = pd.crosstab(df_active_users[index_col], df_active_users[columns_col])
                            # 없는 컬럼도 0으로 채워서 보여주기 위해 reindex
                            for expected_col in col_name_map.keys():
                                if expected_col not in ct.columns:
                                    ct[expected_col] = 0
                            # 컬럼 순서 정렬 및 이름 변경
                            ct = ct[list(col_name_map.keys())].rename(columns=col_name_map)
                            # 인덱스 이름 설정
                            ct.index.name = index_name
                            # 합계 컬럼 추가
                            ct['합계'] = ct.sum(axis=1)
                            return ct.reset_index()

                        t1, t2 = st.columns(2)
                        
                        with t1:
                            st.markdown("**a. 성별 × 장애유형 (실인원)**")
                            df_a_tbl = make_crosstab('gender_clean', 'disability_status', '성별', {'장애':'장애', '비장애':'비장애', '기타':'기타'})
                            st.dataframe(df_a_tbl, use_container_width=True, hide_index=True)
                            make_excel_download(df_a_tbl, f"{target_month}월_성별_장애유형_실인원")

                        with t2:
                            st.markdown("**b. 성별 × 생애주기 (실인원)**")
                            df_b_tbl = make_crosstab('gender_clean', 'age_type', '성별', {'학령기':'학령기', '성인기':'성인기'})
                            st.dataframe(df_b_tbl, use_container_width=True, hide_index=True)
                            make_excel_download(df_b_tbl, f"{target_month}월_성별_생애주기_실인원")

                        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                        t3, t4 = st.columns(2)

                        # 기존인원 / 신규인원 필터링
                        df_existing = df_active_users[df_active_users['reg_type'] == '기존']
                        df_new = df_active_users[df_active_users['reg_type'] == '신규']

                        # 헬퍼 함수 재정의 (df_in 파라미터 추가)
                        def make_crosstab_sub(df_in, index_col, col_target, idx_name, col_map):
                            if df_in.empty:
                                return pd.DataFrame(columns=[idx_name] + list(col_map.values()) + ['합계'])
                            ct = pd.crosstab(df_in[index_col], df_in[col_target])
                            for k in col_map.keys():
                                if k not in ct.columns: ct[k] = 0
                            ct = ct[list(col_map.keys())].rename(columns=col_map)
                            ct.index.name = idx_name
                            ct['합계'] = ct.sum(axis=1)
                            return ct.reset_index()

                        with t3:
                            st.markdown("**c. 기존인원 중 장애/비장애 (실인원)**")
                            # 기존인원은 '성별' 구분 언급이 없으므로, 그냥 전체 합계만 보여주거나 성별로 나누거나 해야 함.
                            # 요청사항: "기존인원 중 장애, 비장애 실인원 구분" -> 표 형태가 모호하므로 '성별'을 행으로 두겠습니다.
                            df_c_tbl = make_crosstab_sub(df_existing, 'gender_clean', 'disability_status', '성별(기존)', {'장애':'장애', '비장애':'비장애'})
                            st.dataframe(df_c_tbl, use_container_width=True, hide_index=True)
                            make_excel_download(df_c_tbl, f"{target_month}월_기존_장애비장애")

                        with t4:
                            st.markdown("**d. 기존인원 중 학령기/성인기 (실인원)**")
                            df_d_tbl = make_crosstab_sub(df_existing, 'gender_clean', 'age_type', '성별(기존)', {'학령기':'학령기', '성인기':'성인기'})
                            st.dataframe(df_d_tbl, use_container_width=True, hide_index=True)
                            make_excel_download(df_d_tbl, f"{target_month}월_기존_생애주기")

                        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                        t5, t6 = st.columns(2)

                        with t5:
                            st.markdown("**e. 신규인원 중 장애/비장애 (실인원)**")
                            df_e_tbl = make_crosstab_sub(df_new, 'gender_clean', 'disability_status', '성별(신규)', {'장애':'장애', '비장애':'비장애'})
                            st.dataframe(df_e_tbl, use_container_width=True, hide_index=True)
                            make_excel_download(df_e_tbl, f"{target_month}월_신규_장애비장애")

                        with t6:
                            st.markdown("**f. 신규인원 중 학령기/성인기 (실인원)**")
                            df_f_tbl = make_crosstab_sub(df_new, 'gender_clean', 'age_type', '성별(신규)', {'학령기':'학령기', '성인기':'성인기'})
                            st.dataframe(df_f_tbl, use_container_width=True, hide_index=True)
                            make_excel_download(df_f_tbl, f"{target_month}월_신규_생애주기")

                    st.markdown("---")

                    # -------------------------------------------------------------
                    # [그래프 섹션] 5 ~ 8
                    # -------------------------------------------------------------
                    st.subheader("📊 월별 추이 그래프")
                    
                    # 그래프용 데이터 집계 (1월 ~ 12월)
                    monthly_stats = []
                    
                    # 누적 계산을 위한 변수
                    prev_cum_real = 0
                    
                    # 1월부터 12월까지 순회
                    for m in range(1, 13):
                        # 해당 월까지의 데이터 (누적용)
                        mask_cum = df_m['attendance_date'].dt.month <= m
                        df_cum = df_m[mask_cum]
                        
                        # 해당 월 단독 데이터 (증가분용)
                        mask_mon = df_m['attendance_date'].dt.month == m
                        df_mon = df_m[mask_mon]
                        
                        # 5. 월누적 실인원 (Cumulative Real)
                        cum_real = df_cum['user_id'].nunique() if not df_cum.empty else 0
                        
                        # 6. 월별 실인원 증가 (Increase Real) 
                        # 정의: 전월 대비 누적 실인원 증가량 (순수 신규 유입)
                        real_increase = cum_real - prev_cum_real
                        prev_cum_real = cum_real
                        
                        # 7. 월누적 연인원 (Cumulative Visits)
                        cum_visits = len(df_cum)
                        
                        # 8. 월별 신규 연인원 증가 (Monthly Visits)
                        # 정의: 해당 월에 발생한 출석 건수
                        mon_visits = len(df_mon)
                        
                        monthly_stats.append({
                            "월": f"{m}월",
                            "누적 실인원": cum_real,
                            "실인원 증가": real_increase,
                            "누적 연인원": cum_visits,
                            "월별 연인원": mon_visits
                        })
                    
                    df_graph = pd.DataFrame(monthly_stats)
                    
                    # 그래프 그리기 (2개씩 배치)
                    g1, g2 = st.columns(2)
                    with g1:
                        st.markdown("**5. 월 누적 실인원**")
                        fig5 = px.bar(df_graph, x="월", y="누적 실인원", text_auto=True, color_discrete_sequence=['#4CAF50'])
                        st.plotly_chart(fig5, use_container_width=True)
                        
                    with g2:
                        st.markdown("**6. 월별 실인원 증가 (순수 신규 유입)**")
                        fig6 = px.bar(df_graph, x="월", y="실인원 증가", text_auto=True, color_discrete_sequence=['#81C784'])
                        st.plotly_chart(fig6, use_container_width=True)
                        
                    g3, g4 = st.columns(2)
                    with g3:
                        st.markdown("**7. 월 누적 연인원**")
                        fig7 = px.bar(df_graph, x="월", y="누적 연인원", text_auto=True, color_discrete_sequence=['#2196F3'])
                        st.plotly_chart(fig7, use_container_width=True)
                        
                    with g4:
                        st.markdown("**8. 월별 연인원 (해당 월 출석수)**")
                        fig8 = px.bar(df_graph, x="월", y="월별 연인원", text_auto=True, color_discrete_sequence=['#64B5F6'])
                        st.plotly_chart(fig8, use_container_width=True)

                else:
                    st.info("데이터가 충분하지 않습니다. 이용자, 수업, 출석 데이터를 먼저 등록해주세요.")
            else:
                finish_loading()
                st.warning("구글 시트 데이터 로드 실패")

        # =========================================================================
        # 4. 이용자 관리 (수정/삭제 색상 변경 + 보호자 연락처 포맷 + 삭제 즉시반영)
        # =========================================================================
        elif menu == "이용자 관리":
            ws = get_worksheet(sh, "users")

            # [검증 함수 정의] - 이용자 관리 메뉴 안에서만 쓰이므로 여기에 정의
            def validate_and_format_birth(val):
                """생년월일 8자리 숫자만 추출"""
                nums = "".join(filter(str.isdigit, str(val)))
                if len(nums) != 8:
                    return None
                return nums

            def validate_and_format_phone(val):
                """010-XXXX-XXXX 형식으로 변환"""
                nums = "".join(filter(str.isdigit, str(val)))
                if len(nums) == 11 and nums.startswith("010"):
                    return f"{nums[:3]}-{nums[3:7]}-{nums[7:]}"
                return val
            
            # ✅ [추가] 삭제 확인 다이얼로그
            @st.dialog("⚠️ 삭제 확인")
            def confirm_delete(user_id, user_name):
                st.warning(f"**{user_name}** 님의 모든 정보가 영구적으로 삭제됩니다.")
                st.error("⛔ 이 작업은 되돌릴 수 없습니다!")
            
                st.markdown("---")
                col1, col2 = st.columns(2)
            
                if col1.button("🗑️ 삭제", type="primary", use_container_width=True):
                    try:
                        # 1. 삭제 실행
                        cell = ws.find(user_id)
                        ws.delete_rows(cell.row)
                    
                        # 2. 세션 상태에 삭제 완료 플래그 설정
                        st.session_state.delete_success = True
                        st.session_state.deleted_name = user_name
                    
                        # 3. 캐시 초기화 및 새로고침
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"삭제 중 오류가 발생했습니다: {e}")
            
                if col2.button("❌ 취소", use_container_width=True):
                    st.rerun()

            if ws is None:
                finish_loading()
                st.stop()

            st.title("👥 이용자 관리")
        
            # ✅ [추가] 삭제 완료 메시지 표시
            if st.session_state.get('delete_success', False):
                st.success(f"🗑️ {st.session_state.get('deleted_name', '이용자')}님이 삭제되었습니다.")
                st.session_state.delete_success = False
                st.session_state.deleted_name = None
        
            # 1. 데이터 불러오기
            data_records = ws.get_all_records()
            df = pd.DataFrame(data_records)
            df = df.astype(str) # 오류 방지를 위해 문자로 변환

            finish_loading()

            # ---------------------------------------------------------------------
            # [A] 표 선택 감지 및 데이터 매핑
            # ---------------------------------------------------------------------
            selected_row_index = None
            mode = "register"
            
            if "user_grid" in st.session_state and st.session_state.user_grid.get("selection", {}).get("rows"):
                selected_row_indices = st.session_state.user_grid["selection"]["rows"]
                if selected_row_indices:
                    selected_row_index = selected_row_indices[0]
                    mode = "edit"

            # ---------------------------------------------------------------------
            # [B] 입력 폼 초기값 설정
            # ---------------------------------------------------------------------
            # 기본값(빈칸) 설정
            default_vals = {
                "name": "", "birth": "", "reg": "", "gender": "남", "phone": "",
                "fam": "", "emer": "", "addr": "",
                "disabled": False, "beneficiary": False, "seoul": False, "school": False
            }
            target_user_id = None

            # 수정 모드면 선택된 행의 데이터로 덮어쓰기
            if mode == "edit" and selected_row_index is not None:
                try:
                    row_data = df.iloc[selected_row_index]
                    target_user_id = row_data['user_id']
                    
                    default_vals["name"] = row_data['name']
                    default_vals["birth"] = row_data['birth_date']
                    default_vals["reg"] = row_data['registration date']
                    default_vals["gender"] = row_data['gender']
                    default_vals["phone"] = row_data['phone']
                    default_vals["fam"] = row_data['family']
                    default_vals["emer"] = row_data['emergency_contact']
                    default_vals["addr"] = row_data['address']
                    
                    default_vals["disabled"] = (str(row_data['is_disabled']).upper() == 'TRUE')
                    default_vals["beneficiary"] = (str(row_data['is_beneficiary']).upper() == 'TRUE')
                    default_vals["seoul"] = (str(row_data['is_seoul_resident']).upper() == 'TRUE')
                    default_vals["school"] = (str(row_data['is_school_age']).upper() == 'TRUE')
                    
                    st.info(f"✏️ **{default_vals['name']}** 님을 수정하거나 삭제할 수 있습니다.")
                except Exception as e:
                    st.error("데이터를 불러오는 중 오류가 발생했습니다.")
                    mode = "register" # 에러나면 등록 모드로 복귀

            # ---------------------------------------------------------------------
            # [C] 입력 폼 그리기
            # ---------------------------------------------------------------------
            with st.form("user_management_form"):
                r1c1, r1c2, r1c3 = st.columns(3)
                input_name = r1c1.text_input("이름", value=default_vals["name"])
                input_birth = r1c2.text_input("생년월일", placeholder="예: 20000101", value=default_vals["birth"])
                input_reg = r1c3.text_input("최초등록일", placeholder="예: 20260101", value=default_vals["reg"])

                r2c1, r2c2 = st.columns(2)
                g_idx = 0 if default_vals["gender"] == "남" else 1
                input_gender = r2c1.selectbox("성별", ["남", "여"], index=g_idx)
                input_phone = r2c2.text_input("연락처", value=default_vals["phone"])

                r3c1, r3c2 = st.columns(2)
                input_fam = r3c1.text_input("보호자", value=default_vals["fam"])
                input_emer = r3c2.text_input("보호자 연락처", value=default_vals["emer"])

                r4c1 = st.columns(1)[0]
                input_addr = r4c1.text_input("주소", value=default_vals["addr"])

                chk_label, chk1, chk2, chk3, chk4 = st.columns([1.2, 1, 1, 1, 1])
                chk_label.markdown("<p style='margin-top: 8px; font-weight: 500;'>특이사항</p>", unsafe_allow_html=True)
                
                chk_disabled = chk1.checkbox("장애", value=default_vals["disabled"])
                chk_beneficiary = chk2.checkbox("수급자", value=default_vals["beneficiary"])
                chk_seoul = chk3.checkbox("서울거주", value=default_vals["seoul"])
                chk_school = chk4.checkbox("학령기", value=default_vals["school"])

                st.markdown("---")
                
                # -----------------------------------------------------------------
                # [D] 버튼 로직 (등록 vs 수정/삭제)
                # -----------------------------------------------------------------
                if mode == "register":
                    # [신규 등록] - Primary(초록색) 버튼 사용
                    submitted = st.form_submit_button("등록하기", type="primary", use_container_width=True)
                    
                    if submitted:
                        clean_birth = validate_and_format_birth(input_birth)
                        clean_phone = validate_and_format_phone(input_phone)
                        clean_emer = validate_and_format_phone(input_emer)

                        if not input_name:
                            st.toast("이름을 입력하세요.", icon="⚠️")
                        elif not clean_birth:
                            st.error("⛔ 생년월일은 반드시 'YYYYMMDD' 8자리 숫자로 입력해주세요.")
                        else:
                            new_id = f"{input_name}{clean_birth}"
                            ids = [str(x) for x in df['user_id'].tolist()] if not df.empty else []
                            
                            if new_id in ids:
                                st.toast("이미 등록된 이용자입니다.", icon="⚠️")
                            else:
                                save_vals = [
                                    new_id, input_name, clean_birth, input_reg, input_gender, clean_phone,
                                    clean_emer, input_addr, input_fam,
                                    "TRUE" if chk_disabled else "FALSE",
                                    "TRUE" if chk_beneficiary else "FALSE",
                                    "TRUE" if chk_seoul else "FALSE",
                                    "TRUE" if chk_school else "FALSE"
                                ]
                                ws.append_row(save_vals)
                                st.toast(f"{input_name}님 등록 완료!", icon="✅")
                                
                                # 데이터 갱신을 위해 캐시가 있다면 비움
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()

                else:
                    # [수정/삭제] - 일반 버튼 사용 (CSS로 파랑/빨강 적용)
                    b_col1, b_col2 = st.columns(2)
                    update_btn = b_col1.form_submit_button("수정하기", type="primary", use_container_width=True) 
                    delete_btn = b_col2.form_submit_button("삭제하기", type="primary", use_container_width=True) 

                    if update_btn:
                        clean_birth = validate_and_format_birth(input_birth)
                        clean_phone = validate_and_format_phone(input_phone)
                        clean_emer = validate_and_format_phone(input_emer)

                        if not clean_birth:
                            st.error("⛔ 수정 실패: 생년월일 형식을 확인해주세요.")
                        else:
                            try:
                                cell = ws.find(target_user_id)
                                row_num = cell.row
                                
                                update_vals = [
                                    target_user_id, input_name, clean_birth, input_reg, input_gender, clean_phone,
                                    clean_emer, input_addr, input_fam,
                                    "TRUE" if chk_disabled else "FALSE",
                                    "TRUE" if chk_beneficiary else "FALSE",
                                    "TRUE" if chk_seoul else "FALSE",
                                    "TRUE" if chk_school else "FALSE"
                                ]
                                ws.update(f"A{row_num}:M{row_num}", [update_vals])
                                
                                st.toast("수정 완료!", icon="✅")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"수정 중 오류: {e}")

                    # ✅ [수정] 삭제 버튼 클릭 시 확인 팝업 표시
                    if delete_btn:
                        confirm_delete(target_user_id, input_name)
                    
            # ---------------------------------------------------------------------
            # [E] 하단 데이터 표 (들여쓰기 수정 완료: if/else 밖으로 빼서 항상 보이게 함)
            # ---------------------------------------------------------------------
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            st.caption("👇 아래 목록에서 행을 클릭하면 위쪽 입력창에서 수정하거나 삭제할 수 있습니다.")
            
            st.dataframe(
                df, 
                use_container_width=True, 
                key="user_grid",
                on_select="rerun", 
                selection_mode="single-row",
                hide_index=True
            )

        # =========================================================================
        # 5. 수업 관리 (수정/삭제 팝업 추가 - 수업 & 교육구분)
        # =========================================================================
        elif menu == "수업 관리":
            ws_c = get_worksheet(sh, sheet_cls)
            ws_edu = get_worksheet(sh, "education_categories")
            get_worksheet(sh, sheet_att)
            get_worksheet(sh, sheet_ext)
            
            # [팝업 함수 1] 수업 삭제 확인
            @st.dialog("⚠️ 수업 삭제 확인")
            def confirm_delete_class(c_id, c_name):
                st.warning(f"수업 **'{c_name}'** 정보를 삭제하시겠습니까?")
                st.caption("참고: 이 수업의 출석 기록은 유지되지만 수업 목록에서는 사라집니다.")
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                # 삭제 버튼 (Primary 스타일을 주되, 빨간색은 CSS로 처리됨을 기대하거나 기본 Primary 색상 사용)
                if col1.button("🗑️ 삭제", type="primary", use_container_width=True):
                    try:
                        cell = ws_c.find(c_id)
                        ws_c.delete_rows(cell.row)
                        st.toast("수업이 삭제되었습니다.", icon="🗑️")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")
                
                if col2.button("❌ 취소", use_container_width=True):
                    st.rerun()

            # [팝업 함수 2] 교육구분 삭제 확인
            @st.dialog("⚠️ 교육구분 삭제 확인")
            def confirm_delete_category(cat_id, cat_name):
                st.warning(f"교육구분 **'{cat_name}'**을(를) 삭제하시겠습니까?")
                st.error("⛔ 삭제 시 이를 사용하던 수업 정보에 영향을 줄 수 있습니다.")
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                if col1.button("🗑️ 삭제", type="primary", use_container_width=True):
                    try:
                        cell = ws_edu.find(cat_id)
                        ws_edu.delete_rows(cell.row)
                        st.toast("교육구분이 삭제되었습니다.", icon="🗑️")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

                if col2.button("❌ 취소", use_container_width=True):
                    st.rerun()

            # 시트 로드 확인
            if ws_c is None or ws_edu is None:
                finish_loading()
                st.error("구글 시트 로드 실패")
                st.stop()
            
            st.title("🏫 수업 관리")
            
            # 데이터 로드
            data_c = ws_c.get_all_records()
            data_edu = ws_edu.get_all_records()
            
            df_c = pd.DataFrame(data_c).astype(str)
            df_edu = pd.DataFrame(data_edu).astype(str)

            finish_loading()

            # ---------------------------------------------------------------------
            # [PART 1] 수업 등록 및 관리
            # ---------------------------------------------------------------------
            st.subheader("➕ 수업 등록 및 관리")
            
            # 1-1. 수업 표 선택 감지
            sel_class_idx = None
            mode_class = "register"
            
            if "class_grid" in st.session_state and st.session_state.class_grid.get("selection", {}).get("rows"):
                sel_rows = st.session_state.class_grid["selection"]["rows"]
                if sel_rows:
                    sel_class_idx = sel_rows[0]
                    mode_class = "edit"

            # 1-2. 수업 폼 초기값 설정
            def_c_biz = BUSINESS_CATEGORIES[0]
            def_c_edu = None
            def_c_name = ""
            def_c_inst = ""
            def_c_date = ""
            target_class_id = None

            if mode_class == "edit" and sel_class_idx is not None:
                try:
                    row_c = df_c.iloc[sel_class_idx]
                    target_class_id = row_c['class_id']
                    
                    # 기존 값 매핑
                    if row_c['business_category'] in BUSINESS_CATEGORIES:
                        def_c_biz = row_c['business_category']
                    
                    # 교육구분 임시 저장 (폼 안에서 필터링 후 매칭)
                    temp_edu_val = row_c['education_category'] 
                    
                    def_c_name = row_c['class_name']
                    def_c_inst = row_c['instructor_name']
                    def_c_date = row_c['start_date']
                    
                    st.info(f"✏️ 수업 '{def_c_name}'을(를) 수정하거나 삭제할 수 있습니다.")
                except:
                    mode_class = "register"

        # ---------------------------------------------------------------------
            # [수업 관리] 1-3. 수업 입력 폼 (테두리 추가 + 드롭박스 즉시 반응 유지)
            # ---------------------------------------------------------------------
            
            # ✅ st.container(border=True)가 '폼'처럼 보이는 테두리를 만들어줍니다.
            # 하지만 st.form과 달리, 내부의 selectbox가 즉시 반응할 수 있습니다!
            with st.container(border=True):
            
                # (1) 사업구분 (대분류) 선택 - 선택 즉시 화면 리로드 (테두리 안에서도 작동함!)
                biz_idx = BUSINESS_CATEGORIES.index(def_c_biz) if def_c_biz in BUSINESS_CATEGORIES else 0
                sel_biz_cat = st.selectbox("1. 사업구분(대분류)", BUSINESS_CATEGORIES, index=biz_idx)

                # (2) 교육구분 (중분류) 필터링 로직
                filtered_edu_list = []
                if not df_edu.empty:
                    filtered_rows = df_edu[df_edu['business_category'] == sel_biz_cat]
                    filtered_edu_list = filtered_rows['category_name'].tolist()

                # 수정 모드값 매칭
                edu_idx = 0
                if mode_class == "edit" and 'temp_edu_val' in locals():
                    if temp_edu_val in filtered_edu_list:
                        edu_idx = filtered_edu_list.index(temp_edu_val)

                if not filtered_edu_list:
                    st.warning(f"⚠️ '{sel_biz_cat}'에 등록된 교육구분이 없습니다.")
                    sel_edu_cat = None
                else:
                    sel_edu_cat = st.selectbox("2. 교육구분명(중분류)", filtered_edu_list, index=edu_idx)

                # (3) 나머지 입력 필드
                c1, c2, c3 = st.columns(3)
                input_class_name = c1.text_input("3. 수업명(소분류)", value=def_c_name)
                input_instructor = c2.text_input("4. 강사명", value=def_c_inst)                      
                input_start_date = c3.text_input("5. 강의 시작일 (예: 20240101)", placeholder="YYYYMMDD", value=def_c_date)
                
                st.markdown("---")

                # -----------------------------------------------------------------
                # [버튼 로직] 테두리 안쪽에 버튼 배치 (꽉 찬 스타일 적용)
                # -----------------------------------------------------------------
                if mode_class == "register":
                    # 신규 등록
                    
                    if st.button("등록하기", type="primary", use_container_width=True):
                        if not sel_edu_cat:
                            st.toast("교육구분을 선택해야 합니다.", icon="⚠️")
                        elif not input_class_name:
                            st.toast("수업명을 입력해주세요.", icon="⚠️")
                        else:
                            new_class_id = f"C{int(time.time())}"
                            ws_c.append_row([new_class_id, input_class_name, sel_biz_cat, sel_edu_cat, input_instructor, input_start_date])
                            st.toast(f"수업 '{input_class_name}' 등록 완료!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                else:
                    # 수정/삭제
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("수정하기", type="primary", use_container_width=True):
                            if not sel_edu_cat or not input_class_name:
                                st.error("필수 정보를 입력해주세요.")
                            else:
                                try:
                                    cell = ws_c.find(target_class_id)
                                    row_n = cell.row
                                    ws_c.update(f"A{row_n}:F{row_n}", [[target_class_id, input_class_name, sel_biz_cat, sel_edu_cat, input_instructor, input_start_date]])
                                    st.toast("수업 정보 수정 완료!", icon="✅")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"수정 오류: {e}")
                    with b2:
                        if st.button("삭제하기", type="primary", use_container_width=True):
                            confirm_delete_class(target_class_id, input_class_name)
            
            # 1-5. 수업 목록 표
            st.caption("👇 아래 목록에서 행을 클릭하면 위쪽 입력창에서 수정하거나 삭제할 수 있습니다.")
            st.dataframe(
                df_c, 
                use_container_width=True, 
                key="class_grid", 
                on_select="rerun", 
                selection_mode="single-row", 
                hide_index=True
            )
            
            st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
            st.markdown("---", unsafe_allow_html=True)

            # ---------------------------------------------------------------------
            # [PART 2] 교육구분 등록 및 관리
            # ---------------------------------------------------------------------
            with st.container():
                st.subheader("⚙️ 교육구분 등록 및 관리")            
                
                # 2-1. 교육구분 표 선택 감지
                sel_edu_idx = None
                mode_edu = "register"
                
                if "edu_grid" in st.session_state and st.session_state.edu_grid.get("selection", {}).get("rows"):
                    sel_rows_edu = st.session_state.edu_grid["selection"]["rows"]
                    if sel_rows_edu:
                        sel_edu_idx = sel_rows_edu[0]
                        mode_edu = "edit"

                # 2-2. 교육구분 폼 초기값
                def_e_biz = BUSINESS_CATEGORIES[0]
                def_e_name = ""
                def_e_type = "내부수업"
                target_cat_id = None

                if mode_edu == "edit" and sel_edu_idx is not None:
                    try:
                        row_e = df_edu.iloc[sel_edu_idx]
                        target_cat_id = row_e['category_id']
                        
                        if row_e['business_category'] in BUSINESS_CATEGORIES:
                            def_e_biz = row_e['business_category']
                        
                        def_e_name = row_e['category_name']
                        
                        if row_e['class_type'] in ["내부수업", "외부수업"]:
                            def_e_type = row_e['class_type']
                            
                        st.info(f"✏️ 교육구분 '{def_e_name}'을(를) 수정하거나 삭제할 수 있습니다.")
                    except:
                        mode_edu = "register"

                # 2-3. 교육구분 입력 폼
                with st.form("new_edu_category"):
                    e_biz = st.selectbox("사업구분 (대분류)", BUSINESS_CATEGORIES, index=BUSINESS_CATEGORIES.index(def_e_biz) if def_e_biz in BUSINESS_CATEGORIES else 0)
                    e_name = st.text_input("교육구분명 (중분류) 입력", placeholder="예: 한글기초교육", value=def_e_name)
                    
                    type_opts = ["내부수업", "외부수업"]
                    e_type = st.selectbox("유형", type_opts, index=type_opts.index(def_e_type) if def_e_type in type_opts else 0)
                    
                    st.markdown("---")

                    # 2-4. 교육구분 버튼 로직
                    if mode_edu == "register":
                        if st.form_submit_button("등록하기", type="primary", use_container_width=True):
                            if e_name:
                                is_exist = False
                                if not df_edu.empty:
                                    is_exist = not df_edu[(df_edu['business_category'] == e_biz) & (df_edu['category_name'] == e_name)].empty
                                
                                if is_exist:
                                    st.error("이미 등록된 교육구분입니다.")
                                else:
                                    new_cat_id = f"E{int(time.time())}"
                                    ws_edu.append_row([new_cat_id, e_biz, e_name, e_type])
                                    st.success(f"교육구분 '{e_name}' 등록 완료!")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                            else:
                                st.error("교육구분명을 입력하세요.")
                    else:
                        # 수정/삭제 모드
                        b1, b2 = st.columns(2)
                        up_btn = b1.form_submit_button("수정하기", type="primary", use_container_width=True) # CSS 파란색
                        del_btn = b2.form_submit_button("삭제하기", type="primary", use_container_width=True) # CSS 빨간색

                        if up_btn:
                            if not e_name:
                                st.error("교육구분명을 입력하세요.")
                            else:
                                try:
                                    cell = ws_edu.find(target_cat_id)
                                    row_n = cell.row
                                    ws_edu.update(f"A{row_n}:D{row_n}", [[target_cat_id, e_biz, e_name, e_type]])
                                    st.toast("교육구분 수정 완료!", icon="✅")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"수정 오류: {e}")

                        if del_btn:
                            # 팝업 호출
                            confirm_delete_category(target_cat_id, e_name)

                # 2-5. 교육구분 목록 표
                st.caption("👇 아래 목록에서 행을 클릭하면 위쪽 입력창에서 수정하거나 삭제할 수 있습니다.")
                st.dataframe(
                    df_edu, 
                    use_container_width=True, 
                    key="edu_grid", 
                    on_select="rerun", 
                    selection_mode="single-row", 
                    hide_index=True
                )

if __name__ == "__main__":
    main()