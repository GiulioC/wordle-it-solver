import requests
import asyncio
import json

from pyppeteer import launch

WORD_LIST = "https://github.com/pietroppeter/wordle-it/raw/master/big5.txt"

async def find_target_word(words):
    browser = await launch({'headless': True})
    page = await browser.newPage()
    await page.goto('https://pietroppeter.github.io/wordle-it/')
    await page.waitFor(1000);

    # hide rules/info banner
    await page.mouse.click(0,0)
    await page.waitFor(1000);

    correct_word = {0: '*', 1: '*', 2: '*', 3: '*', 4: '*'}

    for attempt_num in range(0,6):
        test_word = max(words, key=compute_word_score)
        print(f"Attempt #{attempt_num+1}: {test_word.upper()}", end="\r")

        # write the word in the page
        for char in test_word:
            await page.keyboard.type(char)
            await page.waitFor(100)
        await page.keyboard.press("Enter")

        # wait for page animation after entering word
        await page.waitFor(4000);

        # read gameState from localStorage and check word result for current word
        localStorage = await page.evaluate('''() => {
          let value, storage = {}
          for (let key in localStorage) {
            if (value = localStorage.getItem(key))
              storage[key] = value
          }
          return storage
        }''')
        gameState = json.loads(localStorage['gameState'])

        # get the indexes of absent/present/correct letters in the word
        result_idxs = check_word_result(gameState)
        print(f"Attempt #{attempt_num+1}: {test_word.upper()} - {convert_idxs_to_boxes(result_idxs)}")

        if gameState['gameStatus'] == 'WIN':
            print("Word found:", test_word.upper())
            break;

        # word not found after 6th attempt
        if attempt_num == 6:
            print("Could not find word :(")
            break;

        # fill correct characters, if any
        correct_word = update_correct_word(correct_word, test_word, result_idxs['correct'])

        # filter remaining candidate words
        words = [word for word in words if word_filter(word, test_word, result_idxs, correct_word)]

    await browser.close()

def check_word_result(word_result):
    result_indexes = {
        "absent": [],
        "present": [],
        "correct": []
    }

    # get last not None element from the list (= last try)
    evaluations = list(filter(lambda el: el is not None, word_result['evaluations']))
    for i, ev in enumerate(evaluations[-1]):
        result_indexes[ev].append(i)

    return result_indexes

def word_filter(word, test_word, result_idxs, correct_word):
    if word == test_word:
        return False

    # ignore any word that contains an absent character
    if any([test_word[idx] in word for idx in result_idxs['absent']]):
        return False

    # ignore any word that contains a present character in the same position
    # as the current one
    if any([test_word[idx] not in word or word.index(test_word[idx]) == idx for idx in result_idxs['present']]):
        return False

    # ignore any word that does not have all che correct characters
    if any([c != '*' and word[idx] != c for idx,c in correct_word.items()]):
        return False

    return True

def update_correct_word(correct_word, current_word, correct_idxs):
    for idx in correct_idxs:
        correct_word[idx] = current_word[idx]
    return correct_word

def retrieve_word_list(url):
    res = requests.get(url).text.split("\n")
    return [w for w in res if len(w) == 5 and "'" not in w]

def compute_word_score(word):
    return sum([letters_frequencies[letter] for letter in set(word)])

def convert_idxs_to_boxes(result_idxs):
    boxes = {0: None, 1: None, 2: None, 3: None, 4: None}
    box_map = {"absent":"⚫", "present":"🔴", "correct":"🔵"}
    for type, idxs in result_idxs.items():
        for idx in idxs:
            boxes[idx] = box_map[type]
    return ' '.join(boxes.values())

if __name__ == '__main__':
    res = requests.get(WORD_LIST).text.split("\n")
    words = [w for w in res if len(w) == 5 and "'" not in w]

    letters_occurrences = {}
    for word in words:
        for pos, letter in enumerate(word):
            try:
                letters_occurrences[letter] += 1
            except KeyError:
                letters_occurrences[letter] = 1

    total_occurrences = sum(letters_occurrences.values())
    letters_frequencies = {letter:letters_occurrences[letter]/total_occurrences for letter in letters_occurrences.keys()}

    asyncio.get_event_loop().run_until_complete(find_target_word(words))
