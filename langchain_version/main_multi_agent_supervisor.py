# ============================================
# MULTI-AGENT SYSTEM - WAY 2: SUPERVISOR + AGENTS AS TOOLS
# Har specialist agent ko ek tool mein lapeta gaya hai
# Supervisor (LLM) khud chunta hai ke kaunsa agent chalana hai
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
# 4. SPECIALIST TOOLS (inhein sirf specialist agents use karte hain)
# --------------------------------------------
@tool  # ye function LLM ka tool ban gaya
def get_order_status(order_id: str) -> str:  # order_id ek text hai
    """Order ka status batata hai. Input: 4 digit order ID, jaise 1234."""  # LLM ye padh kar tool samajhta hai
    print(f"         [TOOL CHALA] get_order_status({order_id})")  # screen pe dikhao tool chala
    return orders.get(order_id, "Order not found")  # status do, warna "not found"


@tool  # ye bhi LLM ka tool hai
def request_refund(order_id: str) -> str:  # order_id ek text hai
    """Order ka refund request karta hai. Refund sirf Delivered order ka ho sakta hai."""  # LLM ke liye description
    print(f"         [TOOL CHALA] request_refund({order_id})")  # screen pe dikhao tool chala
    status = orders.get(order_id)  # order ka status nikalo
    if status is None:  # agar order mila hi nahi
        return "Order not found"  # not found batao
    if status != "Delivered":  # agar order abhi deliver nahi hua
        return f"Refund not possible. Order status is {status}."  # refund mumkin nahi
    return f"Refund request created for order {order_id}."  # refund request ban gayi


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
# 6. CHAINS (prompt | llm | parser)
# --------------------------------------------

# General agent ki chain: bina tools ke jawab deta hai
general_prompt = ChatPromptTemplate.from_template(  # general agent ka prompt
    """
You are a general customer support agent.
Answer the request in a helpful and simple way.

Request: {query}
"""
)
general_chain = general_prompt | llm | StrOutputParser()  # prompt -> model -> text

# Reviewer ki chain: jawab ko behtar karti hai
review_prompt = ChatPromptTemplate.from_template(  # review ka prompt
    """
Review this customer support answer.
Is it correct and helpful?
Do not invent information.

Customer Query: {query}
Answer: {answer}

Return ONLY the improved answer text.
Do not add any review, notes, headings or explanation.
"""
)
review_chain = review_prompt | llm | StrOutputParser()  # prompt -> model -> text


# --------------------------------------------
# 7. TOOL AGENT LOOP (jis agent ke paas tools hon wo isay use karta hai)
# --------------------------------------------
def run_tool_agent(agent_name, system_text, agent_tools, query):  # ek agent jo apne tools khud chunta hai
    print(f"      Agent: {agent_name}")  # agent ka naam dikhao
    llm_with_tools = llm.bind_tools(agent_tools)  # Gemini ko sirf is agent ke tools do
    tools_by_name = {t.name: t for t in agent_tools}  # naam se tool dhoondne ke liye dictionary

    messages = [  # chat history list
        SystemMessage(content=system_text),  # agent ka role
        HumanMessage(content=query),  # agent ka kaam
    ]

    for i in range(5):  # zyada se zyada 5 baar loop, taake kabhi infinite na chale
        ai_message = llm_with_tools.invoke(messages)  # Gemini ko history do (Gemini call)
        messages.append(ai_message)  # Gemini ka jawab history mein jor do

        if not ai_message.tool_calls:  # agar Gemini ne koi tool nahi manga
            break  # to jawab tayyar hai

        for call in ai_message.tool_calls:  # Gemini ne jo tools mange un ko dekho
            print(f"         LLM ne tool chuna: {call['name']} {call['args']}")  # tool ka naam aur values
            result = tools_by_name[call["name"]].invoke(call["args"])  # tool asal mein chalao
            print(f"         Tool ka result: {result}")  # result dikhao
            messages.append(  # tool ka result history mein jor do
                ToolMessage(content=str(result), tool_call_id=call["id"])  # id se pata chalta hai ye kis call ka jawab hai
            )

    return get_text(ai_message.content)  # Gemini ka aakhri jawab wapas do


# --------------------------------------------
# 8. SHARED STATE aur AGENTS CHALANE WALA FUNCTION
# --------------------------------------------
shared_state = {"log": ""}  # saare agents ka kaam yahan jama hota hai (sab ke liye common)


