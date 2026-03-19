import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from SQLText import SQLText
import re

sql_text = SQLText()

pattern = r"\((.*?)\)"  # Pattern to capture content inside brackets
matches = re.findall(pattern, sql_text.sql_keywords)  # Extract matches


# matches = groups in sql_text.sql_keywords
splitted = matches[0].split("|")

for word in splitted:
    print(word)

