# === METRICS v2 ===
from itertools import groupby, chain
import time, datetime

META = "metadata"
DURATION = "duration"
TURNS = "turns_array"
TURN_INDEX = "turn_index"
TURN_TEXT = "turn_text"
WORDS_ARR = "words_array"
WORD_TEXT = "word_text"
START_TIME = "start_time"
END_TIME = "end_time"
SOURCE = "source"



def calculate_metrics(normalised):

    metrics={}
    all_turns=normalised[TURNS]
    turns_sorted_by_speaker=None
    turns_grouped_by_speaker=None
    words_grouped_by_speaker=None
    
    # === VOICE ONLY ===
    if normalised["metadata"]["media"]["media_type"] == "voice":
        turns_sorted_by_speaker = sorted(all_turns, key=lambda turn: (turn[SOURCE], turn[START_TIME], turn[END_TIME]))
        turns_grouped_by_speaker = {speaker: list(turn) for speaker, turn in groupby(turns_sorted_by_speaker, lambda turn: turn[SOURCE])}
        words_grouped_by_speaker = {speaker: list(chain(*[[word[WORD_TEXT] for word in turn[WORDS_ARR]] for turn in turns])) for speaker, turns in turns_grouped_by_speaker.items()} # type: ignore
        metrics_by_person = { speaker: {"speaker": speaker} for speaker, turns in turns_grouped_by_speaker.items()}
        # calculate VOICE-ONLY metrics PER PERSON
        for speaker, speaker_turns in turns_grouped_by_speaker.items():
            metrics_by_person[speaker]['talk_rate'] = _talk_rate(speaker=speaker, duration=normalised[META][DURATION], all_turns=all_turns, tgbs=turns_grouped_by_speaker, wgbs=words_grouped_by_speaker) # type: ignore
            metrics_by_person[speaker]['talk_pct'] = _talk_pct(duration=normalised[META][DURATION], speaker_turns=speaker_turns)
            metrics_by_person[speaker]['longest_turn_secs'] = _longest_turn_secs(speaker_turns=speaker_turns) # type: ignore
            metrics_by_person[speaker]['average_turn_secs'] = _average_turn_secs(speaker_turns=speaker_turns) # type: ignore
            metrics_by_person[speaker]['overtalk_incidents_array'] = _overtalk_incidents(speaker=speaker, all_turns=all_turns) # type: ignore
            metrics_by_person[speaker]['overtalk_count'] = _overtalk_count(metrics_by_person[speaker]['overtalk_incidents_array']) # type: ignore
            
        # calculate VOICE-ONLY metrics OVER ALL PEOPLE
        metrics['longest_turn_secs'] = _global_longest_turn_secs(all_turns=all_turns)
        metrics['average_turn_secs'] = _global_average_turn_secs(all_turns=all_turns)
        metrics['silence_pct'] = _global_silence_pct(metrics_by_person=metrics_by_person)
        
    # === CHAT ONLY ===
    elif normalised["metadata"]["media"]["media_type"] == "chat":
        turns_sorted_by_speaker = sorted(all_turns, key=lambda turn: (turn['source'], time.mktime(datetime.datetime.fromisoformat(turn['timestamp']).timetuple())))
        turns_grouped_by_speaker = {speaker: list(turn) for speaker, turn in groupby(turns_sorted_by_speaker, lambda turn: turn[SOURCE])}
        words_grouped_by_speaker = {speaker: list(chain(*[[word for word in turn[TURN_TEXT].split() if word] for turn in turns])) for speaker, turns in turns_grouped_by_speaker.items()} # type: ignore
        metrics_by_person = { speaker: {"speaker": speaker} for speaker, turns in turns_grouped_by_speaker.items()}
        # calculate CHAT-ONLY metrics PER PERSON
            # N/A
        # calculate CHAT-ONLY metrics OVER ALL PEOPLE
            # N/A
    else:
        raise Exception("calculate_metrics: Transcript is not of 'chat' or 'voice' type")

    # calculate GENERIC metrics PER PERSON
    for speaker, speaker_turns in turns_grouped_by_speaker.items():
        metrics_by_person[speaker]['vocab'] = _vocab(speaker_words=words_grouped_by_speaker[speaker]) # type: ignore
        metrics_by_person[speaker]['total_turns'] = _total_turns(speaker_turns=speaker_turns) # type: ignore
        metrics_by_person[speaker]['first_turn'] = _first_turn(speaker_turns=speaker_turns) # type: ignore
        metrics_by_person[speaker]['last_turn'] = _last_turn(speaker_turns=speaker_turns) # type: ignore
        metrics_by_person[speaker]['longest_turn_words'] = _longest_turn_words(speaker_turns=speaker_turns) # type: ignore
        metrics_by_person[speaker]['average_turn_words'] = _average_turn_words(speaker_turns=speaker_turns) # type: ignore

    # calculate GENERIC metrics OVER ALL PEOPLE
    metrics['duration'] = normalised[META][DURATION]
    metrics['total_turns'] = _global_total_turns(all_turns=all_turns)
    metrics['vocab'] = _global_vocab(wgbs=words_grouped_by_speaker)
    metrics['longest_turn_words'] = _global_longest_turn_words(all_turns=all_turns)
    metrics['average_turn_words'] = _global_average_turn_words(all_turns=all_turns)

    # add person metrics
    metrics['speaker_metrics_array'] = list(metrics_by_person.values())
    return metrics

    # ========== PER-PERSON METRICS ==========
    
    # === GENERIC ====
    
