# ============================================
# MULTI-AGENT (PLAN) + MCP
# Supervisor text ka plan likhta hai, code agents ko chalata hai.
# Farq: tools ab MCP server (order_server.py) se aate hain.
# Install: pip install langchain langchain-google-genai python-dotenv langchain-mcp-adapters
# ============================================

# --------------------------------------------
# 1. IMPORTS
# --------------------------------------------
import os  # environment variables aur file path ke liye
import sys  # sys.executable (abhi chal rahe python ka path) ke liye
import asyncio  # async code chalane ke liye
from dotenv import load_dotenv  # .env file se API key load karne ke liye
from langchain_google_genai import ChatGoogleGenerativeAI  # LangChain ka Gemini model
from langchain_core.prompts import ChatPromptTemplate  # prompt template banane ke liye
from langchain_core.output_parsers import StrOutputParser  # model ka jawab simple text mein lene ke liye
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage  # chat ke message types
from langchain_mcp_adapters.client import MultiServerMCPClient  # MCP server se tools lene wala client

# --------------------------------------------
# 2. API CONFIGURATION
# --------------------------------------------
load_dotenv()  # .env file ki API key load karo

llm = ChatGoogleGenerativeAI(  # Gemini model bana rahe hain
    model="gemini-3.5-flash-lite",  # model ka naam
    google_api_key=os.getenv("GEMINI_API_KEY"),  # .env se API key lo
)

# --------------------------------------------
# 3. MCP CLIENT (server ki jagah batana)
# --------------------------------------------
SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "order_server.py")  # server file ka path (isi folder mein)

mcp_client = MultiServerMCPClient(  # MCP client bana rahe hain
    {
        "orders": {  # server ka naam
            "command": sys.executable,  # server ko isi python se chalao
            "args": [SERVER_PATH],  # server ki file
            "transport": "stdio",  # baat stdio ke zariye hogi
        }
    }
)

AGENT_TOOLS = {}  # har agent ke tools yahan rakhe jayenge (main() mein bharte hain)

# --------------------------------------------
# 4. HELPER: jawab ka text nikalna
# --------------------------------------------
def get_text(content):  # content kabhi text hota hai, kabhi tukron ki list
    if isinstance(content, str):  # agar seedha text hai
        return content  # wahi wapas do
    text = ""  # khali text se shuru
    for part in content:  # list ke har tukre ko dekho
        if isinstance(part, dict) and part.get("type") == "text":  # agar tukra text wala hai
            text += part["text"]  # use jor do
    return text  # poora text wapas do


# --------------------------------------------
# 5. CHAINS (prompt | llm | parser)
# --------------------------------------------

# Supervisor ki planner chain: sawal ko steps mein todti hai
plan_prompt = ChatPromptTemplate.from_template(  # plan banane ka prompt
    """
You are the supervisor of a customer support team.
Break the customer's query into 1 to 3 small steps.
Each step is handled by one agent. Available agents:
- order: checks the status of an order
- refund: checks order status and requests refunds
- general: technical problems and any other question

Rules:
- Write one step per line in exactly this format: agent | task
- Each task must be self-contained and include any order ID.
- Use as few steps as possible.
- Output only the step lines, nothing else.

Customer Query: {query}
"""
)
plan_chain = plan_prompt | llm | StrOutputParser()  # prompt -> model -> text

# General agent ki chain: bina tools ke jawab deta hai
general_prompt = ChatPromptTemplate.from_template(  # general agent ka prompt
    """
You are a general customer support agent.
Answer the request in a helpful and simple way.

Request: {query}
"""
)
general_chain = general_prompt | llm | StrOutputParser()  # prompt -> model -> text

# Writer ki chain: saare agents ke kaam se jawab likhti hai
final_prompt = ChatPromptTemplate.from_template(  # final jawab ka prompt
    """
You are a customer support agent.

The customer asked: {query}

Our team did this work:
{results}

Write one short, friendly reply using only this work.
Do not invent any information.
"""
)
final_chain = final_prompt | llm | StrOutputParser()  # prompt -> model -> text

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
# 6. TOOL AGENT LOOP (async, kyunke MCP tools async hote hain)
# --------------------------------------------
async def run_tool_agent(agent_name, system_text, agent_tools, query):  # ek agent jo apne tools khud chunta hai
    print(f"      Agent: {agent_name}")  # agent ka naam dikhao
    llm_with_tools = llm.bind_tools(agent_tools)  # Gemini ko sirf is agent ke tools do
    tools_by_name = {t.name: t for t in agent_tools}  # naam se tool dhoondne ke liye dictionary

    messages = [  # chat history list
        SystemMessage(content=system_text),  # agent ka role
        HumanMessage(content=query),  # agent ka kaam
    ]

    for i in range(5):  # zyada se zyada 5 baar loop, taake kabhi infinite na chale
        ai_message = await llm_with_tools.ainvoke(messages)  # Gemini ko history do (async Gemini call)
        messages.append(ai_message)  # Gemini ka jawab history mein jor do

        if not ai_message.tool_calls:  # agar Gemini ne koi tool nahi manga
            break  # to jawab tayyar hai

        for call in ai_message.tool_calls:  # Gemini ne jo tools mange un ko dekho
            print(f"         LLM ne tool chuna: {call['name']} {call['args']}")  # tool ka naam aur values
            result = await tools_by_name[call["name"]].ainvoke(call["args"])  # MCP server pe tool chalao (async)
            result_text = get_text(result) or str(result)  # result ko saaf text banao
            print(f"         MCP tool ka result: {result_text}")  # result dikhao
            messages.append(  # tool ka result history mein jor do
                ToolMessage(content=result_text, tool_call_id=call["id"])  # id se pata chalta hai ye kis call ka jawab hai
            )

    return get_text(ai_message.content)  # Gemini ka aakhri jawab wapas do


