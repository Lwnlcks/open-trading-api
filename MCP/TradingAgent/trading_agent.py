import asyncio
import os
import json
import logging
from typing import Dict, Any, List, Optional
from mcp_client_connector import MCPClient
from dotenv import load_dotenv

# LLM integration (using OpenAI as an example, but adaptable)
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradingAgent:
    def __init__(self, mcp_server_path: str):
        self.client = MCPClient(mcp_server_path)
        self.investment_direction = ""
        self.logs = []
        if HAS_OPENAI and os.getenv("OPENAI_API_KEY"):
            self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            self.llm = None
            logger.warning("OPENAI_API_KEY가 설정되지 않았거나 openai 패키지가 없습니다. Mock 모드로 동작합니다.")

    async def initialize(self):
        logger.info("Connecting to KIS Trading MCP Server...")
        await self.client.connect()
        logger.info("Connected to MCP Server.")

    def log(self, message: str):
        logger.info(message)
        self.logs.append(message)

    async def get_market_context(self) -> Dict[str, Any]:
        """시장 파악을 위한 데이터 수집"""
        context = {}

        # 1. 국내 시장 거래량 상위
        self.log("국내 시장 거래량 순위 수집 중...")
        vol_rank = await self.client.call_tool("domestic_stock", {
            "api_type": "volume_rank",
            "params": {
                "fid_cond_mrkt_div_code": "J",
                "fid_cond_scr_div_code": "20171",
                "fid_input_iscd": "0000",
                "fid_div_cls_code": "0",
                "fid_blng_cls_code": "0",
                "fid_trgt_cls_code": "111111111",
                "fid_trgt_exls_cls_code": "0000000000"
            }
        })
        context["domestic_volume_rank"] = vol_rank.content if hasattr(vol_rank, 'content') else vol_rank

        # 2. 국내 주요 뉴스
        self.log("시장 뉴스 수집 중...")
        news = await self.client.call_tool("domestic_stock", {
            "api_type": "news_title",
            "params": {
                "fid_news_ofer_entp_code": "007",
                "fid_cond_mrkt_cls_code": "J",
                "fid_input_iscd": "0000",
                "fid_titl_cntt": "",
                "fid_input_date_1": "",
                "fid_input_hour_1": "",
                "fid_rank_sort_cls_code": "1",
                "fid_input_srno": ""
            }
        })
        context["news"] = news.content if hasattr(news, 'content') else news

        # 3. 내 잔고 확인
        self.log("포트폴리오 잔고 확인 중...")
        balance = await self.client.call_tool("domestic_stock", {
            "api_type": "inquire_balance",
            "params": {
                "env_dv": "demo",
                "afhr_flpr_yn": "N",
                "inqr_dvsn": "02",
                "unpr_dvsn": "01",
                "fund_sttl_icld_yn": "N",
                "fncg_amt_auto_rdpt_yn": "N",
                "prcs_dvsn": "00"
            }
        })
        context["portfolio"] = balance.content if hasattr(balance, 'content') else balance

        return context

    def analyze_with_llm(self, user_prompt: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """LLM을 사용하여 시장 데이터를 분석하고 결정을 내림"""
        if not self.llm:
            # Mock fallback
            return {
                "action": "hold",
                "reason": "LLM 설정이 되어 있지 않아 기본적으로 관망합니다."
            }

        system_prompt = """
        당신은 한국투자증권의 전문 트레이딩 에이전트입니다.
        사용자의 투자 방향과 현재 시장 데이터(거래량 순위, 뉴스, 포트폴리오)를 분석하여 최적의 매매 결정을 내리세요.
        결과는 반드시 JSON 형식으로만 응답하며, 다음 필드를 포함해야 합니다:
        - action: "buy" | "sell" | "hold"
        - stock_name: "종목명" (매수/매도 시)
        - quantity: 수량 (정수)
        - reason: 결정 사유 (한글)
        - confidence: 0.0 ~ 1.0
        """

        user_content = f"""
        [사용자 투자 방향]
        {user_prompt}

        [시장 데이터 분석 결과]
        {json.dumps(market_data, ensure_ascii=False)[:4000]} # 토큰 제한을 위해 일부 절삭
        """

        try:
            response = self.llm.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM 분석 중 오류 발생: {e}")
            return {"action": "hold", "reason": f"오류 발생: {str(e)}"}

    async def execute_trade(self, decision: Dict[str, Any]):
        """분석된 결과를 바탕으로 실제 매매 실행"""
        action = decision.get("action")
        if action not in ["buy", "sell"]:
            self.log(f"매매 보류: {decision.get('reason')}")
            return

        stock_name = decision.get("stock_name")
        quantity = decision.get("quantity", 0)

        if not stock_name or quantity <= 0:
            self.log("잘못된 주문 정보입니다.")
            return

        self.log(f"매매 실행 시작: {stock_name} {quantity}주 {action}")

        # 1. 종목 코드 찾기
        code_res = await self.client.call_tool("domestic_stock", {
            "api_type": "find_stock_code",
            "params": {"stock_name": stock_name}
        })

        # MCP 응답 구조 처리
        if hasattr(code_res, 'content'):
            # TextContent 객체인 경우
            text_data = code_res.content[0].text
            code_data = json.loads(text_data)
        else:
            code_data = code_res

        if code_data.get("ok"):
            stock_code = code_data["data"]["stock_code"]

            # 2. 주문 실행 (현금 주문)
            order_res = await self.client.call_tool("domestic_stock", {
                "api_type": "order_cash",
                "params": {
                    "env_dv": "demo", # 테스트 안전을 위해 모의투자 고정
                    "ord_dv": action,
                    "pdno": stock_code,
                    "ord_dvsn": "01", # 시장가
                    "ord_qty": str(quantity),
                    "ord_unpr": "0",
                    "excg_id_dvsn_cd": "KRX"
                }
            })
            self.log(f"주문 결과 수신: {order_res}")
        else:
            self.log(f"종목 코드를 찾을 수 없습니다: {stock_name}")

    async def run(self, user_prompt: str):
        await self.initialize()
        try:
            # 1. 시장 상황 파악
            market_data = await self.get_market_context()

            # 2. LLM 분석
            self.log("LLM 분석을 통한 의사 결정 진행 중...")
            decision = self.analyze_with_llm(user_prompt, market_data)

            # 3. 매매 실행
            await self.execute_trade(decision)

        except Exception as e:
            logger.error(f"실행 중 치명적 오류: {e}")
        finally:
            await self.client.disconnect()
            self.log("에이전트 종료.")

if __name__ == "__main__":
    import sys

    # 설정
    mcp_path = os.path.abspath("../Kis Trading MCP/server.py")
    agent = TradingAgent(mcp_path)

    # 인자 또는 기본값으로 프롬프트 설정
    prompt = sys.argv[1] if len(sys.argv) > 1 else "현재 시장에서 가장 활발한 섹터의 대장주를 1주만 테스트로 매수해줘."

    asyncio.run(agent.run(prompt))
