#!/usr/bin/env python3
"""Simple prompt evaluation script using LLMAgent."""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from the_assistant.integrations.llm.agent import LLMAgent, Task

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Hardcoded system prompt for evaluation
EVALUATION_SYSTEM_PROMPT = """
You are a warm, smart, and human-like personal assistant helping the user manage daily life. 
You summarize only what matters, with a personal tone. Response limit: 4000 symbols. Respond should be on a user's language
"""

# Hardcoded user prompt for evaluation
EVALUATION_USER_PROMPT = """
You are a thoughtful and friendly personal assistant writing a **morning daily briefing** for the USER.

Your tone should be natural, human, and warm — like a trusted assistant who knows the user's habits and priorities. Keep it concise, engaging, and helpful. This is the first message of the day, not a formal report.

Use this structure:
- Start with a **short, warm greeting**, comment on the **day of the week and weather**.
- Mention anything important or unusual **happening today**.
- Optionally, give a **brief heads-up** about Monday if it’s going to be busy — but **skip regular meetings or classes** unless something changed.
- Prioritize what truly matters in **email summaries**:
  - Focus on emails with action items, personal relevance, or urgency.
  - Group minor items into a sentence or skip them entirely.
  - Translate and explain non-English/Russian emails in detail if any.
- Add light personal suggestions if helpful (“Might be worth prepping for Monday” or “Good day to catch up on that backlog.”)
- Never just list all events or emails. Use discretion.

Be brief, human, and helpful. Max response length: 4000 characters.

<CONTEXT>{data}</CONTEXT>
"""

