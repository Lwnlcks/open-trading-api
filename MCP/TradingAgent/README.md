# AI 트레이딩 에이전트 (MCP 기반)

본 에이전트는 **Model Context Protocol (MCP)**를 활용하여 한국투자증권의 OpenAPI와 LLM을 결합, 사용자의 자연어 프롬프트에 따라 능동적으로 시장을 분석하고 매매를 수행하는 에이전트입니다.

## 🚀 주요 기능

1. **자연어 투자 전략 실행**: "반도체 관련주 매수해줘"와 같은 사용자 프롬프트를 분석하여 실제 매매로 연결
2. **시장 상황 자동 분석**: 국내/해외 주식의 거래량 순위, 뉴스 제목 등을 실시간으로 수집
3. **포트폴리오 기반 의사결정**: 현재 잔고와 자산 현황을 파악하여 적절한 매매 수량 결정
4. **MCP 연동**: `Kis Trading MCP` 서버를 클라이언트로 연결하여 보안이 유지된 상태로 API 호출

## 🛠️ 설치 및 설정

### 1. 환경 설정
`MCP/TradingAgent` 폴더에 `.env` 파일을 생성하고 필요한 정보를 입력합니다.

```env
# KIS API 설정 (Kis Trading MCP에서 사용하는 것과 동일)
# 실제 매매를 위해 Kis Trading MCP 서버가 정상 작동해야 합니다.

# LLM 설정
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. 의존성 설치
`mcp` 및 `openai` 파이썬 패키지가 필요합니다.

```bash
pip install mcp openai python-dotenv pandas
```

### 3. KIS Trading MCP 서버 빌드
트레이딩 에이전트는 `MCP/Kis Trading MCP/server.py`를 실행하여 도구들을 호출합니다. 해당 서버가 사용하는 라이브러리(`fastmcp` 등)가 설치되어 있어야 합니다.

## 📈 전략: AI-Driven Market Sentiment & Momentum

이 에이전트는 다음과 같은 단계로 능동적 트레이딩을 수행합니다.

1. **프롬프트 수신**: 사용자의 투자 의도 파악
2. **데이터 수집**:
   - `volume_rank`: 시장의 뜨거운 종목군 파악
   - `news_title`: 최신 뉴스 키워드 추출
   - `inquire_balance`: 투자 가능 금액 및 기존 보유 종목 확인
3. **LLM 추론**: 수집된 데이터와 프롬프트를 결합하여 최적의 종목과 매매 시점 결정
4. **매매 실행**: `order_cash` 등 MCP 도구를 사용하여 즉시 주문 실행

## 🖥️ 실행 방법

```bash
cd MCP/TradingAgent
python trading_agent.py
```

## ⚠️ 주의사항

- **투자 책임**: 본 코드는 샘플이며, 이를 활용한 매매의 결과는 전적으로 사용자에게 책임이 있습니다.
- **모의투자 권장**: 초기 테스트 시 `trading_agent.py` 내의 `env_dv` 파라미터를 반드시 `"demo"`로 설정하여 모의계좌에서 실행하세요.
- **MCP 서버 경로**: `trading_agent.py` 내의 `mcp_path`가 실제 `server.py` 위치와 일치하는지 확인하십시오.
