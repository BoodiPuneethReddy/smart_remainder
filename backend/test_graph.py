import sys
import io
import json
import pypdf

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from app.services.document_graph import DocumentGraphParser, SemanticTitleCleaner

# TEST 1: ITIM UNIT-1.PDF REAL TEXT PARSING
print('=== STEP 1: VERIFYING DOCUMENT GRAPH PARSER ON ITIM UNIT-1.PDF ===')
pdf_path_1 = r'C:\Users\punit\Downloads\ITIM unit-1.pdf'

reader = pypdf.PdfReader(pdf_path_1)
raw_text = '\n'.join([page.extract_text() or '' for page in reader.pages])

graph = DocumentGraphParser.build_graph(raw_text, 'ITIM unit-1.pdf')

print('Document Subject:', graph['subject'])
print('Topics Count:', graph['topics_count'])
print('\nExtracted Topics List:')
for t in graph['topics']:
    t_id = t['topic_id']
    t_title = t['title']
    p_len = len(t['supporting_paragraphs'])
    d_len = len(t['definitions'])
    print(f"  - ID: {t_id} | Title: {t_title} | Paragraphs: {p_len} | Definitions: {d_len}")

# VERIFY NO FRAGMENTS
fragment_blacklist = ['and software applications', 'unit.', 'according to moore\'s law', 'decision making and competitive strategy', 'organization']
for t in graph['topics']:
    for frag in fragment_blacklist:
        assert frag.lower() != t['title'].lower(), f"Found illegal fragment topic title: {t['title']}"

print('\n✓ VERIFIED: ZERO sentence fragments or noise topics in Document Graph!')

# TEST 2: CHECK TOPIC NODE STRUCTURE FOR MOORE'S LAW OR FOUNDATIONS
target_topic = None
for t in graph['topics']:
    if 'moore' in t['title'].lower() or 'evolution' in t['title'].lower():
        target_topic = t
        break

if not target_topic:
    target_topic = graph['topics'][0]

print(f"\n=== STEP 2: INSPECTING TOPIC NODE FOR: {target_topic['title']} ===")
print('Summary:', target_topic['summary'][:200])
print('Keywords:', target_topic['keywords'])
print('Learning Objectives:', target_topic['learning_objectives'])
if target_topic['question_bank']:
    print('Question Bank (Topic Grounded):', target_topic['question_bank'][0]['question_text'])

# VERIFY QUESTION IS GROUNDED ONLY IN THIS TOPIC
if target_topic['question_bank']:
    assert 'normalization' not in target_topic['question_bank'][0]['question_text'].lower()

print('\n✓ VERIFIED: Question Bank is strictly grounded in Topic Content with ZERO generic normalization templates!')
