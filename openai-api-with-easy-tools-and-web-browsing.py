BING_CUSTOM_SEARCH_API_URL = "https://api.bing.microsoft.com/v7.0/custom/search?"

subscriptionKey = ""
openAIAPIKey = ""

#"gpt-3.5-turbo"
#"gpt-4-turbo-preview"

########################
### Fonctions utiles ###
########################

import openai

openAIClient = openai.OpenAI(api_key=openAIAPIKey)

def getLLMAnswer(userMessage, systemMessage="You are a helpful assistant", model="gpt-3.5-turbo") :
    """Cette fonction interagit avec un LLM pour obtenir une réponse à partir d'un message utilisateur"""
    chatCompletion = openAIClient.chat.completions.create(model=model, messages=[{"role": "system", "content": systemMessage}, {"role": "user", "content": userMessage}])
    return(chatCompletion.choices[0].message.content)

##############################

from joblib import Parallel, delayed
import multiprocessing
import warnings

DEDICATED_CORE_NUMBER = max(multiprocessing.cpu_count() - 2, 1)

def multiProcess(f, argumentsList, coreNumber=DEDICATED_CORE_NUMBER, prt=1):
    """Takes a function, a list of parameter sets for the function, and a number of cores to use as parameters.
    Executes the function in parallel across all parameter sets (using 'coreNumber' cores)
    Returns the list of function returns.
    EXAMPLE:
    def f(a, n=10):
        r = 0
        for i in range(n):
            r += a
        return (r, str(a) + str(n))
    results = mp.multiProcess(f, [(3, 5), (3, 10), (3, 15)])
    results will be [(15, '35'), (30, '310'), (45, '315')]
    """
    if len(argumentsList) > DEDICATED_CORE_NUMBER:
        txt = "Warning: "
        txt += "The program can only use " + str(DEDICATED_CORE_NUMBER) + " CPU cores,"
        txt += "\n however, it has been requested to execute the function " + str(
            len(argumentsList)) + " times simultaneously."
        warnings.warn(txt)

    if prt == 1:
        print("Using " + str(len(argumentsList)) + " cores out of " + str(
            multiprocessing.cpu_count()) + " on the processor.")

    resultsList = Parallel(n_jobs=coreNumber)(delayed(f)(*arguments) for arguments in argumentsList)
    return (resultsList)

#################################################################
### Fonctions pour faire des recherches automatiques sur Bing ###
#################################################################

import requests
import time
import json

def runBingSearch(searchQuery, verbose=False):
    """Cette fonction effectue une recherche Bing et retourne les résultats sous forme de texte."""

    print("Running Bing search for query: " + searchQuery)

    # On crée la requête HTTP
    bingQuery = BING_CUSTOM_SEARCH_API_URL + "q='" + searchQuery + "'&customconfig=0"

    # On effectue la requête HTTP
    response = requests.get(bingQuery, headers={'Ocp-Apim-Subscription-Key': subscriptionKey})

    # On récupère les résultats
    responseData = json.loads(response.text)
    results = responseData.get("webPages", {}).get("value", [])

    # On formate les résultats proprement
    searchResultsString = ""
    for result in results :
        searchResultsString += "Title : " + result["name"] + "\n"
        searchResultsString += "URL : " + result["url"] + "\n"
        searchResultsString += "Snippet : " + result["snippet"] + "\n\n"

    # On retire le dernier retour à la ligne
    searchResultsString = searchResultsString[:-2]

    if verbose == True:
        print("bingQuery :")
        print(bingQuery)
        print("searchResultsString :")
        print(searchResultsString)

    return(searchResultsString)



