# ============================================
# SMART SUPPORT AGENT - TOOLS VERSION (Asli Agent)
# Yahan LLM khud tay karta hai ke kaunsa tool chalana hai
# Install: pip install langchain langchain-google-genai python-dotenv
# ============================================

# --------------------------------------------
# 1. IMPORTS
# --------------------------------------------
import os  # environment variables parhne ke liye
from dotenv import load_dotenv  # .env file se API key load karne ke liye
from langchain_google_genai import ChatGoogleGenerativeAI  # LangChain ka Gemini model
from langchain_core.tools import tool  # function ko tool banane wala decorator
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage  # chat ke message types

# --------------------------------------------
# 2. API CONFIGURATION
# --------------------------------------------
load_dotenv()  # .env file ki API key load karo

llm = ChatGoogleGenerativeAI(  # Gemini model bana rahe hain
    model="gemini-3.5-flash-lite",  # model ka 
    
    google_api_key=os.getenv("GEMINI_API_KEY"),  # .env se API key lo
)

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
# Dhyan: LLM tool ko uske DOCSTRING (teen quotes wali line) se samajhta hai.
# Is liye docstring saaf aur sahi likhna zaroori hai.

@tool  # ye decorator is function ko LLM ka tool bana deta hai
def get_order_status(order_id: str) -> str:  # order_id ek text (string) hai
    """Order ka status batata hai. Input: 4 digit order ID, jaise 1234."""  # LLM ye padh kar tool samajhta hai
    print(f"   [TOOL CHALA] get_order_status(order_id={order_id})")  # screen pe dikhao tool chala
    return orders.get(order_id, "Order not found")  # status do, warna "not found"


@tool  # ye bhi LLM ka tool hai
def request_refund(order_id: str) -> str:  # order_id ek text hai
    """Order ka refund request karta hai. Refund sirf Delivered order ka ho sakta hai."""  # LLM ke liye description
    print(f"   [TOOL CHALA] request_refund(order_id={order_id})")  # screen pe dikhao tool chala
    status = orders.get(order_id)  # order ka status nikalo
    if status is None:  # agar order mila hi nahi
        return "Order not found"  # not found batao
    if status != "Delivered":  # agar order abhi deliver nahi hua
        return f"Refund not possible. Order status is {status}."  # refund mumkin nahi
    return f"Refund request created for order {order_id}."  # refund request ban gayi


tools = [get_order_status, request_refund]  # saare tools ki list
tools_by_name = {t.name: t for t in tools}  # naam se tool dhoondne ke liye dictionary

# --------------------------------------------
# 5. LLM KO TOOLS DENA
# --------------------------------------------
llm_with_tools = llm.bind_tools(tools)  # ab Gemini ko in tools ka pata hai aur wo inhein chuna kar sakta hai


# --------------------------------------------
# 6. HELPER: jawab ka text nikalna
# --------------------------------------------
def get_text(content):  # model ka content kabhi text hota hai, kabhi tukron ki list
    if isinstance(content, str):  # agar seedha text hai
        return content  # wahi wapas do
    text = ""  # khali text se shuru
    for part in content:  # list ke har tukre ko dekho
        if isinstance(part, dict) and part.get("type") == "text":  # agar tukra text wala hai
            text += part["text"]  # use jor do
    return text  # poora text wapas do


# --------------------------------------------
# 7. AGENT LOOP
# --------------------------------------------
query = input("Enter your query: ")  # customer se sawal lo

messages = [  # chat history list, isi mein sab kuch jama hota rahega
    SystemMessage(content="You are a customer support agent. Use tools to get real order data. Never invent order information."),  # agent ka role
    HumanMessage(content=query),  # customer ka sawal
]

for step in range(5):  # zyada se zyada 5 baar loop, taake kabhi infinite na chale
    print(f"\n--- STEP {step + 1}: LLM SOCH RAHA HAI ---")  # heading print karo
    ai_message = llm_with_tools.invoke(messages)  # Gemini ko chat history do (Gemini call)
    messages.append(ai_message)  # Gemini ka jawab history mein jor do

    if not ai_message.tool_calls:  # agar Gemini ne koi tool nahi manga
        break  # to jawab tayyar hai, loop khatam

    for call in ai_message.tool_calls:  # Gemini ne jitne tools mange un sab ko dekho
        print(f"LLM ne tool chuna: {call['name']} | args: {call['args']}")  # tool ka naam aur values dikhao
        tool_result = tools_by_name[call["name"]].invoke(call["args"])  # tool asal mein chalao
        print(f"Tool ka result: {tool_result}")  # result dikhao
        messages.append(  # tool ka result history mein jor do
            ToolMessage(content=str(tool_result), tool_call_id=call["id"])  # id se pata chalta hai ye kis call ka jawab hai
        )

# --------------------------------------------
# 8. FINAL ANSWER
# --------------------------------------------
print("\n--- FINAL ANSWER ---")  # heading print karo
print(get_text(ai_message.content))  # Gemini ka aakhri jawab dikhao

# ============================================
# END OF PROJECT CODE
# ============================================
