import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.host = os.getenv("MYSQL_HOST", "localhost")
        self.user = os.getenv("MYSQL_USER", "root")
        self.password = os.getenv("MYSQL_PASSWORD", "")
        self.database = os.getenv("MYSQL_DB", "kis_trading")

    def _get_connection(self):
        return mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database
        )

    def initialize_db(self):
        try:
            conn = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            cursor.execute(f"USE {self.database}")

            # Trading Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trading_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    market_type VARCHAR(20),
                    user_prompt TEXT,
                    decision VARCHAR(20),
                    stock_name VARCHAR(100),
                    quantity INT,
                    reason TEXT,
                    confidence FLOAT,
                    market_data JSON,
                    raw_response JSON
                )
            """)
            conn.commit()
            print("Database and tables initialized.")
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def log_trading(self, market_type, user_prompt, decision_data, market_data):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            sql = """
                INSERT INTO trading_logs
                (market_type, user_prompt, decision, stock_name, quantity, reason, confidence, market_data, raw_response)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                market_type,
                user_prompt,
                decision_data.get("action"),
                decision_data.get("stock_name"),
                decision_data.get("quantity"),
                decision_data.get("reason"),
                decision_data.get("confidence"),
                json.dumps(market_data, ensure_ascii=False),
                json.dumps(decision_data, ensure_ascii=False)
            )
            cursor.execute(sql, values)
            conn.commit()
        except Error as e:
            print(f"Error logging to database: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def get_logs(self, limit=50):
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM trading_logs ORDER BY timestamp DESC LIMIT %s", (limit,))
            return cursor.fetchall()
        except Error as e:
            print(f"Error fetching logs: {e}")
            return []
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

if __name__ == "__main__":
    import json
    db = DatabaseManager()
    db.initialize_db()
