# Personal assistant project

- Temporal
  - (re-)Schedule workflows via chat
  - Agent should know the schedule 
  - Postpone workflow from chat
- Langchain
- FastAPI
- Web UI
  - free tool for super fast prototyping 
- Serverless
- LLMs
- Playwrite
    - how to store secrets? I need it to log in 
    - can I offload handling well defined scenarios to some existing systems?
- Access to Obsidian
- Flows storage
    - a flow defines tasks (prompt), list of available tools, and restrictions around them
- Gmail & calendar integration (how?)
- Telegram bot
- obsidian integration
    - tracking information about my French lessons, trips, budget, etc
    - Propose updates 
    - Make decisions based on given notes (or tags/directory)
    - Update vector database, when new notes/updates
    - How to implement notes edits? So it’s keep the structure. Limit only by update yaml metadata (properties?) and appends to predefined notes.
    - Create new notes from a template
    - Python tooling for md/obsidian?
- morning notifications
    - plans for a day, week, month, important dates 
    - Weather
    - Tasks
- OpenAI API
- Rag set up for old emails and documents 
    - how to download all emails? How to filter out important emails ?
    - Kafka? A producer per data source 
- Raycast plugin 


## Ideas
- a tool call (integration layer) == temporal activity?
  - can I call other activities from an activity? Assuming the langgrap is runnned as a temporal activity?
## Requirements

- Proactive and sheduled workflows
- Event driven workflows
- Human in the loop


## Examples

(Context: there is a obsidian note about this trip, with a todo list)
> Hey, you have a cycling trip to Normandie in 2 weeks, it’s for 4 days! Have you found a cat sitter already?

> Hey, the train is tomorrow morning! Make sure you don’t forget to check cat’s feeder and charge bicycle devices 

(Context: there is a notes about my French lessons, and a note, where I track payments)
> agent: Hey, today was your 15th French lesson. Wanna share what was the topic? By the way you have just 4 paid lessons, consider to male a payment 
> user: actually no lesson today, I forgot to cancel the meeting. And I’ve paid for next 10 lessons 
> Agent: Great! I’ll update the amount of paid lessons to 15 (considering no lesson today), right?
> Yes, correct

> hey, you’ve got a new email from France government service, there is the summary: …
> Do you want me to get more information about some topics ?

> # user defined a scenario/flow « book a barber appointment »
> Go to the website https:xxx.xx
> Select « book »
> Select « Noah »
> Check available dates
> Ask me what date and time I prefer 
> click on the selected date and time
> Use my credentials to log in 
> Show me confirmation 

(Context: it’s a predefined flow. I have a template for the outdoor gear notes)
> agent: hey, it seems like you bought a new peace of outdoor gear, nice! I haven’t found related note in the obsidian. Should we create a new one ? I’ll grab all needed information from the email or internet !

> it’s a public holiday in 3 months, have you planned something already for a long weekend ? Consider one of those unplanned trips you have: …

> you have a trip to Alps next week, pay attention to the weather, it might be rainy, based on the forecast.


> User: I bought a washing machine several years ago, can you find it’s weight ?
> (context: email archive is available in a vector storage, along with other documents)
> agent: let me search for it in my database 
> [search in obsidian notes, documents, emails]
> agent : I found one email related to ordering a washing machine, it’s bosh x566-fd, right? You’ve ordered it in May 2023 on Amazon
> User: yes
> Agent : let me search information about this washing machine 
> …

(Routine collector)
> Agent: hey How is the mood ?
> it was nice weather today and not many meetings, I hope you enjoyed your day !
> Do you want to share something ?
> User: later
> [1 hour pass]
> Agent: do not forget you have doctor appointment tomorrow morning :)
> have you exercised today ?
> User : yes, I’ve run 5k. Also we had guests over our place, I had 3 glass of wine. But I haven’t found time to read today :(
> Agent: [updates habits data in obsidian] cool! I’m happy you found time for socialization. 
