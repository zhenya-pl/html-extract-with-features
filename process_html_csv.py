from bs4 import BeautifulSoup
from bs4 import NavigableString
import lxml.html
from lxml import etree
import re
import nltk
from nltk.tokenize import RegexpTokenizer
import os
import html2text
import csv

def parse_file(file):
    tree = lxml.html.parse(file)
    etree.strip_elements(tree, 'script') #Remove JavaScript
    etree.strip_elements(tree, 'style') #Remove style tags
    page = tree.getroot()
    body = page.cssselect('body')[0] # Do a check that the list is non-empty
    return (page, body)

def find_winner_div(page, body):
    pattern = re.compile(r"\s\s+", re.MULTILINE)
    b_pattern = re.compile(b"\s\s+", re.MULTILINE)
    title = pattern.sub(" ", page.find(".//title").text)
    article = body.find(".//article")
    if (article is not None):
        # First, check for the tag <article>
        winner = article
    else:
        # If that fails, apply div logic.
        divs = body.cssselect('div')
        max_text_ratio = 0
        div_tuples = []
        for div in divs:
            #Calculate ratio of text to all content for each div
            ratio = len(pattern.sub("", div.text_content()))/len(b_pattern.sub(b"", etree.tostring(div)))
            div_tuples.append((div, ratio))
            if ratio > max_text_ratio:
                max_ratio_div = div
                max_text_ratio = ratio
        sorted_divs = sorted(div_tuples, key=lambda div:div[1], reverse=True) #Sort by ratio, highest ratio first
        candidate_divs = []
        if (len(sorted_divs) > 6):
            candidate_divs = [item[0] for item in sorted_divs[0:6]]
        else:
            candidate_divs = [item[0] for item in sorted_divs]
        # Tokenize by words
        tokenizer = RegexpTokenizer(r'\w+')
        max_words = 0
        for div in candidate_divs:
            tokens = tokenizer.tokenize(div.text_content())
            #print(tokens)
            num_tokens = len(tokenizer.tokenize(div.text_content()))
            if num_tokens > max_words:
                max_words = num_tokens
                winner = div
    #Remove whitespace from the final text
    winner_text = (etree.tostring(winner)).decode('utf-8')
    h2tconv = html2text.HTML2Text()
    h2tconv.ignore_links = True
    h2tconv.ignore_images = True
    winner_text = h2tconv.handle(winner_text)
    winner_text = '\n'.join([' '.join(line.split()) for line in winner_text.splitlines() if line.strip()])
    return (title, winner_text, winner)

def tag_text (html, text, cur_tags, ti):
    if (isinstance (html, NavigableString)):
        ctags = cur_tags[:]
        text.append((str(html), ctags))
        return (text, cur_tags)
    else:
        children = html.contents
        for child in children:
            #Add current tag to list
            if ((not isinstance (child, NavigableString))
                and child.name in ti):
                tag = child.name
                cur_tags.append(tag)
            (text, cur_tags) = tag_text(child, text, cur_tags, ti)
        if (len(cur_tags) > 0):
            cur_tags.pop()
        return (text, cur_tags)

def get_sentences(winner_div, tags_to_include):
    wtext = ((etree.tostring(winner_div)).decode('utf-8'))
    div_soup = BeautifulSoup(wtext, "lxml")
    (text, cur_tags) = tag_text(div_soup, [], [], tags_to_include)
    pattern = re.compile(r'\<(.*?)\>')
    text = [x for x in text if (not pattern.findall(x[0]) and not x[0].isspace())]
    sentences = []
    for elem in text:
        t = elem[0]
        f = elem[1]
        sents = tokenizer.tokenize(t)
        for s in sents:
            sentences.append((s, f))
    return sentences

def write_data(sentences, csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as fp:
        writer = csv.writer(fp, delimiter=',')
        for s in sentences:
            row = [s[0]] + s[1]
            writer.writerow(row)


tags_to_include = ['p', 'em', 'i', 'b', 'strong', 'mark', 'small', 'ins', 'u']
tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
cur_sub_tdir = "Path" #EDIT
if (os.path.isdir(cur_sub_tdir)):
    file_list = sorted(os.listdir(cur_sub_tdir))
    for file in file_list:
        if (not os.path.isdir(file) and ".html" in file and ".txt" not in file):
            html_file = os.path.join(cur_sub_tdir, file)
            file = file.replace('.html', '.txt')
            csv_file = html_file.replace('.html', '.csv')
            if (os.path.isfile(html_file)):
                (page, body) = parse_file(html_file)
                (title, winner_text, winner) = find_winner_div(page, body)
                sentences = get_sentences(winner, tags_to_include)
                sentences = [(title, [])] + sentences
                write_data(sentences, csv_file)
