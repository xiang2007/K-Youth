from src.prompt_model import prompt_model
from src.tag_data import tag_data
import sys

def main():
    # res = prompt_model('deepseek-r1:1.5b', sys.argv[1])
    # print(res)
    tag_data("data/jobs_d1.db")


if __name__ == "__main__":
    main()
