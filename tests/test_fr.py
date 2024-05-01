import src.openai_api_with_easy_tools_and_web_browsing as webBrowsingApiGPT

# On entre nos clés d'API
subscriptionKey = ""
openAIAPIKey = ""

### Création de l'outil de recherche Bing ###

# On crée un moteur de recherche Bing qui synthétise les résultats avec GPT-3.5-turbo
bingSearchEngine = webBrowsingApiGPT.BingSearchEngine(openAIAPIKey, subscriptionKey, model="gpt-3.5-turbo")
# On renomme la fonction de recherche Bing (sinon cela ne fonctionne pas en tant que tool dans l'API d'OpenAI)
bingSearch = bingSearchEngine.bingSearch
# On prend la description de la fonction de recherche Bing déjà faite (la fonction doit être nommée 'bingSearch')
bingSearchDescription = webBrowsingApiGPT.BING_SEARCH_DESCRIPTION

### Création de l'outil pour l'addition ###

def adder(a, b):
    """Cette fonction ajoute deux nombres ensemble"""
    return (str(a + b))

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
            "required": ["a", "b"]
        }
    }
}

# On crée une instance de la classe 'OpenaiApiWithEasyToolsAndWebBrowsing'
openaiEpiWithEasyToolsAndWebBrowsing = webBrowsingApiGPT.OpenaiApiWithEasyToolsAndWebBrowsing(openAIAPIKey)

### Renvoie d'une réponse à un prompt en mode 'ponctual' ###
print("MODE PONCTUEL\n")
prompt = "Tu peux chercher sur internet la population de Paris et de New York en l'année 2015, puis additionner les 2 valeurs et me dire le résultat, et enfin ensuite ajouter 10 000 000 à ce résultat"
# On utilise la fonction 'getLLMAnswerWithWebBrowsingAndTools' pour obtenir une réponse à partir d'un message utilisateur
answer = openaiEpiWithEasyToolsAndWebBrowsing.getLLMAnswerWithWebBrowsingAndTools(prompt, systemMessage="You are a helpful assistant", model="gpt-3.5-turbo", mode="ponctual", toolList=[bingSearch, adder], toolDescriptionList=[bingSearchDescription, adderDescription], verbosity=1)
# La réponse, en utilisant l'outil de web browsing et l'additionneur doit être quelque chose du genre :
# "La population totale de Paris et de New York en 2015 était d'environ 31 082 144 habitants.
# Si l'on ajoute 10 000 000 à ce nombre, on obtient 41 082 144."
print(answer)

### Discussion en mode 'continuous' ###s
print("\n\n\nMODE CONTINUE\n")
openaiEpiWithEasyToolsAndWebBrowsing.getLLMAnswerWithWebBrowsingAndTools(None, systemMessage="You are a helpful assistant", model="gpt-3.5-turbo", mode="continuous", toolList=[bingSearch, adder], toolDescriptionList=[bingSearchDescription, adderDescription], verbosity=1)