from typing import Dict, List, Tuple, Any, TypedDict, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END, START
from dataclasses import dataclass, asdict
from web_automation import WebAutomation
import json
import logging
from langchain_core.runnables.graph import CurveStyle, MermaidDrawMethod, NodeStyles
import networkx as nx
import matplotlib.pyplot as plt
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Global automation instance
automation = None
process_log =[]

# Define a TypedDict for our state
class BookingStateDict(TypedDict):
    current_phase: str
    page_data: Dict
    error_count: int
    max_retries: int
    booking_details: Dict
    status: Optional[str]

@dataclass
class BookingState:
    """State for the booking workflow"""
    current_phase: str
    page_data: Dict
    booking_details: Dict
    error_count: int = 0
    max_retries: int = 3
    status: Optional[str] = None
# Tools for the agent
@tool
def analyze_page(tool_input: str = "") -> Dict:
    """Analyze the current page and return relevant information"""
    global automation
    html_details = automation.sync_analyze_html_detailed()
    clickable = automation.sync_get_clickable_elements()

    # Try taking a screenshot and handle timeout errors
    screenshot_path = "current_page.png"
    try:
        automation.sync_take_screenshot(screenshot_path)
    except Exception as e:
        print(f"Screenshot failed: {e}")
        screenshot_path = None

    return {
        "html_analysis": html_details,
        "clickable_elements": clickable,
        "screenshot_path": screenshot_path
    }


@tool
def click_element(selector: str) -> bool:
    """Click an element on the page using the provided selector"""
    global automation
    return automation.sync_click_element(selector)

@tool
def fill_form_fields(fields: Dict[str, str]) -> bool:
    """Fill multiple form fields with their respective values"""
    global automation
    try:
        results = automation.sync_fill_form_fields(fields)
        return results
    except Exception as e:
        return False

@tool
def click_all_book_demo_buttons(tool_input: str = "") -> bool:
    """Click all elements containing 'Book a Demo'."""
    global automation
    return automation.sync_click_all_book_demo_buttons()

@tool
def accept_cookies(tool_input: str = "") -> bool:
    """Accept cookies on the page"""
    global automation
    return automation.sync_accept_cookies()

@tool
def click_and_switch_to_new_tab(selector: str) -> bool:
    """Click an element and switch to the new tab if one is opened"""
    global automation
    return automation.sync_click_and_switch_to_new_tab(selector)

@tool
def reload_page(tool_input: str = "") -> bool:
    """Reload the page"""
    global automation
    return automation.sync_reload_page()

@tool 
def scroll_page(tool_input: str = "") -> bool:
    """Scroll the page in the specified direction"""
    global automation
    return automation.sync_scroll()

# Agent definitions
# def create_base_navigation_agent():
#     """Create a basic agent for navigating to the booking page using just HTML analysis"""
#     llm = ChatOpenAI(model="gpt-4", temperature=0)
    
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", """You are an expert web navigation agent. 
#         Your goal is to find and click the correct element that leads to the booking/demo page.
#         You will analyze the HTML structure and clickable elements to determine the best action.
#         Focus on button text, link text, and element classes/IDs that suggest booking functionality."""),
#         MessagesPlaceholder(variable_name="agent_scratchpad"),
#         ("human", """Based on the HTML analysis and clickable elements, find the element that leads to booking/demo page.
        
#         HTML Analysis: {page_data[html_analysis]}
#         Clickable Elements: {page_data[clickable_elements]}
        
#         Return the selector to click in the format: {"selector": "css-selector-here"}""")
#     ])
    
#     tools = [analyze_page, click_element]
    
#     return create_openai_functions_agent(llm, tools, prompt)

def create_navigation_agent():
    """Create an agent for finding and clicking booking buttons"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""You are an expert at finding and clicking booking-related buttons on websites.
        Your task is to analyze the page elements and find the most appropriate button or link for booking a demo.
        
        When analyzing elements:
        1. Look for text containing variations like "Book", "Demo", "Schedule", "Get Started"
        2. Consider the element's tag type (BUTTON, A, etc.)
        3. Look at the element's class and other attributes
        4. Prioritize elements that are clearly call-to-action buttons/links"""),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        HumanMessage(content="""
        Step 1: Analyze the page and find the button that should be clicked in order to book a demo.
        Step 2: Output the text of the button that should be clicked.
        Current page state: {page_data}
        
        Return only the specific text to click!
        """)
    ])
    
    tools = [analyze_page]
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


