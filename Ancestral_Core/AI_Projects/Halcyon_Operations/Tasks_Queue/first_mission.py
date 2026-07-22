import time
import random

def generate_story():
    themes = ["friendship", "courage", "kindness"]
    characters = ["a brave fox", "a curious child", "a wise owl"]
    settings = ["a magical forest", "a distant planet", "a hidden valley"]

    return f"A story about {random.choice(characters)} in {random.choice(settings)}, teaching {random.choice(themes)}."

def write_book():
    print("Writing book...")
    time.sleep(2)
    story = generate_story()
    with open("E:/AI_Projects/Halcyon_Documents/book.txt", "w") as book:
        book.write(story)
    print("Book written!")

def publish_book():
    print("Publishing...")
    time.sleep(2)
    print("Book published successfully!")

if __name__ == "__main__":
    write_book()
    publish_book()
