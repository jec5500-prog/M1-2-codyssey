def test_configuration_errors_do_not_expose_internal_details(client,monkeypatch):
    from routers import data
    def unavailable():raise RuntimeError('private credential context must stay internal')
    monkeypatch.setattr(data,'get_db',unavailable)
    response=client.get('/api/data')
    assert response.status_code==503
    assert 'private credential' not in response.text


def test_database_errors_do_not_expose_provider_details(client,monkeypatch):
    from routers import data
    from google.api_core.exceptions import ServiceUnavailable
    def unavailable():raise ServiceUnavailable('private database context must stay internal')
    monkeypatch.setattr(data,'get_db',unavailable)
    response=client.get('/api/data')
    assert response.status_code==503
    assert 'private database' not in response.text
