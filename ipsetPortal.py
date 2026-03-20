import subprocess
import random
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import RedirectResponse

app = FastAPI()
# Add session middleware to store the math answer (just a random one here)
app.add_middleware(SessionMiddleware, secret_key="sdfskdfksk-2fdsf")

IPSET_NAME = "brook"

def check_ip_in_set(ip: str) -> bool:
    result = subprocess.run(["sudo", "ipset", "test", IPSET_NAME, ip], capture_output=True)
    return result.returncode == 0

def toggle_ip_status(ip: str):
    if check_ip_in_set(ip):
        subprocess.run(["sudo", "ipset", "del", IPSET_NAME, ip])
        return "Removed (De-authorized)"
    else:
        subprocess.run(["sudo", "ipset", "add", IPSET_NAME, ip])
        return "Added (Authorized)"

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    client_ip = request.client.host
    is_in_set = check_ip_in_set(client_ip)

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
    subprocess.run(["sudo", "ipset", "create", IPSET_NAME, "hash:net"])
    uvicorn.run(app, host="0.0.0.0", port=8000)
