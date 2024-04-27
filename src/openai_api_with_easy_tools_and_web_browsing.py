import time
import openai
import requests
import json

BING_CUSTOM_SEARCH_API_URL = "https://api.bing.microsoft.com/v7.0/custom/search?"

class BingSearchEngine():
    """Class to encapsulate Bing search functions and search result analysis."""

    def __init__(self, openAIAPIKey, subscriptionKey, model="gpt-3.5-turbo"):
        """Initializes the OpenAI client and Bing subscription with the provided API keys."""
        self.openaiClient = openai.OpenAI(api_key=openAIAPIKey)
        self.subscriptionKey = subscriptionKey
        self.model = model

    def getLLMAnswer(self, userMessage, systemMessage="You are a helpful assistant", model="gpt-3.5-turbo") :
        """This function interacts with a LLM to get a response from a user message."""
        chatCompletion = self.openaiClient.chat.completions.create(model=model, messages=[{"role": "system", "content": systemMessage}, {"role": "user", "content": userMessage}])
        return(chatCompletion.choices[0].message.content)

    def runBingSearch(self, searchQuery, verbose=False):
        """This function performs a Bing search and returns the results as text."""

        print("Running Bing search for query: " + searchQuery)

        # Create HTTP request
        bingQuery = BING_CUSTOM_SEARCH_API_URL + "q='" + searchQuery + "'&customconfig=0"

        # Execute HTTP request
        response = requests.get(bingQuery, headers={'Ocp-Apim-Subscription-Key': self.subscriptionKey})

        # Retrieve the results
        responseData = json.loads(response.text)
        results = responseData.get("webPages", {}).get("value", [])

        # Format results properly
        searchResultsString = ""
        for result in results:
            searchResultsString += "Title: " + result["name"] + "\n"
            searchResultsString += "URL: " + result["url"] + "\n"
            searchResultsString += "Snippet: " + result["snippet"] + "\n\n"

        # Remove the last newline
        searchResultsString = searchResultsString[:-2]

        if verbose:
            print("bingQuery:")
            print(bingQuery)
            print("searchResultsString:")
            print(searchResultsString)

        return(searchResultsString)

    def getSearchQueries(self, userRequest, verbose=False):
        """This function generates Bing search queries to fulfill the user's request (processed by a LLM)."""

        print("Generating search queries for Bing to satisfy the user's request...")
        # Enhance the prompt with examples to guide the generation of queries better
        prompt = "Based on the user's request, generate one or several (but non-redundant) short search queries for Bing. " \
                 "If the request covers multiple topics, provide separate queries for each topic, using semicolons to separate them." \
                 "\nFor example, if the user asks about the population of Paris, Beijing, and Baghdad, give only the response: " \
                 "'population Paris;current population Beijing;Baghdad population estimate'." \
                 "\nSimilarly, if asked about both the height of the Eiffel Tower and historical events in 1923 in England, give only the response: " \
                 "'Eiffel Tower height;historical events in 1923 England'." \
                 "Here is the user request: " + userRequest

        # Interact with the LLM to generate search queries
        searchQueries = self.getLLMAnswer(prompt, model=self.model)

        # Split the response using the semicolon as a separator and trim unnecessary spaces
        searchQueriesList = [query.strip() for query in searchQueries.split(';')]

        if verbose:
            print("searchQueriesList:")
            print(searchQueriesList)

        return(searchQueriesList)

    def processSearchResults(self, userRequest, searchResultsString, verbose=False):
        """This function analyzes Bing search results to respond to the user's request (processed by a LLM)."""

        print("Processing Bing search results...")
        # Interact with the LLM to analyze Bing search results
        prompt = "Analyze these Bing search results below to give a short answer to this user request '" + userRequest + "'\n\n'" + searchResultsString + "'"
        analysis = self.getLLMAnswer(prompt, model=self.model)

        if verbose:
            print("analysis:")
            print(analysis)

        # Return the analysis
        return(analysis)

    def bingSearch(self, userRequest, verbose=False):
        """This function performs a Bing search based on the user's request and analyzes the results (processed by a LLM)."""

        # Generate one or more Bing search queries
        searchQueriesList = self.getSearchQueries(userRequest, verbose=verbose)

        # Execute Bing searches
        searchResultsString = [self.runBingSearch(query, verbose) for query in searchQueriesList]

        # Concatenate search results with formatting to separate different queries
        cleanSearchResultsString = ""
        for i in range(len(searchResultsString)):
            cleanSearchResultsString += "SEARCH QUERY " + str(i+1) + ": '" + searchQueriesList[i] + "'\n'''\n" + searchResultsString[i] + "'''\n\n"

        # Analyze search results
        analysis = self.processSearchResults(userRequest, cleanSearchResultsString, verbose=verbose)

        # Return the analysis with an introductory text
        return "HERE IS THE ANALYSIS OF THE BING SEARCH RESULT BASED ON THE USER'S REQUEST:\n" + analysis

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

