# from fastapi import FastAPI
#
# app = FastAPI()
#
#
# @app.get("/")
# async def root():
#     return {"message": "Hello World"}
#
#
# @app.get("/hello/{name}")
# async def say_hello(name: str):
#     return {"message": f"Hello {name}"}
from dotenv import load_dotenv
load_dotenv()

from agent import MiniPlannerAgent
import asyncio

async def main():
    user_input = input("Ask something: ")
    agent = MiniPlannerAgent()
    result = await agent.run(user_input)
    print("\nFinal Answer:\n", result)

if __name__ == "__main__":
    asyncio.run(main())

