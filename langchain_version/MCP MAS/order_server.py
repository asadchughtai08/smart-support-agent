# ============================================
# ORDER MCP SERVER
# Tools (get_order_status, request_refund) ab agent ki file mein nahi,
# balkay is alag program (server) mein hain.
# Is file ko aap khud nahi chalate, client isay khud shuru karta hai.
# Install: pip install langchain-mcp-adapters   (mcp aur FastMCP sath aa jate hain)
# ============================================

# --------------------------------------------
# 1. IMPORTS
# --------------------------------------------
import sys  # stderr pe print karne ke liye
from mcp.server.fastmcp import FastMCP  # MCP server banane wali class

# --------------------------------------------
# 2. SERVER BANANA
# --------------------------------------------
mcp = FastMCP("OrderServer")  # server ka naam

# --------------------------------------------
# 3. DATA (fake orders)
# --------------------------------------------
orders = {  # order ID aur uska status
    "1234": "Shipped",  # order 1234 bhej diya gaya
    "1235": "Processing",  # order 1235 process ho raha hai
    "1236": "Delivered",  # order 1236 pohanch chuka hai
}


# --------------------------------------------
# 4. TOOLS
# --------------------------------------------
# Dhyan: yahan print() normal nahi chalta.
# stdout MCP ke apne messages ke liye hota hai, print() use kharab kar deta hai.
# Is liye hum sirf stderr pe print karte hain.

@mcp.tool()  # ye function MCP tool ban gaya
def get_order_status(order_id: str) -> str:  # order_id ek text hai
    """Order ka status batata hai. Input: 4 digit order ID, jaise 1234."""  # yehi description client ko jati hai
    print(f"[SERVER] get_order_status({order_id})", file=sys.stderr)  # server ki taraf se log
    return orders.get(order_id, "Order not found")  # status do, warna "not found"


@mcp.tool()  # ye bhi MCP tool hai
def request_refund(order_id: str) -> str:  # order_id ek text hai
    """Order ka refund request karta hai. Refund sirf Delivered order ka ho sakta hai."""  # yehi description client ko jati hai
    print(f"[SERVER] request_refund({order_id})", file=sys.stderr)  # server ki taraf se log
    status = orders.get(order_id)  # order ka status nikalo
    if status is None:  # agar order mila hi nahi
        return "Order not found"  # not found batao
    if status != "Delivered":  # agar order abhi deliver nahi hua
        return f"Refund not possible. Order status is {status}."  # refund mumkin nahi
    return f"Refund request created for order {order_id}."  # refund request ban gayi


# --------------------------------------------
# 5. SERVER CHALANA
# --------------------------------------------
if __name__ == "__main__":  # file seedhi chale to
    mcp.run(transport="stdio")  # stdio ke zariye client ka intezar karo
