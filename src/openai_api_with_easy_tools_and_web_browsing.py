import time
import openai
import requests
import json

BING_CUSTOM_SEARCH_API_URL = "https://api.bing.microsoft.com/v7.0/custom/search?"

class BingSearchEngine():
    """We define a class to encapsulate Bing search functions and search result analysis."""

    def __init__(self, openAIAPIKey, subscriptionKey, model="gpt-3.5-turbo"):
        """Initialize the OpenAI client and the Bing subscription key using the provided API keys."""
        self.openaiClient = openai.OpenAI(api_key=openAIAPIKey)
        self.subscriptionKey = subscriptionKey
        self.model = model

    def getLLMAnswer(self, userMessage, systemMessage="You are a helpful assistant", model="gpt-3.5-turbo") :
        """This function interacts with an LLM to get a response from a user message."""
        chatCompletion = self.openaiClient.chat.completions.create(model=model, messages=[{"role": "system", "content": systemMessage}, {"role": "user", "content": userMessage}])
        return(chatCompletion.choices[0].message.content)

    def runBingSearch(self,searchQuery, verbosity=0):
        """This function performs a Bing search and returns the results as text."""

        if verbosity >= 1:
            print("Running Bing search for query: " + searchQuery)

        # Create the HTTP request
        bingQuery = BING_CUSTOM_SEARCH_API_URL + "q='" + searchQuery + "'&customconfig=0"

        # Perform the HTTP request
        response = requests.get(bingQuery, headers={'Ocp-Apim-Subscription-Key': self.subscriptionKey})

        # Retrieve the results
        responseData = json.loads(response.text)
        results = responseData.get("webPages", {}).get("value", [])

        # Format the results properly
        searchResultsString = ""
        for result in results :
            searchResultsString += "Title : " + result["name"] + "\n"
            searchResultsString += "URL : " + result["url"] + "\n"
            searchResultsString += "Snippet : " + result["snippet"] + "\n\n"

        # Remove the last line break
        searchResultsString = searchResultsString[:-2]

        if verbosity >= 2:
            print("bingQuery :")
            print(bingQuery)
            print("searchResultsString :")
            print(searchResultsString)

        return(searchResultsString)



    def getSearchQueries(self, userRequest, verbosity=0):
        """This function generates Bing search queries to meet the user's request
        (via processing by an LLM)"""

        if verbosity >= 1:
            print("Generating search queries for Bing to satisfy the user's request...")

        # Enrich the prompt with examples to better guide the generation of queries
        prompt = "Based on the user's request, generate one or several (but non-redundant) short search queries for Bing. " \
                 "If the request covers multiple topics, provide separate queries for each topic, using semicolons to separate them." \
                 "\nFor example, if the user asks about the population of Paris, Beijing, and Baghdad, give only the response : " \
                 "'population Paris;current population Beijing;Baghdad population estimate'." \
                 "\nSimilarly, if asked about both the height of the Eiffel Tower and historical events in 1923 in England, give only the response : " \
                 "'Eiffel Tower height;historical events in 1923 England'." \
                 "Here is the user request: " + userRequest

        # Interact with the LLM to generate search queries
        searchQueries = self.getLLMAnswer(prompt, model=self.model)

        # Split the response using semicolon as a separator and eliminate unnecessary spaces
        searchQueriesList = [query.strip() for query in searchQueries.split(';')]

        if verbosity >= 1:
            print("searchQueriesList :")
            print(searchQueriesList)

        return(searchQueriesList)



    def processSearchResults(self, userRequest, searchResultsString, verbosity=0):
        """This function analyzes the Bing search results to respond to the user's request
        (via processing by an LLM)"""

        if verbosity >= 1:
            print("Processing Bing search results...")

        # Interact with Anthropic's Haiku LLM to analyze Bing search results
        prompt = "Analyze these Bing search results below to give a short answer to this user request '" + userRequest + "'\n\n'" + searchResultsString + "'"
        analysis = self.getLLMAnswer(prompt, model=self.model)

        if verbosity >= 2:
            print("analysis :")
            print(analysis)

        # Return the analysis
        return(analysis)



    def bingSearch(self, userRequest, verbosity=0):
        """This function performs a Bing search based on the user's request and analyzes the results
        (via processing by an LLM)"""

        # Generate one or more Bing search queries
        searchQueriesList = self.getSearchQueries(userRequest, verbosity=verbosity)

        # Execute the Bing search(es)
        searchResultsString = [self.runBingSearch(e, verbosity) for e in searchQueriesList]

        # Concatenate the search results with some formatting to separate the different queries
        cleanSearchResultsString = ""
        for i in range(len(searchResultsString)):
            cleanSearchResultsString += "SEARCH QUERY " + str(i+1) + " : '" + searchQueriesList[i] + "'\n'''\n" + searchResultsString[i] + "'''\n\n"

        # Analyze the search result(s)
        analysis = self.processSearchResults(userRequest, cleanSearchResultsString, verbosity=verbosity)

        # Return the analysis with an introductory text
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

