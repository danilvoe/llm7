# github mcp собран по MR - https://github.com/github/github-mcp-server/pull/888
# GITHUB_PERSONAL_ACCESS_TOKEN="token"  ./github-mcp-server http --port 8080

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import asyncio
import ollama
import json
import re


class BasicActionLLM:
    def __init__(self):
        self.model = ""
        self.conversation_history = []
        self.system_prompt = ""
        self.finish_prompt = ""
        self.think_delete = False

    def add_to_context(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

    def clear_context(self):
        self.conversation_history = []

    def get_llm_response(self, prompt: str, role='user', tools=True):
        if tools:
            tools = [GeneralInformation.mcp_list_branches]
        else:
            tools = []
        final_response = False
        self.add_to_context(role, prompt)
        try:
            response = ollama.chat(
                model=self.model,
                messages=self.conversation_history,
                stream=False,
                tools=tools,
            )
            llm_response = response["message"]["content"].strip()
            self.add_to_context("assistant", llm_response)
            available_functions = {
                'mcp_list_branches': GeneralInformation.mcp_list_branches,
            }
            for tool in response.message.tool_calls or []:
                function_to_call = available_functions.get(tool.function.name)
                if function_to_call:
                    bra =  function_to_call(**tool.function.arguments)
                    self.clear_context()
                    self.add_to_context('system', f'Список веток: "{bra}" , представлены ветки репозитория {tool.function.arguments.get('repo')} пользователя GitHub {tool.function.arguments.get('owner')}. размышляй и отвечай только на Русском языке')
                    final_response, llm_response = self.get_llm_response('необходимо посчитать количество веток в представленном списке, вернуть список веток и общие их количество. В ответе нужно обязательно указать репозиторий и автора, список  веток нужно оформить в список')
                else:
                    print('Function not found:', tool.function.name)
            return final_response, llm_response
        except Exception as e:
            print(f"Ошибка при обращении к LLM: {str(e)}")
            return final_response, ""

    def clean_response(self, llm_response: str):
        return re.sub(r"<think>.*?</think>", "", llm_response, flags=re.DOTALL).strip()

class GeneralInformation(BasicActionLLM):
    def __init__(self):
        self.model = "qwen3:30b"
        self.conversation_history = []
        self.system_prompt = """
            размышляй и пиши только на Русском языке
            Ты система для работы с Github.
            Умеешь:
            1. собирать список веток в проекте, для этого тебе нужно запросить владельца проекта и название проекта(репозитория) и вызвать функцию для получения веток проекта.
        """
        self.sending_prompt = ""
        self.think_delete = True
        
    
    def get_gamedev_tz_info(self):
        self.add_to_context("system", self.system_prompt)
        _final, response = self.get_llm_response("Привет")
        print(f"Бот: {response}")
        user_input = input("\nВы: ").strip()
        final, response = self.get_llm_response(user_input)
        print(response)
        

    @staticmethod
    def mcp_list_branches(owner:str, repo:str):
        """
        Получение веток проекта

        Args:
            owner: Владелиц проекта(репозиторий)
            repo: Название проекта

        Returns:
            str: список веток
        """
        return asyncio.run( GeneralInformation._mcp_list_branches(owner, repo))
        
    @staticmethod
    async def _mcp_list_branches(owner:str, repo:str):
        async with streamablehttp_client("http://127.0.0.1:8080") as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                try:
                    result = ''
                    await session.initialize()
                    branches = await session.call_tool('list_branches', {'owner': owner,'repo': repo})
                    branches = json.loads(branches.content[0].text)
                    return ", ".join(item["name"] for item in branches)
                except Exception as e:
                    print(f"Ошибка при обращении к LLM: {str(e)}")
        
def main():
    bot_info = GeneralInformation()
    s = bot_info.get_gamedev_tz_info()


if __name__ == "__main__":
    main()