from universe import is_sports
S = [  # (tags, question, expected)
    ([], "Will the Lakers win the NBA Finals?", True),
    (["Sports", "nba"], "Will LeBron score 30?", True),
    ([], "Will Tottenham win the Premier League?", True),
    ([], "Will Max Verstappen win the F1 championship?", True),
    ([], "Will Man City win the Champions League?", True),
    (["Soccer"], "Who wins?", True),
    ([], "Will Navi win the CS2 major?", True),
    ([], "Will Donald Trump win the 2028 election?", False),
    ([], "Will the Fed cut rates in December?", False),
    (["Politics", "Elections"], "Will Emma Smith be governor of Tennessee?", False),
    (["Crypto"], "Will Bitcoin hit $150k in October?", False),
    ([], "Will OpenAI release GPT-6 before 2027?", False),
]
for tags, q, exp in S:
    assert is_sports(tags, q) == exp, (tags, q, exp)
assert is_sports([], "x", "", "nfl-super-bowl-winner")  # slug hyphens split
print("ok", len(S) + 1)