def _vocab(speaker_words):
    # vocab - Voice/Chat
    return len(set(list(map(lambda w: ''.join(filter(str.isalnum, w)).lower(), speaker_words))))
        
def _total_turns(speaker_turns):
    # total_turns - Voice/Chat
    return len(speaker_turns)

def _longest_turn_words(speaker_turns):
    # longest_turn_words - Voice/Chat
    return max([len(turn[WORDS_ARR] if WORDS_ARR in turn else [word for word in turn[TURN_TEXT].split() if word]) for turn in speaker_turns])
    
def _average_turn_words(speaker_turns):
    # average_turn_words - Voice/Chat
    return sum([len(turn[WORDS_ARR] if WORDS_ARR in turn else [word for word in turn[TURN_TEXT].split() if word]) for turn in speaker_turns])/len(speaker_turns)

def _first_turn(speaker_turns):
    # first_turn last_turn - Voice/Chat
    return next((turn['turn_index'] for turn in speaker_turns), None)
    
def _last_turn(speaker_turns):
    return next((turn['turn_index'] for turn in speaker_turns[::-1]), None)


    # === VOICE ONLY ====
    
def _talk_rate(speaker, duration, all_turns, tgbs, wgbs):
    pause_time=0
    talk_rate=0
    for index,turn in enumerate(all_turns):
        if speaker == turn[SOURCE]:
            if index == 0:
                pause_time += turn[START_TIME]
            elif (index+1)<len(all_turns):
                pause_time += max(turn[START_TIME] - all_turns[index - 1][END_TIME], 0) # cap minimum at 0 so overtalking doesnt subtract from speaker pause time
            else:
                pause_time += duration - turn[END_TIME]
    
    speaker_total_words = len(wgbs[speaker])
    speaker_total_time = sum([turn[END_TIME] - turn[START_TIME] for turn in tgbs[speaker]])
    talk_rate = speaker_total_words / ((speaker_total_time + pause_time)/60) if speaker_total_time > 0 else 0
    return talk_rate

def _longest_turn_secs(speaker_turns):
    # longest_turn_secs - Voice
    longest=0
    for turn in speaker_turns:
        if (turn[END_TIME] - turn[START_TIME]) > longest:
            longest = turn[END_TIME] - turn[START_TIME]
    return longest

def _average_turn_secs(speaker_turns):
    # average_turn_secs - Voice
    speaker_talk_duration = [turn[END_TIME] - turn[START_TIME] for turn in speaker_turns]
    average = sum(speaker_talk_duration)/len(speaker_turns)
    return average

def _overtalk_incidents(speaker, all_turns):
    # overtalk - Voice
    incidents=[]
    for i in range(1, len(all_turns)):
        if speaker == all_turns[i][SOURCE] and all_turns[i][START_TIME] < all_turns[i-1][END_TIME]:
            incident = {
                TURN_INDEX: all_turns[i][TURN_INDEX],
                'underparty': all_turns[i-1][SOURCE],
                START_TIME: all_turns[i][START_TIME],
                END_TIME: min(all_turns[i-1][END_TIME], all_turns[i][END_TIME])
            }
            incidents.append(incident)
    return incidents
            
def _overtalk_count(overtalk_incidents):
    return len(overtalk_incidents)

def _talk_pct(duration, speaker_turns):
    # talk_pct - Voice
    return sum([turn[END_TIME]-turn[START_TIME] for turn in speaker_turns]) / duration * 100

    # ========== GLOBAL METRICS ==========
    
    # === GENERIC ====
    
def _global_total_turns(all_turns):
    # total_turns - Voice/Chat
    return len(all_turns) if all_turns else 0
    
def _global_vocab(wgbs):
    # GLOBAL vocab - Voice/Chat
    return len(set(list(map(lambda w: ''.join(filter(str.isalnum, w)).lower(), chain(*wgbs.values())))))

def _global_longest_turn_words(all_turns):
    # GLOBAL longest_turn_words - Voice/Chat
    return max([len(turn[WORDS_ARR] if WORDS_ARR in turn else [word for word in turn[TURN_TEXT].split() if word]) for turn in all_turns]) if all_turns else 0

def _global_average_turn_words(all_turns):
    # GLOBAL average_turn_words - Voice/Chat
    return sum([len(turn[WORDS_ARR] if WORDS_ARR in turn else [word for word in turn[TURN_TEXT].split() if word]) for turn in all_turns])/len(all_turns) if all_turns else 0

    # === VOICE ONLY ====
    
def _global_longest_turn_secs(all_turns):
    # GLOBAL longest_turn_secs - Voice
    longest=0
    for turn in all_turns:
        if (turn[END_TIME] - turn[START_TIME]) > longest:
            longest = turn[END_TIME] - turn[START_TIME]
    return longest

def _global_average_turn_secs(all_turns):
    # GLOBAL average_turn_secs - Voice
    turns_total_talk_duration = [turn[END_TIME] - turn[START_TIME] for turn in all_turns]
    return sum(turns_total_talk_duration)/len(all_turns) if all_turns else 0

def _global_silence_pct(metrics_by_person):
    # GLOBAL silence_pct - Voice
    return 100 - sum([speaker['talk_pct'] for speaker in metrics_by_person.values()])

