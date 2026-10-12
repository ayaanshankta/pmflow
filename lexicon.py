"""ML lexicon (research/ml-rules.md section A): backtest-rules lexicon + ONE pre-registered extension for business/crypto headlines.
Committed BEFORE any label is computed. Do not edit after labelling; a change = new dated amendment at the bottom of research/ml-result.md.
Topics = backtest_truth.TOPICS (10 topics + 11 people) plus EXTRA below. Matching is letter-boundary, case-insensitive (backtest_truth.rx)."""
import re
from backtest_truth import TOPICS as BASE, rx, clean   # noqa: F401  (clean re-exported for ml_dataset)

EXTRA = {   # topic -> (headline terms, market-slug terms)
 "crypto": (["bitcoin","btc","ethereum","ether","crypto","cryptocurrency","solana","xrp","dogecoin","binance","coinbase"],
            ["bitcoin","btc","ethereum","eth","crypto","solana","xrp","dogecoin","doge"]),
 "inflation": (["cpi","inflation","ppi","pce"], ["cpi","inflation","ppi","pce"]),
 "jobs": (["jobs report","nonfarm","payrolls?","unemployment","jobless"], ["jobs","unemployment","nonfarm","payrolls","jobless"]),
 "recession_gdp": (["recession","gdp"], ["recession","gdp"]),
 "oil": (["oil","crude","opec"], ["oil","crude","opec"]),
 "gold_silver": (["gold","silver"], ["gold","silver"]),
 "election": (["election","elections"], ["election","elections"]),
 "central_banks": (["ecb","boj","bank of japan","bank of england","boe"], ["ecb","boj","boe"]),
 "mideast": (["israel","israeli","gaza","hamas","hezbollah","syria"], ["israel","gaza","hamas","hezbollah","syria"]),
 "korea": (["north korea","south korea","kim jong"], ["korea","kim"]),
 "etf": (["etf","etfs"], ["etf"]),
 "tech_cos": (["tesla","nvidia","apple","microsoft","google","alphabet","amazon","meta","openai","anthropic","deepseek","microstrategy"],
              ["tesla","nvidia","apple","microsoft","google","alphabet","amazon","meta","openai","anthropic","deepseek","microstrategy"]),
}
ALL = {**BASE, **EXTRA}
POST_RX = {k: rx(v[0]) for k, v in ALL.items()}
SLUG_RX = {k: rx([re.escape(t) for t in v[1]]) for k, v in ALL.items()}
SLUG_ANY = re.compile("|".join(f"(?:{r.pattern})" for r in SLUG_RX.values()), re.I)
# short-horizon coin-flip markets (5m/15m/hourly "up or down"): resolve within minutes, pinned/noise, would dominate the fills
SLUG_EXCLUDE = re.compile(r"up-?or-?down|updown", re.I)
def topics_of(text): return [k for k, r in POST_RX.items() if r.search(text)]
def slug_ok(slug): return bool(SLUG_ANY.search(slug)) and not SLUG_EXCLUDE.search(slug)

# crude headline polarity for the baseline direction rule (sign of pos - neg word count; 0 = no call)
POS = rx(["surge[sd]?","rall(?:y|ies|ied)","jump(?:s|ed)?","rise[sn]?","rose","soar(?:s|ed)?","gain(?:s|ed)?","beat(?:s)?","record","approv(?:e|es|ed|al)","deal","agree[sd]?","ceasefire","cease-fire","upgrade[sd]?","hike[sd]?","strong(?:er)?","boost(?:s|ed)?","win(?:s)?"])
NEG = rx(["plunge[sd]?","fall(?:s|en)?","fell","drop(?:s|ped)?","miss(?:es|ed)?","crash(?:es|ed)?","cut(?:s)?","ban(?:s|ned)?","war","strike[sd]?","attack(?:s|ed)?","reject(?:s|ed)?","sanction(?:s|ed)?","downgrade[sd]?","weak(?:er)?","slump(?:s|ed)?","tumble[sd]?","lose[sd]?","loss(?:es)?","threat(?:en|ens|ened)?"])
def polarity(text): return int(len(POS.findall(text)) > len(NEG.findall(text))) - int(len(NEG.findall(text)) > len(POS.findall(text)))