def getSearchQueries(userRequest, verbose=False):
    """Cette fonction génère des requêtes de recherche Bing pour satisfaire la demande de l'utilisateur
    (via un traitement par un LLM)"""

    print("Generating search queries for Bing to satisfy the user's request...")
    # On enrichit le prompt avec des exemples pour mieux guider la génération des requêtes
    prompt = "Based on the user's request, generate one or several (but non-redundant) short search queries for Bing. " \
             "If the request covers multiple topics, provide separate queries for each topic, using semicolons to separate them." \
             "\nFor example, if the user asks about the population of Paris, Beijing, and Baghdad, give only the response : " \
             "'population Paris;current population Beijing;Baghdad population estimate'." \
             "\nSimilarly, if asked about both the height of the Eiffel Tower and historical events in 1923 in England, give only the response : " \
             "'Eiffel Tower height;historical events in 1923 England'." \
             "Here is the user request: " + userRequest

    # On interagit avec le LLM pour générer les requêtes de recherche
    searchQueries = getLLMAnswer(prompt)

    # On scinde la réponse en utilisant le point-virgule comme séparateur et on élimine les espaces superflus
    searchQueriesList = [query.strip() for query in searchQueries.split(';')]

    if verbose:
        print("searchQueriesList :")
        print(searchQueriesList)

    return(searchQueriesList)



def processSearchResults(userRequest, searchResultsString, verbose=False):
    """Cette fonction analyse les résultats de recherche Bing pour répondre à la demande de l'utilisateur
    (via un traitement par un LLM)"""

    print("Processing Bing search results...")
    # On interagit avec le LLM Haiku de Anthropic pour analyser les résultats de recherche Bing
    prompt = "Analyze these Bing search results below to give a short answer to this user request '" + userRequest + "'\n\n'" + searchResultsString + "'"
    analysis = getLLMAnswer(prompt)

    if verbose == True:
        print("analysis :")
        print(analysis)

    # On renvoie l'analyse
    return(analysis)



def bingSearch(userRequest, verbose=False):
    """Cette fonction effectue une recherche Bing basée sur la demande de l'utilisateur et analyse les résultats
    (via un traitement par un LLM)"""

    # On génère une ou des requêtes de recherche Bing
    searchQueriesList = getSearchQueries(userRequest, verbose=verbose)

    # On exécute la ou les recherches Bing en parallèle
    searchResultsString = multiProcess(runBingSearch, [(e, verbose) for e in searchQueriesList], prt=0)

    # On concatène les résultats de recherche avec une petite mise en forme pour séparer les différentes requêtes
    cleanSearchResultsString = ""
    for i in range(len(searchResultsString)):
        cleanSearchResultsString += "SEARCH QUERY " + str(i+1) + " : '" + searchQueriesList[i] + "'\n'''\n" + searchResultsString[i] + "'''\n\n"

    # On analyse les résultats de(s) recherche(s)
    analysis = processSearchResults(userRequest, cleanSearchResultsString, verbose=verbose)

    # On renvoie l'analyse avec un texte d'introduction
    analysis = "HERE IS THE ANALYSIS OF THE BING SEARCH RESULT BASED ON THE USER'S REQUEST : \n" + analysis

    return(analysis)

BING_SEARCH_DESCRIPTION = {
"type": "function",
"function": {
    "name": "bingSearch",
    "description": "Perform a Bing search based on the user's request and analyze the results",
    "parameters": {
        "type": "object",
        "properties": {
            "userRequest": {
                "type": "string",
                "description": "The user's request(s) to search for"
                },
            },
        "required": ["userRequest"]
        }
    }
}

#################################################################
### Gestion de la conversation pour faire du function calling ###
#################################################################

def adder(a, b):
    """Cette fonction ajoute deux nombres ensemble"""
    return(str(a + b))

adderDescription = {
"type": "function",
"function": {
    "name": "adder",
    "description": "Add two numbers together",
    "parameters": {
        "type": "object",
        "properties": {
            "a": {
                "type": "integer",
                "description": "The first number to add"
                },
            "b": {
                "type": "integer",
                "description": "The second number to add"
                },
            },
        "required": ["a","b"]
        }
    }
}

def getMessageListFromThread(threadId):
    """Cette fonction affiche les messages d'un fil de discussion d'un thread/d'une conversation.
    La liste en sortie est complétée de droite à gauche, le dernier message est le premier de la liste."""
    messageList = openAIClient.beta.threads.messages.list(thread_id=threadId)
    messageListThread = [message.content[0].text.value for message in messageList if message.role == "assistant"]
    return(messageListThread)

