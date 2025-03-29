from langchain_openai import ChatOpenAI
from browser_use import Agent,  SystemPrompt
import asyncio
from dotenv import load_dotenv
load_dotenv()

class MySystemPrompt(SystemPrompt):
    def important_rules(self) -> str:
        # Get existing rules from parent class
        existing_rules = super().important_rules()

        # Add your custom rules
        new_rules = """
        9. MOST IMPORTANT RULE:
        - ALWAYS open first a new tab and go to wikipedia.com no matter the task!!!
- You are a helpful assistant that is helping me test the demo booking process for different websites. 
- When asked for additional information, you will provide the following information:
- User Name/First Name: Dhruv Raval
- User Email: dhruvraval04@gmail.com
- Make sure to fill out the form with the correct information and book a demo for April 12th, 2025, and if you can't find that date, then book a demo for any day in April 2025.
            """

        # Make sure to use this pattern otherwise the exiting rules will be lost
        return f'{existing_rules}\n{new_rules}'
async def main(url):
    try:
        agent = Agent(
            task=f"""
            Go to {url} and complete the demo booking process:
            1. Find and click the 'Book a Demo' button
            2. Fill out the demo request form with test data. 
            3. Submit the form with the correct information.
            4. Look for a success message, confirmation page, or thank you message
            5. Report back whether the booking was successful or not
            """,
            llm=ChatOpenAI(model="gpt-4o"),
            system_prompt_class= MySystemPrompt
        )
        
        # Run the agent and capture the result
        result = await agent.run()
        
        # Print the agent's execution details
        print("\nExecution Summary:")
        print("-" * 50)
        print(result)
        
        # Check if the result indicates success
        if "success" in result.lower() or "completed" in result.lower() or "thank you" in result.lower():
            print("\n✅ Demo booking was successful!")
            return True
        else:
            print("\n❌ Demo booking may not have been successful.")
            return False
            
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    # Replace this URL with your target website
    target_url = "https://www.skyvern.com/"  # Replace with your actual URL
    
    print(f"Starting demo booking process for: {target_url}")
    success = asyncio.run(main(target_url))
    
    print("\nFinal Status:")
    print("-" * 50)
    print(f"Demo booking test {'succeeded' if success else 'failed'}")