class runFailedError(Exception):
    pass

class runIncompleteError(Exception):
    pass

class OpenaiApiWithEasyToolsAndWebBrowsing():
    """This class allows interacting with the OpenAI API to get responses from user messages."""

    def __init__(self, openAIAPIKey):
        """Initialize the OpenAI client with the provided API key."""
        self.openaiClient = openai.OpenAI(api_key=openAIAPIKey)

    def getMessageListFromThread(self, threadId):
        """This function displays the messages of a thread/discussion thread.
        The output list is populated from right to left, the last message is the first in the list."""
        messageList = self.openaiClient.beta.threads.messages.list(thread_id=threadId)
        messageListThread = [message.content[0].text.value for message in messageList if message.role == "assistant"]
        return(messageListThread)

    def waitForRunCompletion(self, threadId, runId):
        """This function waits for the completion of a thread/conversation run and returns the result"""
        while True:
            # Check the status of the run 10 times per second
            time.sleep(0.1)
            run = self.openaiClient.beta.threads.runs.retrieve(thread_id=threadId, run_id=runId)
            if run.status in ["completed", "failed", "incomplete", "requires_action"]:
                return(run)
            # Lines below are not necessary
            elif run.status == "in_progress" :
                continue

    def getToolReturnList(self, toolsToCall, toolList=[]):
        """This function returns a list of tool returns from a list of tools to call"""

        toolReturnList = []

        # Call the tools requested by the assistant one by one
        for tool in toolsToCall:
            toolReturn = None
            toolCallId = tool.id
            functionName = tool.function.name
            functionArgs = tool.function.arguments

            # Find the corresponding tool in the list of available tools
            for t in toolList:
                if functionName == t.__name__:
                    toolReturn = t(**json.loads(functionArgs))

            # Add the tool return to the list
            toolReturnList.append({"tool_call_id": toolCallId, "output": toolReturn})

        return(toolReturnList)

    def getLLMAnswer(self,
                     userMessage,
                     systemMessage="You are a helpful assistant",
                     model="gpt-3.5-turbo",
                     mode="ponctual",
                     toolList=[],
                     toolDescriptionList=[],
                     temperature=1,
                     top_p=1,
                     max_prompt_tokens=32768,
                     max_completion_tokens=32768,
                     verbosity=0):
        """This function interacts with an LLM to get a response from a user message.
        There is 'ponctual' mode for a single response or 'continuous' mode for
        continuous conversation with user input (then set userMessage=None)."""

        # Initialize the assistant with the list of tools
        assistant = self.openaiClient.beta.assistants.create(instructions=systemMessage, model=model, tools=toolDescriptionList)

        # Create a discussion thread
        thread = self.openaiClient.beta.threads.create()

        # Continuous conversation loop
        while True:
            if mode == "continuous":
                print("\nYour request (Type 'exit' to exit the program) : ")
                userMessage = input()
                if userMessage.lower() == "exit":
                    break

            # Create a message and a run
            self.openaiClient.beta.threads.messages.create(thread_id=thread.id, role="user", content=userMessage)
            run = self.openaiClient.beta.threads.runs.create(thread_id=thread.id,
                                                             assistant_id=assistant.id,
                                                             temperature=temperature,
                                                             top_p=top_p,
                                                             max_prompt_tokens=max_prompt_tokens,
                                                             max_completion_tokens=max_completion_tokens
                                                             )
            # Wait for the end of the run
            run = self.waitForRunCompletion(thread.id, run.id)

            # If (and as long as) the discussion run returns a tool to be called, call it
            while run.status == "requires_action":
                # Retrieve the tools to be called
                toolsToCall = run.required_action.submit_tool_outputs.tool_calls
                if verbosity >= 1:
                    print("Tool(s) called:")
                    [print("   " + str(t)) for t in toolsToCall]
                toolReturnList = self.getToolReturnList(toolsToCall, toolList=toolList)
                run = self.openaiClient.beta.threads.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=toolReturnList)
                # Wait for the end of the run
                run = self.waitForRunCompletion(thread.id, run.id)

            # If the discussion run returns a failure, raise an exception
            if run.status == "failed":
                raise runFailedError(run.last_error)

            # If the discussion run returns "incomplete", raise an exception
            if run.status == "incomplete":
                raise runIncompleteError(run.incomplete_details)

            # If in punctual mode, display the messages and exit the loop
            if mode == "ponctual":
                return(self.getMessageListFromThread(thread.id)[0])

            # Display the messages and restart the loop to continue the conversation
            print("\nAssistant response:\n" + self.getMessageListFromThread(thread.id)[0])
            time.sleep(0.1)
