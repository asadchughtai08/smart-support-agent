# ============================================
# SMART SUPPORT AGENT - LANGCHAIN VERSION
# Prompt Chaining + Routing + Tool Use
# Install: pip install langchain langchain-google-genai python-dotenv
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

# --------------------------------------------
# 2. API CONFIGURATION
# --------------------------------------------
load_dotenv()  # .env file ki API key load karo

MODEL = "gemini-3.5-flash-lite"  # model ka naam ek jagah rakha, badalna asaan ho

llm = ChatGoogleGenerativeAI(  # Gemini model bana rahe hain (pehle genai.Client tha)
    model=MODEL,  # upar wala model name use karo
    google_api_key=os.getenv("GEMINI_API_KEY"),  # .env se API key lo
)

# --------------------------------------------
# 3. TOOL: ORDER STATUS
# --------------------------------------------
orders = {  # fake order data, dictionary mein
    "1234": "Shipped",  # order 1234 ka status
    "1235": "Processing",  # order 1235 ka status
    "1236": "Delivered",  # order 1236 ka status
}


def extract_order_id(query):  # query mein se 4 digit order ID nikalne ka function
    match = re.search(r"\b\d{4}\b", query)  # 4 digit ka number dhoondo
    if match:  # agar number mil gaya
        return match.group()  # wo number wapas do
    else:  # agar nahi mila
        return None  # None wapas do


def get_order_status(order_id):  # order ka status check karne ka function
    status = orders.get(order_id)  # dictionary se status dhoondo
    if status:  # agar order mil gaya
        return status  # status wapas do
    else:  # agar order nahi mila
        return "Order not found"  # not found ka message do


# --------------------------------------------
# 4. CUSTOMER QUERY
# --------------------------------------------
query = input("Enter your query: ")  # customer se sawal lo

# --------------------------------------------
# 5. CHAIN 1: INTENT EXTRACTION
# --------------------------------------------
prompt1 = ChatPromptTemplate.from_template(  # pehla prompt (f-string ki jagah template)
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
"""  # {query} mein customer ka sawal aayega
)

intent_chain = prompt1 | llm | StrOutputParser()  # chain: prompt -> model -> text

intent = intent_chain.invoke({"query": query}).strip()  # chain chalao aur extra space hata do

print("\n--- STEP 1: INTENT EXTRACTION ---")  # heading print karo
print("Intent:", intent)  # intent dikhao

# --------------------------------------------
# 6. ROUTING
# --------------------------------------------
if "order" in intent.lower():  # agar intent mein "order" hai
    agent = "Order Agent"  # to Order Agent chuno
elif "refund" in intent.lower():  # agar intent mein "refund" hai
    agent = "Refund Agent"  # to Refund Agent chuno
elif "technical" in intent.lower():  # agar intent mein "technical" hai
    agent = "Technical Agent"  # to Technical Agent chuno
elif "purchase" in intent.lower():  # agar intent mein "purchase" hai
    agent = "Purchase Agent"  # to Purchase Agent chuno
else:  # warna
    agent = "General Support Agent"  # default agent

print("\n--- STEP 2: ROUTING ---")  # heading print karo
print("Selected Agent:", agent)  # agent ka naam dikhao

# --------------------------------------------
# 7. TOOL EXECUTION
# --------------------------------------------
result = None  # shuru mein result khali
order_id = None  # shuru mein order ID khali

if agent == "Order Agent":  # sirf Order Agent ke liye tool chalao
    order_id = extract_order_id(query)  # query se order ID nikalo

    if order_id:  # agar ID mil gayi
        result = get_order_status(order_id)  # tool se status lo
        print("\n--- STEP 3: TOOL EXECUTION ---")  # heading print karo
        print("Extracted Order ID:", order_id)  # ID dikhao
    else:  # agar ID nahi mili
        result = "Order ID not found in the query."  # message set karo
        print("\n--- STEP 3: TOOL EXECUTION ---")  # heading print karo
        print("Extracted Order ID: None")  # None dikhao

# --------------------------------------------
# 8. CHAIN 2: ANSWER GENERATION
# --------------------------------------------
if agent == "Order Agent":  # agar Order Agent hai to tool ka result use karo
    prompt2 = ChatPromptTemplate.from_template(  # order wala prompt
        """
You are a customer support agent.

The customer's order ID is {order_id}.
The actual order status is {result}.

Customer Query: {query}

Answer the customer in a simple and friendly way.

Do not invent any order information.
"""
    )
    inputs = {"order_id": order_id, "result": result, "query": query}  # prompt ki values dictionary mein

else:  # agar Order Agent nahi hai
    prompt2 = ChatPromptTemplate.from_template(  # normal wala prompt
        """
You are a {agent}.

Answer the customer's query in a helpful
and simple way.

Customer Query: {query}
Intent: {intent}
"""
    )
    inputs = {"agent": agent, "query": query, "intent": intent}  # prompt ki values dictionary mein

answer_chain = prompt2 | llm | StrOutputParser()  # chain: prompt -> model -> text

answer = answer_chain.invoke(inputs)  # chain chalao, jawab lo

# --------------------------------------------
# 9. FINAL ANSWER
# --------------------------------------------
print("\n--- STEP 4: FINAL ANSWER ---")  # heading print karo
print(answer)  # pehla jawab dikhao

# --------------------------------------------
# 10. CHAIN 3: REFLECTION
# --------------------------------------------
review_prompt = ChatPromptTemplate.from_template(  # jawab review karne ka prompt
    """
Review this customer support answer.
Is it correct and helpful?
Do not invent information.

Customer Query: {query}
Answer: {answer}

Return the improved answer.
"""
)

review_chain = review_prompt | llm | StrOutputParser()  # chain: prompt -> model -> text

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