# --------------------------------------------
# 7. SHARED STATE aur AGENTS CHALANE WALA FUNCTION
# --------------------------------------------
shared_state = {"log": ""}  # saare agents ka kaam yahan jama hota hai


async def call_agent(agent, task):  # kisi bhi specialist agent ko kaam dena
    full_task = task  # shuru mein sirf kaam
    if shared_state["log"]:  # agar pehle koi agent kaam kar chuka hai
        full_task = task + "\n\nWork done so far by the team:\n" + shared_state["log"]  # to wo bhi sath do

    print(f"   [{agent} agent] task: {task}")  # kaunsa agent aur kaam dikhao

    if agent == "order":  # Order Agent
        result = await run_tool_agent(  # tool agent chalao
            "Order Agent",  # naam
            "You are an order tracking agent. Use tools to get real order data. Never invent order information.",  # role
            AGENT_TOOLS["order"],  # is ke paas sirf status ka MCP tool
            full_task,  # kaam
        )
    elif agent == "refund":  # Refund Agent
        result = await run_tool_agent(  # tool agent chalao
            "Refund Agent",  # naam
            "You are a refund agent. Check the order status first, then request a refund if allowed. Never invent order information.",  # role
            AGENT_TOOLS["refund"],  # is ke paas dono MCP tools
            full_task,  # kaam
        )
    else:  # General Agent (baqi sab)
        result = await general_chain.ainvoke({"query": full_task})  # bina tools ke jawab

    shared_state["log"] += f"[{agent}] {task} -> {result}\n"  # is agent ka result shared state mein jor do
    print(f"   [{agent} agent] result: {result}")  # result dikhao
    return result  # result wapas do


# --------------------------------------------
# 8. PLAN PARSER (plan ke text ko steps ki list banata hai)
# --------------------------------------------
VALID_AGENTS = ["order", "refund", "general"]  # sirf ye agents allowed hain


def parse_plan(plan_text):  # plan ke text se (agent, task) ki list banata hai
    steps = []  # shuru mein khali list
    for line in plan_text.split("\n"):  # plan ki har line ko dekho
        if "|" in line:  # sirf wo lines jin mein "|" ho
            left, task = line.split("|", 1)  # "|" se pehle ka hissa left, baad ka task
            for name in VALID_AGENTS:  # har agent ka naam check karo
                if name in left.lower():  # agar naam left hisse mein maujood hai
                    steps.append((name, task.strip()))  # step list mein jor do
                    break  # naam mil gaya, aage dhoondne ki zaroorat nahi
    return steps[:3]  # zyada se zyada 3 steps rakho


# --------------------------------------------
# 9. MAIN (async)
# --------------------------------------------
async def main():  # poora program yahan chalta hai
    # STEP 0: MCP SERVER SE TOOLS LO
    print("--- STEP 0: MCP SERVER SE TOOLS ---")  # heading print karo
    mcp_tools = await mcp_client.get_tools()  # server shuru hoga aur tools ki list milegi
    print("Tools mile:", [t.name for t in mcp_tools])  # tools ke naam dikhao

    tool_by_name = {t.name: t for t in mcp_tools}  # naam se tool dhoondne ke liye dictionary
    AGENT_TOOLS["order"] = [tool_by_name["get_order_status"]]  # Order Agent ko sirf status ka tool
    AGENT_TOOLS["refund"] = [tool_by_name["get_order_status"], tool_by_name["request_refund"]]  # Refund Agent ko dono

    query = input("\nEnter your query: ")  # customer se sawal lo

    # STEP 1: SUPERVISOR PLAN BANATA HAI
    print("\n--- STEP 1: PLAN ---")  # heading print karo
    plan_text = await plan_chain.ainvoke({"query": query})  # supervisor se plan lo (Gemini call)
    steps = parse_plan(plan_text)  # plan ko steps ki list mein badlo

    if not steps:  # agar plan samajh nahi aaya
        steps = [("general", query)]  # to General Agent poora sawal sambhale

    for number, (agent, task) in enumerate(steps, start=1):  # steps screen pe dikhao
        print(f"{number}. [{agent}] {task}")  # step ka number, agent aur kaam

    # STEP 2: AGENTS KAAM KARTE HAIN
    print("\n--- STEP 2: AGENTS KAAM KARTE HAIN ---")  # heading print karo
    for agent, task in steps:  # har step ko ek ek kar ke chalao
        await call_agent(agent, task)  # sahi agent ko kaam do

    # STEP 3: WRITER JAWAB LIKHTA HAI
    print("\n--- STEP 3: WRITER ---")  # heading print karo
    answer = await final_chain.ainvoke({"query": query, "results": shared_state["log"]})  # saare kaam se jawab banao
    print(answer)  # pehla jawab dikhao

    # STEP 4: REVIEWER
    try:  # error aaye to program crash na ho
        final_answer = await review_chain.ainvoke({"query": query, "answer": answer})  # jawab review karwao
        print("\n--- STEP 4: REVIEWER ---")  # heading print karo

    except Exception as e:  # agar reviewer fail ho jaye
        final_answer = answer  # to pehla jawab hi final maan lo
        print("error in reviewer step:", e)  # error dikhao

    print(final_answer)  # final jawab dikhao


if __name__ == "__main__":  # file seedhi chale to
    asyncio.run(main())  # async main() ko chalao

# ============================================
# END OF PROJECT CODE
# ============================================