def waitForRunCompletion(threadId, runId):
    """Cette fonction attend la fin d'une exécution de thread/de conversation et renvoie le résultat"""
    while True:
        # On check le statut de l'exécution 10 fois par seconde
        time.sleep(0.1)
        run = openAIClient.beta.threads.runs.retrieve(thread_id=threadId, run_id=runId)
        if run.status in ["completed", "failed", "requires_action"]:
            return(run)
        # Lignes ci-dessous non nécessaires
        elif run.status == "in_progress" :
            continue

def getToolReturnList(toolsToCall, toolList=[]):
    """Cette fonction renvoie une liste de retours d'outils à partir d'une liste d'outils à appeler"""

    toolReturnList = []

    # On appelle les outils demandés par l'assistant un par un
    for tool in toolsToCall:
        toolReturn = None
        toolCallId = tool.id
        functionName = tool.function.name
        functionArgs = tool.function.arguments

        # On cherche l'outil correspondant dans la liste des outils disponibles
        for t in toolList:
            if functionName == t.__name__:
                toolReturn = t(**json.loads(functionArgs))

        # On ajoute le renvoie de l'outil à la liste
        toolReturnList.append({"tool_call_id": toolCallId, "output": toolReturn})

    return(toolReturnList)

def getLLMAnswerWithWebBrowsingAndTools(userMessage, systemMessage="You are a helpful assistant", model="gpt-3.5-turbo", mode="ponctual", additionnalToolList=[], additionnalToolDescriptionList=[]) :
    """Cette fonction interagit avec un LLM pour obtenir une réponse à partir d'un message utilisateur.
    Il y a le mode 'ponctual' pour avoir un unique renvoie ou le mode 'continuous' pour avoir
    une conversation continue avec input utilisateur (mettre alors userMessage=None)."""

    # On initialise la liste des outils avec bingSearch par défaut
    toolList = [bingSearch] + additionnalToolList
    toolDescriptionList = [BING_SEARCH_DESCRIPTION] + additionnalToolDescriptionList

    # On initialise l'assistant avec la liste des outils
    assistant = openAIClient.beta.assistants.create(instructions=systemMessage, model=model, tools=toolDescriptionList)

    # On crée un fil de discussion
    thread = openAIClient.beta.threads.create()

    # Boucle de conversation continue
    while True:
        if mode == "continuous":
            print("Type 'exit' to exit the program. \nYour request : ")
            userMessage = input()
            if userMessage.lower() == "exit":
                break

        # Création d'un message et d'une exécution
        openAIClient.beta.threads.messages.create(thread_id=thread.id, role="user", content=userMessage)
        run = openAIClient.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
        # Attente de la fin de l'exécution
        run = waitForRunCompletion(thread.id, run.id)

        # Si (et tant que) l'exécution de la discussion renvoie un outil à appeler, on l'appelle
        while run.status == "requires_action":
            # On récupère les outils à appeler
            toolsToCall = run.required_action.submit_tool_outputs.tool_calls
            print("Tools to call :")
            [print("   " + str(t)) for t in toolsToCall]
            toolReturnList = getToolReturnList(toolsToCall, toolList=toolList)
            run = openAIClient.beta.threads.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=toolReturnList)
            # Attente de la fin de l'exécution
            run = waitForRunCompletion(thread.id, run.id)

        # Si l'exécution de la discussion renvoie un échec, on l'affiche
        if run.status == "failed":
            print(run.error)

        # Si on est en mode ponctuel, on affiche les messages et on sort de la boucle
        if mode == "ponctual":
            return(getMessageListFromThread(thread.id)[0])

        # Affichage des messages et on recommence la boucle pour continuer la conversation
        print("Assistant response:\n" + getMessageListFromThread(thread.id)[0])
        time.sleep(0.1)

additionnalToolList = [adder]
additionnalToolDescriptionList = [adderDescription]

answer = getLLMAnswerWithWebBrowsingAndTools("Tu peux chercher sur internet la population de Paris et de New York en l'année 2015, puis additionner les 2 valeurs et me dire le résultat, et enfin ensuite ajouter 10 000 000 à ce résultat", mode="ponctual", additionnalToolList=additionnalToolList, additionnalToolDescriptionList=additionnalToolDescriptionList)

print(answer)