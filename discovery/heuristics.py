"""Offline, rule-based analysis of customer interviews.

Works without an API key. The rules come from customer-discovery practice
(e.g. "The Mom Test"): past behaviour is evidence, opinions and predictions
about the future are not, and compliments are noise.
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

INTERVIEWER_TAGS = ("interviewer", "q", "me", "us")

# --- Question quality (for the interviewer's lines) -------------------------

QUESTION_RULES: List[Tuple[str, str, str]] = [
    (r"\b(wouldn'?t|don'?t|isn'?t|aren'?t) you (think|agree|say|want|love)\b",
     "Leading question",
     "It suggests the answer you want. Ask what they actually did instead."),
    (r"\b(would|will) you (use|pay|buy|try|switch|sign up)\b",
     "Hypothetical future",
     "People are bad at predicting their own behaviour. Ask: 'When did you last deal with this? What did you do?'"),
    (r"\bif (we|i|you) (built|build|made|make|had)\b",
     "Hypothetical future",
     "Asks them to imagine your solution. Ask about the problem as it exists today."),
    (r"\b(our|my) (app|product|idea|solution|platform|startup|tool)\b",
     "Pitching",
     "Talking about your solution biases the conversation. Keep the focus on their life."),
    (r"\b(do you like|what do you think of|how much would you pay)\b",
     "Opinion-seeking",
     "Opinions are cheap. Ask what they currently spend (time or money) on this problem."),
]

GOOD_QUESTION_HINTS = re.compile(
    r"\b(last time|walk me through|tell me about|how do you currently|what did you|"
    r"how often|what have you tried|why was that hard|what happened)\b", re.I)


@dataclass
class QuestionFlag:
    question: str
    issue: str
    advice: str


def review_questions(questions: List[str]) -> Tuple[List[QuestionFlag], List[str]]:
    """Return (flagged questions, strong questions)."""
    flags, strong = [], []
    for q in questions:
        hit = False
        for pattern, issue, advice in QUESTION_RULES:
            if re.search(pattern, q, re.I):
                flags.append(QuestionFlag(q, issue, advice))
                hit = True
                break
        if not hit and GOOD_QUESTION_HINTS.search(q):
            strong.append(q)
    return flags, strong


# --- Statement classification (for the customer's lines) -------------------

EVIDENCE = re.compile(
    r"\b(last (week|month|year|time)|yesterday|i (spent|tried|used|paid|bought|switched|"
    r"built|made|lost|missed|called|asked|had to|ended up|gave up|sent|got|joined|went|took|"
    r"found|told|wrote|ran|never)|i \w+ed|we (spent|tried|use|used|paid|pay|bought)|i use|"
    r"every (day|week|month)|\w+ ago)\b|\$\s?\d|\b\d+\b", re.I)
OPINION = re.compile(
    r"\b(i would|i'd (probably|definitely|maybe|love|use|pay)|i might|i think|maybe|"
    r"probably|i guess|i'd love|would be (nice|cool|great)|i will|i'll (definitely|"
    r"probably))\b", re.I)
COMPLIMENT = re.compile(
    r"\b(great idea|love (it|this|that)|sounds (great|cool|awesome|amazing)|"
    r"that'?s (cool|awesome|amazing|smart)|good luck)\b", re.I)
PAIN = re.compile(
    r"\b(frustrat\w*|annoy\w*|hate|waste\w*|struggl\w*|hard|difficult|pain|stress\w*|"
    r"confus\w*|nightmare|overwhelm\w*|tedious|forgot|missed|lost|expensive|too long|"
    r"takes forever|give up|gave up)\b", re.I)

LABEL_EVIDENCE = "Evidence (past behaviour)"
LABEL_OPINION = "Opinion / prediction"
LABEL_COMPLIMENT = "Compliment (ignore)"
LABEL_CONTEXT = "Context"


def classify_statement(text: str) -> str:
    if COMPLIMENT.search(text):
        return LABEL_COMPLIMENT
    if EVIDENCE.search(text):
        return LABEL_EVIDENCE
    if OPINION.search(text):
        return LABEL_OPINION
    return LABEL_CONTEXT


# --- Transcript parsing ----------------------------------------------------

@dataclass
class Turn:
    speaker: str
    text: str
    is_interviewer: bool


@dataclass
class InterviewAnalysis:
    name: str
    turns: List[Turn]
    question_flags: List[QuestionFlag] = field(default_factory=list)
    strong_questions: List[str] = field(default_factory=list)
    statements: List[Tuple[str, str]] = field(default_factory=list)  # (label, text)
    pains: List[str] = field(default_factory=list)

    @property
    def label_counts(self) -> Dict[str, int]:
        return dict(Counter(label for label, _ in self.statements))

    @property
    def evidence_ratio(self) -> float:
        if not self.statements:
            return 0.0
        n = sum(1 for label, _ in self.statements if label == LABEL_EVIDENCE)
        return n / len(self.statements)


LINE = re.compile(r"^\s*([A-Za-z][\w .'-]{0,30}?)\s*:\s*(.+)$")


def parse_transcript(raw: str) -> List[Turn]:
    """Parse 'Speaker: text' lines. Lines without a speaker continue the last turn."""
    turns: List[Turn] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        m = LINE.match(line)
        if m:
            speaker = m.group(1).strip()
            turns.append(Turn(speaker, m.group(2).strip(),
                              speaker.lower() in INTERVIEWER_TAGS))
        elif turns:
            turns[-1].text += " " + line.strip()
    return turns


def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 3]


def analyze_interview(name: str, raw: str) -> InterviewAnalysis:
    turns = parse_transcript(raw)
    result = InterviewAnalysis(name=name, turns=turns)
    questions = [t.text for t in turns if t.is_interviewer]
    result.question_flags, result.strong_questions = review_questions(questions)
    for t in turns:
        if t.is_interviewer:
            continue
        for sentence in split_sentences(t.text):
            result.statements.append((classify_statement(sentence), sentence))
            if PAIN.search(sentence):
                result.pains.append(sentence)
    return result


# --- Cross-interview themes ------------------------------------------------

STOPWORDS = set("""a an the and or but if so to of in on at for with from by is are was were
be been am i me my we our you your it its this that they them their he she his her
just really very like do did does have has had not no yes yeah um uh can could
would should will about then than there what when where which who how all any some
one get got go going thing things lot kind sort know mean think also because even
it's i'm i'd don't that's didn't half most much many probably maybe honestly sure
last month week year already never ever time times
""".split())


def themes(analyses: List[InterviewAnalysis], top_n: int = 8) -> List[Tuple[str, int, List[str]]]:
    """Words customers use in more than one interview, ranked by how many interviews."""
    mentions: Dict[str, set] = {}
    for a in analyses:
        words = set()
        for _, sentence in a.statements:
            for w in re.findall(r"[a-z']{4,}", sentence.lower()):
                if w not in STOPWORDS:
                    words.add(w)
        for w in words:
            mentions.setdefault(w, set()).add(a.name)
    ranked = sorted(mentions.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    return [(w, len(names), sorted(names)) for w, names in ranked[:top_n] if len(names) > 1]


def coaching_prompts(analyses: List[InterviewAnalysis]) -> List[str]:
    """Questions a coach would ask the team after reading their interviews."""
    out: List[str] = []
    if not analyses:
        return out
    avg = sum(a.evidence_ratio for a in analyses) / len(analyses)
    if avg < 0.35:
        out.append("Most of what you heard is opinion, not behaviour. What did these people "
                   "actually *do* the last time the problem happened?")
    compliments = sum(a.label_counts.get(LABEL_COMPLIMENT, 0) for a in analyses)
    if compliments:
        out.append(f"You collected {compliments} compliment(s). Did anyone commit time, money "
                   "or a referral? If not, treat the compliments as zero evidence.")
    flagged = sum(len(a.question_flags) for a in analyses)
    if flagged:
        out.append(f"{flagged} of your questions were leading, hypothetical or pitching. "
                   "Rewrite them before the next round of interviews.")
    no_pain = [a.name for a in analyses if not a.pains]
    if no_pain:
        out.append("No clear pain showed up in: " + ", ".join(no_pain) +
                   ". Are these people really in your target segment?")
    if len(analyses) < 5:
        out.append(f"You have {len(analyses)} interview(s). Patterns usually start to show "
                   "around 5-10 per segment. Who are the next people to talk to?")
    out.append("Which single assumption, if wrong, would kill this venture? What is the "
               "cheapest test you could run this week to check it?")
    return out


def demo_summary(analyses: List[InterviewAnalysis]) -> Optional[str]:
    if not analyses:
        return None
    total = sum(len(a.statements) for a in analyses)
    ev = sum(a.label_counts.get(LABEL_EVIDENCE, 0) for a in analyses)
    return (f"{len(analyses)} interviews, {total} customer statements, "
            f"{ev} backed by past behaviour ({(ev / total * 100) if total else 0:.0f}%).")
