from http.server import BaseHTTPRequestHandler
import json, os, requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
API_KEY    = os.environ.get("GEMINI_API_KEY", "")

PROMPT = """คุณคือผู้เชี่ยวชาญด้านการอ่านใบกำกับภาษี (Tax Invoice) ภาษาไทย อังกฤษ จีน และลายมือ

ส่งผลลัพธ์เป็น JSON array เท่านั้น ห้ามมีข้อความอื่น ห้ามมี markdown backtick
แม้พบใบเดียวก็ให้ส่งเป็น array ที่มี 1 element

[{"invoice_date":"DD.MM.YYYY หรือ null","invoice_date_thai":"วว.ดด.ปปปป หรือ null","buyer_name":"null","buyer_tax_id":"13หลักตัวเลขล้วน หรือ null","buyer_branch":"null","buyer_address":"null","seller_name":"null","seller_tax_id":"13หลักตัวเลขล้วน หรือ null","seller_branch":"null","seller_address":"null","amount_before_vat":"ตัวเลขทศนิยม หรือ null","vat_amount":"ตัวเลขทศนิยม หรือ null","total_with_vat":"ตัวเลขทศนิยม หรือ null","source_page":"หน้าที่พบ หรือ null","uncertain_fields":["field:เหตุผล"],"notes":"null"}]

กฎ: เลขภาษีตัวเลขล้วนไม่มีขีด · ยอดเงินตัวเลขล้วนไม่มีบาทไม่มีลูกน้ำ · ไม่พบใส่ null · ไม่มั่นใจระบุใน uncertain_fields"""


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if not API_KEY:
            self._json(500, {"error": "GEMINI_API_KEY ยังไม่ได้ตั้งค่าใน Vercel Environment Variables"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data   = json.loads(self.rfile.read(length))

            b64      = data["b64"]
            mime     = data["mime"]
            filename = data.get("filename", "file")
            is_pdf   = mime == "application/pdf"
            extra    = "เอกสารนี้อาจมีหลายหน้า กรุณาดึงข้อมูลใบกำกับภาษีทุกใบที่พบ" if is_pdf else ""

            payload = {
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime, "data": b64}},
                        {"text": f"ไฟล์: {filename}\n{extra}\n\n{PROMPT}"}
                    ]
                }],
                "generationConfig": {"temperature": 0, "maxOutputTokens": 4000}
            }

            resp = requests.post(f"{GEMINI_URL}?key={API_KEY}", json=payload, timeout=120)
            resp.raise_for_status()

            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(text)
            self._json(200, {"result": parsed if isinstance(parsed, list) else [parsed]})

        except requests.HTTPError as e:
            self._json(e.response.status_code, {"error": e.response.text[:300]})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, *_): pass
