# === SPELLCHECKER ===
import re
from spellchecker import SpellChecker
from operator import concat
from functools import reduce
import json
from time import time

import os
import logging

#TODO Remove termcolor after debug
# from termcolor import colored, cprint

class Options:
    correct_words = None
    def __init__(self, opt):
        if (opt is not None) and 'add_words' in opt:
            self.correct_words = opt["add_words"]

spell=None
# add_words_loc = 'spellchecker/add_words.json'
# remove_words_loc = 'spellchecker/remove_words.json'

remove_words_loc = os.path.join(os.path.dirname(__file__), 'spellchecker', 'remove_words.json')

# VARIABLES for cleaning text: ========================
# Match as many URLS as possible (optional https://)
re_url='(?:(?:(?:https?|ftp)://(?:[^\s/$.?#]+\.)[^\s/$.?#].[^\s\]]*)|(?:(?:[^\s/$.?#]+\.)+(?:(?:[a-zA-Z]{2,}\/)|(?:(?:aero|asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|name|net|org|pro|tel|travel|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|au|aw|ax|az|ba|bb|bd|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cx|cy|cz|cz|de|dj|dk|dm|do|dz|ec|ee|eg|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|mg|mh|mk|ml|mn|mn|mo|mp|mr|ms|mt|mu|mv|mw|mx|mz|na|nc|ne|nf|ng|ni|nl|nr|nu|nz|nom|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ra|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|sj|sk|sl|sm|sn|sr|st|su|sv|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw|arpa)(?:(?=[\s\/])|$)))[^\s\]]*))'
# Match all emails (official RFC standard regex)
re_email='(?:[a-z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&\'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])'
# Split on Whitespace, and Symbols that aren't ' (apostrophes)
re_split_on='(?:^\'|\'$)|(?:(?![\'])[.\W])'
# Match non-digits
re_has_digits='[0-9]'
# Self-explanatory I hope
minSpellCheckCharLength = 4
#=====================================================

def spellcheck(normalised, options):
    global spell       
    opts = Options(options)
    instantiate_time = 0
    
    if not spell:
        start_time = time()
        spell = SpellChecker()
        with open(remove_words_loc, 'r') as f:
            incorrect_words = json.load(f)
        if opts.correct_words:
            spell.word_frequency.load_words(opts.correct_words)
        spell.word_frequency.remove_words(incorrect_words)
        correct_words = None
        del correct_words
        incorrect_words = None
        del incorrect_words
        instantiate_time = time() - start_time

    logging.info(f"Spellchecker instantiated in {instantiate_time} seconds")
    logging.info("Current Working Directory: %s", os.getcwd())
    
    for turn in normalised["turns_array"]:
        text = turn["turn_text"]
        cleaned = clean_turn_text(text)
        turn = correct_turn(turn=turn, cleaned=cleaned)

    logging.info("Spellcheck completed successfully")

    return normalised, instantiate_time

def clean_turn_text(turn):
    # print(turn)
    turn_split_whitespace = re.split(f'(\s)', turn)
    turn_split_nested = [([((True, el) if not re.search(re_has_digits, el) and len(el) > minSpellCheckCharLength else (False, el)) for el in re.split(
        f'({re_split_on})', block) if el != ''] if not re.search(f'{re_url}|{re_email}', block) else [(False, block)]) for block in turn_split_whitespace]
    turn_split = reduce(concat, turn_split_nested)
    # print([t for f,t in turn_split])
    turn_split_with_indexing = []
    for i, item in enumerate(turn_split):
        flag, token = item # type: ignore
        running_len = sum([len(token) for (flag, token) in turn_split[:i]]) # type: ignore
        # print(running_len, running_len+len(token), turn[running_len:running_len+len(token)])
        turn_split_with_indexing.append((flag, token, running_len, running_len+len(token)))
    # rebuild = ''.join([ token for flag, token, start, end in turn_split_with_indexing])
    # if rebuild != turn:
    #     raise Exception(f"sentence rebuild does not match original, something went wrong during deconstruction:\nOriginal:{turn}\nRebuilt :{rebuild}")
    return turn_split_with_indexing

def correct_turn(turn, cleaned):
    new_turn_split = [o for f, o, s, e in cleaned]
    words_to_check = [ (i,o,s,e) for i, (f,o,s,e) in enumerate(cleaned) if f]
    # cprint(words_to_check,'yellow')
    
    
    # Misspelled
    misspelled = tuple(set(spell.unknown([o.lower() for (i,o,s,e) in words_to_check]))) # type: ignore
    if not misspelled:
        return turn
    # cprint(misspelled,'blue')
    misspelled = reduce(concat, [ [(i,o,s,e) for (i,o,s,e) in words_to_check if o.lower()==m] for m in misspelled])
    # cprint(misspelled,'blue')

    # Corrected
    corrected = [(ind,ori,sta,end,spell.correction(ori.lower())) for (ind,ori,sta,end) in misspelled] # type: ignore
    # cprint(corrected,'red')
    for i, (ind,ori,sta,end,cor) in enumerate(corrected):
        if not bool(re.search('[a-z]',ori)):
            corrected[i] = (ind,ori,sta,end,cor.upper())
        elif bool(re.search('^[A-Z]',ori)):
            corrected[i] = (ind,ori,sta,end,re.sub('(^[a-z])(.*)',lambda x: x.group(1).upper() + x.group(2), cor))
    # cprint(corrected,'red')
    
    # Update Token List
    for (ind,ori,sta,end,cor) in corrected:
        if not ori.lower() == cor.lower():
            new_turn_split[ind]=cor
    # cprint(new_turn_split,'green')
    
    # Re-calc character positions
    new_turn_split_with_indexing = []
    for i, token in enumerate(new_turn_split):
        running_len = sum([len(token) for token in new_turn_split[:i]])
        new_turn_split_with_indexing.append((token, running_len, running_len+len(token)))
    # cprint(new_turn_split_with_indexing, 'green')
    
    # add corrected positions to corrected
    for i, (ind,ori,sta,end,cor) in enumerate(corrected):
        corrected[i] = (ind,ori,sta,end,cor,new_turn_split_with_indexing[ind][1],new_turn_split_with_indexing[ind][2]) # type: ignore
    # cprint(corrected,'magenta')
    
    new_turn_text = ''.join(new_turn_split)
    # cprint(new_turn_text,'green')
    
    # Write the list of misspelled words into the Transcript
    
    tags=[]
    
    corrected = sorted(corrected, key=lambda x: x[0])
    for (ind,ori,sta,end,cor,c_sta,c_end) in corrected: # type: ignore
        tag={"text":ori,
             "start":sta,
             "end":end }
        if not ori.lower()==cor.lower():
            tag={**tag,
                 "corr":cor }
        tags.append(tag)
    
    if not new_turn_text == turn["turn_text"]:
        turn["corr_text"]=new_turn_text
    turn["misspelled_words"]=tags
    return turn
