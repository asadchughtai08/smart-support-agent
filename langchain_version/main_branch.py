# ============================================
# SMART SUPPORT AGENT - RunnableBranch Routing
# Prompt Chaining + Routing + Tool Use + Reflection
# ============================================

# --------------------------------------------
# 1. IMPORTS
# --------------------------------------------
import os  # environment variables parhne ke liye
import re  # query mein se order ID nikalne ke liye
from dotenv import load_dotenv  # .env file se API key load karne ke liye
from langchain_google_genai import ChatGoogleGenerativeAI  # LangChain ka Gemini model
from langchain_core.prompts import ChatPromptTemplate  # prompt template banane ke liye
from langchain_core.output_parsers import StrOutputParser  # model ka jawab simple text mein lene ke liye
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough  # routing ke liye

# --------------------------------------------
# 2. API CONFIGURATION
# --------------------------------------------
load_dotenv()  # .env file ki API key load karo

llm = ChatGoogleGenerativeAI(  # Gemini model bana rahe hain
    model="gemini-3.5-flash-lite",  # model ka naam
    google_api_key=os.getenv("GEMINI_API_KEY"),  # .env se API key lo
    #temperature=0,  # 0 rakha taake routing har baar same aaye
)

# --------------------------------------------
# 3. TOOL: ORDER STATUS
# --------------------------------------------
orders = {  # fake order data
    "1234": "Shipped",  # order 1234 ka status
    "1235": "Processing",  # order 1235 ka status
    "1236": "Delivered",  # order 1236 ka status
}


def extract_order_id(query):  # query mein se 4 digit order ID nikalta hai
    match =re.search(r"(?<!\d)\d{4}(?!\d)", query)  # 4 digit ka number dhoondo
    if match:  # agar mil gaya
        return match.group()  # number wapas do
    else:  # agar nahi mila
        return None  # None wapas do     


def get_order_status(order_id):  # order ka status batata hai
    status = orders.get(order_id)  # dictionary se status dhoondo
    if status:  # agar order mil gaya
        return status  # status wapas do
    else:  # agar nahi mila
        return "Order not found"  # not found ka message do


# --------------------------------------------
# 4. CHAINS (prompt | llm | parser)
# --------------------------------------------

# Chain 1: intent pehchanne wali chain
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
    | RunnableLambda(lambda text: text.strip().lower())  # extra space hatao aur lowercase karo (exact match ke liye zaroori)
)

# Chain 2: order agent ka jawab banane wali chain
order_prompt = ChatPromptTemplate.from_template(  # order wala prompt
    """
You are a customer support agent.

The customer's order ID is {order_id}.
The actual order status is {result}.

Customer Query: {query}

Answer the customer in a simple and friendly way.

Do not invent any order information.
"""
)
order_chain = order_prompt | llm | StrOutputParser()  # prompt -> model -> text

# Chain 3: baqi agents ka jawab banane wali chain
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

# Chain 4: reflection chain
review_prompt = ChatPromptTemplate.from_template(  # review ka prompt
    """
Review this customer support answer.
Is it correct and helpful?
Do not invent information.

Customer Query: {query}
Answer: {answer}

Return the improved answer.
"""
)
review_chain = review_prompt | llm | StrOutputParser()  # prompt -> model -> text


# --------------------------------------------
# 5. HANDLERS (har agent ka apna function)
# --------------------------------------------
# Har handler ko ek dictionary x milti hai: {"query": ..., "intent": ...}

def agent_answer(agent_name, x):  # baqi sab agents ka common kaam
    print("\n--- STEP 2: ROUTING ---")  # heading print karo
    print("Selected Agent:", agent_name)  # agent ka naam dikhao
    return other_chain.invoke(  # chain chalao aur jawab wapas do
        {"agent": agent_name, "query": x["query"], "intent": x["intent"]}  # prompt ki values
    )


def order_handler(x):  # Order Agent (ye tool bhi chalata hai)
    query = x["query"]  # dictionary se query nikalo
    print("\n--- STEP 2: ROUTING ---")  # heading print karo
    print("Selected Agent: Order Agent")  # agent ka naam dikhao

    order_id = extract_order_id(query)  # query se order ID nikalo
    if order_id:  # agar ID mil gayi
        result = get_order_status(order_id)  # tool se status lo
    else:  # agar ID nahi mili
        result = "Order ID not found in the query."  # message set karo

    print("\n--- STEP 3: TOOL EXECUTION ---")  # heading print karo
    print("Extracted Order ID:", order_id)  # ID dikhao

    return order_chain.invoke(  # chain chalao aur jawab wapas do
        {"order_id": order_id, "result": result, "query": query}  # prompt ki values
    )


def refund_handler(x):  # Refund Agent
    return agent_answer("Refund Agent", x)  # common function ko agent ka naam do


def technical_handler(x):  # Technical Agent
    return agent_answer("Technical Agent", x)  # common function ko agent ka naam do


def purchase_handler(x):  # Purchase Agent
    return agent_answer("Purchase Agent", x)  # common function ko agent ka naam do


def general_handler(x):  # General Support Agent (default)
    return agent_answer("General Support Agent", x)  # common function ko agent ka naam do


# --------------------------------------------
# 6. ROUTING: RunnableBranch
# --------------------------------------------
# RunnableBranch ek if / elif / else ki tarah kaam karta hai.
# Har line (condition, handler) ka jora hai. Aakhri wala default (else) hai.
delegation_branch = RunnableBranch(
    (lambda x: "order" in x["intent"], RunnableLambda(order_handler)),  # intent mein "order" ho to Order Agent
    (lambda x: "refund" in x["intent"], RunnableLambda(refund_handler)),  # "refund" ho to Refund Agent
    (lambda x: "technical" in x["intent"], RunnableLambda(technical_handler)),  # "technical" ho to Technical Agent
    (lambda x: "purchase" in x["intent"], RunnableLambda(purchase_handler)),  # "purchase" ho to Purchase Agent
    RunnableLambda(general_handler),  # koi match na ho to General Agent (default)
)


def show_intent(x):  # intent print karne ka chota function
    print("\n--- STEP 1: INTENT EXTRACTION ---")  # heading print karo
    print("Intent:", x["intent"])  # intent dikhao
    return x  # dictionary ko aage bhej do (badle baghair)


# Poora coordinator: intent nikalo -> print karo -> sahi branch chalao
coordinator = (
    RunnablePassthrough.assign(intent=intent_chain)  # dictionary mein "intent" naya key jor do
    | RunnableLambda(show_intent)  # intent print karo
    | delegation_branch  # sahi handler chalao
)

# --------------------------------------------
# 7. PROGRAM START
# --------------------------------------------
query = input("Enter your query: ")  # customer se sawal lo

answer = coordinator.invoke({"query": query})  # poora flow ek hi call mein chalao

print("\n--- STEP 4: FINAL ANSWER ---")  # heading print karo
print(answer)  # pehla jawab dikhao

# --------------------------------------------
# 8. REFLECTION
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
