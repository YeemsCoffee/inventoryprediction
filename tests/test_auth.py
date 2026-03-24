"""Tests for authentication and role-based access."""


class TestLogin:
    def test_login_page_loads(self, client):
        response = client.get('/auth/login')
        assert response.status_code == 200

    def test_login_valid_admin(self, client, admin_user):
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'admin123',
        }, follow_redirects=True)
        assert response.status_code == 200

    def test_login_invalid_password(self, client, admin_user):
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'wrong',
        }, follow_redirects=True)
        assert b'Invalid email or password' in response.data

    def test_redirect_unauthenticated(self, client):
        response = client.get('/')
        assert response.status_code == 302


class TestPermissions:
    def _login(self, client, email, password):
        return client.post('/auth/login', data={
            'email': email,
            'password': password,
        }, follow_redirects=True)

    def test_warehouse_cannot_access_admin(self, client, warehouse_user):
        self._login(client, 'warehouse@test.com', 'warehouse123')
        response = client.get('/admin/stores')
        assert response.status_code == 403

    def test_admin_can_access_admin(self, client, admin_user):
        self._login(client, 'admin@test.com', 'admin123')
        response = client.get('/admin/stores')
        assert response.status_code == 200
