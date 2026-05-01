# Test Cases and Scoring

## How Test Cases Work

Each coding challenge has a set of test cases. Your code is compiled and run against each one.

### Visible vs Hidden Test Cases
- **Sample test cases** are visible before you start and help you understand expected input/output format.
- **Hidden test cases** are revealed only after submission and test edge cases and performance.

### Scoring
- Each test case is worth equal points unless the problem states otherwise.
- Partial credit is given for passing some test cases.
- Score = (passed test cases / total test cases) * problem points.

## Common Issues

### "Wrong Answer"
Your solution produces incorrect output for at least one test case. Debug by:
1. Re-reading the problem constraints carefully.
2. Testing with the sample inputs manually.
3. Checking for off-by-one errors or edge cases (empty input, single element, large N).

### "Time Limit Exceeded"
Your solution is too slow. Fix by:
1. Reviewing your algorithm complexity (aim for O(n log n) or better for large inputs).
2. Avoiding repeated work — use memoization or dynamic programming.
3. Using efficient I/O (avoid repeated print statements in Python; use sys.stdout.write).

### "Runtime Error"
Your code crashed. Common causes:
- Array index out of bounds.
- Division by zero.
- Stack overflow from deep recursion (increase recursion limit with sys.setrecursionlimit in Python).
- Null/None dereference.

### "Compilation Error"
Your code has syntax errors. Check:
- Missing semicolons (Java/C++).
- Indentation errors (Python).
- Missing import statements.

## Languages Supported

HackerRank supports 40+ languages including Python 3, Java 11/17, C++17, JavaScript (Node.js), Go, Ruby, Scala, Kotlin, Swift, R, and more.

Each language has a fixed runtime version per challenge. You cannot change the runtime version.
