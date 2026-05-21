# KIS AI Trading Agent (MCP + Gemini + MySQL + Flask)

본 에이전트는 **Model Context Protocol (MCP)**를 통해 한국투자증권 OpenAPI와 **구글 Gemini AI**를 결합한 능동형 자동매매 시스템입니다. 시장 시간에 따라 국내 및 해외 주식을 자동으로 분석하고 매매 결정을 내리며, 모든 기록은 MySQL에 저장되고 Flask 웹 대시보드를 통해 확인할 수 있습니다.

## 🚀 주요 기능

1. **시간 기반 멀티 마켓 트레이딩**:
   - 국장 시간 (09:00~15:30): 국내 주식 분석 및 매매
   - 미장 시간 (22:30~05:00): 해외 주식 분석 및 매매
   - 겹치는 시간: 동시 운영
2. **Gemini AI 기반 의사결정**: 구글의 Gemini-1.5-flash 모델을 사용하여 복합적인 시장 상황 판단
3. **데이터베이스 로깅**: 모든 판단 근거, 시장 데이터, 매매 결과를 MySQL에 영구 저장
4. **웹 대시보드**: Flask 기반 UI로 실시간 트레이딩 히스토리 모니터링

## 🛠️ 설치 및 설정

### 1. KIS OpenAPI 키 발급 및 적용
한국투자증권 [Developers 센터](https://apiportal.koreainvestment.com/)에서 앱키(App Key)와 앱시크릿(App Secret)을 발급받으세요. (실전투자 및 모의투자 각각 발급 필요)

**키 적용 방법:**
1. 프로젝트 루트의 `kis_devlp.yaml` 파일을 텍스트 에디터로 엽니다.
2. 아래 항목에 발급받은 값을 입력합니다:
   - `my_app`: 실전투자 앱키
   - `my_sec`: 실전투자 앱시크릿
   - `paper_app`: 모의투자 앱키
   - `paper_sec`: 모의투자 앱시크릿
   - `my_acct_stock`: 계좌번호 앞 8자리
3. 또는 시스템 환경변수에 `KIS_APP_KEY`, `KIS_APP_SECRET` 등으로 설정하여 MCP 서버가 인식하게 할 수 있습니다.
4. **Kis Trading MCP** 서버 설정:
   - `MCP/Kis Trading MCP/Readme.md`를 참고하여 Docker 또는 로컬 환경에서 서버를 실행 가능한 상태로 만듭니다. 에이전트는 이 서버를 통해 통신합니다.

### 2. 환경 변수 설정 (.env)
`MCP/TradingAgent/.env` 파일을 생성하고 다음 내용을 입력합니다.

```env
# Gemini API Key (Google AI Studio에서 발급)
GEMINI_API_KEY=your_gemini_api_key

# MySQL 설정
MYSQL_HOST=localhost
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
MYSQL_DB=kis_trading

# KIS 설정 (MCP 서버 연동용 환경변수)
KIS_APP_KEY=실전_앱키
KIS_APP_SECRET=실전_시크릿
KIS_ACCT_STOCK=계좌번호_8자리
# ... 기타 필요한 KIS 정보
```

### 3. 의존성 설치
```bash
pip install mcp google-generativeai mysql-connector-python flask python-dotenv pandas
```

## 🖥️ 실행 방법

### 1. 트레이딩 실행
```bash
python trading_agent.py "최근 반도체 시장이 뜨거운데 관련 우량주 매수해줘"
```

### 2. 웹 대시보드 실행
```bash
python web_app.py
```
브라우저에서 `http://localhost:5000` 접속 시 대시보드 확인 가능

## 📊 데이터베이스 구조
- `trading_logs` 테이블: 시간, 시장구분, 사용자 프롬프트, 결정(BUY/SELL), 종목명, 수량, **판단 사유**, 신뢰도, 원본 시장 데이터 등을 저장합니다.

## ⚠️ 주의사항
- **거래 시간**: `MarketHours` 클래스에 정의된 시간에만 에이전트가 작동합니다.
- **모의투자**: 기본적으로 `env_dv="demo"`로 설정되어 안전한 테스트가 가능합니다. 실전 매매 전환 시 코드를 수정하십시오.
