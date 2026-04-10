import subprocess
import random
import re
import ipaddress
from typing import Optional
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse

app = FastAPI()

# --- 1. NFTABLES CORE ---

def run_nft(args):
    cmd = ["sudo", "nft"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip(), result.stderr.strip()

@app.on_event("startup")
def init_brook_firewall():
    run_nft(["add", "table", "ip", "nat"])
    run_nft(["add", "chain", "ip", "nat", "PREROUTING",
             "{ type nat hook prerouting priority dstnat; }"])
    run_nft(["add", "set", "ip", "nat", "brook",
             "{ type ipv4_addr; flags timeout, dynamic; }"])

    run_nft([
        "add", "rule", "ip", "nat", "PREROUTING",
        "ip", "saddr", "@brook",
        "tcp", "dport", "443",
        "update", "@brook", "{", "ip", "saddr", "timeout", "3600s", "}",
        "redirect", "to", ":8080"
    ])

# --- 解析 nft set ---
def get_brook_ips():
    success, stdout, _ = run_nft(["list", "set", "ip", "nat", "brook"])
    if not success:
        return []

    results = []

    # ✅ 优先匹配 expires（最重要）
    expires_pattern = r"(\d+\.\d+\.\d+\.\d+).*?expires\s+([\w\d]+)"
    expires_matches = re.findall(expires_pattern, stdout)

    # 转成 dict 方便后面合并
    expires_dict = {ip: exp for ip, exp in expires_matches}

    # ✅ 再匹配 timeout（作为 fallback）
    timeout_pattern = r"(\d+\.\d+\.\d+\.\d+).*?timeout\s+([\w\d]+)"
    timeout_matches = re.findall(timeout_pattern, stdout)

    for ip, timeout in timeout_matches:
        if ip in expires_dict:
            results.append((ip, expires_dict[ip]))  # ⭐ 用 expires
        else:
            results.append((ip, f"timeout {timeout}"))

    # ✅ 兜底（极端情况）
    if not results:
        ips = re.findall(r"\d+\.\d+\.\d+\.\d+", stdout)
        results = [(ip, "N/A") for ip in ips]

    return results

# --- IP 校验 ---
def validate_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except:
        return False

# --- 2. UI ---

def generate_html(message: str = "", msg_type: str = "info"):
    num1, num2 = random.randint(1, 10), random.randint(1, 10)
    ans = num1 + num2

    active_ips = get_brook_ips()

    rows = "".join([
        f"<tr><td>{ip}</td><td>{exp}</td></tr>"
        for ip, exp in active_ips
    ])

    color = "green" if msg_type == "success" else "red"
    alert = f"<p style='color:{color};font-weight:bold'>{message}</p>" if message else ""

    return f"""
    <html>
    <head><meta charset="UTF-8"><title>Brook Manager</title>
    <style>
        body {{ font-family: sans-serif; max-width: 450px; margin: 40px auto; text-align: center; }}
        .box {{ border: 1px solid #ccc; padding: 20px; border-radius: 8px; background: #f9f9f9; }}
        input {{ width: 90%; padding: 10px; margin: 10px 0; }}
        button {{ width: 95%; padding: 12px; background: #28a745; color: white; border: none; cursor: pointer; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; border-bottom: 1px solid #ddd; font-size: 0.9em; }}
    </style>
    </head>
    <body>
        <div class="box">
            <h2>NFTable web ui demo</h2>
            {alert}
            <form action="/fastapiPortal/toggle" method="post">
                <input type="text" name="custom_ip" placeholder="Target IP (Optional)">
                <p>Math: <b>{num1} + {num2} = ?</b></p>
                <input type="number" name="user_ans" required>
                <input type="hidden" name="real_ans" value="{ans}">
                <button type="submit">Toggle Status</button>
            </form>
        </div>

        <h3>Current Redirected IPs</h3>
        <table>
            <thead><tr><th>IP Address</th><th>Expires</th></tr></thead>
            <tbody>{rows or '<tr><td colspan="2">No active IPs</td></tr>'}</tbody>
        </table>
    </body>
    </html>
    """
def get_target_ip(request: Request, custom_ip: Optional[str]) -> str:
    # 1️⃣ 用户输入优先（必须校验）
    if custom_ip and custom_ip.strip():
        ip = custom_ip.strip()
        if validate_ip(ip):
            return ip
        else:
            raise ValueError("Invalid custom IP")

    # 2️⃣ 仅信任来自本机代理的 header（Nginx）
    client_host = request.client.host

    if client_host in ("127.0.0.1", "::1"):
        x_real_ip = request.headers.get("x-real-ip")
        if x_real_ip and validate_ip(x_real_ip):
            return x_real_ip
    # 3️⃣ fallback
    return client_host

# --- 3. ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def index():
    return generate_html()

@app.post("/toggle", response_class=HTMLResponse)
async def toggle(
    request: Request,
    user_ans: int = Form(...),
    real_ans: int = Form(...),
    custom_ip: Optional[str] = Form(None)
):
    if user_ans != real_ans:
        return generate_html("Math Error!", "error")

    # 目标 IP
    # target_ip = custom_ip.strip() if custom_ip and custom_ip.strip() else request.client.host
    target_ip = get_target_ip(request,  custom_ip)

    if not validate_ip(target_ip):
        return generate_html("Invalid IP!", "error")

    current_list = [ip for ip, _ in get_brook_ips()]

    # --- TOGGLE ---
    if target_ip in current_list:
        success, _, err = run_nft([
            "delete", "element", "ip", "nat", "brook",
            f"{{ {target_ip} }}"
        ])
        msg = f"Removed: {target_ip}" if success else err
    else:
        success, _, err = run_nft([
            "add", "element", "ip", "nat", "brook",
            f"{{ {target_ip} timeout 1h }}"
        ])
        msg = f"Added: {target_ip}" if success else err

    # ⭐ 再次读取，确保页面展示最新状态
    return generate_html(msg, "success" if success else "error")

# --- MAIN ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
