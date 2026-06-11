from src.prompt_model import prompt_model

def main():
    res = prompt_model('deepseek-r1:1.5b', "hi")
    print(res)


if __name__ == "__main__":
    main()