def create_verification_agent():
    """Create an agent for verifying we've reached the booking page"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""You are an expert verification agent.
        Your goal is to confirm that we have successfully reached a booking or demo scheduling page.
        Analyze the page content, forms, and visual elements to verify we are in the correct location.
        Look for indicators like:
        - Form fields for contact/scheduling information
        - Headers/text mentioning booking, scheduling, or demos
        - Calendar widgets or time selection elements
        - Submit buttons related to booking"""),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        HumanMessage(content="""
        Step 1: Verify if this is a booking page based on its content and layout.
        Step 2: If there are links to book a demo, it is a "calendar_view". If there are form fields to fill out, it is a "form_view". If it is a booking page, classify it into one of two types: "calendar_view" or "form_view".
        Current page state: {page_data}
        
        Return your assessment in the format:
        {"verified": true/false, "reason": "explanation of verification result", "page_type": "calendar_view" or "form_view"}""")
    ])
    
    tools = [analyze_page]
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

def create_calendar_view_agent():
    """Create an agent for analyzing the calendar view and outputting the text of the buttons to click"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""You are an expert booking agent.
        Your task is to analyze the page (will be a page with buttons to book a demo).
        You will be given the page data of a calendar view, and you will need to output the text of the buttons that should be clicked, these should be date/time buttons. Make sure to only output texts of buttons that exist on the page.
        """),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        HumanMessage(content="""
        Step 1: Analyze the page and find the next available date button that should be clicked.
        Step 2: Output the text of the button that should be clicked.
        Step 3: find an available time button that should be clicked. It must be a valid time, with text such as "10:00", "2:00 pm", "11:00 am", etc. 
        Step 4: Output the text of the time button that should be clicked.
        Current page state: {page_data}
        
        In the scenario that only one button is available, output the text of the button in the format:
        {"buttons_to_click": ["button_text"]}
        Return your assessment in the format:
        {"buttons_to_click": ["button1_text", "button2_text", "button3_text"]} or {"buttons_to_click": "no_buttons_to_click"}""")
    ])
    
    tools = [analyze_page, scroll_page]
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

def create_form_filling_agent():
    """Create an agent for filling the booking form"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""You are an expert form filling agent.
        Your goal is to correctly fill out the booking form with the provided details.
        
        When encountering form fields:
        1. Use provided booking details when they match directly
        2. For fields that require splitting or transformation (e.g., "name" into "first_name" and "last_name"):
           - Intelligently split/transform the provided data
        3. For fields not in booking details:
           - Use reasonable defaults based on context
           - For location fields (country, state, etc.): Use "United States" and related defaults
           - For company size: Choose a mid-range option
           - For industry: Choose "Technology" or "Software"
           - For any other fields: Use appropriate professional defaults
        
        
        
        Always ensure the data is professional and consistent."""),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        HumanMessage(content="""
        Step 1: Analyze the page and find the form fields that should be filled out. Fields like "First Name", "Email" are very likely to be form fields that should be filled out.
        Step 2: Find the submit button and output its button text.
        Step 3: Pair the form fields with the details provided.
        Current page state: {page_data}
        Fill out the form with these details: {details}
        
        You should also output the text of the button that should be clicked to submit the form.
        ONLY output the form fields in the format:
        {"fields": {"selector1": "value1", "selector2": "value2", ...}, "button_text": "button_text"}
        
        
        
        """)
    ])
    
    tools = [analyze_page, scroll_page]
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

  



