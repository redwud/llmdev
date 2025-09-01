import pytest
from authenticator import Authenticator 

username = 'test_username'
password = 'test_password'

@pytest.fixture
def auth():
    _auth = Authenticator() 
    yield _auth
    del _auth

def test_register_ok( auth ):
    auth.register( username, password )
    assert username in auth.users
    assert auth.users[username] == password

def test_register_ng( auth ):
    auth.register( username, password )
    with pytest.raises(ValueError, match="エラー: ユーザーは既に存在します。"):
        auth.register( username, password )

def test_login_ok( auth ):
    auth.register( username, password )
    assert auth.login( username, password ) == "ログイン成功" 

def test_login_ng( auth ):
    auth.register( username, password )
    with pytest.raises(ValueError, match="エラー: ユーザー名またはパスワードが正しくありません。"):
        auth.login(username, password+"wrong") 