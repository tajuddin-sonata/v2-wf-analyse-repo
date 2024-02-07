import spacy
from collections import defaultdict
from spacytextblob.spacytextblob import SpacyTextBlob
from time import time
from itertools import groupby
from spacy.tokens import Doc #################
nlp = None

# Define custom extension attributes
Doc.set_extension('blob', default=None) ####################

class Options:
    nlp_ignore = []
    rule_patterns = None
    def __init__(self, opt):
        if (opt is not None) and 'nlp_ignore' in opt:
            self.nlp_ignore = [str(x).lower() for x in opt['nlp_ignore']]
        if (opt is not None) and 'rule_patterns' in opt:
            self.rule_patterns = opt['rule_patterns']

def nlp_spacy(transcript, options=None):
    opts = Options(options)
    global nlp
    instantiate_time = 0

    if not nlp:
        start_time = time()
        # nlp=spacy.load("en_core_web_sm")
        nlp = spacy.load("en_core_web_trf")
        if opts.rule_patterns:
            nlp.add_pipe('entity_ruler', config={"validate": True}).add_patterns(opts.rule_patterns) # type: ignore
        nlp.add_pipe("merge_entities")
        nlp.add_pipe('spacytextblob')
        instantiate_time = time()-start_time

    combined_data = list(zip(
        *[(turn["turn_index"], turn["source"], turn["turn_text"]) for turn in transcript["turns_array"] if str(turn['source']).lower() not in opts.nlp_ignore]))
    indexes_to_zip, speakers_to_zip, texts_to_zip = combined_data if len(combined_data)>0 else ((),(),()); del combined_data

    nlp_turns = [{
        'turn_index': index,
        'speaker': speaker,
        **docjson,
        'ents': [{**ent, 'text': docjson['text'][ent['start']: ent['end']]} for ent in docjson['ents']],
        'sents': [{**sent, 'text': docjson['text'][sent['start']: sent['end']]} for sent in docjson['sents']],
        'tokens': [{**token, 'text': docjson['text'][token['start']: token['end']]} for token in docjson['tokens']],
        'sentiment': {'polarity': doc._.blob.polarity, 'subjectivity': doc._.blob.subjectivity}
    } for index, speaker, doc, docjson in [(index, speaker, doc, doc.to_json())
        for (index, speaker, doc) in zip(indexes_to_zip, speakers_to_zip, nlp.pipe(texts_to_zip))]]

    # group to match previous output format
    nlp_turns = {key: list(val) for key, val in groupby(sorted(nlp_turns, key=lambda turn: (
        turn['speaker'], turn['turn_index'])), lambda turn: turn['speaker'])}

    return nlp_turns, instantiate_time
