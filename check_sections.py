import os

filepath = r'E:\rskmn\Npersonal\projects\yr4\final\physics-guided-orbit-discovery-prototype\docs\development\PHASE_1_STEP_4_5_1_COMPARE_ASSESSMENT.md'

# Read file
with open(filepath, 'r', encoding='utf-16') as f:
    content = f.read()

# Check for section markers various ways
print('=== Section Detection ===')
terms = [
    '1. Inspect Existing Functionality',
    '2. Understand the Scientific Data',
    '3. Define Comparison Functionality',
    '4. CLI Interface Proposal',
    '5. Architecture and Implementation Plan',
    '6. Testing Strategy',
    '6. Unresolved Questions',
    'C4.5.1',
    'PHASE_1_STEP_4_5_1',
]

for term in terms:
    # Check exact match
    idx = content.find(term)
    print('Term \"' + term + '\" found at index ' + str(idx))

# Also print first 200 chars to see formatting
print()
print('First 200 chars:')
print(content[:200])
"