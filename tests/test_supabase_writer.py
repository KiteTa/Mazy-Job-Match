from unittest.mock import MagicMock, patch

import pytest

from output.supabase_writer import insert_pipeline_run, upsert_jobs


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://test.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY', 'test-key')
    import output.supabase_writer as sw
    sw._client_instance = None
    yield
    sw._client_instance = None


def _job(**overrides):
    base = {
        'id': 'abc123',
        'source': 'greenhouse',
        'title': 'Software Engineer',
        'company': 'Acme',
        'locations': ['San Francisco, CA'],
        'url': 'https://example.com/job/1',
        'apply_url': 'https://example.com/apply/1',
        'description_text': 'Some description',
        'published_at': '2026-06-16T10:00:00Z',
        'active': True,
    }
    return {**base, **overrides}


@patch('output.supabase_writer.create_client')
def test_upsert_jobs_builds_records(mock_create):
    mock_client = MagicMock()
    mock_create.return_value = mock_client

    upsert_jobs([_job(), _job(id='def456', company='Beta')])

    mock_client.table.assert_called_once_with('jobs')
    call_args = mock_client.table.return_value.upsert.call_args
    records = call_args[0][0]
    assert len(records) == 2
    assert records[0]['id'] == 'abc123'
    assert records[1]['id'] == 'def456'
    assert call_args[1]['on_conflict'] == 'company,title'


@patch('output.supabase_writer.create_client')
def test_upsert_jobs_noop_when_empty(mock_create):
    upsert_jobs([])
    mock_create.assert_not_called()


@patch('output.supabase_writer.create_client')
def test_upsert_jobs_defaults_locations_to_empty_list(mock_create):
    mock_client = MagicMock()
    mock_create.return_value = mock_client

    upsert_jobs([_job(locations=None)])

    records = mock_client.table.return_value.upsert.call_args[0][0]
    assert records[0]['locations'] == []


@patch('output.supabase_writer.create_client')
def test_insert_pipeline_run_sends_correct_row(mock_create):
    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value.data = [{'id': 'test-uuid'}]
    mock_create.return_value = mock_client

    run_id = insert_pipeline_run(
        '2026-06-16',
        {'total_scraped': 50, 'after_filters': 12},
        {'after_active': 48, 'after_seniority_tech': 12},
    )

    mock_client.table.assert_called_once_with('pipeline_runs')
    row = mock_client.table.return_value.insert.call_args[0][0]
    assert row['run_date'] == '2026-06-16'
    assert row['total_scraped'] == 50
    assert row['after_filters'] == 12
    assert row['filter_breakdown'] == {'after_active': 48, 'after_seniority_tech': 12}
    assert 'run_timestamp' in row
    assert run_id == 'test-uuid'