def create_completion_verification_agent():
    """Create an agent for verifying successful completion of the booking process"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content="""You are an expert verification agent.
        Your goal is to confirm that the booking/demo scheduling process has been successfully completed.
        Analyze the page content and visual elements to verify we have received confirmation.
        Look for indicators like:
        - Success/confirmation messages
        - Booking reference numbers or confirmation codes
        - Calendar invites or next steps information
        - Thank you messages
        - Confirmation emails mentioned
        - Visual indicators like checkmarks or success icons"""),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        HumanMessage(content="""Verify if the booking process is complete.
        Current page state: {page_data}
        
        Return your assessment in the format:
        {"completed": True/False, "reason": "explanation of verification result", "confirmation_details": "any booking reference numbers or important details found"}""")
    ])
    
    tools = [analyze_page]
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


# State management functions
def should_retry(state: Dict) -> Dict:
    """Determine if we should retry the current phase"""
    global process_log
    if state["error_count"] < state["max_retries"]:
        process_log.append({"retry_navigation": f"retrying from start for the {state['error_count']} time"})
        return{"error_count": state["error_count"] + 1}
    else:
        
        process_log.append({"retry_navigation": "exceeded max retries"})
        return{"status": "failure"}




def navigate_to_booking(state: Dict) -> Dict:
    """Handle navigation to booking page"""
    global process_log
    try:
        # Get page data and update state
        page_data = analyze_page("")
        #state["page_data"] = page_data
        
        # Accept cookies
        accept_cookies("")
        
        # Create and run the booking button agent
        agent = create_navigation_agent()
    
        
        result = agent.invoke({
            "page_data": page_data,
            "chat_history": []
        })
        
        # Parse the agent's response
        try:
            
            process_log.append({"navigation": f"agent selected: {result['output']} as the text for the button to click"})
            response = result["output"]
            #print(f"Agent selected: {response['explanation']}")
            
            # Try to click using the selected text
            if click_and_switch_to_new_tab(f"a:has-text('{response}')"):
                process_log.append({"navigation": f"clicked the button with text: {response}"})
                return{"page_data": page_data, "status": "success"}
            
            # If direct click fails, try the selector
            #if click_element(response["selector"]):
            #    state["current_phase"] = "booking_page_verification"
            #    return {"next": "booking_page_verification"}
            
            # If both fail, try the fallback method
            if click_all_book_demo_buttons(""):
                process_log.append({"navigation": f"clicked all book demo buttons"})
                return{"page_data": page_data, "status": "success"}
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error parsing agent response: {str(e)}")
            process_log.append({"navigation": f"error parsing agent response: {str(e)}"})
        return{"page_data": page_data, "status": "retry"}
    except Exception as e:
        logging.error(f"Error in {state['current_phase']}: {str(e)}")
        process_log.append({"navigation": f"error in {state['current_phase']}: {str(e)}"})
        return{"page_data": page_data, "status": "retry"}
def booking_page_verification(state: Dict) -> Dict:
    """Handle verification of booking page"""
    agent = create_verification_agent()
    global process_log
    try:
        # Update state with new page data
        page_data = analyze_page("")  # Pass empty string as tool_input
        #page is the same, so retry
        if(page_data == state["page_data"]):
            process_log.append({"booking_page_verification": "page is the same, so retry"})
            return{"page_data": page_data, "status": "retry"}
        #state["page_data"] = page_data
        
        result = agent.invoke({
            "page_data": page_data,
            "chat_history": []
        })

        result = json.loads(result["output"])
        process_log.append({"booking_page_verification": f"agent verified: {result['verified']} and the page type is: {result['page_type']}"})
        if result["verified"]:
            if result["page_type"] == "calendar_view":
                return{"page_data": page_data, "status": "calendar_view"}
            elif result["page_type"] == "form_view":
                return{"page_data": page_data, "status": "form_view"}
        return{"page_data": page_data, "status": "retry"}
    except Exception as e:
        logging.error(f"Error in {state['current_phase']}: {str(e)}")
        process_log.append({"booking_page_verification": f"error in {state['current_phase']}: {str(e)}"})
        return{"page_data": page_data, "status": "retry"}
def calendar_view_button_clicking(state: Dict) -> Dict:
    """Handle clicking the buttons in the calendar view"""
    agent = create_calendar_view_agent()    
    global process_log
    try:
        # Update state with new page data
        reload_page("")
        if (state["error_count"] > 0):
            process_log.append({"calendar_view_button_clicking": "scrolling page since there was an error"})
            scroll_page("")
        page_data = analyze_page("")
        state["page_data"] = page_data
        
        result = agent.invoke({
            "page_data": page_data,
            "chat_history": []
        })  

        process_log.append({"calendar_view_button_clicking": f"agent output: {result['output']}"})
        result = json.loads(result["output"])
        failed = True
        if result["buttons_to_click"] != "no_buttons_to_click":
            for button in result["buttons_to_click"]:
                try: 
                    click_and_switch_to_new_tab(f"button:has-text('{button}')")
                    process_log.append({"calendar_view_button_clicking": f"clicked the button with text: {button}"})
                    failed = False
                except Exception as e:
                    logging.error(f"Error in {state['current_phase']}: {str(e)}")
                    process_log.append({"calendar_view_button_clicking": f"error in clicking the button with text: {button}: {str(e)}"})
                    #return{"status": "retry"}
        if failed:
            process_log.append({"calendar_view_button_clicking": "failed to click any buttons"})
            return{"page_data": page_data, "status": "retry"}
        else:
            process_log.append({"calendar_view_button_clicking": "clicked all buttons"})
            return{"page_data": page_data, "status": "success"}
    except Exception as e:
        logging.error(f"Error in {state['current_phase']}: {str(e)}")
        process_log.append({"calendar_view_button_clicking": f"error in {state['current_phase']}: {str(e)}"})
        return{"page_data": page_data, "status": "retry"}
    
    
    
    
# # def analyze_page_and_assign_tasks(state: BookingState) -> Dict:
#     """Handle analyzing the page and assigning tasks to the other agents"""
#     agent = create_analyzing_agent()
    
#     try:
#         # Update state with new page data
#         page_data = analyze_page("")
#         state.page_data = page_data
        
#         result = agent.invoke({
#             "page_data": page_data,
#             "chat_history": []
#         })
        
#         result = json.loads(result["output"])
#         if result["next_action"] == "click_button":
#             try: 
#                 click_element(result["button_text"])
#                 state.current_phase = "completion_verification"
#                 return {"next": "completion_verification"}
#             except Exception as e:
#                 logging.error(f"Error in {state.current_phase}: {str(e)}")
#                 return {"next": "booking_page_verification"}
#         elif result["next_action"] == "fill_form":
#             state.current_phase = "form_filling"
#             return {"next": "form_filling"}
#         else:
#             logging.error(f"Unknown next action: {result['next_action']}")
#             return {"next": "booking_page_verification"}
#     except Exception as e:
#         logging.error(f"Error in {state.current_phase}: {str(e)}")
#         return {"next": "retry_navigation"}

def fill_booking_form(state: Dict) -> Dict:
    """Handle form filling"""
    agent = create_form_filling_agent()
    global process_log
    
    try:
        # Update state with new page data
        if (state["error_count"] > 0):
            scroll_page("")
        page_data = analyze_page("")
        state["page_data"] = page_data
        details = state["booking_details"]
        
        result = agent.invoke({
            "booking_details": details,
            "page_data": page_data,
            "chat_history": []
        })
        process_log.append({"form_filling": f"agent output: {result['output']}"})
        result = json.loads(result["output"])
        failed = True
        print(result)
        if(fill_form_fields({"fields": result["fields"]})):
            failed = False
            process_log.append({"form_filling": f"filled the form with the fields: {result['fields']}"})
        if click_and_switch_to_new_tab(f"button:has-text('{result['button_text']}')"):
            failed = False
            process_log.append({"form_filling": f"clicked the button with text: {result['button_text']}"})
        if failed:
            process_log.append({"form_filling": "failed to fill the form or click the button"})
            return {"page_data": page_data, "status": "retry"}
        
        else:
            process_log.append({"form_filling": "filled the form and clicked the button"})
            return {"page_data": page_data, "status": "success"}
        
    except Exception as e:
        logging.error(f"Error in {state['current_phase']}: {str(e)}")
        return {"page_data": page_data, "status": "retry"}


def verify_booking_complete(state: Dict) -> Dict:
    """Handle verification of booking completion"""
    agent = create_completion_verification_agent()
    global process_log
    try:
        # Update state with new page data
        page_data = analyze_page("")
        state["page_data"] = page_data
        
        result = agent.invoke({
            "page_data": page_data,
            "chat_history": []
        })
        process_log.append({"verify_booking_complete": f"agent output: {result['output']}"})
        result = json.loads(result["output"])
        if result["completed"]:
            process_log.append({"verify_booking_complete": "booking is complete"})
            return {"page_data": page_data, "status": "success"}    
        else:
            process_log.append({"verify_booking_complete": "booking is not complete, so we go back to the start"})
        return {"page_data": page_data, "status": "retry"}
        
    except Exception as e:
        logging.error(f"Error in {state.current_phase}: {str(e)}")
        return {"page_data": page_data, "status": "retry"}

            


# Create the workflow graph
def create_booking_workflow(initial_state: Dict) -> StateGraph:
    """Create the booking workflow graph"""
    # Create workflow with proper schema
    workflow = StateGraph(BookingStateDict)
    
    workflow.add_node("navigation", navigate_to_booking)
    workflow.add_node("retry_navigation", should_retry)
    workflow.add_node("booking_page_verification", booking_page_verification)
    workflow.add_node("calendar_view_button_clicking", calendar_view_button_clicking)
    workflow.add_node("form_filling", fill_booking_form)
    workflow.add_node("retry_form", should_retry)
    workflow.add_node("verify_completion", verify_booking_complete)
    
    # Define edges

    workflow.add_edge(START, "navigation")

    # Define conditional edges based on "status"
    workflow.add_conditional_edges(
        "navigation",
        lambda state: state.get("status", "retry"),  # Default to "retry" if status is missing
        {
            "success": "booking_page_verification",
            "retry": "retry_navigation"
        }
    )
    
    workflow.add_conditional_edges(
        "booking_page_verification",
        lambda state: state.get("status", "not_verified"),
        {
            "calendar_view": "calendar_view_button_clicking",
            "form_view": "form_filling",
            "retry": "retry_navigation"
        }
    )
    
    workflow.add_conditional_edges(
        "calendar_view_button_clicking",
        lambda state: state.get("status", "form_error"),
        {
            "success": "booking_page_verification",  # Assume another node
            "retry": "retry_navigation"
        }
    )
    
    workflow.add_conditional_edges(
        "retry_navigation",
        lambda state: "retry" if state["error_count"] < state["max_retries"] else "end",
        {
            "retry": "navigation",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "form_filling",
        lambda state: state.get("status", "retry"),
        {
            "success": "verify_completion",
            "retry": "retry_navigation"
        }
    )

    workflow.add_conditional_edges(
        "verify_completion",
        lambda state: "success" if state["status"] == "success" else "retry",
        {
            "success": END,
            "retry": "booking_page_verification"
        }
    )
    
    # workflow.add_edge("booking_page_verification", "calendar_view_button_clicking")
    # workflow.add_edge("booking_page_verification", "retry_navigation")
    
    # workflow.add_edge("calendar_view_button_clicking", "retry_navigation")
    # workflow.add_edge("calendar_view_button_clicking", "booking_page_verification")
    # workflow.add_edge("form_filling", "verify_completion")
    # workflow.add_edge("form_filling", "retry_form")
    # workflow.add_edge("retry_form", "form_filling")
    # workflow.add_edge("retry_form", END)

    # workflow.add_edge("verify_completion", END)


    return workflow.compile()

# Example usage
def run_booking_automation(url: str, booking_details: Dict):
    global automation
    automation = WebAutomation()
    
    try:
        # Initialize the automation
        automation.sync_initialize()
        automation.sync_navigate_to(url)
        
        initial_state = {
            "current_phase": "navigation",
            "page_data": {},
            "booking_details": booking_details,
            "error_count": 0,
            "max_retries": 3,
            "status": None
        }
        
        workflow = create_booking_workflow(initial_state)
        
        # Run the workflow
        final_state = workflow.invoke(initial_state)
        global process_log
        process_log.append({"status": final_state["status"] })
        return process_log

    except Exception as e:
        logging.error(f"Error in run_booking_automation: {str(e)}")
        return False
        
    finally:
        try:
            automation.sync_close()
        except Exception as e:
            logging.error(f"Error closing automation: {str(e)}")


# def validate_booking_details(details: Dict) -> bool:
#     required_fields = ["name", "email"]
#     return all(field in details for field in required_fields)

if __name__ == "__main__":
    booking_details = {
        "name": "John Doe",
        "email": "john@example.com",
        "company": "Example Corp",
        "phone": "+1234567890"
    }
    
    log = run_booking_automation(
        url="https://www.scale.com/",
        booking_details=booking_details
    )
    success = True
    print(log)
    if(log[-1]["status"] == "retry"):
        success = False
    print(log)
    print("Booking successful!" if success else "Booking failed!") 