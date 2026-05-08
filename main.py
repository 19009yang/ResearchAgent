import os

from dotenv import load_dotenv

from tools.logging_config import setup_logging

# from .workflow_1 import run_workflow
from agent.ReAct_Agent import run_workflow


    
def main():
    setup_logging()
    #执行ReAct工作流
    run_workflow()


if __name__ == "__main__":
    main()