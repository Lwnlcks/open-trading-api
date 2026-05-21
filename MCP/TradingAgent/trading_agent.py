import asyncio
import os
import json
import logging
from datetime import datetime, time
from typing import Dict, Any, List, Optional
import google.generativeai as genai
from mcp_client_connector import MCPClient
from database_manager import DatabaseManager
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MarketHours:
    @staticmethod
    def get_active_markets() -> List[str]:
        """현재 시간에 활성화된 시장 반환 (KST 기준)"""
        now = datetime.now()
        current_time = now.time()

        # 한국 시장: 09:00 ~ 15:30
        domestic_active = time(9, 0) <= current_time <= time(15, 30)

        # 미국 시장 (KST 기준): 22:30 ~ 05:00 (단순화된 정규장 시간)
        overseas_active = current_time >= time(22, 30) or current_time <= time(5, 0)

        active = []
        if domestic_active: active.append("domestic")
        if overseas_active: active.append("overseas")

        return active

class TradingAgent:
    def __init__(self, mcp_server_path: str):
        self.client = MCPClient(mcp_server_path)
        self.db = DatabaseManager()

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini AI initialized.")
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY가 설정되지 않았습니다.")

    async def initialize(self):
        logger.info("Connecting to KIS Trading MCP Server...")
        await self.client.connect()
        self.db.initialize_db()
        logger.info("Initialization complete.")

    def log(self, message: str):
        logger.info(message)

    async def get_market_context(self, market_type: str) -> Dict[str, Any]:
        """특정 시장 데이터 수집 (MCP 도구 호출)"""
        context = {}
        try:
            if market_type == "domestic":
                self.log("국내 시장 데이터 수집 중...")
                vol = await self.client.call_tool("domestic_stock", {
                    "api_type": "volume_rank",
                    "params": {"fid_cond_mrkt_div_code": "J", "fid_cond_scr_div_code": "20171", "fid_input_iscd": "0000", "fid_div_cls_code": "0", "fid_blng_cls_code": "0", "fid_trgt_cls_code": "111111111", "fid_trgt_exls_cls_code": "0000000000"}
                })
                balance = await self.client.call_tool("domestic_stock", {
                    "api_type": "inquire_balance",
                    "params": {"env_dv": "demo", "afhr_flpr_yn": "N", "inqr_dvsn": "02", "unpr_dvsn": "01", "fund_sttl_icld_yn": "N", "fncg_amt_auto_rdpt_yn": "N", "prcs_dvsn": "00"}
                })
                context = {"volume": str(vol), "balance": str(balance)}
            else:
                self.log("해외 시장 데이터 수집 중...")
                vol = await self.client.call_tool("overseas_stock", {
                    "api_type": "trade_vol",
                    "params": {"excd": "NAS", "nday": "0", "vol_rang": "0"}
                })
                balance = await self.client.call_tool("overseas_stock", {
                    "api_type": "inquire_balance",
                    "params": {"ovrs_excg_cd": "NASD", "tr_crcy_cd": "USD", "env_dv": "demo"}
                })
                context = {"volume": str(vol), "balance": str(balance)}
        except Exception as e:
            logger.error(f"Error fetching market context: {e}")
        return context

    def analyze_with_gemini(self, user_prompt: str, market_data: Dict[str, Any], market_type: str) -> Dict[str, Any]:
        if not self.model:
            return {"action": "hold", "reason": "Gemini API Key missing."}

        prompt = f"""
        당신은 한국투자증권 전문 AI 트레이더입니다. {market_type} 주식 시장 데이터를 기반으로 분석하세요.
        사용자 투자 방향: {user_prompt}
        현재 시장 데이터 요약: {json.dumps(market_data, ensure_ascii=False)[:5000]}

        위 데이터를 바탕으로 매매 결정을 내리세요. 결과는 반드시 JSON 형식으로만 응답해야 합니다.
        응답 형식:
        {{
            "action": "buy" | "sell" | "hold",
            "stock_name": "종목명",
            "quantity": 수량(숫자),
            "reason": "구체적인 판단 이유 (한글)",
            "confidence": 0.0~1.0
        }}
        """
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            # JSON만 추출
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"Gemini analysis error: {e}")
            return {"action": "hold", "reason": f"AI 분석 오류: {str(e)}"}

    async def execute_trade(self, decision: Dict[str, Any], market_type: str):
        action = decision.get("action")
        if action not in ["buy", "sell"]:
            self.log(f"관망: {decision.get('reason')}")
            return

        stock_name = decision.get("stock_name")
        quantity = decision.get("quantity", 0)

        self.log(f"매매 실행: {market_type} | {action} {stock_name} {quantity}주")

        try:
            if market_type == "domestic":
                # 종목 코드 검색
                code_res = await self.client.call_tool("domestic_stock", {
                    "api_type": "find_stock_code",
                    "params": {"stock_name": stock_name}
                })
                # MCP 반환 처리
                content = code_res.content[0].text if hasattr(code_res, 'content') else str(code_res)
                code_data = json.loads(content) if isinstance(content, str) and content.startswith('{') else {}

                if code_data.get("ok"):
                    stock_code = code_data["data"]["stock_code"]
                    await self.client.call_tool("domestic_stock", {
                        "api_type": "order_cash",
                        "params": {
                            "env_dv": "demo", "ord_dv": action, "pdno": stock_code,
                            "ord_dvsn": "01", "ord_qty": str(quantity), "ord_unpr": "0", "excg_id_dvsn_cd": "KRX"
                        }
                    })
            else:
                # 해외 주식은 종목 코드가 보통 심볼(AAPL 등)이므로 직접 시도하거나 검색
                # 여기서는 심볼이 바로 들어왔다고 가정하거나 추가 검색 로직 필요
                await self.client.call_tool("overseas_stock", {
                    "api_type": "order",
                    "params": {
                        "env_dv": "demo", "ord_dv": action, "pdno": stock_name, # stock_name이 AAPL 등 심볼인 경우
                        "ovrs_excg_cd": "NASD", "ord_qty": str(quantity), "ovrs_ord_unpr": "0", "ord_dvsn": "00"
                    }
                })
        except Exception as e:
            logger.error(f"Trade execution error: {e}")

    async def run(self, user_prompt: str):
        await self.initialize()
        active_markets = MarketHours.get_active_markets()

        if not active_markets:
            self.log("현재 거래 가능한 시장이 없습니다. (장외 시간)")
            # 테스트를 위해 강제로 국내 시장 진행 가능 (필요시)
            # active_markets = ["domestic"]

        for m_type in active_markets:
            self.log(f"--- {m_type.upper()} 시장 분석 및 트레이딩 시작 ---")
            m_data = await self.get_market_context(m_type)
            decision = self.analyze_with_gemini(user_prompt, m_data, m_type)

            # MySQL에 저장
            self.db.log_trading(m_type, user_prompt, decision, m_data)

            # 매매 실행
            await self.execute_trade(decision, m_type)

        await self.client.disconnect()
        self.log("에이전트 작업 완료.")

if __name__ == "__main__":
    import sys
    mcp_path = os.path.abspath("../Kis Trading MCP/server.py")
    agent = TradingAgent(mcp_path)
    prompt = sys.argv[1] if len(sys.argv) > 1 else "현재 시장에서 가장 유망한 종목을 선정해 소량 매수해줘."
    asyncio.run(agent.run(prompt))
