import asyncio

from browser_use import Agent, BrowserSession
from browser_use.llm import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini")

async def main():
    agent = Agent(
        task="""
    Go to https://home.shortcutssoftware.com/lesgarconsbarbiers#/_h/locations/info
    Select Paris -> Les Garçons Barbiers - St Lazare
    Click "Prendre un rendez-vous"
    Select CHEVEUX -> COUPE COIFFAGE
    Click Suivant
    Select Noah
    Select 3 nearest availiable days and show my all availiable time slots
    Do not proceed, just show me the available time slots. This is you final task.
    """,
        llm=llm,
        browser_session=BrowserSession(headless=True)
    )
    result = await agent.run()
    print(result)

asyncio.run(main())
