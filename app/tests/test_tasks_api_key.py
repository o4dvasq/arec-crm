"""
test_tasks_api_key.py — Tests for task API enforcement and grouping functions.

Covers:
- POST /crm/api/tasks returns 400 when org, owner, or text is missing
- get_tasks_grouped_by_prospect() and get_tasks_grouped_by_owner() from crm_reader
"""

import os
import sys
import json
import pytest
from unittest.mock import patch

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from flask import Flask
from delivery.crm_blueprint import crm_bp
from sources.crm_reader import get_tasks_grouped_by_prospect, get_tasks_grouped_by_owner


# ---------------------------------------------------------------------------
# Flask test client fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app = Flask(
        __name__,
        template_folder=os.path.join(_APP_DIR, 'templates'),
        static_folder=os.path.join(_APP_DIR, 'static'),
    )
    app.config['TESTING'] = True
    app.register_blueprint(crm_bp)

    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# POST /crm/api/tasks — missing field enforcement
# ---------------------------------------------------------------------------

class TestTaskCreateEnforcement:
    def test_missing_org_returns_400(self, client):
        resp = client.post(
            '/crm/api/tasks',
            json={'text': 'Do something', 'owner': 'Oscar'},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['ok'] is False
        assert 'org' in data['error']

    def test_missing_owner_returns_400(self, client):
        resp = client.post(
            '/crm/api/tasks',
            json={'org': 'Test Org', 'text': 'Do something'},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['ok'] is False
        assert 'owner' in data['error']

    def test_missing_text_returns_400(self, client):
        resp = client.post(
            '/crm/api/tasks',
            json={'org': 'Test Org', 'owner': 'Oscar'},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['ok'] is False

    def test_empty_org_returns_400(self, client):
        resp = client.post(
            '/crm/api/tasks',
            json={'org': '', 'text': 'Do something', 'owner': 'Oscar'},
        )
        assert resp.status_code == 400

    def test_empty_owner_returns_400(self, client):
        resp = client.post(
            '/crm/api/tasks',
            json={'org': 'Test Org', 'text': 'Do something', 'owner': ''},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# get_tasks_grouped_by_prospect
# ---------------------------------------------------------------------------

MOCK_TASKS = [
    {'org': 'Alpha Fund', 'text': 'Send deck', 'owner': 'Oscar Vasquez',
     'priority': 'Hi', 'status': 'open', 'section': 'IR', 'raw_line': ''},
    {'org': 'Alpha Fund', 'text': 'Schedule call', 'owner': 'Tony Avila',
     'priority': 'Med', 'status': 'open', 'section': 'IR', 'raw_line': ''},
    {'org': 'Beta Capital', 'text': 'Follow up', 'owner': 'Oscar Vasquez',
     'priority': 'Lo', 'status': 'open', 'section': 'IR', 'raw_line': ''},
    # done task — should be excluded
    {'org': 'Alpha Fund', 'text': 'Done task', 'owner': 'Oscar Vasquez',
     'priority': 'Hi', 'status': 'done', 'section': 'IR', 'raw_line': ''},
    # task without owner — should be excluded
    {'org': 'Beta Capital', 'text': 'No owner task', 'owner': '',
     'priority': 'Med', 'status': 'open', 'section': 'IR', 'raw_line': ''},
]

MOCK_PROSPECTS = [
    {'org': 'Alpha Fund', 'Target': '$200M', 'offering': 'Fund II'},
    {'org': 'Beta Capital', 'Target': '$500M', 'offering': 'Fund II'},
]


class TestGetTasksGroupedByProspect:
    def test_groups_by_org(self):
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_prospect()
        orgs = [g['org'] for g in groups]
        assert 'Alpha Fund' in orgs
        assert 'Beta Capital' in orgs

    def test_sorted_by_target_descending(self):
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_prospect()
        # Beta Capital ($500M) should come before Alpha Fund ($200M)
        assert groups[0]['org'] == 'Beta Capital'
        assert groups[1]['org'] == 'Alpha Fund'

    def test_excludes_done_tasks(self):
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_prospect()
        alpha = next(g for g in groups if g['org'] == 'Alpha Fund')
        texts = [t['text'] for t in alpha['tasks']]
        assert 'Done task' not in texts

    def test_excludes_tasks_without_owner(self):
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_prospect()
        beta = next(g for g in groups if g['org'] == 'Beta Capital')
        texts = [t['text'] for t in beta['tasks']]
        assert 'No owner task' not in texts

    def test_tasks_sorted_hi_before_med(self):
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_prospect()
        alpha = next(g for g in groups if g['org'] == 'Alpha Fund')
        priorities = [t['priority'] for t in alpha['tasks']]
        assert priorities.index('Hi') < priorities.index('Med')

    def test_priority_normalized(self):
        tasks = [
            {'org': 'Alpha Fund', 'text': 'task1', 'owner': 'Oscar',
             'priority': 'high', 'status': 'open', 'section': 'IR', 'raw_line': ''},
            {'org': 'Alpha Fund', 'text': 'task2', 'owner': 'Oscar',
             'priority': 'normal', 'status': 'open', 'section': 'IR', 'raw_line': ''},
        ]
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=tasks), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_prospect()
        alpha = next(g for g in groups if g['org'] == 'Alpha Fund')
        priorities = {t['priority'] for t in alpha['tasks']}
        assert 'Hi' in priorities
        assert 'Med' in priorities
        assert 'high' not in priorities
        assert 'normal' not in priorities


# ---------------------------------------------------------------------------
# get_tasks_grouped_by_owner
# ---------------------------------------------------------------------------

class TestGetTasksGroupedByOwner:
    def test_groups_by_owner(self):
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_owner()
        owners = [g['owner'] for g in groups]
        assert 'Oscar Vasquez' in owners
        assert 'Tony Avila' in owners

    def test_sorted_by_max_target_descending(self):
        # Oscar has tasks for Alpha ($200M) and Beta ($500M) → max $500M
        # Tony only has Alpha ($200M) → max $200M
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_owner()
        oscar = next(g for g in groups if g['owner'] == 'Oscar Vasquez')
        tony = next(g for g in groups if g['owner'] == 'Tony Avila')
        assert oscar['max_target'] > tony['max_target']
        assert groups.index(oscar) < groups.index(tony)

    def test_excludes_done_tasks(self):
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_owner()
        oscar = next(g for g in groups if g['owner'] == 'Oscar Vasquez')
        texts = [t['text'] for t in oscar['tasks']]
        assert 'Done task' not in texts

    def test_tasks_contain_org_for_subtitle(self):
        with patch('sources.crm_reader.get_all_prospect_tasks', return_value=MOCK_TASKS), \
             patch('sources.crm_reader.load_prospects', return_value=MOCK_PROSPECTS):
            groups = get_tasks_grouped_by_owner()
        oscar = next(g for g in groups if g['owner'] == 'Oscar Vasquez')
        orgs = {t['org'] for t in oscar['tasks']}
        assert 'Alpha Fund' in orgs or 'Beta Capital' in orgs
