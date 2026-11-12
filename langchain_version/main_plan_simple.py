# ============================================
# PLANNING - SABSE SIMPLE VERSION
# Step 1: LLM pehle plan banata hai (chhote steps ki list)
# Step 2: Har step ko ek ek kar ke chalao (tools ke sath)
# Step 3: Saare results se final jawab banao
# Install: pip install langchain langchain-google-genai python-dotenv
# ============================================

# --------------------------------------------
# 1. IMPORTS
# --------------------------------------------
import os  # environment variables parhne ke liye
from dotenv import load_dotenv  # .env file se API key load karne ke liye
from langchain_google_genai import ChatGoogleGenerativeAI  # LangChain ka Gemini model
from langchain_core.prompts import ChatPromptTemplate  # prompt template banane ke liye
from langchain_core.output_parsers import StrOutputParser  # model ka jawab simple text mein lene ke liye
from langchain_core.tools import tool  # function ko tool banane wala decorator
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage  # chat ke message types

# --------------------------------------------
# 2. API CONFIGURATION
# --------------------------------------------
load_dotenv()  # .env file ki API key load karo

llm = ChatGoogleGenerativeAI(  # Gemini model bana rahe hain
    model="gemini-3.5-flash-lite",  # model ka naam
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
@tool  # ye function LLM ka tool ban gaya
def get_order_status(order_id: str) -> str:  # order_id ek text hai
    """Order ka status batata hai. Input: 4 digit order ID, jaise 1234."""  # LLM ye padh kar tool samajhta hai
    print(f"      [TOOL CHALA] get_order_status({order_id})")  # screen pe dikhao tool chala
    return orders.get(order_id, "Order not found")  # status do, warna "not found"


@tool  # ye bhi LLM ka tool hai
def request_refund(order_id: str) -> str:  # order_id ek text hai
    """Order ka refund request karta hai. Refund sirf Delivered order ka ho sakta hai."""  # LLM ke liye description
    print(f"      [TOOL CHALA] request_refund({order_id})")  # screen pe dikhao tool chala
    status = orders.get(order_id)  # order ka status nikalo
    if status is None:  # agar order mila hi nahi
        return "Order not found"  # not found batao
    if status != "Delivered":  # agar order abhi deliver nahi hua
        return f"Refund not possible. Order status is {status}."  # refund mumkin nahi
    return f"Refund request created for order {order_id}."  # refund request ban gayi


tools = [get_order_status, request_refund]  # saare tools ki list
tools_by_name = {t.name: t for t in tools}  # naam se tool dhoondne ke liye dictionary
llm_with_tools = llm.bind_tools(tools)  # Gemini ko tools de diye


# --------------------------------------------
# 5. HELPER: jawab ka text nikalna
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
# 6. PLANNER CHAIN: sawal ko steps mein todta hai
# --------------------------------------------
plan_prompt = ChatPromptTemplate.from_template(  # plan banane ka prompt
    """
You are a planner for a customer support agent.
Break the customer's query into 1 to 3 short steps.
Write each step on a new line.
Each step must be self-contained and include any order ID.
Output only the steps, nothing else.

Customer Query: {query}
"""
)
plan_chain = plan_prompt | llm | StrOutputParser()  # prompt -> model -> text

# --------------------------------------------
# 7. FINAL ANSWER CHAIN: saare results se jawab banata hai
# --------------------------------------------
final_prompt = ChatPromptTemplate.from_template(  # final jawab ka prompt
    """
You are a customer support agent.

The customer asked: {query}

These steps were completed:
{results}

Write one short, friendly reply using only these results.
Do not invent any information.
"""
)
final_chain = final_prompt | llm | StrOutputParser()  # prompt -> model -> text


# --------------------------------------------
# 8. EK STEP CHALANE WALA FUNCTION (tool agent)
# --------------------------------------------
def run_step(task):  # ek step ka kaam karta hai, zaroorat ho to tools chalata hai
    messages = [  # chat history list
        SystemMessage(content="You are a support agent. Use tools to get real order data. Never invent order information."),  # role
        HumanMessage(content=task),  # is step ka kaam
    ]

    for i in range(5):  # zyada se zyada 5 baar loop, taake kabhi infinite na chale
        ai_message = llm_with_tools.invoke(messages)  # Gemini ko history do (Gemini call)
        messages.append(ai_message)  # Gemini ka jawab history mein jor do

        if not ai_message.tool_calls:  # agar Gemini ne koi tool nahi manga
            break  # to jawab tayyar hai

        for call in ai_message.tool_calls:  # Gemini ne jo tools mange un ko dekho
            print(f"      LLM ne tool chuna: {call['name']} {call['args']}")  # tool ka naam aur values
            result = tools_by_name[call["name"]].invoke(call["args"])  # tool asal mein chalao
            print(f"      Tool ka result: {result}")  # result dikhao
            messages.append(  # tool ka result history mein jor do
                ToolMessage(content=str(result), tool_call_id=call["id"])  # id se pata chalta hai ye kis call ka jawab hai
            )

    return get_text(ai_message.content)  # Gemini ka aakhri jawab wapas do


# --------------------------------------------
# 9. PROGRAM START
# --------------------------------------------
query = input("Enter your query: ")  # customer se sawal lo

# STEP 1: PLAN BANAO
print("\n--- STEP 1: PLAN ---")  # heading print karo
plan_text = plan_chain.invoke({"query": query})  # Gemini se plan lo (Gemini call)

steps = []  # steps ki khali list
for line in plan_text.split("\n"):  # plan ki har line ko dekho
    line = line.strip()  # line ke aage peeche ke space hatao
    if line:  # agar line khali nahi hai
        steps.append(line)  # to usay steps mein jor do

if not steps:  # agar plan khali aaya
    steps = [query]  # to poora sawal hi ek step maan lo

for number, step in enumerate(steps, start=1):  # saare steps screen pe dikhao
    print(f"{number}. {step}")  # step ka number aur kaam

# STEP 2: STEPS CHALAO
print("\n--- STEP 2: EXECUTION ---")  # heading print karo
results = ""  # pichle steps ke results yahan jama honge

for number, step in enumerate(steps, start=1):  # har step ko ek ek kar ke chalao
    print(f"\n[Step {number}/{len(steps)}] {step}")  # kaunsa step chal raha hai
    task = step  # step ka kaam
    if results:  # agar pehle koi step ho chuka hai
        task = step + "\n\nResults of earlier steps:\n" + results  # pichle results bhi sath do
    step_result = run_step(task)  # step chalao
    print(f"   Step result: {step_result}")  # step ka result dikhao
    results += f"Step {number}: {step_result}\n"  # result jama kar lo

# STEP 3: FINAL JAWAB
print("\n--- STEP 3: FINAL ANSWER ---")  # heading print karo
answer = final_chain.invoke({"query": query, "results": results})  # saare results se jawab banao (Gemini call)
print(answer)  # final jawab dikhao

# ============================================
# END OF PROJECT CODE
# ============================================
