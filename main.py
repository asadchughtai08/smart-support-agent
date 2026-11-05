
# ============================================
# SMART SUPPORT AGENT
# Prompt Chaining + Routing + Tool Use
# ============================================


# --------------------------------------------
# 1. IMPORTS
# --------------------------------------------

# Gemini AI ko use karne ke liye
from google import genai

# .env file se API key load karne ke liye
from dotenv import load_dotenv

# Environment variables read karne ke liye
import os

import re

# --------------------------------------------
# 2. API CONFIGURATION
# --------------------------------------------

# .env file ki API key load karo
load_dotenv()

# Gemini client create karo
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# AI model ka naam ek variable mein rakhna
# Isse model change karna easy hota hai
MODEL = "gemini-3.5-flash-lite"


# --------------------------------------------
# 3. TOOL: ORDER STATUS
# --------------------------------------------

# Fake/local order data
# Dictionary mein order ID aur status store hain

orders = {
    "1234": "Shipped",
    "1235": "Processing",
    "1236": "Delivered"
}


def extract_order_id(query):

    match = re.search(r"\b\d{4}\b", query)

    if match:
        return match.group()

    else:
        return None

# Order status check karne ka function
def get_order_status(order_id):

    # Dictionary se order status find karo
    status = orders.get(order_id)

    # Agar order mil gaya
    if status:
        return status

    # Agar order nahi mila
    else:
        return "Order not found"


# --------------------------------------------
# 4. CUSTOMER QUERY
# --------------------------------------------

# Customer se query input lena
query = input("Enter your query: ")


# --------------------------------------------
# 5. PROMPT CHAINING: INTENT EXTRACTION
# --------------------------------------------

# First prompt:
# Customer query ka intent identify karna

prompt1 = f"""
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


# Gemini ko first prompt bhejna
response1 = client.models.generate_content(
    model=MODEL,
    contents=prompt1
)


# AI ka output intent variable mein store karo
intent = response1.text.strip()


# Console par intent print karo
print("\n--- STEP 1: INTENT EXTRACTION ---")
print("Intent:", intent)


# --------------------------------------------
# 6. ROUTING
# --------------------------------------------

# Intent ke mutabiq correct agent select karo

if "order" in intent.lower():

    # Order tracking query
    agent = "Order Agent"

elif "refund" in intent.lower():

    # Refund query
    agent = "Refund Agent"

elif "technical" in intent.lower():

    # Technical problem
    agent = "Technical Agent"

elif "purchase" in intent.lower():

    # Purchase related query
    agent = "Purchase Agent"

else:

    # Default agent
    agent = "General Support Agent"


# Selected agent print karo
print("\n--- STEP 2: ROUTING ---")
print("Selected Agent:", agent)


# --------------------------------------------
# 7. TOOL EXECUTION
# --------------------------------------------

# result ko initialize karna
# Taake variable undefined na ho

result = None

# Order ID ko initialize karna
order_id = None


# Agar Order Agent select hua

if agent == "Order Agent":

    
    order_id=extract_order_id(query)

    if order_id:
        
        result = get_order_status(order_id)

        print("\n--- STEP 3: TOOL EXECUTION ---")
        print("Extracted Order ID:", order_id)

    else:
        result = "Order ID not found in the query."

        print("\n--- STEP 3: TOOL EXECUTION ---")
        print("Extracted Order ID: None")


# --------------------------------------------
# 8. PROMPT CHAINING: ANSWER GENERATION
# --------------------------------------------

# Agar Order Agent hai to tool result use karo

if agent == "Order Agent":

    prompt2 = f"""
    You are a customer support agent.

    The customer's order ID is {order_id}.
    The actual order status is {result}.

    Customer Query: {query}

    Answer the customer in a simple and friendly way.

    Do not invent any order information.
    """

# Agar Order Agent nahi hai
else:

    prompt2 = f"""
    You are a {agent}.

    Answer the customer's query in a helpful
    and simple way.

    Customer Query: {query}
    Intent: {intent}
    """


# Gemini ko second prompt bhejna
response2 = client.models.generate_content(
    model=MODEL,
    contents=prompt2
)


# Final answer text store karna
answer = response2.text


# --------------------------------------------
# 9. FINAL ANSWER
# --------------------------------------------

print("\n--- STEP 4: FINAL ANSWER ---")
print(answer)


# STEP 5: REFLECTION

review_prompt = f"""
Review this customer support answer.
Is it correct and helpful?
Do not invent information.

Customer Query: {query}
Answer: {answer}

Return the improved answer.
"""
try:
    review_response = client.models.generate_content(
        model=MODEL,
        contents=review_prompt
    )

    final_answer = review_response.text
    print("\n--- STEP 5: REFLECTION ---")

except Exception as e: 

    final_answer = answer
    print("error in reflection step:", e)    

print(final_answer)

# ============================================
# END OF PROJECT CODE
# ============================================