# Sample data for the task
SAMPLE_DATA = """
Current time: 2025-07-26 Saturday 07:23

Todays' weather: Overcast, high 27.3°C low 17.3°C

<events>- французский 💅 (2025-07-29 12:05)  [personal]
- День рождения Петра Окунцева (2025-07-30 14:15)  [personal]
- французский💅 (2025-07-31 12:30)  [personal]
- Monthly dependencies upgrade day (2025-07-28 00:00)  [work]
- ✨ Aleksandr <> Luuk - 1:1 (Weekly) (2025-07-28 11:00) Paris-5th-Grand Boulevards - Booth Solo (1) [work]
- Backend COP (2025-07-28 15:00)  [work]
- Orbiit P&E Weekly Sync [Mandatory] (2025-07-28 17:15)  [work]
- Time blocked for French lesson (2025-07-29 12:05) Paris-5th-Grand Boulevards - Booth Solo (1) [work]
- 🪄 Sasha <> Anna Weekly 1:1 (2025-07-30 10:30) Paris-5th-Grand Boulevards - Booth Solo (1) [work]
- Time blocked for French lessons. (2025-07-31 12:30) Paris-5th-Grand Boulevards - Booth Solo (1) [work]</events>


Inbox emails previews (total: 31):
<emails><email>[personal] Votre bulletin de paie pour juillet 2025 est disponible from PayFit <no-reply@payfit.com> unread:True
| |   
---  
| | |   
---  
Bonjour Aleksandr,  
Votre bulletin de paie pour juillet 2025 est maintenant disponible sur votre
espace personnel. félicitations pour le travail accompli !  
  
|  
---  
| Accéder à mon espace personnel  
---  
|  
---  
|  
---  
PayFit • 1 Rue de Saint-Pétersbourg, 75008 Paris

</<email>>
<email>[personal] Votre colis a bien été livré ! from La Poste-Colissimo <noreply@notif-colissimo-laposte.info> unread:True
|  |  |  | Votre colis est arrivé  
---  
|  | Mon espace client La Poste  
---  
|  |   
---  
|  SUIVRE MON COLIS  
---  
|  |  |  |  | |   
---  
| **Votre Colissimo confié par ZALANDO a été livré en mobilité douce le 26
juillet 2025.**|  
---|---|---  
---  
|  | |   
---  
| |   
---|---|---  
---  
|  
---  
| Votre colis a été livré en mobilité douce !  
La Poste et Colissimo s’engagent au quotidien pour vous proposer une livraison
qui contribue à limiter l’impact environnemental de vos colis.  
Pour en savoir plus, rendez-vous sur La Poste s’engage** _﻿_**|  
---|---|---  
---  
|  | |   
---  
| Bonjour,  
Votre colis n°6A23509690329 a été livré à l'adresse suivante :  
8 RUE D AUMALE75009 PARIS 09  
Colissimo vous remercie de votre confiance.|  
---|---|---  
---  
|  | 
# Besoin de plus d'informations ?  
---  
|  |  SUIVRE MON COLIS EN TEMPS REEL  
---  
|  CONSULTER L'AIDE EN LIGNE  
---  
|  
---  
|  | 
## Colissimo, le choix d'une livraison plus responsable et réussie  
---  
|  |  La Poste-Colissimo est responsable du traitement de vos données à caractère personnel transmises par l’expéditeur. Vous recevez ce mail car nous collectons vos données dans le cadre du transport, de la distribution et du suivi de votre colis Colissimo. Pour en savoir plus sur vos droits et la protection de vos données, consultez notre politique de protection des données à caractère personnel.  
---  
|  |  2025 ©LA POSTE.  
[...9 lines left]</<email>>
<email>[personal] Justin Hodges, PhD, Tom Yeh, and Sebastian Raschka, PhD posted new notes from Substack <no-reply@substack.com> unread:True
Justin Hodges, PhD, Tom Yeh, and Sebastian Raschka, PhD posted new notes

͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   

 | |   
---  
### Justin Hodges, PhD, Tom Yeh, and Sebastian Raschka, PhD posted new notes  
| | | | | | | | Justin Hodges, PhD| | | | 7d  
---|---|---|---|---  
Neural Networks entirely from scratch - a YouTube video series. The video
shown here is a video of his 100 pages of handwritten notes on the topic
"Building Neural Networks from Scratch". Nothing is assumed. Everything is…  
Read More  
| 108|  | 14|  |   
---|---|---|---|---  
| | | | | | Tom Yeh| | 3d  
---|---|---  
Can you follow the…  
Read More  
| 84|  | 7|  |   
---|---|---|---|---  
| | | | | | Sebastian Raschka, PhD| | | | 3d  
---|---|---|---|---  
This might be the best coding model yet…  
Read More  
|  
---  
| 89| 11| 4|  |   
---|---|---|---|---  
| | | | | |   
---|---|---|---  
| See more notes in the Substack app  
(C) 2025 Substack Inc.  
548 Market Street PMB 72296, San Francisco, CA 94104  
Unsubscribe  
422  


</<email>>
<email>[personal] “sde”: Amazon Web Services (AWS) is hiring from LinkedIn Job Alerts <jobalerts-noreply@linkedin.com> unread:True
Actively recruiting

͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏

|  |  |  |   
---  
|

#  Your job alert for **sde**  
---  
|

##  1 new job in 75009 matches your preferences.  
---  
|  |  |  |  |  Senior Business Intelligence Engineer , Long-term planning   
---  
Amazon Web Services (AWS) * Clichy  
|  |  |  |  Actively recruiting   
---|---  
|  |  See all jobs   
---  
* * *  
|  |   
---  
Job search smarter with Premium  
|  |  Retry Premium for €0   
---  
|

##  Get the new LinkedIn desktop app  
---  
##  Also available on mobile  
* * *  
This email was intended for Alexandr Kushnarev (Senior Software Engineer/Tech
Lead)  
---  
Learn why we included this.  
You are receiving Job Alert emails.  
Manage job alerts  · Unsubscribe · Help  
© 2025 LinkedIn Corporation, 1000 West Maude Avenue, Sunnyvale, CA 94085.
LinkedIn and the LinkedIn logo are registered trademarks of LinkedIn.

</<email>>
<email>[personal] “principal engineer”: Subsea7 is hiring from LinkedIn Job Alerts <jobalerts-noreply@linkedin.com> unread:True
Posted on 7/25/25

͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏

|  |  |  |   
---  
|

#  Your job alert for **principal engineer**  
---  
|

##  1 new job in Paris matches your preferences.  
---  
|  |  |  |  |  Principal Engineer - Installation and Project Engineering (IPE)   
---  
Subsea7 * Paris (On-site)  
|  
---  
|  |  See all jobs   
---  
* * *  
|  |   
---  
Job search smarter with Premium  
|  |  Retry Premium for €0   
---  
|

##  Get the new LinkedIn desktop app  
---  
##  Also available on mobile  
* * *  
This email was intended for Alexandr Kushnarev (Senior Software Engineer/Tech
Lead)  
---  
Learn why we included this.  
You are receiving Job Alert emails.  
Manage job alerts  · Unsubscribe · Help  
© 2025 LinkedIn Corporation, 1000 West Maude Avenue, Sunnyvale, CA 94085.
LinkedIn and the LinkedIn logo are registered trademarks of LinkedIn.

</<email>>
<email>[personal] “senior software engineer”: Ashby is hiring  for €76K-€185K / year from LinkedIn Job Alerts <jobalerts-noreply@linkedin.com> unread:True
Posted on 7/25/25

͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏ ͏
͏ ͏ ͏ ͏

|  |  |  |   
---  
|

#  Your job alert for **senior software engineer**  
---  
|

##  13 new jobs in Clichy match your preferences.  
---  
|  |  |  |  |  Senior Software Engineer - Product Engineering, EMEA   
---  
Ashby * European Union (Remote)  
€76K-€185K / year  
|  
---  
|  |  |  |  |  Senior Software Engineer   
---  
Oho Group Ltd * European Union (Remote)  
|  |  |  |  Actively recruiting   
---|---  
|  |  Easy Apply   
---|---  
|  |  |  |  |  Intermediate / Senior Software Engineer Scientific Engine (Python) - CDI   
---  
La French Tech Taiwan * Paris (Hybrid)  
|  
---  
|  |  |  |  |  Senior Software Engineer Java   
---  
Mirakl * France (Remote)  
|  |  |  |  Actively recruiting   
---|---  
|  |  |  |  |  Senior Software Engineer   
---  
CyGO Entrepreneurs * France (Remote)  
|  |  |  |  Easy Apply   
---|---  
|  |  |  |  |  Senior Software Engineer - Frontend   
---  
Restream * EMEA (Remote)  
|  |  |  |  Actively recruiting   
[...24 lines left]</<email>>
<email>[personal] Votre facture est disponible sur sfr.fr from SFR <facture@sfr.fr> unread:True
|  _Votre facture est disponible sur sfr.fr_  
---  
  
|  |   
---  
Client Mobile :  
Votre numero de ligne : 0678864431  
C'est aussi votre identifiant de connexion pour votre espace client  
  
---  
votre service client vous informe  
Cher client,  
  
  
Nous vous informons que votre facture du **24/07/2025 de la ligne 06 78 86 44
31** d'un montant de **16.99 euros TTC** est disponible sur votre application
SFR & Moi et sur votre Espace Client.  
  
Je consulte ma facture  
Besoin d'aide pour comprendre votre facture ? Retrouvez notre guide
d'explications en cliquant ici.  
  
  
  
  
  
Merci de votre confiance et à bientôt,  
  
  
Votre équipe SFR  
---  
---  
|  |  |  |  |  **Une question ?  
Vos réponses ici ! **  
---  
|  |   
---  
SFR & Moi  
|  
---  
Espace client  
|  |  Par téléphone au   
---  
|  |  |  Je me rends dans   
la boutique SFR  
la plus proche  
---  
|  |  |  **À bientôt**  
---  
sur sfr.fr  
[...13 lines left]</<email>>
<email>[personal] 3 Days Only: 15% Off Summer Essentials from "Bronson Mfg. Co." <cs@bronsonshop.com> unread:False
Military-inspired styles built for the heat. Ends July 27 — don’t miss out.

                                      
                                      
                                      
                                      
                  

|  |  |  |   
---  
|  |   
---  
---  
|  SHOP NOW  
---  
|  | **New Stuff’s In — And Yes, It’s on Sale!**  
---  
|  |  |  |   
---  
Side Closing Short Sleeve Henley T-Shirt - White  
---  
$ 35.99  
---  
|  SHOP NOW  
---  
|  |   
---  
Side Closing Short Sleeve Henley T-Shirt - Embryo  
---  
$ 35.99  
---  
|  SHOP NOW  
---  
|  |  |   
---  
Side Closing Short Sleeve Henley T-Shirt - Navy  
---  
$ 35.99  
---  
|  SHOP NOW  
---  
|  |   
---  
Vietnam War OG-107 Fatigue Utility Shorts - Olive  
---  
$ 39.99  
---  
|  SHOP NOW  
---  
|  |   
[...19 lines left]</<email>>
<email>[personal] Hatching Growth: How we found and acquired our first 1,000 users? from Glasp <glasp@substack.com> unread:False
Glasp's note: This is Hatching Growth, a series of articles about how Glasp
organically reached millions of users.

͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   

| |   
---|---|---  
| | | Forwarded this email? Subscribe here for more  
---  
# Hatching Growth: How we found and acquired our first 1,000 users?

| | Kei Watanabe and Kazuki Nakayashiki  
---  
| Jul 25  
---  
| | |   
---|---|---  
  
---  
| | |   
---  
| |   
---  
| |   
---  
| |   
---  
| | READ IN APP  
---  
  
**Glasp 's note:** This is _**Hatching Growth ,**_ a series of articles about
how Glasp organically reached millions of users. We've tried more than
hundreds of growth hacks and tactics. In this series, we'll highlight some
that worked and some that didn't, and the lessons we learned along the way. If
you have questions about any specific growth hack or tactic, feel free to
leave a comment. While we prefer not to use the term "user," please note that
we'll use it here for convenience 🙇‍♂️

[...196 lines left]</<email>>
<email>[personal] Master the Art of Multi-Exposure 🎞️ from 500px <info@500px.com> unread:False
| | |   
---  
| | 
# FRAME x FRAME  
---  
# The 500px Weekly  
---  
|  
---  
| | **July 25, 2025**  
---  
|  **Log in** or **sign up**  
---  
| | 
# This month we’re exploring:  
---  
# Innovative Approaches to Motion in Photography  
---  
| | 
# July 25: Multi-Exposure Techniques for Dynamic Imagery  
  
---  
---  
| | 
# THIS WEEK'S HIGHLIGHTS  
---  
| 3 min read  
---  
| | 📸 Creating Visual Rhythm with Multiple Exposures  
📸 Join the In Color Quest Series for a shot at $1,500  
📸 Plan Your Exposures for Cohesive Composition  
---  
| |   
---  
| | 
# COVER STORY  
---  
---  
# Creating Visual Rhythm with Multiple Exposures  
---  
Photography is a medium filled with endless creative possibilities, and one
captivating technique stands out: multiple exposures. By layering two or more
images into a single photograph, you can introduce visual rhythm, tell
compelling stories, and create unique, dreamlike effects.  
  
Ready to explore how multiple exposures can elevate your photography? Let's
dive in!  
---  
# The Artistic Appeal of Multiple Exposures  
---  
[...168 lines left]</<email>>
<email>[personal] Limits and selfie checks for extra security from Revolut <no-reply@revolut.com> unread:True
|  | | |   
---  
| | You are your strongest password  
---  
| | Turn on Wealth Protection to activate selfie checks for an extra layer of security when you withdraw  
---  
| | | Set up Wealth Protection  
---  
| | |   
---  
| | Hi Aleksandr,When it comes to everyday spending — or long-term planning — you should always feel in control.That’s where Wealth Protection comes in: our customisable setting that enables withdrawal limits and selfie verification for money leaving your account. Toggle it on or off with a tap via Security in-app.  
---  
| | | |   
---  
### Use your face to withdraw

If you want to dial up the security on your investments, toggle on Wealth
Protection in the security control centre. Then use a selfie check to keep
your personal finance exactly that: personal.  
---  
| | | |   
---  
### Set limits you control

When it comes to your assets, control is key. Set transfer and withdrawal
limits to help you keep a close eye on the assets you want extra secure. And
if your goals or lifestyle change, you can easily adjust, or turn them on and
off in a tap.  
---  
| | | Set up Wealth Protection  
---  
| | Remember: we don’t just help defend your money, we proactively protect your peace of mind.If you’ve got an issue, our encrypted customer chat service team is with you 24/7 to make sure you’re covered — even on a Sunday.   
---  
| | — Team Revolut  
---  
| | Wealth Protection does not provide any guarantee or insurance against future losses in the protected accounts. Wealth protection products may vary per country.  
---  
| |   
---  
| |   
---  
| | |  © Revolut France   
  
Revolut Bank UAB is a credit institution licensed in the Republic of Lithuania
with company number 304580906 and authorisation code LB002119, and whose
registered office is at Konstitucijos ave. 21B, LT-08130 Vilnius, the Republic
of Lithuania. Revolut Bank UAB has established a branch in France authorised
by the French Prudential Supervision and Resolution Authority and whose
registered office is at 10 avenue Kléber 75116 Paris, France. Revolut Bank UAB
is licensed by the European Central Bank and regulated by the Bank of
[...42 lines left]</<email>>
<email>[personal] Vélib’ Métropole | Fermeture temporaire de stations from "Vélib' Métropole" <bonjour@velib-metropole.fr> unread:True
|  |  |  |  En prévision de l'arrivée du Tour de France à Paris, plusieurs stations seront fermées  
---  
---  
Si vous avez des difficultés pour visualiser ce message, _cliquez ici_.  
---  
---  
---  
---  
Cher.e.s abonné.e.s,   À l’occasion de l’arrivée du **Tour de France à Paris
le dimanche 27 juillet** , et sur demande de la Préfecture de Police, nous
procéderons à la fermeture de **36 stations Vélib’** , principalement situées
à proximité des **Champs-Élysées**. Ces stations seront neutralisées **dès le
samedi 26 juillet dans la journée, au plus tard à 20h** , et rouvriront dans
la nuit du **dimanche 27 au lundi 28 juillet**. Tous les Vélib’ seront retirés
et les bornettes seront bloquées par des dispositifs rouges.   Pour organiser
vos trajets, trouver un Vélib’ et une station disponible pour le restituer,
consultez la carte des stations sur l’**application Vélib’**.   💡 **Important
:** le dépôt d’un Vélib’ en dehors d’une bornette (hors stations Station+)
entraînera une facturation hors forfait et l’application de pénalités. Plus
d’infos ici.   Merci de votre compréhension et bon Tour de France à tou.te.s !  
---  
| Voir les stations fermées  
---  
---  
---  
---  
Merci de ne pas répondre à cet e-mail.  
---  
---  
Vélib' Métropole  
TSA 71111, Asnières-Sur-Seine Cedex, 92667  
  
Désinscription  
---  
---

</<email>>
<email>[personal] Votre colis arrive ! from La Poste-Colissimo <noreply@notif-colissimo-laposte.info> unread:True
|  |  |  | Informations importantes pour votre livraison  
---  
|  | Mon espace client La Poste  
---  
|  |   
---  
|  SUIVRE MON COLIS  
---  
|  |  |  |  | |   
---  
| **Votre Colissimo confié par ZALANDO sera livré lundi 28 juillet.**|  
---|---|---  
---  
|  | |   
---  
| Bonjour,  
Votre colis n°6A23509690329 est en route.  
Pour vous simplifier la vie, il sera déposé directement dans votre boîte aux
lettres si les dimensions le permettent.|  
---|---|---  
---  
|  | |   
---  
| **Facilitez vos livraisons !**|  
---|---|---  
---  
|  | |   
---  
| Renseignez vos coordonnées dans votre Compte La Poste afin d'être contacté
par le facteur. Votre adresse postale et numéro de téléphone mobile sont
précieux pour faciliter vos livraisons.|  
---|---|---  
---  
|  | |   
---  
| CREER OU ACCEDER A MON COMPTE|  
---|---|---  
---  
|  | 
# Besoin de plus d'informations ?  
---  
|  |  SUIVRE MON COLIS EN TEMPS REEL  
---  
|  CONSULTER L'AIDE EN LIGNE  
---  
|  
---  
|  | 
## Colissimo, le choix d'une livraison plus responsable et réussie  
---  
[...12 lines left]</<email>>
<email>[personal] Retraite progressive - Quel opérateur mobile ?- Allocation de rentrée from Service Public <lettres@information.dila.gouv.fr> unread:True
Si ce message ne s'affiche pas correctement, voir en ligne.  
---  
Pour être sûr de recevoir nos communications,  
ajoutez le courriel lettres@information.dila.gouv.fr à votre carnet
d'adresses.  
| Lettre n°1206 du 24 juillet 2025 |      
---|---  
|

## Quel opérateur mobile fournit la meilleure qualité de réseau près de chez
vous ?

Publié le 16 juillet 2025 |  | Vous souhaitez obtenir des informations sur la couverture Internet mobile de votre lieu de vacances, ou mettre en balance les performances des (...)   Lire la suite >  
---|---  
|

##  Formation - Travail  
---  
| Retraites Publié le 24 juillet 2025 |  | 
### La retraite progressive bientôt accessible à partir de 60 ans

Les décrets fixant l’âge permettant d’accéder à la retraite progressive sont
parus le 23 juillet 2025 au _Journal officiel_. La mesure entrera en (...)
Lire la suite >  
---|---  
| Obligation de sécurité Publié le 17 juillet 2025 |  | 
### L’obligation de l’employeur s’étend-elle aux locaux des sociétés où
intervient le salarié ?

La Cour de cassation, dans un arrêt du 11 juin 2025 publié au bulletin,
précise les contours de l’obligation de sécurité de l’employeur (...)   Lire
la suite >  
---|---  
|

##  Logement  
---  
| Rénovation énergétique Publié le 24 juillet 2025 |  | 
### Réouverture du guichet MaPrimeRénov’ : quelles seront les nouvelles
modalités du dispositif ?

Depuis fin juin, vous ne pouvez plus déposer de demande de subvention
MaPrimeRénov’ pour une rénovation énergétique d’ampleur de votre logement.
(...)   Lire la suite >  
---|---  
| Très haut débit Publié le 23 juillet 2025 |  | 
### Une aide pour faciliter le raccordement à la fibre optique

À partir du 1er septembre 2025, une aide à l’installation de la fibre optique
est mise en place en cas de difficulté de raccordement. Cette (...)   Lire la
[...115 lines left]</<email>>
<email>[personal] Cursor makes developers less effective? from The Pragmatic Engineer <pragmaticengineer+the-pulse@substack.com> unread:True
A study into the workflows of experienced developers found that devs who use
Cursor for bugfixes are around 19% slower than devs who use no AI tools at
all.

͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏
͏   ͏   ͏   ͏   ͏   ͏   ͏   ͏   

| |   
---|---|---  
| | | Forwarded this email? Subscribe here for more  
---  
---  
# Cursor makes developers less effective?

### A study into the workflows of experienced developers found that devs who
use Cursor for bugfixes are around 19% slower than devs who use no AI tools at
all.

| | Gergely Orosz  
---  
| Jul 24  
---  
|  
---  
  
---  
| | |   
---  
| |   
---  
| |   
---  
| |   
---  
| | READ IN APP  
---  
  
An interesting study has been published by the nonprofit org, Model Evaluation
and Threat Research (METR). They recruited 16 experienced developers who
[...199 lines left]</<email>>
<email>[work] Weekly Report for Hivebrite: July 19th, 2025 - July 26th, 2025 from Sentry <noreply@md.getsentry.com> unread:True
|

#

|  **Weekly Update for Hivebrite**  
July 19th, 2025 - July 26th, 2025  
---|---  
|

#### Total Project Errors

# 1.6k

View All Errors |  |   
---  
|  
---  
|  
---  
|  
---  
|  
---  
|  
---  
|  
---  
Sat  |  Sun  |  Mon  |  Tue  |  Wed  |  Thu  |  Fri   
# Something slow?

Trace those 10-second page loads to poor-performing API calls. Set Up Tracing  
| Project | Errors | Dropped | Transactions | Dropped  
---|---|---|---|---|---  
|  alumni_connect_back | 1.6k | 31 | 0 | 0  
#### Issues Breakdown

|  New (2) Escalating (0) Regressed (18) Ongoing (3)  
---|---  
|  |  |  |   
---|---|---|---  
#### Issues with the most errors

250

Failed to open TCP connection to :80 (Connection refused - connect(2) for nil
port 80) (Faraday::ConnectionFailed)
Sidekiq/Web::Notification::WebsocketNotificationJob

back_alumni_connect

[...22 lines left]</<email>>
<email>[work] Dagster+ Pro Upgrade from Naomi Mastico <naomi@dagsterlabs.com> unread:False
Hi everyone,

  

Thanks very much for your time today. It was very interesting learning about
your use case with Hivebrite and your plans to expand your Dagster instance.

  

Dagster+ Pro Plans include unlimited deployments, so this would certainly fit
into your use case.

  

In order to build out an estimate, I just need a better estimate of the number
of seats and credits you'd like to include in your plan.  
  
From there, please schedule some time with me to present that to a budget
holder on your end.  
  
Are there any additional questions on your end?  
  
Thanks very much and looking forward to continuing the conversation!  
  
Naomi

</<email>>
<email>[work] Recap of your meeting with Dagster from Fathom <no-reply@fathom.video> unread:False
Meeting Purpose Discuss Hivebrite's Dagster usage and potential upgrade to Pro
plan for multi-environment support and GDPR compliance. Key Takeaways \-
Hivebrite (Orbit) uses Dagster primarily as a scheduler/workflow tool, with
most business logic in microservices \- Considering upgrade to Pro for
multiple persistent deployments, hybrid mode for EU GDPR compliance \- Pro
plan starts at $15-20K annually, includes unlimited deployments, code
locations, and role-based access \- Next steps: Naomi to send calculator for
credit usage estimation and prepare a custom proposal Topics Current Dagster
Usage \- Primarily used as a scheduler and workflow tool \- Most business
logic executed in microservices, Dagster calls these services \- Some ETL
jobs, but not the main use case \- Considering moving some workflows to
Temporal \- Plan to redesign jobs to utilize more Dagster features (e.g.,
artifacts between steps) Compliance and Infrastructure Needs \- Need to
process PII data in EU for GDPR compliance \- Require deployments in multiple
regions (EU, US, Switzerland, Australia) \- Considering hybrid mode or fully
on-premises deployment \- Want separate production and pre-prod/testing
environments Challenges with Current Plan \- Unable to have multiple
persistent deployments within one account \- Pre-prod environment connects to
ephemeral Dagster environments, causing configuration updates Upgrade
Considerations \- Pro plan starts at $15-20K annually \- Includes unlimited
deployments, code locations, role-based access \- Per-seat licensing model \-
Dagster credits based on asset materializations and op runs \- More cost-
effective at scale compared to starter plan Questions and Concerns \-
Possibility of persistent open pull requests for maintaining environments \-
Potential for custom plans between starter and pro (not available) \- Need to
evaluate budget and get approval from leadership Next Steps \- Naomi to send
calculator for estimating credit usage \- Hivebrite team to discuss internally
and provide information on budget \- Naomi to prepare a custom proposal based
on Hivebrite's needs \- Schedule follow-up meeting with decision-maker present
\- Hivebrite to evaluate hybrid deployment option and credit usage projections

|  |  |   
---  
|  |  |  |  Meeting with Dagster   
---  
Dagster Intro with Naomi  
July 24, 2025  •  21 mins  •  View Meeting or Ask Fathom  
|  Action Items ✨  
---  
|  |  |  |  Ask about best practices for persistent open pull requests for maintaining persistent environments in Dagster   
---  
Naomi Mastico  
|  |  |  Discuss with Luke to get validation on potential Dagster Pro upgrade proposition and associated costs   
---  
Lucas BOISSERIE  
|  |  |  Provide Naomi information about budget constraints for Dagster Pro upgrade via email   
---  
Lucas BOISSERIE  
|  |  |  Send calculator to help understand credit usage and build upgrade proposal   
---  
[...76 lines left]</<email>>
<email>[work] Sasha Kushnarev, your team is working on these pages--join the conversation from Confluence <confluence@hivebrite.atlassian.net> unread:False
| | |   
---  
| | Sasha Kushnarev, we know you’re busy.  
---  
So here are the **3 Confluence pages** from hivebrite we recommend to help you
stay up to date.  
---  
| |  RECOMMENDATIONS  
---  
| | |  Hivebrite Technical Shift and AI Vision  
---  
Product & Engineering • Owned by Pierre Jolivet  
1\. Introduction & Current State Analysis 1.1 Company Mission & Product
Overview Hivebrite empowers organizations to build, manage, and grow thriving
online communities through our comprehensive SaaS p...Read more  
| | |  25.H2 6 month roadmap update [Orbiit]  
---  
Product & Engineering • Owned by Andrew Fiedler  
Orbiit 25.H2 Overview Updates (updated Nov 2024) The only item shared in the
6-12mo Orbiit roadmap which has changed is Linked Questions - its a discovery
topic for H2 to make sure that its valuable ...Read more  
| | |  Platform - Larzac - PI#4  
---  
Product & Engineering • Owned by Simon ARTIGE  
READ ME : Guidelines to define an objective For all @product-management-team
@eng-managers please, make sure your objectives are quite specific. If it’s a
delivery one: what scope are you going to d...Read more  
| | Too many emails? Unsubscribe or customise your preferences.  
---  
---  
| | Download the Confluence mobile app on iOS or Android to read notifications and comment on the go.  
---  
---  
| | This email was sent by Atlassian Confluence •  Privacy policy  
---  
| |   
---  
| | |   
---

</<email>>
<email>[work] Recap for "🪄 Sasha <> Anna Weekly 1:1" from Fathom <no-reply@fathom.video> unread:False
Meeting Purpose Weekly 1:1 between Anna and Sasha, covering Anna's potential
job change and Workspace API functionality. Key Takeaways \- Anna is
considering leaving Hivebrite for a new job opportunity, pending final
decision after meeting the new team \- Workspace API handles sandboxes, custom
fields, and engagement data mapping \- New custom field integration with
Hivebrite is in production, allowing field mapping and syncing Topics Anna's
Potential Job Change \- Anna has received an offer from a new company and is
in discussions with Hivebrite \- Main reasons for considering: financial
benefits, learning opportunities, and office proximity \- Anna has informed
Luke (manager), Billy, and Patty; final decision pending after meeting the new
team \- Sasha supportive of Anna's potential move for career growth and new
experiences Workspace API Overview \- Handles sandboxes (demo environments)
for client demonstrations \- Includes Custom Fields Router for creating and
syncing custom fields \- Engagement Data Map syncing for relating opt-in form
answers to custom fields \- LLM service used for mapping custom fields
semantically \- Currently not actively used in production New Custom Field
Integration with Hivebrite \- New endpoints for field mapping between
Hivebrite and Orbit \- Allows creating new custom fields or mapping to
existing ones \- Syncs member data from Hivebrite to Orbit based on field
mappings \- Currently one-way sync (Hivebrite to Orbit), with potential for
two-way sync in the future Challenges and Considerations \- Semantic mapping
of custom fields using LLM raises questions about control and accuracy \-
Merging options when mapping fields with different sets of options \-
Potential issues with field naming and option handling need debugging Next
Steps \- Anna to make final decision on job offer after meeting the new team
\- Anna to send a follow-up meeting invite to continue discussion on Workspace
API and custom field integration \- Aleksandr to debug issues with custom
field naming and option handling in the new integration \- Consider
implementation of two-way sync between Hivebrite and Orbit for custom fields
in the future

|  |  |   
---  
|  |  |  |  Internal Meeting   
---  
🪄 Sasha <> Anna Weekly 1:1  
July 16, 2025  •  66 mins  •  View Meeting or Ask Fathom  
|  Action Items ✨  
---  
|  |  |  |  Send meeting invite for follow-up discussion on Workspace API and custom fields this week   
---  
Anna Bezlova  
|  Meeting Summary ✨  
---  
General Template  Customize   •  Change Template  
## Meeting Purpose

Weekly 1:1 between Anna and Sasha, covering Anna's potential job change and
Workspace API functionality.

[...56 lines left]</<email>></emails>

User settings:
- ignore_emails: ['notifications@github.com', '*@tldrnewsletter.com']
- location: Paris, France
- greet: Саша
- briefing_time: 09:00
"""


async def main() -> None:
    """Run the prompt evaluation."""
    logger.info("Starting prompt evaluation...")
    
    # Initialize LLM agent with evaluation system prompt
    agent = LLMAgent(
        system_prompt=EVALUATION_SYSTEM_PROMPT,
    )

    # Create evaluation task
    task = Task(
        prompt=EVALUATION_USER_PROMPT,
        data=SAMPLE_DATA
    )
    
    try:
        # Run the evaluation
        result = await agent.run(task)
        
        print("\n" + "="*60)
        print("PROMPT EVALUATION RESULTS")
        print("="*60)
        print(result)
        print("="*60)
        
        logger.info("Evaluation completed successfully")
        
    except Exception as e:
        logger.error("Evaluation failed: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())