def call_agent(agent, task):  # kisi bhi specialist agent ko kaam dena
    full_task = task  # shuru mein sirf kaam
    if shared_state["log"]:  # agar pehle koi agent kaam kar chuka hai
        full_task = task + "\n\nWork done so far by the team:\n" + shared_state["log"]  # to wo bhi sath do

    print(f"   [{agent} agent] task: {task}")  # kaunsa agent aur kaam dikhao

    if agent == "order":  # Order Agent
        result = run_tool_agent(  # tool agent chalao
            "Order Agent",  # naam
            "You are an order tracking agent. Use tools to get real order data. Never invent order information.",  # role
            [get_order_status],  # is ke paas sirf status ka tool
            full_task,  # kaam
        )
    elif agent == "refund":  # Refund Agent
        result = run_tool_agent(  # tool agent chalao
            "Refund Agent",  # naam
            "You are a refund agent. Check the order status first, then request a refund if allowed. Never invent order information.",  # role
            [get_order_status, request_refund],  # is ke paas dono tools
            full_task,  # kaam
        )
    else:  # General Agent (baqi sab)
        result = general_chain.invoke({"query": full_task})  # bina tools ke jawab

    shared_state["log"] += f"[{agent}] {task} -> {result}\n"  # is agent ka result shared state mein jor do
    print(f"   [{agent} agent] result: {result}")  # result dikhao
    return result  # result wapas do


# --------------------------------------------
# 9. AGENTS AS TOOLS (supervisor ke tools)
# --------------------------------------------
# Har specialist agent ko ek tool mein lapet diya.
# Docstring hi supervisor ko batati hai ke ye agent kab use karna hai.

@tool  # Order Agent ab supervisor ka tool hai
def order_agent(request: str) -> str:  # request ek text hai
    """Order Agent. Use it to check the status of an order. Input: a clear request that includes the 4 digit order ID."""  # supervisor ye padhta hai
    return call_agent("order", request)  # asli kaam call_agent karta hai


@tool  # Refund Agent ab supervisor ka tool hai
def refund_agent(request: str) -> str:  # request ek text hai
    """Refund Agent. Use it to request a refund for an order. Input: a clear request that includes the 4 digit order ID."""  # supervisor ye padhta hai
    return call_agent("refund", request)  # asli kaam call_agent karta hai


@tool  # General Agent ab supervisor ka tool hai
def general_agent(request: str) -> str:  # request ek text hai
    """General Agent. Use it for technical problems and any other question that needs no order data. Input: the question."""  # supervisor ye padhta hai
    return call_agent("general", request)  # asli kaam call_agent karta hai


supervisor_tools = [order_agent, refund_agent, general_agent]  # supervisor ke tools yehi 3 agents hain
supervisor_tools_by_name = {t.name: t for t in supervisor_tools}  # naam se tool dhoondne ke liye dictionary
supervisor_llm = llm.bind_tools(supervisor_tools)  # Gemini ko ye tools de do

# --------------------------------------------
# 10. PROGRAM START
# --------------------------------------------
query = input("Enter your query: ")  # customer se sawal lo

# STEP 1: SUPERVISOR AGENTS KO CHALATA HAI
print("\n--- STEP 1: SUPERVISOR ---")  # heading print karo

messages = [  # chat history list
    SystemMessage(content=(  # supervisor ka role
        "You are the supervisor of a customer support team. "
        "Use the agent tools to get the work done. "
        "You may call several agents one after another, and use earlier results. "
        "When the work is done, write one short, friendly reply. Never invent information."
    )),
    HumanMessage(content=query),  # customer ka sawal
]

for i in range(6):  # zyada se zyada 6 baar loop, taake kabhi infinite na chale
    ai_message = supervisor_llm.invoke(messages)  # Gemini ko history do (Gemini call)
    messages.append(ai_message)  # Gemini ka jawab history mein jor do

    if not ai_message.tool_calls:  # agar supervisor ne koi agent nahi manga
        break  # to jawab tayyar hai

    for call in ai_message.tool_calls:  # supervisor ne jo agents mange un ko dekho
        print(f"Supervisor ne agent chuna: {call['name']} {call['args']}")  # agent ka naam aur kaam
        result = supervisor_tools_by_name[call["name"]].invoke(call["args"])  # agent asal mein chalao
        messages.append(  # agent ka result history mein jor do
            ToolMessage(content=str(result), tool_call_id=call["id"])  # id se pata chalta hai ye kis call ka jawab hai
        )

# STEP 2: SUPERVISOR KA JAWAB
print("\n--- STEP 2: SUPERVISOR KA JAWAB ---")  # heading print karo
answer = get_text(ai_message.content)  # supervisor ka aakhri jawab
print(answer)  # pehla jawab dikhao

# STEP 3: REVIEWER
try:  # error aaye to program crash na ho
    final_answer = review_chain.invoke({"query": query, "answer": answer})  # jawab review karwao (Gemini call)
    print("\n--- STEP 3: REVIEWER ---")  # heading print karo

except Exception as e:  # agar reviewer fail ho jaye
    final_answer = answer  # to pehla jawab hi final maan lo
    print("error in reviewer step:", e)  # error dikhao

print(final_answer)  # final jawab dikhao

# ============================================
# END OF PROJECT CODE
# ============================================
