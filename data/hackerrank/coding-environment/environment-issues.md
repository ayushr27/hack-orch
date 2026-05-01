# Coding Environment Troubleshooting

## The IDE froze during my test

If the IDE freezes:
1. Do NOT close the tab — this may consume one of your remaining attempt slots.
2. Wait 30 seconds for the IDE to recover.
3. If still frozen, hard-refresh (Ctrl+Shift+R / Cmd+Shift+R) — your saved code is preserved.
4. If you lose progress, contact the recruiting company (not HackerRank) to explain the situation.

## I accidentally closed the tab

Your code is auto-saved every 30 seconds. Reopen the assessment link from your email — your progress will be restored if you saved before closing.

## The timer kept running when I had connection issues

The timer runs server-side. Connectivity issues on your end do not pause the timer. If you had verifiable network outages (ISP records, screenshots), document them and contact the recruiting company for a manual review. HackerRank support cannot adjust timer records.

## My output looks correct but the test case still fails

Possible causes:
- Trailing spaces or extra newlines in your output. Use `.strip()` in Python.
- Integer vs float formatting differences. If the problem says "print an integer", don't print 4.0.
- Case sensitivity in string outputs. Match expected output exactly.
- Encoding issues with special characters — stick to ASCII unless the problem specifies otherwise.

## Code compiled locally but gives compile error on HackerRank

HackerRank uses fixed language versions. Your local compiler may be newer. Check:
- Java: HackerRank uses Java 8, 11, or 17 depending on challenge. Avoid newer-version-only features.
- C++: Use C++14 or C++17 features only.
- Python: Confirm the challenge uses Python 3, not Python 2.
