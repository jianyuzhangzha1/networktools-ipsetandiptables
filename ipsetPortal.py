import subprocess
import random
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse

# sudo nft add table ip filter
# sudo nft 'add set ip filter brook { type ipv4_addr; flags timeout, dynamic; }'
# sudo nft add element ip filter brook { 1.2.3.4 timeout 600s }

def init_brook_firewall():
    """
    初始化 nftables 环境：创建表、链、集合及规则。
    """
    commands = [
        # 1. 创建表 (ip 家族)
        ["sudo", "nft", "add", "table", "ip", "filter"],
        
        # 2. 创建 INPUT 基础链 (这是解决 "No such file or directory" 的关键)
        # type filter: 过滤类型; hook input: 挂载到输入钩子; priority 0: 优先级
        ["sudo", "nft", "add", "chain", "ip", "filter", "INPUT", 
         "{ type filter hook input priority 0; }"],
        
        # 3. 创建 brook 集合
        ["sudo", "nft", "add", "set", "ip", "filter", "brook", 
         "{ type ipv4_addr; flags timeout, dynamic; }"],
        
        # 4. 添加规则：仅当 IP 在 @brook 中时，更新其时间并拦截
        ["sudo", "nft", "add", "rule", "ip", "filter", "INPUT", 
         "ip", "saddr", "@brook", 
         "update", "@brook", "{", "ip", "saddr", "timeout", "3600s", "}", 
         "counter", "drop"]
    ]

    for cmd in commands:
        try:
            # 必须捕获输出，否则 {} 中的分号可能会引起子进程层面的误解
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            # 如果是“已存在”类报错则忽略，其他报错打印出来
            if "already exists" not in e.stderr:
                print(f"⚠️ nftables 配置提示: {e.stderr.strip()}")

    print("✅ Brook 防火墙环境初始化完成。")

def update_brook_ip(ip, timeout="3600s"):
    """
    Adds a new IP or resets the timeout of an existing IP in the 'brook' set.
    """
    cmd = [
        "sudo", "nft", "add", "element", "ip", "filter", "brook", 
        f"{{ {ip} timeout {timeout} }}"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"🚀 IP {ip} blocked/reset for {timeout}.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error updating IP {ip}: {e.stderr.strip()}")

app = FastAPI()
# Add session middleware to store the math answer (just a random one here)
app.add_middleware(SessionMiddleware, secret_key="sdfskdfksk-2fdsf")

IPSET_NAME = "brook"


def delete_brook_ip(ip):
    """Manually removes an IP from the brook set immediately."""
    cmd = ["sudo", "nft", "delete", "element", "ip", "filter", "brook", f"{{ {ip} }}"]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"🗑️ IP {ip} has been removed from Brook.")
    except subprocess.CalledProcessError as e:
        # If the IP isn't in the list, nft will return an error
        if "No such file or directory" in e.stderr.decode():
            print(f"ℹ️ IP {ip} was not in the set.")
        else:
            print(f"❌ Error deleting {ip}: {e.stderr.decode().strip()}")

def is_ip_in_brook(ip):
    """Checks if the IP is currently in the 'brook' set."""
    cmd = ["sudo", "nft", "list", "set", "ip", "filter", "brook"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Look for the IP as a whole word to avoid partial matches (e.g., .1 matching .11)
        return ip in result.stdout
    except subprocess.CalledProcessError:
        return False

def toggle_ip_status(client_ip, timeout="3600s"):
    """
    If IP is blocked: Unblock it.
    If IP is free: Block it.
    Returns: True if the IP is NOW blocked, False if it is NOW free.
    """
    if is_ip_in_brook(client_ip):
        # Currently blocked -> Unblock
        delete_brook_ip(client_ip)
        return False
    else:
        # Currently free -> Block
        update_brook_ip(client_ip, timeout)
        return True
            
@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    client_ip = request.client.host
    is_in_set = is_ip_in_brook(client_ip)

    # Generate random math question
    num1, num2 = random.randint(1, 10), random.randint(1, 10)
    request.session["math_answer"] = num1 + num2

    status_text = "Authorized" if is_in_set else "Unauthorized"
    status_color = "green" if is_in_set else "red"

    return f"""
    <html>
        <body style="font-family: sans-serif; padding: 20px;">
            <h2>IP Access Control</h2>
            <p>Your IP: <b>{client_ip}</b></p>
            <p>Status: <span style="color: {status_color}; font-weight: bold;">{status_text}</span></p>
            <hr>
            <form action="/verify" method="post">
                <p>Solve this to toggle status: <b>{num1} + {num2} = ?</b></p>
                <input type="number" name="user_answer" required>
                <input type="submit" value="Submit">
            </form>
        </body>
    </html>
    """

@app.post("/verify")
async def verify_answer(request: Request, user_answer: int = Form(...)):
    client_ip = request.client.host
    correct_answer = request.session.get("math_answer")

    if correct_answer is None:
        return "Session expired. Please refresh the page."

    if user_answer == correct_answer:
        # Clear the answer so it can't be reused
        request.session.pop("math_answer")
        action = toggle_ip_status(client_ip)
        referer = request.headers.get("referer") # 获取来源地址
        return RedirectResponse( "/", status_code=303)
    else:
        return {"status": "Error", "message": "Wrong answer, try again."}


if __name__ == "__main__":
    import uvicorn
    init_brook_firewall()
    uvicorn.run(app, host="0.0.0.0", port=8000)