class OpenaiApiWithEasyToolsAndWebBrowsing():
    """This class allows interaction with the OpenAI API to obtain answers from user messages."""

    def __init__(self, openAIAPIKey):
        """Initializes the OpenAI client with the provided API key."""
        self.openaiClient = openai.OpenAI(api_key=openAIAPIKey)

    def getMessageListFromThread(self, threadId):
        """This function displays the messages of a thread/conversation. The output list is completed from right to left, the last message being the first in the list."""
        messageList = self.openaiClient.beta.threads.messages.list(thread_id=threadId)
        messageListThread = [message.content[0].text.value for message in messageList if message.role == "assistant"]
        return(messageListThread)

    def waitForRunCompletion(self, threadId, runId):
        """This function waits for the completion of a thread/conversation execution and returns the result."""
        while True:
            # Check the execution status 10 times per second
            time.sleep(0.1)
            run = self.openaiClient.beta.threads.runs.retrieve(thread_id=threadId, run_id=runId)
            if run.status in ["completed", "failed", "requires_action"]:
                return(run)
            # Below lines are unnecessary
            elif run.status == "in_progress":
                continue

    def getToolReturnList(self, toolsToCall, toolList=[]):
        """This function returns a list of tool outputs from a list of tools to be called."""

        toolReturnList = []

        # Call the requested tools one by one by the assistant
        for tool in toolsToCall:
            toolReturn = None
            toolCallId = tool.id
            functionName = tool.function.name
            functionArgs = tool.function.arguments

            # Search for the corresponding tool in the list of available tools
            for t in toolList:
                if functionName == t.__name__:
                    toolReturn = t(**json.loads(functionArgs))

            # Add the tool output to the list
            toolReturnList.append({"tool_call_id": toolCallId, "output": toolReturn})

        return(toolReturnList)

    def getLLMAnswerWithWebBrowsingAndTools(self, userMessage, systemMessage="You are a helpful assistant", model="gpt-3.5-turbo", mode="ponctual", toolList=[], toolDescriptionList=[]) :
        """This function interacts with a LLM to get a response from a user message. It includes 'ponctual' mode for a single return or 'continuous' mode for a continuous conversation with user input (set userMessage=None for the latter)."""

        # Initialize the assistant with the list of tools
        assistant = self.openaiClient.beta.assistants.create(instructions=systemMessage, model=model, tools=toolDescriptionList)

        # Create a conversation thread
        thread = self.openaiClient.beta.threads.create()

        # Continuous conversation loop
        while True:
            if mode == "continuous":
                print("Type 'exit' to exit the program. \nYour request: ")
                userMessage = input()
                if userMessage.lower() == "exit":
                    break

            # Create a message and an execution
            self.openaiClient.beta.threads.messages.create(thread_id=thread.id, role="user", content=userMessage)
            run = self.openaiClient.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant.id)
            # Wait for the execution to complete
            run = self.waitForRunCompletion(thread.id, run.id)

            # If (and while) the conversation execution returns a tool to call, it is called
            while run.status == "requires_action":
                # Retrieve the tools to be called
                toolsToCall = run.required_action.submit_tool_outputs.tool_calls
                print("Tools to call:")
                [print("   " + str(t)) for t in toolsToCall]
                toolReturnList = self.getToolReturnList(toolsToCall, toolList=toolList)
                run = self.openaiClient.beta.threads.runs.submit_tool_outputs(thread_id=thread.id, run_id=run.id, tool_outputs=toolReturnList)
                # Wait for the execution to complete
                run = self.waitForRunCompletion(thread.id, run.id)

            # If the conversation execution returns a failure, it is displayed
            if run.status == "failed":
                print(run.error)

            # If in 'ponctual' mode, display messages and exit the loop
            if mode == "ponctual":
                return(self.getMessageListFromThread(thread.id)[0])

            # Display messages and restart the loop to continue the conversation
            print("Assistant response:\n" + self.getMessageListFromThread(thread.id)[0])
            time.sleep(0.1)