from src.prompt_model import prompt_model
from src.tag_data import tag_data
from src.find_skill_gaps import find_skill_gaps
from pathlib import Path
import sys

def main():
    # res = prompt_model('deepseek-r1:1.5b', sys.argv[1])
    # print(res)
    # tag_data("data/jobs_d1.db")
    res = find_skill_gaps("data/resume_d3_eval.txt", "data/jobs_d3_eval.db")
    print(res.gaps)


if __name__ == "__main__":
    main()
