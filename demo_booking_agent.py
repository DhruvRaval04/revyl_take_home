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

# Define a TypedDict for our state
class BookingStateDict(TypedDict):
    current_phase: str
    page_data: Dict
    error_count: int
    max_retries: int
    booking_details: Dict

@dataclass
class BookingState:
    """State for the booking workflow"""
    current_phase: str
    page_data: Dict
    booking_details: Dict
    error_count: int = 0
    max_retries: int = 3

# Tools for the agent
@tool
def analyze_page(tool_input: str = "") -> Dict:
    """Analyze the current page and return relevant information"""
    global automation
    html_details = automation.sync_analyze_html_detailed()
    clickable = automation.sync_get_clickable_elements()
    automation.sync_take_screenshot("current_page.png")
    
    return {
        "html_analysis": html_details,
        "clickable_elements": clickable,
        "screenshot_path": "current_page.png"
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
        HumanMessage(content="""Verify if we have reached a booking/demo page.
        Current page state: {page_data}
        
        Return only the specific text to click!
        """)
    ])
    
    tools = [analyze_page, click_element]
    
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
        Step 1: Verify if this is a booking page based on its content.
        Step 2: If there are links to book a demo, it is a "link_view". If there are form fields to fill out, it is a "form_view". If it is a booking page, classify it into one of two types: "link_view" or "form_view.".
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
        You will be given the page data and in the case of a button, you will output the text of the buttons that should be clicked.
        """),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        HumanMessage(content="""
        Step 1: Analyze the page and find the buttons that should be clicked in order. Some examples of these buttons may be buttons to select a date, select a time, or a button to book a demo.
        Step 2: Make sure these buttons are clickable, they shouldn't be disabled or grayed out.
        Step 3: Output the text of the buttons that should be clicked in order.
        Step 4: If there are no buttons to click, output "no_buttons_to_click".
        Current page state: {page_data}
        
        Return your assessment in the format:
        {"buttons_to_click": ["button1_text", "button2_text", "button3_text"]} or {"buttons_to_click": "no_buttons_to_click"}""")
    ])
    
    tools = [analyze_page, click_element]
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

def create_form_filling_agent():
    """Create an agent for filling the booking form"""
    llm = ChatOpenAI(model="gpt-4-vision-preview", temperature=0)
    
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
        MessagesPlaceholder(variable_name="chat_history"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        HumanMessage(content="""Fill out the form with these details: {booking_details}
        Current page state: {page_data}
        
        Return the form fields in the format:
        {"fields": {"selector1": "value1", "selector2": "value2", ...}}
        
        After all fields are filled, return:
        {"action": "submit", "selector": "submit-button-selector"}
        
        Include explanation for any transformed or default values used.""")
    ])
    
    tools = [analyze_page, fill_form_fields, click_element]
    
    return create_openai_functions_agent(llm, tools, prompt)

  



def create_completion_verification_agent():
    """Create an agent for verifying successful completion of the booking process"""
    llm = ChatOpenAI(model="gpt-4-vision-preview", temperature=0)
    
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
        MessagesPlaceholder(variable_name="chat_history"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        HumanMessage(content="""Verify if the booking process is complete.
        Current page state: {page_data}
        
        Return your assessment in the format:
        {"completed": true/false, "reason": "explanation of verification result", "confirmation_details": "any booking reference numbers or important details found"}""")
    ])
    
    tools = [analyze_page]
    
    return create_openai_functions_agent(llm, tools, prompt)


# State management functions
def should_retry(state: Dict) -> Dict:
    """Determine if we should retry the current phase"""
    if state["error_count"] < state["max_retries"]:
        state["error_count"] += 1
        return {"next": state["current_phase"]}
    return {"next": END}




def navigate_to_booking(state: Dict) -> Dict:
    """Handle navigation to booking page"""
    try:
        # Get page data and update state
        page_data = analyze_page("")
        state["page_data"] = page_data
        
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
            response = result["output"]
            #print(f"Agent selected: {response['explanation']}")
            
            # Try to click using the selected text
            if click_element(f"a:has-text('{response}')"):
                state["current_phase"] = "booking_page_verification"
                return {"next": "booking_page_verification"}
            
            # If direct click fails, try the selector
            #if click_element(response["selector"]):
            #    state["current_phase"] = "booking_page_verification"
            #    return {"next": "booking_page_verification"}
            
            # If both fail, try the fallback method
            if click_all_book_demo_buttons(""):
                state["current_phase"] = "booking_page_verification"
                return {"next": "booking_page_verification"}
                
        except (json.JSONDecodeError, KeyError) as e:
            logging.error(f"Error parsing agent response: {str(e)}")
        
        return {"next": "retry_navigation"}
        
    except Exception as e:
        logging.error(f"Error in {state['current_phase']}: {str(e)}")
        return {"next": "retry_navigation"}

def booking_page_verification(state: Dict) -> Dict:
    """Handle verification of booking page"""
    agent = create_verification_agent()
    
    try:
        # Update state with new page data
        page_data = analyze_page("")  # Pass empty string as tool_input
        state["page_data"] = page_data
        
        result = agent.invoke({
            "page_data": page_data,
            "chat_history": []
        })

        result = json.loads(result["output"])
        
        if result["verified"]:
            if result["page_type"] == "link_view":
                state["current_phase"] = "calendar_view_button_clicking"
                return {"next": "calendar_view_button_clicking"}
            elif result["page_type"] == "form_view":
                state["current_phase"] = "form_filling"
                return {"next": "form_filling"}
        
        return {"next": "retry_navigation"}
        
    except Exception as e:
        logging.error(f"Error in {state['current_phase']}: {str(e)}")
        return {"next": "retry_navigation"}

def calendar_view_button_clicking(state: Dict) -> Dict:
    """Handle clicking the buttons in the calendar view"""
    agent = create_calendar_view_agent()    
    
    try:
        # Update state with new page data
        page_data = analyze_page("")
        state["page_data"] = page_data
        
        result = agent.invoke({
            "page_data": page_data,
            "chat_history": []
        })  
        
        result = json.loads(result["output"])
        
        if result["buttons_to_click"] != "no_buttons_to_click":
            for button in result["buttons_to_click"]:
                try: 
                    if(click_element(f"a:has-text('{button}')")):
                        state["current_phase"] = "booking_page_verification"
                        return {"next": "booking_page_verification"}
                except Exception as e:
                    logging.error(f"Error in {state['current_phase']}: {str(e)}")
                    return {"next": "retry_navigation"}
        
        return {"next": "retry_navigation"}
    
    except Exception as e:
        logging.error(f"Error in {state['current_phase']}: {str(e)}")
        return {"next": "retry_navigation"}
    
    
    
    
    
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

def fill_booking_form(state: BookingState) -> Dict:
    """Handle form filling"""
    agent = create_form_filling_agent()
    
    try:
        # Update state with new page data
        page_data = analyze_page(state)
        state.page_data = page_data
        
        result = agent.invoke({
            "booking_details": state.booking_details,
            "page_data": page_data,
            "chat_history": []
        })
        
        if "fields" in result:
            if fill_form_fields(result["fields"], state):
                return {"next": "form_filling"}
        elif "action" in result and result["action"] == "submit":
            if click_element(result["selector"], state):
                state.current_phase = "verify_completion"
                return {"next": "verify_completion"}
        return {"next": "retry_form"}
        
    except Exception as e:
        logging.error(f"Error in {state.current_phase}: {str(e)}")
        return {"next": "retry_form"}


def verify_booking_complete(state: BookingState) -> Dict:
    """Handle verification of booking completion"""
    agent = create_completion_verification_agent()
    
    try:
        # Update state with new page data
        page_data = analyze_page(state)
        state.page_data = page_data
        
        result = agent.invoke({
            "page_data": page_data,
            "chat_history": []
        })
        
        if result["completed"]:
            return {"next": END}    
        
        return {"next": "form_filling"}
        
    except Exception as e:
        logging.error(f"Error in {state.current_phase}: {str(e)}")
        return {"next": "form_filling"}

            


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
    workflow.add_edge("navigation", "retry_navigation") 
    workflow.add_edge("navigation", "booking_page_verification")
    workflow.add_edge("retry_navigation", "navigation")
    workflow.add_edge("retry_navigation", END)
    
    workflow.add_edge("booking_page_verification", "calendar_view_button_clicking")
    workflow.add_edge("booking_page_verification", "retry_navigation")
    
    workflow.add_edge("calendar_view_button_clicking", "retry_navigation")
    workflow.add_edge("calendar_view_button_clicking", "booking_page_verification")
    workflow.add_edge("form_filling", "verify_completion")
    workflow.add_edge("form_filling", "retry_form")
    workflow.add_edge("retry_form", "form_filling")
    workflow.add_edge("retry_form", END)

    workflow.add_edge("verify_completion", END)


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
            "max_retries": 3
        }
        
        workflow = create_booking_workflow(initial_state)
        
        # Run the workflow
        final_state = workflow.invoke(initial_state)
        return final_state["current_phase"] == END

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
    
    success = run_booking_automation(
        url="https://www.revyl.ai/",
        booking_details=booking_details
    )
    
    print("Booking successful!" if success else "Booking failed!") 