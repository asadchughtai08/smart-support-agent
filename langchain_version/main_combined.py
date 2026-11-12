# ============================================
# SMART SUPPORT AGENT - COMBINED VERSION
# Routing (RunnableBranch) + Tools (asli agent) + Reflection
# Pehle code routing se sahi agent chunta hai,
# phir wo agent khud tay karta hai ke kaunsa tool chalana hai.
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
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough  # routing ke liye
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
# Dhyan: LLM tool ko uske DOCSTRING (teen quotes wali line) se samajhta hai.

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

# Chain 1: intent pehchanne wali chain (routing ke liye)
intent_prompt = ChatPromptTemplate.from_template(  # intent ka prompt
    """
Identify the intent of this customer query.

Possible intents:
- order_tracking
- refund
- technical_issue
- purchase
- general

Return only the intent.

Customer Query: {query}
"""
)
intent_chain = (
    intent_prompt  # pehle prompt
    | llm  # phir model
    | StrOutputParser()  # phir jawab text mein
    | RunnableLambda(lambda text: text.strip().lower())  # extra space hatao aur lowercase karo
)

# Chain 2: un agents ke liye jin ko tools ki zaroorat nahi
other_prompt = ChatPromptTemplate.from_template(  # normal wala prompt
    """
You are a {agent}.

Answer the customer's query in a helpful
and simple way.

Customer Query: {query}
Intent: {intent}
"""
)
other_chain = other_prompt | llm | StrOutputParser()  # prompt -> model -> text

# Chain 3: reflection chain
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
# 7. TOOL AGENT (ye hai combine ka asal hissa)
# --------------------------------------------
def run_tool_agent(agent_name, system_text, agent_tools, query):  # ek agent jo apne tools khud chunta hai
    print("\n--- STEP 2: ROUTING ---")  # heading print karo
    print("Selected Agent:", agent_name)  # agent ka naam dikhao

    llm_with_tools = llm.bind_tools(agent_tools)  # Gemini ko sirf is agent ke tools do
    tools_by_name = {t.name: t for t in agent_tools}  # naam se tool dhoondne ke liye dictionary

    messages = [  # chat history list
        SystemMessage(content=system_text),  # agent ka role
        HumanMessage(content=query),  # customer ka sawal
    ]

    print("\n--- STEP 3: TOOL AGENT ---")  # heading print karo
    for step in range(5):  # zyada se zyada 5 baar loop, taake kabhi infinite na chale
        ai_message = llm_with_tools.invoke(messages)  # Gemini ko history do (Gemini call)
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

    return get_text(ai_message.content)  # Gemini ka aakhri jawab wapas do


# --------------------------------------------
# 8. HANDLERS (har intent ka apna handler)
# --------------------------------------------
# Har handler ko ek dictionary x milti hai: {"query": ..., "intent": ...}

def order_handler(x):  # Order Agent: sirf status check kar sakta hai
    return run_tool_agent(  # tool agent chalao
        "Order Agent",  # agent ka naam
        "You are an order tracking agent. Use tools to get real order data. Never invent order information.",  # role
        [get_order_status],  # is agent ke paas sirf ye ek tool hai
        x["query"],  # customer ka sawal
    )


def refund_handler(x):  # Refund Agent: status bhi dekh sakta hai aur refund bhi kar sakta hai
    return run_tool_agent(  # tool agent chalao
        "Refund Agent",  # agent ka naam
        "You are a refund agent. Check the order status first, then request a refund if allowed. Never invent order information.",  # role
        [get_order_status, request_refund],  # is agent ke paas dono tools hain
        x["query"],  # customer ka sawal
    )


def agent_answer(agent_name, x):  # baqi agents ka common kaam (tools ke baghair)
    print("\n--- STEP 2: ROUTING ---")  # heading print karo
    print("Selected Agent:", agent_name)  # agent ka naam dikhao
    return other_chain.invoke(  # chain chalao aur jawab wapas do
        {"agent": agent_name, "query": x["query"], "intent": x["intent"]}  # prompt ki values
    )


def technical_handler(x):  # Technical Agent
    return agent_answer("Technical Agent", x)  # common function ko agent ka naam do


def purchase_handler(x):  # Purchase Agent
    return agent_answer("Purchase Agent", x)  # common function ko agent ka naam do


def general_handler(x):  # General Support Agent (default)
    return agent_answer("General Support Agent", x)  # common function ko agent ka naam do


# --------------------------------------------
# 9. ROUTING: RunnableBranch
# --------------------------------------------
delegation_branch = RunnableBranch(
    (lambda x: "order" in x["intent"], RunnableLambda(order_handler)),  # "order" ho to Order Agent
    (lambda x: "refund" in x["intent"], RunnableLambda(refund_handler)),  # "refund" ho to Refund Agent
    (lambda x: "technical" in x["intent"], RunnableLambda(technical_handler)),  # "technical" ho to Technical Agent
    (lambda x: "purchase" in x["intent"], RunnableLambda(purchase_handler)),  # "purchase" ho to Purchase Agent
    RunnableLambda(general_handler),  # koi match na ho to General Agent (default)
)


def show_intent(x):  # intent print karne ka chota function
    print("\n--- STEP 1: INTENT EXTRACTION ---")  # heading print karo
    print("Intent:", x["intent"])  # intent dikhao
    return x  # dictionary ko aage bhej do (badle baghair)


coordinator = (
    RunnablePassthrough.assign(intent=intent_chain)  # dictionary mein "intent" naya key jor do
    | RunnableLambda(show_intent)  # intent print karo
    | delegation_branch  # sahi handler chalao
)

# --------------------------------------------
# 10. PROGRAM START
# --------------------------------------------
query = input("Enter your query: ")  # customer se sawal lo

answer = coordinator.invoke({"query": query})  # poora flow ek hi call mein chalao

print("\n--- STEP 4: FINAL ANSWER ---")  # heading print karo
print(answer)  # pehla jawab dikhao

# --------------------------------------------
# 11. REFLECTION
# --------------------------------------------
try:  # error aaye to program crash na ho
    final_answer = review_chain.invoke({"query": query, "answer": answer})  # jawab review karwao
    print("\n--- STEP 5: REFLECTION ---")  # heading print karo

except Exception as e:  # agar reflection fail ho jaye
    final_answer = answer  # to pehla jawab hi final maan lo
    print("error in reflection step:", e)  # error dikhao

print(final_answer)  # final jawab dikhao

# ============================================
# END OF PROJECT CODE
# ============================================
